#!/usr/bin/env python3
"""
SENSEX EXPIRY DAY DIRECTION SCALPER
Detect trend changes: Bearish->Bullish, Bullish->Bearish, Sideways
"""

import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "C:/Users/yashs/Documents/Trading Bot/file1")

try:
    import yfinance as yf
except:
    import subprocess

    subprocess.run([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf

from telegram_notifier import TelegramNotifier


class DirectionDetector:
    def __init__(self):
        self.price_history = []
        self.volume_history = []
        self.time_history = []
        self.max_history = 20

    def add_data(self, price, volume=0):
        """Add price data point"""
        self.price_history.append(price)
        self.volume_history.append(volume)
        self.time_history.append(datetime.now())

        if len(self.price_history) > self.max_history:
            self.price_history.pop(0)
            self.volume_history.pop(0)
            self.time_history.pop(0)

    def calculate_sma(self, period=5):
        """Calculate Simple Moving Average"""
        if len(self.price_history) < period:
            return None
        return sum(self.price_history[-period:]) / period

    def calculate_ema(self, period=5):
        """Calculate Exponential Moving Average"""
        if len(self.price_history) < period:
            return None

        multiplier = 2 / (period + 1)
        ema = self.price_history[0]

        for price in self.price_history[1:]:
            ema = (price - ema) * multiplier + ema

        return ema

    def calculate_momentum(self):
        """Calculate momentum and rate of change"""
        if len(self.price_history) < 3:
            return 0, "SIDEWAYS"

        recent = self.price_history[-3:]
        roc = ((recent[-1] - recent[0]) / recent[0]) * 100

        if roc > 0.2:
            momentum_type = "BULLISH"
        elif roc < -0.2:
            momentum_type = "BEARISH"
        else:
            momentum_type = "SIDEWAYS"

        return roc, momentum_type

    def detect_trend_change(self):
        """Detect if trend is changing"""
        if len(self.price_history) < 5:
            return "WARMING_UP", 0, "SIDEWAYS"

        sma5 = self.calculate_sma(5)
        sma10 = self.calculate_sma(10) if len(self.price_history) >= 10 else sma5

        current_price = self.price_history[-1]
        prev_price = (
            self.price_history[-2] if len(self.price_history) >= 2 else current_price
        )

        roc, momentum_type = self.calculate_momentum()

        change_pct = ((current_price - prev_price) / prev_price) * 100

        if sma5 and sma10:
            if sma5 > sma10 * 1.002:
                trend = "BULLISH"
            elif sma5 < sma10 * 0.998:
                trend = "BEARISH"
            else:
                trend = "SIDEWAYS"
        else:
            if change_pct > 0.1:
                trend = "BULLISH"
            elif change_pct < -0.1:
                trend = "BEARISH"
            else:
                trend = "SIDEWAYS"

        prev_change = (
            ((self.price_history[-2] - self.price_history[-3]) / self.price_history[-3])
            * 100
            if len(self.price_history) >= 3
            else 0
        )

        if prev_change < -0.2 and change_pct > 0.1:
            direction_change = "BEARISH_TO_BULLISH"
            signal = "REVERSAL_UP"
        elif prev_change > 0.2 and change_pct < -0.1:
            direction_change = "BULLISH_TO_BEARISH"
            signal = "REVERSAL_DOWN"
        elif abs(change_pct) < 0.1 and abs(prev_change) < 0.1:
            direction_change = "SIDEWAYS"
            signal = "CONSOLIDATION"
        else:
            direction_change = trend
            signal = "TREND_CONTINUATION"

        return signal, roc, direction_change

    def detect_support_resistance(self):
        """Detect support and resistance levels"""
        if len(self.price_history) < 5:
            return None, None

        high = max(self.price_history)
        low = min(self.price_history)
        current = self.price_history[-1]

        resistance = high - (high - low) * 0.25
        support = low + (high - low) * 0.25

        return support, resistance


class ExpiryDirectionScalper:
    def __init__(self):
        self.telegram = TelegramNotifier()
        self.detector = DirectionDetector()
        self.lot_size = 50
        self.trades_executed = []

    def get_sensex_data(self):
        """Get current Sensex data"""
        try:
            ticker = yf.Ticker("^BSESN")
            info = ticker.info
            price = info.get("regularMarketPrice") or info.get("currentPrice")
            prev = info.get("regularMarketPreviousClose") or price
            change = ((price - prev) / prev) * 100
            return {"price": price, "prev": prev, "change": change}
        except:
            return None

    def calculate_premium(self, strike, option_type, price):
        """Calculate option premium"""
        diff = abs(price - strike)

        if option_type == "CE":
            if strike > price:
                return 15
            else:
                return max(15, diff * 0.05 + 10)
        else:
            if strike < price:
                return 15
            else:
                return max(15, diff * 0.05 + 10)

    def generate_trade_with_direction(self):
        """Generate trade based on current direction"""
        data = self.get_sensex_data()
        if not data:
            print("Could not get Sensex data")
            return None

        price = data["price"]
        change = data["change"]

        self.detector.add_data(price)

        signal, roc, direction = self.detector.detect_trend_change()
        support, resistance = self.detector.detect_support_resistance()

        print(f"\n{'=' * 60}")
        print("SENSEX EXPIRY - DIRECTION DETECTOR")
        print("=" * 60)
        print(f"Price: {price:,.2f} | Change: {change:+.2f}%")
        print(f"Momentum: {roc:+.3f}%")
        print(f"Signal: {signal}")
        print(f"Direction: {direction}")

        if support and resistance:
            print(f"Support: {support:,.2f} | Resistance: {resistance:,.2f}")

        print("=" * 60)

        strike = round(price / 100) * 100

        if "BEARISH_TO_BULLISH" in direction or signal == "REVERSAL_UP":
            action = "BUY CALL"
            option_type = "CE"
            strike = strike + 100
            reason = "REVERSAL: Bearish -> Bullish"
            confidence = 85
        elif "BULLISH_TO_BEARISH" in direction or signal == "REVERSAL_DOWN":
            action = "BUY PUT"
            option_type = "PE"
            strike = strike - 100
            reason = "REVERSAL: Bullish -> Bearish"
            confidence = 85
        elif direction == "SIDEWAYS" or signal == "CONSOLIDATION":
            action = "BUY PUT"
            option_type = "PE"
            strike = strike - 100
            reason = "SIDEWAYS: Preferring PUT for safety"
            confidence = 60
        elif change > 0.5:
            action = "BUY CALL"
            option_type = "CE"
            strike = strike + 100
            reason = "BULLISH: Strong upward momentum"
            confidence = 75
        elif change < -0.5:
            action = "BUY PUT"
            option_type = "PE"
            strike = strike - 100
            reason = "BEARISH: Strong downward momentum"
            confidence = 75
        else:
            action = "BUY PUT"
            option_type = "PE"
            strike = strike - 100
            reason = "NEUTRAL: Defaulting to PUT"
            confidence = 55

        entry = self.calculate_premium(strike, option_type, price)
        sl = entry * 0.70
        target1 = entry * 1.50
        target2 = entry * 1.75
        target3 = entry * 2.00

        trade = {
            "action": action,
            "strike": strike,
            "option_type": option_type,
            "entry": entry,
            "sl": sl,
            "target1": target1,
            "target2": target2,
            "target3": target3,
            "reason": reason,
            "confidence": confidence,
            "signal": signal,
            "direction": direction,
            "price": price,
            "change": change,
        }

        print(f"\n[TRADE DECISION]")
        print(f"Action: {action}")
        print(f"Strike: {strike}")
        print(f"Entry: Rs{entry} | SL: Rs{sl}")
        print(f"Targets: {target1} | {target2} | {target3}")
        print(f"Reason: {reason}")
        print(f"Confidence: {confidence}%")

        return trade, price

    def send_to_telegram(self, trade, price):
        """Send trade to Telegram"""
        msg = f"""
[SENSEX EXPIRY - DIRECTION SCALPER]

Price: {trade["price"]:,.2f} ({trade["change"]:+.2f}%)

--- DIRECTION ANALYSIS ---
Signal: {trade["signal"]}
Direction: {trade["direction"]}
Momentum: {trade["change"]:+.2f}%

--- TRADE ---
Action: {trade["action"]}
Strike: {trade["strike"]}
Expiry: TODAY
Lot Size: 50

Entry: Rs{trade["entry"]}
SL: Rs{trade["sl"]} (-30%)
T1: Rs{trade["target1"]} (+50%)
T2: Rs{trade["target2"]} (+75%)
T3: Rs{trade["target3"]} (+100%)

Reason: {trade["reason"]}
Confidence: {trade["confidence"]}%

--- HOW SIGNAL WORKS ---
1. BEARISH_TO_BULLISH -> BUY CALL (reversal)
2. BULLISH_TO_BEARISH -> BUY PUT (reversal)
3. SIDEWAYS -> BUY PUT (safety)
4. Strong momentum -> Trade in that direction
"""

        self.telegram.send_message(msg)
        print(f"\n[SENT trade to Telegram]")

    def run_live_direction(self, duration_minutes=60):
        """Run live direction detection and trading"""
        print(f"\n[Starting {duration_minutes} min live direction monitoring...]")
        print("[Press Ctrl+C to stop]\n")

        start_time = time.time()
        trade_sent = False
        last_direction = None

        try:
            while time.time() - start_time < duration_minutes * 60:
                data = self.get_sensex_data()
                if not data:
                    time.sleep(10)
                    continue

                price = data["price"]
                change = data["change"]

                self.detector.add_data(price)

                signal, roc, direction = self.detector.detect_trend_change()

                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] "
                    f"Price: {price:,.0f} | Change: {change:+.2f}% | "
                    f"Signal: {signal} | Direction: {direction}"
                )

                if direction != last_direction and not trade_sent:
                    print(
                        f"\n[DIRECTION CHANGE DETECTED: {last_direction} -> {direction}]"
                    )

                    trade, _ = self.generate_trade_with_direction()
                    if trade:
                        self.send_to_telegram(trade, price)
                        trade_sent = True
                        last_direction = direction

                elif not trade_sent:
                    trade, _ = self.generate_trade_with_direction()
                    if trade:
                        self.send_to_telegram(trade, price)
                        trade_sent = True

                time.sleep(30)

        except KeyboardInterrupt:
            print("\n[Stopped by user]")

        print("\n[Monitoring complete]")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--monitor", action="store_true", help="Run live monitoring")
    parser.add_argument("--duration", type=int, default=60, help="Duration in minutes")
    args = parser.parse_args()

    scalper = ExpiryDirectionScalper()

    if args.monitor:
        scalper.run_live_direction(args.duration)
    else:
        trade, price = scalper.generate_trade_with_direction()
        if trade:
            scalper.send_to_telegram(trade, price)
