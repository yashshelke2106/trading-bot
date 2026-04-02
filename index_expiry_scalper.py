#!/usr/bin/env python3
"""
INDEX EXPIRY SCALPER - NIFTY & SENSEX
Detect direction changes, pick entries at bottom, exit on higher targets
"""

import sys
import time
import json
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


INDEXES = {
    "NIFTY": {"symbol": "^NSEI", "lot": 25, "tick": 50},
    "SENSEX": {"symbol": "^BSESN", "lot": 50, "tick": 100},
}


class DirectionDetector:
    def __init__(self, name):
        self.name = name
        self.price_history = []
        self.max_history = 20

    def add_price(self, price):
        self.price_history.append(price)
        if len(self.price_history) > self.max_history:
            self.price_history.pop(0)

    def detect_direction(self, current_price):
        """Detect current direction"""
        if len(self.price_history) < 3:
            return "WARMING_UP", "SIDEWAYS", 0

        prev = self.price_history[-2] if len(self.price_history) >= 2 else current_price
        prev2 = self.price_history[-3] if len(self.price_history) >= 3 else prev

        change_now = ((current_price - prev) / prev) * 100
        change_prev = ((prev - prev2) / prev2) * 100

        if change_now > 0.15:
            direction = "BULLISH"
        elif change_now < -0.15:
            direction = "BEARISH"
        else:
            direction = "SIDEWAYS"

        if change_prev < -0.2 and change_now > 0.1:
            signal = "BEARISH_TO_BULLISH"
        elif change_prev > 0.2 and change_now < -0.1:
            signal = "BULLISH_TO_BEARISH"
        elif abs(change_now) < 0.1 and abs(change_prev) < 0.1:
            signal = "CONSOLIDATION"
        else:
            signal = "TREND_CONTINUATION"

        return signal, direction, change_now


class IndexExpiryScaler:
    def __init__(self):
        self.telegram = TelegramWatcher()
        self.detectors = {name: DirectionDetector(name) for name in INDEXES}
        self.trades_log = []

    def get_index_data(self, symbol):
        """Get index data"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            price = info.get("regularMarketPrice") or info.get("currentPrice")
            prev = info.get("regularMarketPreviousClose") or price
            change = ((price - prev) / prev) * 100
            return {"price": price, "prev": prev, "change": change}
        except:
            return None

    def get_strike(self, price, direction):
        """Calculate ATM strike"""
        idx = INDEXES[direction["symbol"]]["tick"]
        return round(price / idx) * idx

    def get_premium(self, strike, option_type, price):
        """Estimate premium"""
        diff = abs(price - strike)

        if option_type == "CE":
            if strike > price:
                return 15
            return max(15, diff * 0.03 + 15)
        else:
            if strike < price:
                return 15
            return max(15, diff * 0.03 + 15)

    def analyze_index(self, name):
        """Analyze single index"""
        idx = INDEXES[name]
        data = self.get_index_data(idx["symbol"])

        if not data:
            return None

        price = data["price"]
        change = data["change"]

        self.detectors[name].add_price(price)

        signal, direction, momentum = self.detectors[name].detect_direction(price)

        if "REVERSAL_UP" in signal or (direction == "BULLISH" and momentum > 0.3):
            action = "BUY CALL"
            option = "CE"
            strike = self.get_strike(price, {"symbol": name}) + idx["tick"]
            reason = f"REVERSAL UP: {signal}"
            conf = 85
        elif "REVERSAL_DOWN" in signal or (direction == "BEARISH" and momentum < -0.3):
            action = "BUY PUT"
            option = "PE"
            strike = self.get_strike(price, {"symbol": name}) - idx["tick"]
            reason = f"REVERSAL DOWN: {signal}"
            conf = 85
        elif direction == "SIDEWAYS":
            action = "BUY PUT"
            option = "PE"
            strike = self.get_strike(price, {"symbol": name}) - idx["tick"]
            reason = "SIDEWAYS - Safer with PUT"
            conf = 60
        else:
            action = "BUY CALL" if change > 0 else "BUY PUT"
            option = "CE" if change > 0 else "PE"
            strike = self.get_strike(price, {"symbol": name}) + (
                idx["tick"] if change > 0 else -idx["tick"]
            )
            reason = f"MOMENTUM: {direction}"
            conf = 70

        entry = self.get_premium(strike, option, price)
        sl = entry * 0.70
        t1 = entry * 1.50
        t2 = entry * 1.75
        t3 = entry * 2.00

        return {
            "name": name,
            "price": price,
            "change": change,
            "signal": signal,
            "direction": direction,
            "momentum": momentum,
            "action": action,
            "option": option,
            "strike": strike,
            "expiry": "TODAY",
            "lot": idx["lot"],
            "entry": entry,
            "sl": sl,
            "t1": t1,
            "t2": t2,
            "t3": t3,
            "value": entry * idx["lot"],
            "reason": reason,
            "conf": conf,
        }

    def analyze_all(self):
        """Analyze both NIFTY and SENSEX"""
        results = {}

        for name in INDEXES:
            result = self.analyze_index(name)
            if result:
                results[name] = result

        return results

    def print_analysis(self, results):
        """Print analysis to console"""
        print(f"\n{'=' * 70}")
        print("INDEX EXPIRY SCALPER - NIFTY & SENSEX")
        print("=" * 70)

        for name, data in results.items():
            print(f"\n{name}:")
            print(f"  Price: {data['price']:,.2f} ({data['change']:+.2f}%)")
            print(f"  Signal: {data['signal']}")
            print(f"  Direction: {data['direction']}")
            print(f"  -> {data['action']} {data['strike']} @ Rs{data['entry']}")
            print(
                f"  SL: Rs{data['sl']} | T1: Rs{data['t1']} | T2: Rs{data['t2']} | T3: Rs{data['t3']}"
            )
            print(f"  Reason: {data['reason']}")

    def send_to_telegram(self, results):
        """Send to Telegram"""
        msg = "[INDEX EXPIRY SCALPER - NIFTY & SENSEX]\n\n"

        for name, data in results.items():
            msg += f"=== {name} ===\n"
            msg += f"Price: {data['price']:,.2f} ({data['change']:+.2f}%)\n"
            msg += f"Signal: {data['signal']}\n"
            msg += f"Direction: {data['direction']}\n\n"

            msg += f"--- TRADE ---\n"
            msg += f"Action: {data['action']}\n"
            msg += f"Strike: {data['strike']}\n"
            msg += f"Expiry: {data['expiry']}\n"
            msg += f"Lot: {data['lot']}\n\n"

            msg += f"Entry: Rs{data['entry']}\n"
            msg += f"SL: Rs{data['sl']} (-30%)\n"
            msg += f"T1: Rs{data['t1']} (+50%)\n"
            msg += f"T2: Rs{data['t2']} (+75%)\n"
            msg += f"T3: Rs{data['t3']} (+100%)\n\n"

            msg += f"Value: Rs{data['value']:,.0f}\n"
            msg += f"Reason: {data['reason']}\n"
            msg += f"Confidence: {data['conf']}%\n\n"

        msg += "--- STRATEGY ---\n"
        msg += "1. Pick entry at bottom (price approaching session low)\n"
        msg += "2. Exit on +50%, +75%, +100% targets\n"
        msg += "3. Stop at -30%\n"
        msg += "4. Monitor direction changes in real-time\n"

        self.telegram.send_message(msg)
        print(f"\n[SENT analysis to Telegram]")

    def run_once(self):
        """Run single analysis"""
        results = self.analyze_all()
        if results:
            self.print_analysis(results)
            self.send_to_telegram(results)
        return results

    def run_live(self, duration_minutes=60):
        """Run live monitoring"""
        print(f"\n[Starting {duration_minutes} min live monitoring...]")
        print("[Press Ctrl+C to stop]\n")

        start = time.time()
        last_direction = {name: "WARMING_UP" for name in INDEXES}

        try:
            while time.time() - start < duration_minutes * 60:
                results = self.analyze_all()

                for name, data in results.items():
                    dir_now = data["direction"]
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] "
                        f"{name}: {data['price']:,.0f} ({data['change']:+.2f}%) | "
                        f"{data['signal']} | {dir_now}"
                    )

                    if dir_now != last_direction[name]:
                        print(f"\n[DIRECTION CHANGE: {name} -> {dir_now}]")
                        self.send_to_telegram({name: data})
                        last_direction[name] = dir_now

                time.sleep(30)

        except KeyboardInterrupt:
            print("\n[Stopped by user]")


class TelegramWatcher:
    def __init__(self):
        try:
            from telegram_notifier import TelegramNotifier

            self.telegram = TelegramNotifier()
            self.is_configured = True
        except:
            self.is_configured = False

    def send_message(self, msg):
        if self.is_configured:
            self.telegram.send_message(msg)
        print(msg)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--monitor", action="store_true", help="Run live monitoring")
    parser.add_argument("--duration", type=int, default=60, help="Duration in minutes")
    parser.add_argument("--nifty", action="store_true", help="Only NIFTY")
    parser.add_argument("--sensex", action="store_true", help="Only SENSEX")
    args = parser.parse_args()

    scalper = IndexExpiryScaler()

    if args.nifty:
        INDEXES = {"NIFTY": INDEXES["NIFTY"]}
    elif args.sensex:
        INDEXES = {"SENSEX": INDEXES["SENSEX"]}

    if args.monitor:
        scalper.run_live(args.duration)
    else:
        scalper.run_once()
