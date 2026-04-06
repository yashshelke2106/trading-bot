#!/usr/bin/env python3
"""
LIVE TRADING SCANNER - EVERY 15 MINUTES
======================================
1. Checks market sentiment every 15 minutes
2. Scans for trade opportunities
3. Sends alerts via Telegram when trades found
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
        self.scan_interval = 15  # minutes
        self.min_score = 40  # Minimum score for trade alert

        self.stocks = {
            "BHEL": "BHEL.NS",
            "NMDC": "NMDC.NS",
            "COALINDIA": "COALINDIA.NS",
            "POWERGRID": "POWERGRID.NS",
            "NTPC": "NTPC.NS",
            "BEL": "BEL.NS",
            "ONGC": "ONGC.NS",
            "HINDALCO": "HINDALCO.NS",
            "JSWSTEEL": "JSWSTEEL.NS",
            "TATASTEEL": "TATASTEEL.NS",
            "SBIN": "SBIN.NS",
            "ICICIBANK": "ICICIBANK.NS",
            "AXISBANK": "AXISBANK.NS",
        }

    def get_data(self, symbol, period="1d", interval="5m"):
        try:
            df = yf.Ticker(symbol).history(period=period, interval=interval)
            if df is not None and len(df) > 20:
                df.index = df.index.tz_localize(None) if df.index.tz else df.index
                return df
        except:
            pass
        return None

    def calc_rsi(self, prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calc_macd(self, prices):
        exp12 = prices.ewm(span=12).mean()
        exp26 = prices.ewm(span=26).mean()
        macd = exp12 - exp26
        signal = macd.ewm(span=9).mean()
        return macd, signal

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
        """Get overall market sentiment"""
        indices = {
            "NIFTY": "^NSEI",
            "BANKNIFTY": "^NSEBANK",
        }

        total_rsi = 0
        count = 0
        bullish = 0

        for name, symbol in indices.items():
            df = self.get_data(symbol)
            if df is not None:
                rsi = self.calc_rsi(df["Close"]).iloc[-1]
                macd, signal = self.calc_macd(df["Close"])

                total_rsi += rsi
                count += 1

                if macd.iloc[-1] > signal.iloc[-1]:
                    bullish += 1

        if count == 0:
            return "UNKNOWN", 50

        avg_rsi = total_rsi / count
        sentiment = "BULLISH" if bullish > count / 2 else "BEARISH"

        return sentiment, avg_rsi

    def scan_stocks(self, sentiment):
        """Scan stocks for trades"""
        results = []

        for name, symbol in self.stocks.items():
            df = self.get_data(symbol)
            if df is None or len(df) < 30:
                continue

            close = df["Close"]
            current = close.iloc[-1]

            rsi = self.calc_rsi(close).iloc[-1]
            macd, signal = self.calc_macd(close)
            macd_val = macd.iloc[-1]
            signal_val = signal.iloc[-1]
            atr = self.calc_atr(df).iloc[-1]

            mom = ((close.iloc[-1] - close.iloc[-20]) / close.iloc[-20]) * 100

            vol = (
                df["Volume"].iloc[-10:].mean() / df["Volume"].iloc[-50:-10].mean()
                if len(df) > 50
                else 1
            )

            score = 0
            direction = None

            if sentiment == "BEARISH":
                if rsi > 55:
                    score += 25
                    direction = "SHORT"
                elif rsi < 35:
                    score -= 10

                if macd_val < signal_val:
                    score += 25
                else:
                    score -= 10

                if mom < -1:
                    score += 15
                    direction = "SHORT"

                if vol > 1.3:
                    score += 10

            elif sentiment == "BULLISH":
                if rsi < 45:
                    score += 25
                    direction = "LONG"
                elif rsi > 70:
                    score -= 10

                if macd_val > signal_val:
                    score += 25
                else:
                    score -= 10

                if mom > 1:
                    score += 15
                    direction = "LONG"

                if vol > 1.3:
                    score += 10

            if score >= self.min_score:
                # Calculate trade setup
                if direction == "SHORT":
                    strike = round(current * 0.99 / 5) * 5
                    option_type = "PE"
                    entry = max(5, atr * 0.3)
                else:
                    strike = round(current * 1.01 / 5) * 5
                    option_type = "CE"
                    entry = max(5, atr * 0.3)

                results.append(
                    {
                        "name": name,
                        "price": current,
                        "rsi": rsi,
                        "macd": macd_val - signal_val,
                        "momentum": mom,
                        "volume": vol,
                        "score": score,
                        "direction": direction,
                        "strike": int(strike),
                        "option": option_type,
                        "entry": round(entry, 2),
                        "sl": round(entry * 0.6, 2),
                        "target": round(entry * 2, 2),
                    }
                )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def format_sentiment_message(self, sentiment, avg_rsi):
        """Format sentiment update"""
        emoji = "BULLISH" if sentiment == "BULLISH" else "BEARISH"

        msg = f"""
*MARKET SENTIMENT - {datetime.now().strftime("%H:%M")}*

Market: {sentiment}
Avg RSI: {avg_rsi:.1f}

RSI < 40 = Oversold (Buy)
RSI > 60 = Overbought (Sell)
"""
        return msg

    def format_trade_alert(self, results):
        """Format trade alerts"""
        msg = f"""
*TRADE ALERTS - {datetime.now().strftime("%H:%M")}*

Found {len(results)} potential trades:

"""

        for i, trade in enumerate(results[:5], 1):
            direction_emoji = "PUT" if trade["direction"] == "SHORT" else "CALL"

            msg += f"{i}. {trade['name']} {direction_emoji}\n"
            msg += f"   Price: {trade['price']:.2f}\n"
            msg += f"   Strike: {trade['strike']} {trade['option']}\n"
            msg += f"   Entry: {trade['entry']} | SL: {trade['sl']} | Target: {trade['target']}\n"
            msg += f"   RSI: {trade['rsi']:.1f} | Momentum: {trade['momentum']:.1f}%\n"
            msg += f"   Score: {trade['score']}\n\n"

        return msg

    def run_live_scan(self):
        """Run one scan cycle"""
        now = datetime.now()

        print(f"\n[{now.strftime('%H:%M:%S')}] Scanning...")

        # Get sentiment
        sentiment, avg_rsi = self.get_market_sentiment()
        print(f"  Sentiment: {sentiment} | RSI: {avg_rsi:.1f}")

        # Send sentiment update
        self.telegram.send_message(self.format_sentiment_message(sentiment, avg_rsi))

        # Scan for trades
        trades = self.scan_stocks(sentiment)

        if trades:
            print(f"  Found {len(trades)} potential trades!")

            # Check if we should alert (avoid spam)
            should_alert = True
            if self.last_trade_alert:
                time_diff = (now - self.last_trade_alert).total_seconds() / 60
                if time_diff < 30 and len(trades) <= len(
                    getattr(self, "_last_trades", [])
                ):
                    should_alert = False
                    print("  Skipping alert (already sent recently)")

            if should_alert:
                self.telegram.send_message(self.format_trade_alert(trades))
                self.last_trade_alert = now
                self._last_trades = trades
        else:
            print(f"  No trades found")

        return sentiment, trades

    def run_continuous(self):
        """Run continuous scanning"""
        print("=" * 60)
        print("LIVE TRADING SCANNER")
        print("=" * 60)
        print("Scanning every 15 minutes")
        print("Sending sentiment updates + trade alerts")
        print("Press Ctrl+C to stop")
        print("=" * 60)

        try:
            while True:
                now = datetime.now()

                # Skip if market closed (optional)
                # 9:15 - 15:30 IST

                sentiment, trades = self.run_live_scan()

                print(f"\nNext scan in {self.scan_interval} minutes...")
                print(f"Press Ctrl+C to stop\n")

                time.sleep(self.scan_interval * 60)

        except KeyboardInterrupt:
            print("\n\nScanner stopped.")


def quick_scan():
    """Quick one-time scan"""
    scanner = LiveTradingScanner()
    sentiment, trades = scanner.run_live_scan()

    print("\n" + "=" * 60)
    print("SCAN RESULTS")
    print("=" * 60)

    print(f"\nMarket Sentiment: {sentiment}")
    print(f"Found {len(trades)} trades")

    if trades:
        print("\nTop Trades:")
        for trade in trades[:5]:
            print(
                f"  {trade['name']}: {trade['direction']} {trade['option']} {trade['strike']} @ {trade['entry']}"
            )


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
