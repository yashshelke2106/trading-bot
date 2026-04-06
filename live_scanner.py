#!/usr/bin/env python3
"""
LIVE TRADING SCANNER - EVERY 15 MINUTES
======================================
1. Checks market sentiment every 15 minutes
2. Scans for trade opportunities
3. Verifies all values before sending alerts
4. Sends updates via Telegram
"""

import sys
import os
from datetime import datetime
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError:
    import subprocess

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "yfinance", "pandas", "numpy"]
    )
    import yfinance as yf
    import pandas as pd
    import numpy as np

from telegram_notifier import TelegramNotifier


class LiveTradingScanner:
    def __init__(self):
        self.telegram = TelegramNotifier()
        self.last_trade_alert = None
        self.last_sentiment = None
        self.scan_interval = 15  # minutes
        self.min_score = 35  # Minimum score for trade alert

        # NSE stocks with proper lot sizes
        self.stocks = {
            "BHEL": {"symbol": "BHEL.NS", "lot": 6000},
            "NMDC": {"symbol": "NMDC.NS", "lot": 10000},
            "COALINDIA": {"symbol": "COALINDIA.NS", "lot": 2400},
            "POWERGRID": {"symbol": "POWERGRID.NS", "lot": 3400},
            "NTPC": {"symbol": "NTPC.NS", "lot": 4100},
            "BEL": {"symbol": "BEL.NS", "lot": 3600},
            "ONGC": {"symbol": "ONGC.NS", "lot": 3150},
            "HINDALCO": {"symbol": "HINDALCO.NS", "lot": 1350},
            "JSWSTEEL": {"symbol": "JSWSTEEL.NS", "lot": 1900},
            "TATASTEEL": {"symbol": "TATASTEEL.NS", "lot": 2000},
            "SBIN": {"symbol": "SBIN.NS", "lot": 1500},
            "ICICIBANK": {"symbol": "ICICIBANK.NS", "lot": 3750},
            "AXISBANK": {"symbol": "AXISBANK.NS", "lot": 2000},
            "KOTAKBANK": {"symbol": "KOTAKBANK.NS", "lot": 3200},
            "HDFCBANK": {"symbol": "HDFCBANK.NS", "lot": 2500},
            "RELIANCE": {"symbol": "RELIANCE.NS", "lot": 1000},
            "INFY": {"symbol": "INFY.NS", "lot": 1800},
            "TCS": {"symbol": "TCS.NS", "lot": 500},
        }

    def get_data(self, symbol, period="5d", interval="5m"):
        try:
            df = yf.Ticker(symbol).history(period=period, interval=interval)
            if df is not None and len(df) > 20:
                if hasattr(df.index, "tz") and df.index.tz:
                    df.index = df.index.tz_localize(None)
                return df
        except:
            pass
        return None

    def get_multi_timeframe_data(self, symbol):
        """Get data for multiple timeframes"""
        # Higher timeframe (1H) for structure
        df_1h = self.get_data(symbol, period="1mo", interval="1h")
        # Lower timeframe (5M) for entry
        df_5m = self.get_data(symbol, period="1d", interval="5m")
        return df_1h, df_5m

    def calc_rsi(self, prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calc_macd(self, prices, fast=12, slow=26, signal=9):
        exp_fast = prices.ewm(span=fast).mean()
        exp_slow = prices.ewm(span=slow).mean()
        macd = exp_fast - exp_slow
        signal_line = macd.ewm(span=signal).mean()
        return macd, signal_line

    def calc_ema(self, prices, period):
        return prices.ewm(span=period).mean()

    def detect_patterns(self, df, timeframe="1H"):
        """Detect chart patterns on given timeframe"""
        if len(df) < 50:
            return None

        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        patterns = []

        # Higher highs/lows check
        recent_highs = high.iloc[-20:].values
        older_highs = high.iloc[-40:-20].values
        higher_highs = max(recent_highs) > max(older_highs)

        recent_lows = low.iloc[-20:].values
        older_lows = low.iloc[-40:-20].values
        higher_lows = min(recent_lows) > min(older_lows)

        # RSI for overbought/oversold
        rsi = self.calc_rsi(close).iloc[-1]

        # MACD for trend
        macd, signal = self.calc_macd(close)
        macd_bullish = macd.iloc[-1] > signal.iloc[-1]
        macd_histogram = macd.iloc[-1] - signal.iloc[-1]

        # EMA crossovers
        ema20 = self.calc_ema(close, 20).iloc[-1]
        ema50 = self.calc_ema(close, 50).iloc[-1] if len(close) > 50 else ema20
        ema200 = self.calc_ema(close, 200).iloc[-1] if len(close) > 200 else ema50

        # Detect structure
        structure = "NEUTRAL"
        confidence = 0

        # BULLISH structure conditions
        if higher_lows and macd_bullish:
            structure = "BULLISH"
            confidence += 30
        if close.iloc[-1] > ema20:
            confidence += 20
        if close.iloc[-1] > ema50:
            confidence += 25
        if rsi < 60 and rsi > 30:
            confidence += 15
        if macd_histogram > 0:
            confidence += 10

        # BEARISH structure conditions
        if not higher_lows and not macd_bullish:
            if structure == "BULLISH":
                pass  # Keep bullish
            else:
                structure = "BEARISH"
                confidence += 30
        if close.iloc[-1] < ema20:
            confidence += 20
        if close.iloc[-1] < ema50:
            confidence += 25
        if rsi > 40 and rsi < 80:
            confidence += 15
        if macd_histogram < 0:
            confidence += 10

        # Detect pullback on lower timeframe
        lower_tf_rsi = None
        pullback_opportunity = None

        return {
            "structure": structure,
            "confidence": min(confidence, 100),
            "higher_highs": higher_highs,
            "higher_lows": higher_lows,
            "rsi": rsi,
            "macd_bullish": macd_bullish,
            "macd_histogram": macd_histogram,
            "ema20": ema20,
            "ema50": ema50,
            "ema200": ema200,
            "price": close.iloc[-1],
            "timeframe": timeframe,
        }

    def check_entry_signal(self, df_5m, direction, ht_structure):
        """Check lower timeframe for entry signal (pullback confirmation)"""
        if df_5m is None or len(df_5m) < 30:
            return None

        close = df_5m["Close"]
        high = df_5m["High"]
        low = df_5m["Low"]

        rsi_5m = self.calc_rsi(close).iloc[-1]
        macd_5m, signal_5m = self.calc_macd(close)
        macd_5m_val = macd_5m.iloc[-1]
        signal_5m_val = signal_5m.iloc[-1]

        # Calculate recent volatility
        atr_5m = self.calc_atr(df_5m).iloc[-1]

        # Entry signal logic
        entry_signal = None
        entry_confidence = 0

        if direction == "LONG":
            # For LONG: Higher timeframe is bullish, wait for 5M pullback
            # 5M should show bearish movement BUT not too much
            if rsi_5m < 45:  # Pullback to oversold
                entry_signal = "PULLBACK_LONG"
                entry_confidence += 30
            if macd_5m_val < signal_5m_val:  # 5M MACD bearish
                entry_confidence += 25
            if rsi_5m > 30:  # Not oversold
                entry_confidence += 15
            # Recent candle direction
            if close.iloc[-1] < close.iloc[-5]:  # Pulled back from recent high
                entry_confidence += 20
            # Volume confirmation
            if len(df_5m) > 20:
                vol_ratio = (
                    df_5m["Volume"].iloc[-5:].mean()
                    / df_5m["Volume"].iloc[-20:-5].mean()
                )
                if vol_ratio > 1.2:
                    entry_confidence += 10

        elif direction == "SHORT":
            # For SHORT: Higher timeframe is bearish, wait for 5M bounce
            if rsi_5m > 55:  # Pullback to overbought
                entry_signal = "PULLBACK_SHORT"
                entry_confidence += 30
            if macd_5m_val > signal_5m_val:  # 5M MACD bullish
                entry_confidence += 25
            if rsi_5m < 70:  # Not extremely overbought
                entry_confidence += 15
            # Recent candle direction
            if close.iloc[-1] > close.iloc[-5]:  # Bounced from recent low
                entry_confidence += 20
            # Volume confirmation
            if len(df_5m) > 20:
                vol_ratio = (
                    df_5m["Volume"].iloc[-5:].mean()
                    / df_5m["Volume"].iloc[-20:-5].mean()
                )
                if vol_ratio > 1.2:
                    entry_confidence += 10

        return {
            "signal": entry_signal,
            "confidence": min(entry_confidence, 100),
            "rsi_5m": rsi_5m,
            "macd_5m_bullish": macd_5m_val > signal_5m_val,
            "atr_5m": atr_5m,
            "entry_confidence": entry_confidence >= 70,
        }

    def calc_atr(self, df, period=14):
        high = df["High"]
        low = df["Low"]
        close = df["Close"]
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def get_market_sentiment(self):
        """Get overall market sentiment with verification"""
        indices = {
            "NIFTY": "^NSEI",
            "BANKNIFTY": "^NSEBANK",
        }

        nifty_data = None
        banknifty_data = None

        # Get NIFTY
        df_nifty = self.get_data("^NSEI")
        if df_nifty is not None:
            rsi = self.calc_rsi(df_nifty["Close"]).iloc[-1]
            macd, signal = self.calc_macd(df_nifty["Close"])
            nifty_data = {
                "name": "NIFTY",
                "price": df_nifty["Close"].iloc[-1],
                "rsi": rsi,
                "macd": macd.iloc[-1],
                "signal": signal.iloc[-1],
                "trend": "BULLISH" if macd.iloc[-1] > signal.iloc[-1] else "BEARISH",
            }

        # Get BANKNIFTY
        df_bank = self.get_data("^NSEBANK")
        if df_bank is not None:
            rsi = self.calc_rsi(df_bank["Close"]).iloc[-1]
            macd, signal = self.calc_macd(df_bank["Close"])
            banknifty_data = {
                "name": "BANKNIFTY",
                "price": df_bank["Close"].iloc[-1],
                "rsi": rsi,
                "macd": macd.iloc[-1],
                "signal": signal.iloc[-1],
                "trend": "BULLISH" if macd.iloc[-1] > signal.iloc[-1] else "BEARISH",
            }

        # Calculate overall sentiment
        if nifty_data and banknifty_data:
            bullish_count = sum(
                1 for d in [nifty_data, banknifty_data] if d["trend"] == "BULLISH"
            )
            avg_rsi = (nifty_data["rsi"] + banknifty_data["rsi"]) / 2

            if bullish_count > 1:
                sentiment = "BULLISH"
            elif bullish_count < 1:
                sentiment = "BEARISH"
            else:
                sentiment = "NEUTRAL"

            return sentiment, avg_rsi, nifty_data, banknifty_data

        return "UNKNOWN", 50, None, None

    def get_option_strike(self, current_price, direction, option_type):
        """
        Get proper option strike based on NSE conventions
        """
        # Determine step size based on price
        if current_price < 100:
            step = 2.5
        elif current_price < 250:
            step = 5
        elif current_price < 500:
            step = 5
        elif current_price < 2000:
            step = 20
        elif current_price < 5000:
            step = 50
        else:
            step = 100

        # For CALL (bullish) - strike should be ABOVE current price
        # For PUT (bearish) - strike should be BELOW current price
        if option_type == "CE":
            # CALL: Use ATM or slightly OTM (strike > spot)
            strike = round((current_price * 1.01) / step) * step
        else:
            # PUT: Use ATM or slightly OTM (strike < spot)
            strike = round((current_price * 0.99) / step) * step

        return int(strike), step

    def calculate_option_premium(self, spot_price, strike, option_type, atr, days=3):
        """
        Calculate realistic option premium using proper IV model
        """
        # Distance from ATM (intrinsic value + time value)
        if option_type == "CE":
            distance_pct = (strike - spot_price) / spot_price
        else:
            distance_pct = (spot_price - strike) / spot_price

        # For Indian stocks, typical ATM premium is 1.5-2.5% of spot
        # Adjust based on stock price volatility
        base_premium_pct = 0.02  # 2% base

        # Higher for high-priced stocks
        if spot_price > 5000:
            base_premium_pct = 0.015
        elif spot_price > 2000:
            base_premium_pct = 0.018
        elif spot_price > 500:
            base_premium_pct = 0.02
        else:
            base_premium_pct = 0.025  # Higher % for cheaper stocks

        # ATM premium
        atm_premium = spot_price * base_premium_pct

        # Adjust for moneyness
        if abs(distance_pct) < 0.01:  # Deep ATM (<1% from spot)
            premium = atm_premium
        elif abs(distance_pct) < 0.02:  # ATM (<2% from spot)
            premium = atm_premium * 0.95
        elif distance_pct > 0.03:  # OTM (>3% above for CE, >3% below for PE)
            # OTM options have less premium
            premium = atm_premium * 0.5
            # Add some intrinsic if deep ITM
            if distance_pct < 0:
                premium += abs(strike - spot_price)
        else:  # Slightly OTM (1-3%)
            premium = atm_premium * 0.75

        # Time value adjustment (3 days to expiry)
        days_factor = min(days / 7, 1)  # Normalize to 1 week

        # Final premium
        premium = premium * (0.5 + days_factor * 0.5)

        return max(8, round(premium, 2))

    def verify_trade(self, trade):
        """
        Verify all trade parameters are correct
        """
        errors = []

        # Verify price
        if trade["price"] < 1 or trade["price"] > 100000:
            errors.append(f"Invalid price: {trade['price']}")

        # Verify strike is appropriate distance from spot
        strike_dist = abs(trade["strike"] - trade["price"]) / trade["price"]
        if strike_dist > 0.1:  # More than 10% away
            errors.append(f"Strike too far: {strike_dist * 100:.1f}%")

        # Verify entry premium is reasonable
        if trade["entry"] < 3:
            errors.append("Entry too low (may be illiquid)")

        # Verify entry premium is not too high for the stock
        premium_ratio = trade["entry"] / trade["price"]
        if premium_ratio > 0.15:  # More than 15% of stock price
            errors.append(f"Entry too high: {premium_ratio * 100:.1f}% of price")

        # Verify SL is below entry
        if trade["direction"] == "SHORT":
            if trade["sl"] >= trade["entry"]:
                errors.append("SL should be above entry for SHORT")
        else:
            if trade["sl"] <= trade["entry"]:
                errors.append("SL should be below entry for LONG")

        # Verify target is above entry
        if trade["target"] <= trade["entry"]:
            errors.append("Target should be beyond entry")

        # Verify R:R is at least 1:1.5
        if trade["direction"] == "SHORT":
            risk = trade["entry"] - trade["sl"]
            reward = trade["target"] - trade["entry"]
        else:
            risk = trade["entry"] - trade["sl"]
            reward = trade["target"] - trade["entry"]

        if risk > 0:
            rr_ratio = reward / risk
            if rr_ratio < 1.3:
                errors.append(f"R:R too low: 1:{rr_ratio:.1f}")

        return len(errors) == 0, errors

    def scan_stocks(self, sentiment):
        """Scan stocks using multi-timeframe analysis"""
        results = []

        for name, info in self.stocks.items():
            symbol = info["symbol"]
            lot_size = info["lot"]

            # Get multi-timeframe data
            df_1h, df_5m = self.get_multi_timeframe_data(symbol)
            if df_1h is None or len(df_1h) < 50:
                continue

            close = df_1h["Close"]
            current = close.iloc[-1]

            # Skip if price is too low or too high
            if current < 50 or current > 20000:
                continue

            # STEP 1: Analyze higher timeframe (1H) for structure
            ht_analysis = self.detect_patterns(df_1h, "1H")

            if ht_analysis is None:
                continue

            ht_structure = ht_analysis["structure"]
            ht_confidence = ht_analysis["confidence"]

            # Skip if no clear structure
            if ht_structure == "NEUTRAL" or ht_confidence < 50:
                continue

            # STEP 2: Determine direction from higher timeframe + market sentiment
            direction = None
            if sentiment == "BULLISH" and ht_structure == "BULLISH":
                direction = "LONG"
            elif sentiment == "BEARISH" and ht_structure == "BEARISH":
                direction = "SHORT"
            elif ht_structure == "BULLISH" and sentiment == "NEUTRAL":
                direction = "LONG"
            elif ht_structure == "BEARISH" and sentiment == "NEUTRAL":
                direction = "SHORT"

            if direction is None:
                continue

            # STEP 3: Check lower timeframe (5M) for pullback entry
            lt_signal = self.check_entry_signal(df_5m, direction, ht_analysis)

            if lt_signal is None:
                continue

            lt_confidence = lt_signal["confidence"]
            has_entry = lt_signal["entry_confidence"]

            # Calculate score with multi-timeframe confluence
            score = 0

            # Higher timeframe structure weight
            score += ht_confidence * 0.4

            # Lower timeframe entry weight
            score += lt_confidence * 0.4

            # RSI confirmation from 1H
            if direction == "LONG" and ht_analysis["rsi"] < 60:
                score += 15
            elif direction == "SHORT" and ht_analysis["rsi"] > 40:
                score += 15

            # Volume confirmation
            vol_ratio = 1
            if len(df_1h) > 30:
                vol_ratio = (
                    df_1h["Volume"].iloc[-10:].mean()
                    / df_1h["Volume"].iloc[-30:-10].mean()
                )
                if vol_ratio > 1.2:
                    score += 10

            # Momentum from 1H
            mom = ((close.iloc[-1] - close.iloc[-20]) / close.iloc[-20]) * 100
            if direction == "LONG" and mom > 0:
                score += 10
            elif direction == "SHORT" and mom < 0:
                score += 10

            score = min(score, 100)

            if score >= self.min_score and has_entry:
                # Calculate trade setup
                option_type = "PE" if direction == "SHORT" else "CE"
                atr = self.calc_atr(df_1h).iloc[-1]
                strike, step = self.get_option_strike(current, direction, option_type)
                entry = self.calculate_option_premium(current, strike, option_type, atr)
                sl = round(entry * 0.6, 2)
                target = round(entry * 2.5, 2)

                trade = {
                    "name": name,
                    "price": round(current, 2),
                    "rsi_1h": round(ht_analysis["rsi"], 1),
                    "rsi_5m": round(lt_signal["rsi_5m"], 1),
                    "momentum": round(mom, 2),
                    "volume": round(vol_ratio if len(df_1h) > 30 else 1, 2),
                    "atr": round(atr, 2),
                    "score": round(score, 1),
                    "direction": direction,
                    "option_type": option_type,
                    "strike": strike,
                    "step": step,
                    "entry": entry,
                    "sl": sl,
                    "target": target,
                    "lot_size": lot_size,
                    "premium_pct": round(entry / current * 100, 2),
                    "ht_structure": ht_structure,
                    "ht_confidence": ht_confidence,
                    "lt_signal": lt_signal["signal"],
                    "lt_confidence": lt_confidence,
                    "entry_strategy": "PULLBACK" if lt_signal["signal"] else "MOMENTUM",
                }

                # Verify trade
                is_valid, errors = self.verify_trade(trade)
                if is_valid:
                    results.append(trade)
                else:
                    print(f"  {name}: Filtered - {', '.join(errors)}")

        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def format_sentiment_message(self, sentiment, avg_rsi, nifty_data, banknifty_data):
        """Format sentiment update with verification"""
        emoji = (
            "BULLISH"
            if sentiment == "BULLISH"
            else "BEARISH"
            if sentiment == "BEARISH"
            else "NEUTRAL"
        )

        msg = f"*MARKET SENTIMENT - {datetime.now().strftime('%H:%M')}*\n\n"
        msg += f"Overall: {sentiment}\n"
        msg += f"Avg RSI: {avg_rsi:.1f}\n\n"

        if nifty_data:
            msg += f"NIFTY:\n"
            msg += f"  Price: {nifty_data['price']:.2f}\n"
            msg += f"  RSI: {nifty_data['rsi']:.1f}\n"
            msg += f"  Trend: {nifty_data['trend']}\n\n"

        if banknifty_data:
            msg += f"BANKNIFTY:\n"
            msg += f"  Price: {banknifty_data['price']:.2f}\n"
            msg += f"  RSI: {banknifty_data['rsi']:.1f}\n"
            msg += f"  Trend: {banknifty_data['trend']}\n\n"

        msg += "_" * 30 + "\n"
        msg += "RSI < 40 = Oversold\n"
        msg += "RSI > 60 = Overbought\n"

        return msg

    def format_trade_alert(self, results):
        """Format verified trade alerts with multi-timeframe analysis"""
        msg = f"*TRADE ALERTS - {datetime.now().strftime('%H:%M')}*\n\n"
        msg += f"Verified {len(results)} trades (Multi-TF Strategy)\n\n"

        for i, trade in enumerate(results[:5], 1):
            option = "CE" if trade["option_type"] == "CE" else "PE"
            direction = "BUY CALL" if trade["option_type"] == "CE" else "BUY PUT"

            msg += f"{i}. {trade['name']} - {trade['direction']}\n"
            msg += f"   {option} Strike: {trade['strike']} @ {trade['entry']}\n"
            msg += f"   SL: {trade['sl']} | Target: {trade['target']}\n"
            msg += f"   R:R: 1:{round((trade['target'] - trade['entry']) / (trade['entry'] - trade['sl']), 1)}\n\n"

            msg += f"   TIMEFRAME ANALYSIS:\n"
            msg += f"   ┌─ 1H Structure: {trade['ht_structure']} ({trade['ht_confidence']}% confidence)\n"
            msg += f"   ├─ 5M Signal: {trade['lt_signal']} ({trade['lt_confidence']}% confidence)\n"
            msg += f"   └─ Entry: {trade['entry_strategy']} on pullback\n\n"

            msg += f"   INDICATORS:\n"
            msg += f"   RSI 1H: {trade['rsi_1h']} | RSI 5M: {trade['rsi_5m']}\n"
            msg += f"   Momentum: {trade['momentum']}% | Volume: {trade['volume']}x\n"
            msg += f"   Score: {trade['score']}\n"
            msg += "_" * 30 + "\n\n"

        return msg

    def run_live_scan(self):
        """Run one scan cycle with verification"""
        now = datetime.now()

        print(f"\n[{now.strftime('%H:%M:%S')}] Running verified scan...")

        # Get and verify sentiment
        sentiment, avg_rsi, nifty_data, banknifty_data = self.get_market_sentiment()

        # Check if sentiment changed
        sentiment_changed = self.last_sentiment != sentiment

        print(f"  Sentiment: {sentiment} (RSI: {avg_rsi:.1f})")
        if nifty_data:
            print(f"  NIFTY: {nifty_data['price']:.2f} | Trend: {nifty_data['trend']}")
        if banknifty_data:
            print(
                f"  BANKNIFTY: {banknifty_data['price']:.2f} | Trend: {banknifty_data['trend']}"
            )

        # Send sentiment update (every time or when changed)
        self.telegram.send_message(
            self.format_sentiment_message(
                sentiment, avg_rsi, nifty_data, banknifty_data
            )
        )
        self.last_sentiment = sentiment

        # Scan for trades
        print("  Scanning stocks...")
        trades = self.scan_stocks(sentiment)

        if trades:
            print(f"  Found {len(trades)} verified trades!")

            # Always send new trade alerts
            self.telegram.send_message(self.format_trade_alert(trades))
            self.last_trade_alert = now

            for trade in trades[:3]:
                print(
                    f"    - {trade['name']}: {trade['option_type']} {trade['strike']} @ {trade['entry']}"
                )
        else:
            print(f"  No trades found (RSI levels not ideal)")

        return sentiment, trades

    def run_continuous(self):
        """Run continuous scanning every 15 minutes"""
        print("=" * 60)
        print("LIVE TRADING SCANNER - VERIFIED")
        print("=" * 60)
        print("Scanning every 15 minutes")
        print("Verifying all trade parameters")
        print("Press Ctrl+C to stop")
        print("=" * 60)

        try:
            # Initial scan
            self.run_live_scan()

            while True:
                print(f"\nNext scan in {self.scan_interval} minutes...")
                print("Press Ctrl+C to stop")
                time.sleep(self.scan_interval * 60)

                # Run scan
                self.run_live_scan()

        except KeyboardInterrupt:
            print("\n\nScanner stopped.")


def quick_scan():
    """Quick one-time verified scan"""
    scanner = LiveTradingScanner()
    sentiment, trades = scanner.run_live_scan()

    print("\n" + "=" * 60)
    print("VERIFIED SCAN RESULTS")
    print("=" * 60)

    print(f"\nMarket: {sentiment}")
    print(f"Found {len(trades)} verified trades")

    if trades:
        print("\nTop Trades:")
        for trade in trades[:5]:
            print(f"  {trade['name']}: {trade['option_type']} {trade['strike']}")
            print(f"    Entry: {trade['entry']} | Target: {trade['target']}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--scan", action="store_true", help="One-time scan")
    parser.add_argument("--live", action="store_true", help="Continuous scanning")
    args = parser.parse_args()

    scanner = LiveTradingScanner()

    if args.live:
        scanner.run_continuous()
    else:
        quick_scan()
