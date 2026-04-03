"""
REAL-TIME MARKET DATA STREAMER
==============================
Streams live market data every second via Dhan WebSocket

Usage:
    python live_ticker.py                    # Stream all stocks
    python live_ticker.py --symbols TCS INFY # Stream specific stocks
    python live_ticker.py --interval 5       # Update every 5 seconds
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dhanhq import dhanhq

    DHAN_AVAILABLE = True
except ImportError:
    DHAN_AVAILABLE = False


def load_credentials():
    cred_file = os.path.join(os.path.dirname(__file__), "dhan_credentials.json")
    if os.path.exists(cred_file):
        with open(cred_file, "r") as f:
            return json.load(f)
    return {}


class LiveTicker:
    def __init__(self, symbols: List[str] = None, interval: int = 1):
        self.creds = load_credentials()
        self.interval = interval  # seconds
        self.is_running = False

        # Default symbols to track
        self.symbols = symbols or [
            "NIFTY",
            "BANKNIFTY",
            "FINNIFTY",
            "RELIANCE",
            "TCS",
            "HDFCBANK",
            "ICICIBANK",
            "INFY",
            "SBIN",
            "BAJFINANCE",
            "KOTAKBANK",
            "TATAMOTORS",
            "SUNPHARMA",
            "TATASTEEL",
            "ITC",
        ]

        # Security ID mapping (NSE EQ)
        self.security_ids = {
            "NIFTY": "26000",
            "BANKNIFTY": "26001",
            "FINNIFTY": "26032",
            "RELIANCE": "2885",
            "TCS": "11536",
            "HDFCBANK": "1333",
            "ICICIBANK": "4963",
            "KOTAKBANK": "4702",
            "INFY": "1594",
            "SBIN": "3045",
            "BAJFINANCE": "8117",
            "HINDUNILVR": "1394",
            "ITC": "1665",
            "TATAMOTORS": "10682",
            "SUNPHARMA": "2851",
            "TATASTEEL": "3031",
            "ADANIPOWER": "1222",
            "MARUTI": "10999",
            "M&M": "5192",
            "ASIANPAINT": "3783",
            "NESTLEIND": "11864",
            "HCLTECH": "5289",
            "WIPRO": "3787",
            "TECHM": "10604",
            "LT": "2935",
            "AXISBANK": "9950",
            "INDUSINDBK": "4928",
        }

        # Connect
        self.dhan = None
        self.connect()

        # Price cache
        self.prices = {}
        self.prev_prices = {}
        self.open_prices = {}
        self.high_prices = {}
        self.low_prices = {}

    def connect(self):
        if not DHAN_AVAILABLE:
            print("[ERROR] dhanhq not installed!")
            return False

        api_key = self.creds.get("api_key")
        access_token = self.creds.get("access_token")
        client_id = self.creds.get("client_id")

        if not all([api_key, access_token, client_id]):
            print("[ERROR] Missing credentials!")
            return False

        try:
            self.dhan = dhanhq(api_key, access_token, client_id)
            print("[SUCCESS] Connected to Dhan!")
            return True
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            return False

    def get_live_quote(self, symbol: str) -> Optional[Dict]:
        """Get live quote for a symbol"""
        if not self.dhan:
            return None

        sec_id = self.security_ids.get(symbol)
        if not sec_id:
            return None

        # Use historical data as fallback
        try:
            from datetime import datetime, timedelta

            result = self.dhan.intraday_minute_data(
                security_id=sec_id,
                exchange_segment="NSECM",
                instrument_type="EQUITY",
                from_date=datetime.now().strftime("%Y-%m-%d"),
                to_date=datetime.now().strftime("%Y-%m-%d"),
                interval=1,
            )
            if result and result.get("data"):
                data = result["data"]
                if isinstance(data, dict):
                    last_candle = {
                        k: v[-1] if isinstance(v, list) else v for k, v in data.items()
                    }
                    return {
                        "symbol": symbol,
                        "ltp": last_candle.get("close", 0),
                        "open": last_candle.get("open", 0),
                        "high": last_candle.get("high", 0),
                        "low": last_candle.get("low", 0),
                        "volume": last_candle.get("volume", 0),
                    }
        except Exception as e:
            pass

        return None

        sec_id = self.security_ids.get(symbol)
        if not sec_id:
            return None

        try:
            # Use ticker_data for real-time
            result = self.dhan.ticker_data([sec_id])
            if result and len(result) > 0:
                return result[0]
        except Exception as e:
            pass

        # Fallback to historical data
        try:
            from datetime import datetime, timedelta

            result = self.dhan.intraday_minute_data(
                security_id=sec_id,
                exchange_segment="NSE_EQ",
                instrument_type="EQUITY",
                from_date=datetime.now().strftime("%Y-%m-%d"),
                to_date=datetime.now().strftime("%Y-%m-%d"),
                interval=1,
            )
            if result and result.get("data"):
                data = result["data"]
                if isinstance(data, dict):
                    last_candle = {
                        k: v[-1] if isinstance(v, list) else v for k, v in data.items()
                    }
                    return {
                        "symbol": symbol,
                        "ltp": last_candle.get("close", 0),
                        "open": last_candle.get("open", 0),
                        "high": last_candle.get("high", 0),
                        "low": last_candle.get("low", 0),
                        "volume": last_candle.get("volume", 0),
                    }
        except Exception as e:
            pass

        return None

    def calculate_change(self, current: float, previous: float) -> tuple:
        """Calculate price change and percentage"""
        if previous == 0:
            return 0, 0
        change = current - previous
        pct = (change / previous) * 100
        return change, pct

    def update_prices(self):
        """Update all prices"""
        self.prev_prices = self.prices.copy()

        for symbol in self.symbols:
            quote = self.get_live_quote(symbol)
            if quote:
                ltp = quote.get("ltp", quote.get("close", 0))
                self.prices[symbol] = ltp

                # Track high/low
                if symbol not in self.high_prices or ltp > self.high_prices[symbol]:
                    self.high_prices[symbol] = ltp
                if symbol not in self.low_prices or ltp < self.low_prices[symbol]:
                    self.low_prices[symbol] = ltp
                if symbol not in self.open_prices:
                    self.open_prices[symbol] = ltp

    def print_ticker(self):
        """Print live ticker"""
        # Clear screen
        os.system("cls" if os.name == "nt" else "clear")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'=' * 80}")
        print(f"  LIVE MARKET TICKER - {timestamp} (Updating every {self.interval}s)")
        print(f"{'=' * 80}")
        print()
        print(
            f"{'SYMBOL':<12} {'LTP':>12} {'CHANGE':>10} {'%CHG':>8} {'HIGH':>12} {'LOW':>12} {'VOL':>12}"
        )
        print(f"{'-' * 80}")

        # Sort by percentage change
        sorted_symbols = sorted(
            self.prices.keys(),
            key=lambda x: self.calculate_change(
                self.prices.get(x, 0), self.prev_prices.get(x, self.prices.get(x, 0))
            )[1],
            reverse=True,
        )

        for symbol in sorted_symbols:
            ltp = self.prices.get(symbol, 0)
            prev = self.prev_prices.get(symbol, ltp)
            change, pct = self.calculate_change(ltp, prev)

            high = self.high_prices.get(symbol, ltp)
            low = self.low_prices.get(symbol, ltp)

            # Color coding
            if change > 0:
                indicator = "+"
                color = "\033[92m"  # Green
            elif change < 0:
                indicator = ""
                color = "\033[91m"  # Red
            else:
                indicator = ""
                color = "\033[0m"  # Reset

            reset = "\033[0m"
            print(
                f"{symbol:<12} {color}{ltp:>12.2f} {indicator}{change:>9.2f} {pct:>7.2f}% {high:>12.2f} {low:>12.2f}{reset}"
            )

        print(f"{'-' * 80}")
        print(f"  {len(self.prices)} symbols tracked | Press Ctrl+C to stop")

    def run(self, duration: int = 0):
        """
        Run the ticker
        duration: 0 = infinite, otherwise seconds
        """
        self.is_running = True
        start_time = time.time()

        print(f"\nStarting Live Ticker...")
        print(f"Symbols: {', '.join(self.symbols)}")
        print(f"Update interval: {self.interval} second(s)")
        print("Press Ctrl+C to stop\n")

        try:
            while self.is_running:
                self.update_prices()
                self.print_ticker()

                # Check duration
                if duration > 0 and (time.time() - start_time) >= duration:
                    break

                time.sleep(self.interval)

        except KeyboardInterrupt:
            print("\n\nStopping ticker...")
            self.is_running = False

        print("\nTicker stopped.")

    def stop(self):
        self.is_running = False


def main():
    parser = argparse.ArgumentParser(description="Live Market Ticker")
    parser.add_argument("--symbols", nargs="+", help="Symbols to track")
    parser.add_argument(
        "--interval",
        type=int,
        default=1,
        help="Update interval in seconds (default: 1)",
    )
    parser.add_argument(
        "--duration", type=int, default=0, help="Duration in seconds (0 = infinite)"
    )
    args = parser.parse_args()

    ticker = LiveTicker(symbols=args.symbols, interval=args.interval)
    ticker.run(duration=args.duration)


if __name__ == "__main__":
    main()
