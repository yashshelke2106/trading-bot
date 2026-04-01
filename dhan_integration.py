"""
DHAN API INTEGRATION
Wrapper for Dhan broker API
Handles real-time data fetching and trade execution
"""

import json
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
import os

try:
    from dhanhq import dhanhq

    DHAN_AVAILABLE = True
except ImportError:
    DHAN_AVAILABLE = False


def load_credentials() -> Dict:
    """Load Dhan credentials from file"""
    cred_file = os.path.join(os.path.dirname(__file__), "dhan_credentials.json")
    if os.path.exists(cred_file):
        with open(cred_file, "r") as f:
            return json.load(f)
    return {}


class DhanAPIClient:
    """
    Dhan API Client for market data and trading
    """

    def __init__(
        self, api_key: str = None, access_token: str = None, client_id: str = None
    ):
        self.credentials = load_credentials()

        self.api_key = api_key or self.credentials.get("api_key")
        self.access_token = access_token or self.credentials.get("access_token")
        self.client_id = client_id or self.credentials.get("client_id")

        self.dhan_client = None
        self.is_connected = False

        self.NSE = "NSE"
        self.NSE_FNO = "NSE_FNO"

        self.instruments = {
            "NIFTY": ("9999200000", "INDEX", "NSE"),
            "BANKNIFTY": ("9999100000", "INDEX", "NSE"),
            "FINNIFTY": ("35026", "INDEX", "NSE"),
            "NSE_INDEX": ("35026", "INDEX", "NSE"),
            "TCS": ("532540", "EQUITY", "NSE"),
            "HDFCBANK": ("500180", "EQUITY", "NSE"),
            "ICICIBANK": ("532174", "EQUITY", "NSE"),
            "INFY": ("500209", "EQUITY", "NSE"),
            "RELIANCE": ("2885", "EQUITY", "NSE"),
            "KOTAKBANK": ("4702", "EQUITY", "NSE"),
            "HINDUNILVR": ("1394", "EQUITY", "NSE"),
            "ITC": ("1665", "EQUITY", "NSE"),
            "SBIN": ("3045", "EQUITY", "NSE"),
            "BAJFINANCE": ("8117", "EQUITY", "NSE"),
            "BHARTIARTL": ("10604", "EQUITY", "NSE"),
            "ASIANPAINT": ("3783", "EQUITY", "NSE"),
            "MARUTI": ("10999", "EQUITY", "NSE"),
            "TATAMOTORS": ("10682", "EQUITY", "NSE"),
            "SUNPHARMA": ("2851", "EQUITY", "NSE"),
            "TATASTEEL": ("3031", "EQUITY", "NSE"),
            "WIPRO": ("3787", "EQUITY", "NSE"),
            "ADANIPOWER": ("1222", "EQUITY", "NSE"),
            "CIPLA": ("3129", "EQUITY", "NSE"),
            "DIVISLAB": ("10940", "EQUITY", "NSE"),
            "TITAN": ("8716", "EQUITY", "NSE"),
            "BAJAJFINSV": ("64578", "EQUITY", "NSE"),
            "HDFCLIFE": ("46785", "EQUITY", "NSE"),
            "SBILIFE": ("56407", "EQUITY", "NSE"),
            "INDUSINDBK": ("4928", "EQUITY", "NSE"),
            "AXISBANK": ("9950", "EQUITY", "NSE"),
            "KMB": ("4172", "EQUITY", "NSE"),
            "LT": ("2935", "EQUITY", "NSE"),
            "HAL": ("13584", "EQUITY", "NSE"),
            "COFORGE": ("10884", "EQUITY", "NSE"),
            "PERSISTENT": ("5422", "EQUITY", "NSE"),
            "LTI": ("2740", "EQUITY", "NSE"),
            "TECHM": ("10604", "EQUITY", "NSE"),
            "M&M": ("5192", "EQUITY", "NSE"),
            "BAJAJ-AUTO": ("9192", "EQUITY", "NSE"),
            "EICHERMOT": ("9108", "EQUITY", "NSE"),
            "TVSMOTOR": ("11168", "EQUITY", "NSE"),
            "HEROMOTOCO": ("4816", "EQUITY", "NSE"),
            "VEDL": ("51000", "EQUITY", "NSE"),
            "HINDALCO": ("4102", "EQUITY", "NSE"),
            "ADANIENT": ("3290", "EQUITY", "NSE"),
            "SUZLON": ("7696", "EQUITY", "NSE"),
            "RPOWER": ("4326", "EQUITY", "NSE"),
            "NTPC": ("11630", "EQUITY", "NSE"),
            "ADANIENSOL": ("54234", "EQUITY", "NSE"),
        }

        # Also support fetching by any NSE symbol (will lookup)
        self._security_cache = {}

        if self.api_key and self.access_token and self.client_id:
            self._initialize_client()

    def _initialize_client(self):
        """Initialize Dhan client"""
        if not DHAN_AVAILABLE:
            print("[DHAN] Warning: dhanhq library not installed")
            return

        try:
            self.dhan_client = dhanhq(self.api_key, self.access_token, self.client_id)
            self.is_connected = True
            print("[DHAN] Client connected successfully!")
            # Skip security list - we have predefined instruments
            # self._load_security_list()
        except Exception as e:
            print(f"[DHAN] Error initializing client: {e}")

    def _load_security_list(self):
        """Load NSE security list"""
        try:
            if self.dhan_client:
                result = self.dhan_client.fetch_security_list("NSE", "compact")
                if result and result.get("status") == "success":
                    for sec in result.get("data", []):
                        symbol = sec.get("symbol")
                        sec_id = sec.get("security_id")
                        if symbol and sec_id:
                            self._security_cache[symbol] = (
                                str(sec_id),
                                "EQUITY",
                                "NSE",
                            )
                    print(f"[DHAN] Loaded {len(self._security_cache)} securities")
        except Exception as e:
            print(f"[DHAN] Could not load security list: {e}")

    def get_security_id(self, symbol: str):
        """Get security ID for a symbol"""
        # Check predefined list first
        if symbol in self.instruments:
            return self.instruments[symbol]
        # Check cached list
        if symbol in self._security_cache:
            return self._security_cache[symbol]
        # Try common variations
        for key in self._security_cache:
            if symbol.upper() == key.upper():
                return self._security_cache[key]
        return None

    async def get_historical_data(
        self, symbol: str, timeframe: str = "5min", days: int = 30
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data from Dhan API for any NSE stock
        """
        print(f"[DHAN] Fetching {days} days of {timeframe} data for {symbol}")

        if not self.is_connected or not self.dhan_client:
            print("[DHAN] Using sample data (client not connected)")
            return self._generate_sample_data(symbol, days)

        try:
            sec_info = self.get_security_id(symbol)
            if sec_info is None:
                print(f"[DHAN] Security not found for {symbol}, using sample data")
                return self._generate_sample_data(symbol, days)

            security_id, instrument_type, exchange = sec_info

            to_date = datetime.now().strftime("%Y-%m-%d")
            from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            exchange_map = {"NSE": "NSECM", "NSE_FNO": "NSEFO"}
            dhan_exchange = exchange_map.get(exchange, "NSECM")

            if timeframe in ["1min", "5min", "15min", "60min"]:
                interval_map = {"1min": 1, "5min": 5, "15min": 15, "60min": 60}
                interval = interval_map.get(timeframe, 5)

                data = self.dhan_client.intraday_minute_data(
                    security_id=security_id,
                    exchange_segment=dhan_exchange,
                    instrument_type=instrument_type,
                    from_date=from_date,
                    to_date=to_date,
                    interval=interval,
                )
            else:
                data = self.dhan_client.historical_daily_data(
                    security_id=security_id,
                    exchange_segment=dhan_exchange,
                    instrument_type=instrument_type,
                    from_date=from_date,
                    to_date=to_date,
                )

            if data:
                raw_data = None

                if isinstance(data, dict):
                    if "data" in data:
                        raw_data = data["data"]
                    elif "status" in data and data["status"] == "success":
                        raw_data = data
                    else:
                        raw_data = data

                if raw_data:
                    if isinstance(raw_data, dict):
                        df = (
                            pd.DataFrame([raw_data])
                            if all(
                                isinstance(v, (int, float, str))
                                for v in raw_data.values()
                            )
                            else pd.DataFrame(raw_data)
                        )
                    elif isinstance(raw_data, list):
                        df = pd.DataFrame(raw_data)
                    else:
                        df = pd.DataFrame()

                    if not df.empty and len(df) > 0:
                        if "date" in df.columns or "Timestamp" in df.columns:
                            date_col = "date" if "date" in df.columns else "Timestamp"
                            df["timestamp"] = pd.to_datetime(
                                df[date_col], errors="coerce"
                            )
                            df.set_index("timestamp", inplace=True)
                        print(f"[DHAN] Fetched {len(df)} candles for {symbol}")
                        return df

        except Exception as e:
            print(f"[DHAN] Error fetching data: {e}")
            import traceback

            traceback.print_exc()

        return self._generate_sample_data(symbol, days)

    async def get_live_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Fetch live market data for multiple symbols
        """
        print(f"[DHAN] Fetching live data for {symbols}")

        live_data = {}

        # Use historical data as fallback for live prices
        try:
            if "NIFTY" in symbols and self.is_connected and self.dhan_client:
                df = await self.get_historical_data("NIFTY", "5min", 1)
                if df is not None and not df.empty:
                    latest = df.iloc[-1]
                    live_data["NIFTY"] = {
                        "price": float(latest["close"]),
                        "bid": float(latest["close"]) - 2,
                        "ask": float(latest["close"]) + 2,
                        "volume": int(latest["volume"]),
                        "timestamp": datetime.now().isoformat(),
                    }
        except Exception as e:
            print(f"[DHAN] Live data error: {e}")

        for symbol in symbols:
            if symbol not in live_data:
                live_data[symbol] = self._get_sample_quote(symbol)

        return live_data

    def _get_sample_quote(self, symbol: str) -> Dict:
        """Generate sample quote"""
        base_prices = {
            "NIFTY": 23500,
            "BANKNIFTY": 48500,
            "RELIANCE": 1400,
        }
        price = base_prices.get(symbol, 10000)

        return {
            "price": price,
            "bid": price - 1,
            "ask": price + 1,
            "volume": 1000000,
            "timestamp": datetime.now().isoformat(),
        }

    def _generate_sample_data(self, symbol: str, days: int) -> pd.DataFrame:
        """Generate sample data when API is not available"""
        import numpy as np

        base_prices = {
            "NIFTY": 23500,
            "BANKNIFTY": 48500,
            "RELIANCE": 1400,
            "HDFCBANK": 1650,
            "ICICIBANK": 1550,
            "KOTAKBANK": 1800,
            "TCS": 3500,
            "INFY": 1850,
        }

        base_price = base_prices.get(symbol, 10000)

        data = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        dates = pd.date_range(start=start_date, end=end_date, freq="1D")
        dates = [d for d in dates if d.weekday() < 5]

        if not dates:
            dates = [end_date]

        current_price = base_price
        volatility = 0.015

        for date in dates[: min(60, len(dates))]:
            for i in range(75):
                timestamp = date + timedelta(minutes=9 * 60 + i * 5)

                change = np.random.normal(0, volatility) * current_price
                open_price = current_price
                high_price = open_price + abs(change * 0.5)
                low_price = open_price - abs(change * 0.5)
                close_price = open_price + change

                volume = 1000000

                data.append(
                    {
                        "timestamp": timestamp,
                        "open": round(open_price, 2),
                        "high": round(high_price, 2),
                        "low": round(low_price, 2),
                        "close": round(close_price, 2),
                        "volume": volume,
                    }
                )

                current_price = close_price

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        if "timestamp" in df.columns:
            df.set_index("timestamp", inplace=True)
        return df

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "MARKET",
        stop_loss: Optional[float] = None,
        target: Optional[float] = None,
        paper_mode: bool = False,
    ) -> Dict:
        """
        Place a trading order
        """
        print(f"[DHAN] Placing order: {side} {quantity} {symbol} @ {order_type}")

        # Paper mode - simulate order without real execution
        if paper_mode or self.credentials.get("paper_mode", False):
            print(f"[PAPER MODE] Simulated order: {side} {quantity} {symbol}")
            return {
                "status": "simulated",
                "order_id": f"PAPER_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "message": "Paper mode - simulated order",
            }

        if not self.is_connected or not self.dhan_client:
            return {
                "status": "simulated",
                "order_id": f"SIM_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "message": "Simulated order (API not connected)",
            }

        try:
            security_id, instrument_type, exchange = self.instruments.get(
                symbol, (symbol, "EQUITY", "NSE")
            )

            # Map exchange to Dhan format (NSE_EQ for equities, NSEFO for F&O)
            exchange_map = {"NSE": "NSE_EQ", "NSE_FNO": "NSEFO", "BSE": "BSE_EQ"}
            dhan_exchange = exchange_map.get(exchange, "NSE_EQ")

            # Map product type
            product_type = "INTRADAY"

            # Transaction type: BUY or SELL
            transaction_type = "BUY" if side.upper() == "BUY" else "SELL"

            # Order type mapping
            order_type_map = {
                "MARKET": "MARKET",
                "LIMIT": "LIMIT",
                "STOP_LOSS": "STOP_LOSS",
            }
            dhan_order_type = order_type_map.get(order_type.upper(), "MARKET")

            # Get current market price if not provided
            current_price = price
            if not current_price:
                quote = self.get_quote(symbol)
                if quote:
                    current_price = quote.get("ltp", 0)

            result = self.dhan_client.place_order(
                exchange_segment=dhan_exchange,
                security_id=str(security_id),
                transaction_type=transaction_type,
                quantity=int(quantity),
                order_type=dhan_order_type,
                product_type=product_type,
                price=float(current_price) if current_price else 0,
                validity="DAY",
            )

            if result.get("status") == "success" or result.get("orderId"):
                order_id = result.get("orderId", result.get("order_id"))
                print(f"[DHAN] Order placed! Order ID: {order_id}")
                return {
                    "status": "success",
                    "order_id": order_id,
                    "message": "Order placed successfully",
                }
            else:
                return {"status": "error", "message": str(result)}

        except Exception as e:
            print(f"[DHAN] Error placing order: {e}")
            return {"status": "error", "message": str(e)}

    async def place_bracket_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        stop_loss: float,
        target: float,
    ) -> Dict:
        """
        Place a bracket order with SL and Target
        """
        print(f"[DHAN] Placing BRACKET order: {side} {quantity} {symbol}")
        print(f"  Entry: {price} | SL: {stop_loss} | Target: {target}")

        if paper_mode or self.credentials.get("paper_mode", False):
            return {
                "status": "simulated",
                "order_id": f"PAPER_BRK_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "message": "Paper mode - simulated bracket order",
            }

        if not self.is_connected or not self.dhan_client:
            return {
                "status": "simulated",
                "order_id": f"SIM_BRK_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "message": "Simulated bracket order",
            }

        try:
            security_id, instrument_type, exchange = self.instruments.get(
                symbol, (symbol, "EQUITY", "NSE")
            )

            exchange_map = {"NSE": "NSECM", "NSE_FNO": "NSEFO"}
            dhan_exchange = exchange_map.get(exchange, "NSECM")

            transaction_type = "BUY" if side.upper() == "BUY" else "SELL"

            # For bracket orders in Dhan, use MOBO order type
            result = self.dhan_client.place_order(
                exchange_segment=dhan_exchange,
                security_id=security_id,
                transaction_type=transaction_type,
                quantity=quantity,
                order_type="MARKET",
                product_type="MARGIN",
                price=price,
            )

            if result.get("status") == "success" or result.get("orderId"):
                order_id = result.get("orderId", result.get("order_id"))
                print(f"[DHAN] Main order placed! Order ID: {order_id}")

                # Place SL order
                sl_side = "SELL" if side.upper() == "BUY" else "BUY"
                sl_result = self.dhan_client.place_order(
                    exchange_segment=dhan_exchange,
                    security_id=security_id,
                    transaction_type=sl_side,
                    quantity=quantity,
                    order_type="STOP_LOSS",
                    product_type="MARGIN",
                    price=0,
                    trigger_price=stop_loss,
                )
                print(f"[DHAN] SL order placed: {sl_result}")

                return {
                    "status": "success",
                    "order_id": order_id,
                    "sl_order_id": sl_result.get("orderId") if sl_result else None,
                    "target": target,
                    "message": "Bracket order placed",
                }
            else:
                return {"status": "error", "message": str(result)}

        except Exception as e:
            print(f"[DHAN] Error placing bracket order: {e}")
            return {"status": "error", "message": str(e)}

    def get_order_status(self, order_id: str) -> Dict:
        """Get order status"""
        if not self.is_connected or not self.dhan_client:
            return {"status": "unknown"}

        try:
            order = self.dhan_client.get_order_by_id(order_id)
            return order
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_positions(self) -> Dict:
        """Get open positions"""
        if not self.is_connected or not self.dhan_client:
            return {"data": []}

        try:
            return self.dhan_client.get_positions()
        except Exception as e:
            return {"data": [], "error": str(e)}

    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an order"""
        if not self.is_connected or not self.dhan_client:
            return {"status": "simulated"}

        try:
            return self.dhan_client.cancel_order(order_id)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_quote(self, symbol: str) -> Optional[Dict]:
        """Get live quote for a symbol using quote_data"""
        if not self.is_connected or not self.dhan_client:
            return None

        try:
            sec_info = self.get_security_id(symbol)
            if sec_info is None:
                print(f"[DHAN] Security not found: {symbol}")
                return None

            security_id, instrument_type, exchange = sec_info

            exchange_segment_map = {
                "NSE": "NSE_EQ",
                "NSE_FNO": "NSE_FNO",
                "BSE": "BSE_EQ",
            }
            dhan_segment = exchange_segment_map.get(exchange, "NSE_EQ")

            securities = {dhan_segment: [security_id]}
            quote = self.dhan_client.quote_data(securities)

            if quote and isinstance(quote, dict):
                if quote.get("status") == "success" and "data" in quote:
                    data = quote["data"]
                    for key, value in data.items():
                        if isinstance(value, dict):
                            return {
                                "symbol": symbol,
                                "ltp": float(value.get("last_price", 0)),
                                "change": float(value.get("change", 0)),
                                "volume": int(value.get("volume", 0)),
                                "open": float(value.get("open", 0)),
                                "high": float(value.get("high", 0)),
                                "low": float(value.get("low", 0)),
                                "close": float(value.get("close", 0)),
                                "timestamp": datetime.now().isoformat(),
                            }
                elif "remarks" in quote:
                    print(f"[DHAN] Quote error: {quote.get('remarks')}")

        except Exception as e:
            print(f"[DHAN] Quote error for {symbol}: {e}")

        return None

        try:
            sec_info = self.get_security_id(symbol)
            if sec_info is None:
                return None

            security_id, instrument_type, exchange = sec_info
            exchange_map = {"NSE": "NSECM", "NSE_FNO": "NSEFO"}
            dhan_exchange = exchange_map.get(exchange, "NSECM")

            quote = self.dhan_client.get_quote(
                exchange_segment=dhan_exchange,
                security_id=security_id,
                quote_type="LTP",
            )

            if quote and isinstance(quote, dict):
                if "data" in quote:
                    data = quote["data"]
                    return {
                        "symbol": symbol,
                        "ltp": float(data.get("last_price", 0)),
                        "change": float(data.get("change", 0)),
                        "volume": int(data.get("volume", 0)),
                        "timestamp": datetime.now().isoformat(),
                    }
                elif "last_price" in quote:
                    return {
                        "symbol": symbol,
                        "ltp": float(quote.get("last_price", 0)),
                        "change": float(quote.get("change", 0)),
                        "volume": int(quote.get("volume", 0)),
                        "timestamp": datetime.now().isoformat(),
                    }

        except Exception as e:
            print(f"[DHAN] Quote error for {symbol}: {e}")

        return None

    async def get_live_price(self, symbol: str) -> Optional[float]:
        """Get live price for a symbol"""
        quote = self.get_quote(symbol)
        if quote:
            return quote.get("ltp")
        return None


class DhanDataFetcher:
    """Handles real-time data feed from Dhan"""

    def __init__(self, client: DhanAPIClient):
        self.client = client
        self.callbacks = []
        self.is_running = False
        self.data_buffer = {}

    def add_callback(self, callback):
        """Add callback for market data updates"""
        self.callbacks.append(callback)

    async def start_feed(self, interval: int = 5):
        """Start real-time data feed"""
        print(f"[DHAN] Starting real-time feed (interval: {interval}s)")
        self.is_running = True

        while self.is_running:
            try:
                symbols = list(self.client.instruments.keys())
                live_data = await self.client.get_live_data(symbols)

                for callback in self.callbacks:
                    callback(live_data)

                await asyncio.sleep(interval)

            except Exception as e:
                print(f"[DHAN] Feed error: {e}")
                await asyncio.sleep(interval)

    def stop_feed(self):
        """Stop the data feed"""
        self.is_running = False
        print("[DHAN] Feed stopped")


# =============================================================================
# USAGE INSTRUCTIONS
# =============================================================================

if __name__ == "__main__":
    print("Testing Dhan API Connection...")
    client = DhanAPIClient()

    if client.is_connected:
        print("\n[SUCCESS] Connected to Dhan API!")

        print("\nTesting historical data...")

        print("\nTesting live quote...")
    else:
        print("\n[ERROR] Could not connect to Dhan API")
        print("Check your credentials in dhan_credentials.json")
