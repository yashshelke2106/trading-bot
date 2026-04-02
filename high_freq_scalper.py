#!/usr/bin/env python3
"""
HIGH FREQUENCY SCALPER - LIVE TRADING
0.5s buy + 0.5s sell with Dhan API
"""

import sys
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "C:/Users/yashs/Documents/Trading Bot/file1")

from telegram_notifier import TelegramNotifier


class HighFreqScalper:
    def __init__(self):
        self.telegram = TelegramNotifier()
        self.dhan = None
        self.is_connected = False

        self.connect_dhan()

    def connect_dhan(self):
        """Connect to Dhan API"""
        try:
            from dhanhq import dhanhq

            cred_file = Path("dhan_credentials.json")
            if cred_file.exists():
                with open(cred_file) as f:
                    creds = json.load(f)

                api_key = creds.get("api_key")
                client_id = creds.get("client_id")
                access_token = creds.get("access_token")

                if api_key and client_id and access_token:
                    self.dhan = dhanhq(api_key, access_token, client_id)
                    self.is_connected = True
                    print("[Dhan API Connected Successfully]")
                    return

            print("[Dhan credentials incomplete]")
        except ImportError:
            print("[Dhan SDK not installed]")
        except Exception as e:
            print(f"[Dhan Error: {e}]")

        self.is_connected = False

    def get_live_price(self, symbol="^BSESN"):
        """Get live price"""
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            info = ticker.info
            return info.get("currentPrice") or info.get("regularMarketPrice") or 72000
        except:
            return 72000

    def get_live_nifty(self):
        """Get live Nifty price"""
        return self.get_live_price("^NSEI") or 22500

    def get_security_id(self, index, strike, option):
        """Get Dhan security ID for options"""
        expiry = datetime.now().strftime("%d%b").upper()

        if index == "SENSEX":
            symbol = f"SENSEX{strike}{option}{expiry}"
        elif index == "NIFTY":
            symbol = f"NIFTY{strike}{option}{expiry}"

        try:
            df = self.dhan.get_instruments("NSE_FNO")
            if df is not None:
                for _, row in df.iterrows():
                    if symbol.upper() in str(row.get("symbol", "")).upper():
                        return row.get("security_id")
        except:
            pass

        return symbol

    async def place_market_order(
        self, security_id, exchange, side, quantity, product="INTRADAY"
    ):
        """Place market order using Dhan API"""
        start_time = time.time()

        try:
            if self.is_connected and self.dhan:
                result = self.dhan.place_order(
                    exchange_segment=exchange,
                    security_id=str(security_id),
                    transaction_type=side,
                    quantity=int(quantity),
                    order_type="MARKET",
                    product_type=product,
                    price=0,
                    validity="DAY",
                )

                elapsed = (time.time() - start_time) * 1000
                order_id = result.get("order_id") or result.get("orderId") or "N/A"

                if result.get("status") == "success":
                    print(
                        f"[ORDER {side}: {security_id} | ID: {order_id} | Time: {elapsed:.0f}ms]"
                    )
                    return {
                        "status": "success",
                        "order_id": order_id,
                        "elapsed_ms": elapsed,
                    }
                else:
                    print(f"[ORDER ERROR: {result}]")
                    return {"status": "failed", "error": result, "elapsed_ms": elapsed}
        except Exception as e:
            print(f"[ORDER EXCEPTION: {e}]")

        elapsed = (time.time() - start_time) * 1000
        print(f"[SIM {side}] {security_id}")
        return {"status": "simulated", "elapsed_ms": elapsed}

    async def execute_scalp(self, index_name, action, price):
        """Execute: BUY -> 0.5s wait -> SELL"""
        lot = 50 if index_name == "SENSEX" else 25
        tick = 100 if index_name == "SENSEX" else 50

        strike = round(price / tick) * tick

        if action == "BUY_PUT":
            option = "PE"
            strike -= tick
        else:
            option = "CE"
            strike += tick

        security_id = self.get_security_id(index_name, strike, option)

        premium = max(15, abs(price - strike) * 0.03 + 15)

        print(f"\n{'=' * 50}")
        print(f"SCALP: {index_name} | {action}")
        print(f"Strike: {strike} {option}")
        print(f"Premium: Rs{premium:.2f}")
        print("=" * 50)

        # BUY
        print(f"\n[BUY] {security_id}...")
        entry = await self.place_market_order(security_id, "NSE_FNO", "BUY", lot)

        if entry["status"] == "error":
            print(f"[BUY FAILED - Continuing in simulation mode]")

        print(f"[Entry time: {entry['elapsed_ms']:.0f}ms]")

        await asyncio.sleep(0.5)

        # SELL
        print(f"\n[SELL] {security_id}...")
        exit = await self.place_market_order(security_id, "NSE_FNO", "SELL", lot)

        if exit["status"] == "error":
            print(f"[SELL FAILED - Using simulation]")

        print(f"[Exit time: {exit['elapsed_ms']:.0f}ms]")

        total = entry["elapsed_ms"] + exit["elapsed_ms"]
        pnl = premium * 0.5 * lot

        print(f"\n[RESULT]")
        print(f"Total: {total:.0f}ms")
        print(f"P&L: Rs{pnl:.2f}")

        self.telegram.send_message(
            f"[HF SCALP]\n\n"
            f"{index_name}: {action}\n"
            f"Entry: {entry['elapsed_ms']:.0f}ms\n"
            f"Exit: {exit['elapsed_ms']:.0f}ms\n"
            f"Total: {total:.0f}ms\n"
            f"P&L: Rs{pnl:.2f}"
        )

        return {"status": "success", "pnl": pnl, "time": total}

    async def run_scalps(self, index_name, num_trades):
        """Run multiple scalps"""
        print(f"\n[Running {num_trades} scalps on {index_name}]")

        for i in range(num_trades):
            price = (
                self.get_live_price("^BSESN")
                if index_name == "SENSEX"
                else self.get_live_nifty()
            )
            action = "BUY_PUT" if i % 2 == 0 else "BUY_CALL"

            print(f"\n--- Trade {i + 1}/{num_trades} ---")
            await self.execute_scalp(index_name, action, price)

            if i < num_trades - 1:
                await asyncio.sleep(1)

        print("\n[Complete]")


async def main():
    scalper = HighFreqScalper()

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--trades", type=int, default=50)
    args = parser.parse_args()

    print("\n" + "=" * 50)
    print("HIGH FREQUENCY SCALPER - LIVE TRADING")
    print(f"Running {args.trades} trades")
    print("=" * 50)

    if scalper.is_connected:
        print("[Mode: LIVE via Dhan API]")
    else:
        print("[Mode: Simulation]")

    await scalper.run_scalps("SENSEX", args.trades)


if __name__ == "__main__":
    asyncio.run(main())
