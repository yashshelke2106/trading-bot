"""
EXPIRY DAY SCALPER
Scalping strategy for Nifty 50, Sensex on expiry days
High volatility, tight stops, quick trades
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dhan_integration import DhanAPIClient
from telegram_notifier import TelegramNotifier


class ExpiryScalper:
    def __init__(self):
        self.dhan = DhanAPIClient()
        self.telegram = TelegramNotifier()
        self.positions = {}
        self.trades_log = []
        self.paper_mode = self.dhan.credentials.get("paper_mode", True)

        self.config = {
            "indices": ["NIFTY", "SENSEX"],
            "timeframe": "1min",
            "lookback_candles": 20,
            "max_positions": 2,
            "risk_per_trade": 0.005,
            "max_loss_per_day": 0.02,
            "profit_target": 0.008,
            "stop_loss_pct": 0.003,
            "trailing_activation": 0.005,
            "trailing_distance": 0.002,
        }

        self.daily_stats = {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "pnl": 0,
            "start_time": datetime.now(),
        }

    def is_expiry_day(self) -> bool:
        today = datetime.now()
        days_until_thursday = (3 - today.weekday()) % 7
        if days_until_thursday == 0 and today.hour < 15:
            return True
        elif days_until_thursday == 1 and today.hour >= 15:
            return True
        return False

    def get_next_expiry(self) -> str:
        today = datetime.now()
        days_until_thursday = (3 - today.weekday()) % 7
        if days_until_thursday == 0 and today.hour >= 15:
            days_until_thursday = 7
        expiry = today + timedelta(days=days_until_thursday)
        return expiry.strftime("%d%b").upper()

    async def fetch_live_candles(self, symbol: str, candles: int = 30) -> pd.DataFrame:
        try:
            df = await self.dhan.get_historical_data(symbol, "1min", 1)
            if df is not None and len(df) >= candles:
                return df.tail(candles)
            return pd.DataFrame()
        except Exception as e:
            print(f"[SCALPER] Error fetching {symbol}: {e}")
            return self._generate_sample_candles(symbol, candles)

    def _generate_sample_candles(self, symbol: str, candles: int) -> pd.DataFrame:
        base = {"NIFTY": 23500, "SENSEX": 77500}.get(symbol, 20000)
        data = []
        now = datetime.now()

        for i in range(candles):
            ts = now - timedelta(minutes=candles - i)
            open_p = base + np.random.randint(-50, 50)
            close_p = open_p + np.random.randint(-30, 30)
            high_p = max(open_p, close_p) + np.random.randint(0, 20)
            low_p = min(open_p, close_p) - np.random.randint(0, 20)
            vol = np.random.randint(50000, 200000)

            data.append(
                {
                    "timestamp": ts,
                    "open": open_p,
                    "high": high_p,
                    "low": low_p,
                    "close": close_p,
                    "volume": vol,
                }
            )

        return pd.DataFrame(data).set_index("timestamp")

    def analyze_momentum(self, df: pd.DataFrame) -> Dict:
        if df.empty or len(df) < 15:
            return {"signal": "neutral", "strength": 0}

        df = df.copy()
        df["ema_5"] = df["close"].ewm(span=5).mean()
        df["ema_10"] = df["close"].ewm(span=10).mean()
        df["ema_20"] = df["close"].ewm(span=20).mean()

        df["rsi"] = self._calculate_rsi(df["close"], 7)
        df["atr"] = self._calculate_atr(df, 7)

        df["volume_ma"] = df["volume"].rolling(10).mean()
        df["volume_ratio"] = df["volume"] / df["volume_ma"]

        last = df.iloc[-1]
        prev = df.iloc[-2]

        up_moves = sum(
            1
            for i in range(-1, -6, -1)
            if df.iloc[i]["close"] > df.iloc[i - 1]["close"]
        )
        momentum = up_moves / 5

        ema_bullish = last["ema_5"] > last["ema_10"] > last["ema_20"]
        ema_bearish = last["ema_5"] < last["ema_10"] < last["ema_20"]

        rsi_val = last["rsi"]
        vol_surge = last["volume_ratio"] > 1.3

        price_change = (last["close"] - prev["close"]) / prev["close"] * 100

        if (
            ema_bullish
            and rsi_val > 55
            and rsi_val < 75
            and (momentum > 0.6 or price_change > 0.1)
        ):
            signal = "long"
            strength = min(100, int(momentum * 100 + (rsi_val - 55) * 2))
        elif (
            ema_bearish
            and rsi_val < 45
            and rsi_val > 25
            and (momentum < 0.4 or price_change < -0.1)
        ):
            signal = "short"
            strength = min(100, int((1 - momentum) * 100 + (45 - rsi_val) * 2))
        else:
            signal = "neutral"
            strength = 0

        return {
            "signal": signal,
            "strength": strength,
            "rsi": rsi_val,
            "atr": last["atr"],
            "ema_5": last["ema_5"],
            "ema_10": last["ema_10"],
            "price": last["close"],
            "volume_ratio": last["volume_ratio"],
            "momentum": momentum,
        }

    def _calculate_rsi(self, prices: pd.Series, period: int = 7) -> pd.Series:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss.replace(0, 0.0001)
        return 100 - (100 / (1 + rs))

    def _calculate_atr(self, df: pd.DataFrame, period: int = 7) -> float:
        high_low = df["high"] - df["low"]
        high_close = abs(df["high"] - df["close"].shift())
        low_close = abs(df["low"] - df["close"].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(period).mean().iloc[-1]

    def calculate_levels(self, price: float, atr: float, direction: str) -> Dict:
        if direction == "long":
            entry = price + (atr * 0.3)
            sl = price - (atr * 0.8)
            target = entry + (atr * 1.5)
        else:
            entry = price - (atr * 0.3)
            sl = price + (atr * 0.8)
            target = entry - (atr * 1.5)

        return {
            "entry": round(entry, 2),
            "stop_loss": round(sl, 2),
            "target": round(target, 2),
            "risk": abs(entry - sl),
            "reward": abs(target - entry),
        }

    async def scan_indices(self) -> List[Dict]:
        signals = []

        for index in self.config["indices"]:
            df = await self.fetch_live_candles(index, 25)
            if df.empty:
                continue

            analysis = self.analyze_momentum(df)

            if analysis["signal"] != "neutral" and analysis["strength"] >= 60:
                levels = self.calculate_levels(
                    analysis["price"], analysis["atr"], analysis["signal"]
                )

                signal = {
                    "symbol": index,
                    "signal": analysis["signal"],
                    "strength": analysis["strength"],
                    "entry": levels["entry"],
                    "stop_loss": levels["stop_loss"],
                    "target": levels["target"],
                    "rsi": round(analysis["rsi"], 1),
                    "atr": round(analysis["atr"], 2),
                    "timestamp": datetime.now(),
                }
                signals.append(signal)

                await self.telegram.send_message(
                    f"📊 *{index} EXPIRY SIGNAL*\n"
                    f"Direction: *{signal['signal'].upper()}*\n"
                    f"Entry: `{signal['entry']}`\n"
                    f"SL: `{signal['stop_loss']}`\n"
                    f"Target: `{signal['target']}`\n"
                    f"Confidence: `{signal['strength']}%`\n"
                    f"RSI: `{signal['rsi']}` | ATR: `{signal['atr']}`"
                )

        return signals

    async def execute_trade(self, signal: Dict) -> Optional[Dict]:
        if len(self.positions) >= self.config["max_positions"]:
            return None

        symbol = signal["symbol"]
        if symbol in self.positions:
            return None

        capital = 100000
        risk_amount = capital * self.config["risk_per_trade"]

        price = signal["entry"]
        sl_diff = abs(price - signal["stop_loss"])
        quantity = int(risk_amount / sl_diff)

        if quantity < 1:
            quantity = 1

        trade = {
            "symbol": symbol,
            "side": signal["signal"],
            "entry": price,
            "quantity": quantity,
            "stop_loss": signal["stop_loss"],
            "target": signal["target"],
            "entry_time": datetime.now(),
            "status": "open",
            "pnl": 0,
            "trail_active": False,
            "trail_price": None,
        }

        if self.paper_mode:
            print(f"[PAPER] LONG {quantity} {symbol} @ {price}")
            trade["order_id"] = f"PAPER_{datetime.now().strftime('%H%M%S')}"
        else:
            result = await self.dhan.place_order(
                symbol=symbol,
                side="BUY" if signal["signal"] == "long" else "SELL",
                quantity=quantity,
                price=price,
                stop_loss=signal["stop_loss"],
            )
            trade["order_id"] = result.get("order_id")

        self.positions[symbol] = trade
        self.daily_stats["trades"] += 1

        return trade

    async def monitor_positions(self):
        if not self.positions:
            return

        for symbol, pos in list(self.positions.items()):
            if pos["status"] != "open":
                continue

            try:
                quote = self.dhan.get_quote(symbol)
                if quote:
                    current_price = quote.get("ltp", pos["entry"])
                else:
                    df = await self.fetch_live_candles(symbol, 5)
                    current_price = (
                        df.iloc[-1]["close"] if not df.empty else pos["entry"]
                    )
            except:
                current_price = pos["entry"]

            pnl_pct = (current_price - pos["entry"]) / pos["entry"] * 100
            if pos["side"] == "short":
                pnl_pct = -pnl_pct

            pos["pnl"] = pnl_pct
            pos["current_price"] = current_price

            trail_activation = self.config["trailing_activation"] * 100
            trail_dist = self.config["trailing_distance"] * 100

            if pnl_pct >= trail_activation and not pos["trail_active"]:
                pos["trail_active"] = True
                pos["trail_price"] = pos["entry"] + (pos["target"] - pos["entry"]) * 0.3

            if pos["trail_active"] and pos["trail_price"]:
                if pos["side"] == "long" and current_price > pos["trail_price"]:
                    new_trail = current_price - (pos["target"] - pos["entry"]) * 0.15
                    pos["trail_price"] = min(new_trail, pos["trail_price"])
                elif pos["side"] == "short" and current_price < pos["trail_price"]:
                    new_trail = current_price + (pos["entry"] - pos["target"]) * 0.15
                    pos["trail_price"] = max(new_trail, pos["trail_price"])

                if pos["side"] == "long":
                    pos["stop_loss"] = max(pos["stop_loss"], pos["trail_price"])
                else:
                    pos["stop_loss"] = min(pos["stop_loss"], pos["trail_price"])

            sl_hit = pos["side"] == "long" and current_price <= pos["stop_loss"]
            target_hit = pos["side"] == "long" and current_price >= pos["target"]

            if pos["side"] == "short":
                sl_hit = current_price >= pos["stop_loss"]
                target_hit = current_price <= pos["target"]

            if target_hit:
                await self._close_trade(pos, "TARGET HIT", current_price)
            elif sl_hit:
                await self._close_trade(pos, "SL HIT", current_price)

    async def _close_trade(self, pos: Dict, reason: str, exit_price: float):
        pos["status"] = "closed"
        pos["exit_price"] = exit_price
        pos["exit_time"] = datetime.now()
        pos["reason"] = reason

        pnl = (exit_price - pos["entry"]) * pos["quantity"]
        if pos["side"] == "short":
            pnl = -pnl

        pos["realized_pnl"] = pnl
        self.daily_stats["pnl"] += pnl

        if pnl > 0:
            self.daily_stats["wins"] += 1
        else:
            self.daily_stats["losses"] += 1

        self.trades_log.append(pos)

        emoji = "✅" if pnl > 0 else "❌"
        await self.telegram.send_message(
            f"{emoji} *TRADE CLOSED*\n"
            f"{pos['symbol']} {pos['side'].upper()}\n"
            f"Entry: `{pos['entry']}` | Exit: `{exit_price}`\n"
            f"P&L: `{pnl:.2f}` ({pos['pnl']:.2f}%)\n"
            f"Reason: {reason}"
        )

        del self.positions[pos["symbol"]]

    def print_status(self):
        os.system("cls" if os.name == "nt" else "clear")

        expiry = self.get_next_expiry()
        print(f"═══════════════════════════════════════════")
        print(f"   EXPIRY SCALPER - {expiry} EXPIRY")
        print(f"═══════════════════════════════════════════")
        print(f"Mode: {'PAPER' if self.paper_mode else 'LIVE'}")
        print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
        print(f"Expiry Day: {'YES' if self.is_expiry_day() else 'NO'}")
        print()
        print(f"─── TODAY'S STATS ───")
        print(
            f"Trades: {self.daily_stats['trades']} | W: {self.daily_stats['wins']} | L: {self.daily_stats['losses']}"
        )
        print(f"P&L: {self.daily_stats['pnl']:.2f}")
        print()

        if self.positions:
            print(f"─── OPEN POSITIONS ───")
            for sym, pos in self.positions.items():
                side_emoji = "🟢" if pos["side"] == "long" else "🔴"
                trail = (
                    f" | Trail: {pos['stop_loss']:.2f}"
                    if pos.get("trail_active")
                    else ""
                )
                print(
                    f"{side_emoji} {sym}: {pos['pnl']:.2f}% | SL: {pos['stop_loss']:.2f}{trail}"
                )
        else:
            print("─── No open positions ───")

        print(f"\n═══════════════════════════════════════════")

    async def run(self):
        print("Starting Expiry Scalper...")

        if self.paper_mode:
            print("[PAPER MODE] No real orders will be placed")

        await self.telegram.send_message("🚀 Expiry Scalper Started")

        scan_interval = 60
        iteration = 0

        while True:
            try:
                if self.is_expiry_day():
                    signals = await self.scan_indices()

                    for signal in signals:
                        if self.daily_stats["pnl"] < -self.daily_stats[
                            "start_time"
                        ].strftime("%Y-%m-%d"):
                            print("[SCALPER] Daily loss limit reached")
                            break

                        trade = await self.execute_trade(signal)
                        if trade:
                            print(f"Trade executed: {trade}")

                await self.monitor_positions()

                self.print_status()

                iteration += 1
                await asyncio.sleep(scan_interval)

            except KeyboardInterrupt:
                print("\n[SCALPER] Stopping...")
                break
            except Exception as e:
                print(f"[SCALPER] Error: {e}")
                await asyncio.sleep(30)


async def main():
    scalper = ExpiryScalper()

    if not scalper.is_expiry_day():
        print("⚠️  Today is NOT an expiry day. Signals may be limited.")
        print("Expiry scalper works best on Thursday expiry days.")

    await scalper.run()


if __name__ == "__main__":
    asyncio.run(main())
