"""
TELEGRAM BOT - ON-DEMAND SIGNALS
Respond to commands: /scan, /signals, /help, /accuracy
"""

import requests
import json
import os
import sys
from datetime import datetime, time, timedelta
from typing import Dict, List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dhan_integration import DhanAPIClient
from telegram_notifier import TelegramNotifier


class TradingTelegramBot:
    def __init__(self):
        self.load_config()
        self.token = self.config.get("bot_token")
        self.chat_id = self.config.get("chat_id")
        self.base_url = f"https://api.telegram.org/bot{self.token}"

        self.dhan = DhanAPIClient()

        self.lot_sizes = {
            "NIFTY": 65,
            "BANKNIFTY": 30,
            "FINNIFTY": 25,
            "RELIANCE": 500,
            "TCS": 250,
            "INFY": 250,
            "HDFCBANK": 250,
            "ICICIBANK": 250,
            "KOTAKBANK": 250,
            "SBIN": 250,
            "BAJFINANCE": 250,
            "ITC": 250,
            "HEROMOTOCO": 125,
            "EICHERMOT": 125,
            "MARUTI": 100,
        }

        self.stats = self.load_stats()

    def is_market_holiday(self, date) -> bool:
        holidays_2026 = [
            "2026-01-01",
            "2026-01-26",
            "2026-02-26",
            "2026-03-10",
            "2026-03-30",
            "2026-04-03",
            "2026-04-14",
            "2026-05-01",
            "2026-05-12",
            "2026-08-15",
            "2026-08-27",
            "2026-10-02",
            "2026-10-21",
            "2026-11-04",
            "2026-11-05",
            "2026-12-25",
        ]
        return date.strftime("%Y-%m-%d") in holidays_2026

    def is_market_open(self) -> tuple:
        now = datetime.now()
        now_time = now.time()

        if now.weekday() >= 5:
            return False, "Weekend"
        if self.is_market_holiday(now):
            return False, "Market Holiday"
        if now_time < time(9, 15):
            return False, f"Pre-market (opens 9:15 AM)"
        if now_time > time(15, 30):
            return False, f"Market closed (reopens tomorrow)"
        return True, "Open"

    def get_next_trading_day(self) -> str:
        now = datetime.now()
        for i in range(1, 8):
            next_day = now + timedelta(days=i)
            if next_day.weekday() < 5 and not self.is_market_holiday(next_day):
                return next_day.strftime("%A, %d %B")
        return "Monday"

    def load_config(self):
        config_file = os.path.join(os.path.dirname(__file__), "telegram_config.json")
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                self.config = json.load(f)
        else:
            self.config = {}

    def load_stats(self):
        stats_file = os.path.join(os.path.dirname(__file__), "scanner_stats.json")
        if os.path.exists(stats_file):
            with open(stats_file, "r") as f:
                data = json.load(f)
                return data.get("results", {"wins": 0, "losses": 0})
        return {"wins": 0, "losses": 0}

    def get_updates(self, offset: int = 0) -> List:
        try:
            url = f"{self.base_url}/getUpdates"
            params = {"offset": offset, "timeout": 60}
            response = requests.get(url, params=params, timeout=70)
            data = response.json()
            if data.get("ok"):
                return data.get("result", [])
        except Exception as e:
            print(f"Error getting updates: {e}")
        return []

    def send_message(self, chat_id: int, text: str, parse_mode: str = "Markdown"):
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "reply_markup": self.get_keyboard(),
            }
            requests.post(url, json=data)
        except Exception as e:
            print(f"Error sending message: {e}")

    def get_keyboard(self):
        keyboard = {
            "keyboard": [
                ["/scan", "/signals"],
                ["/accuracy", "/help"],
                ["/top5", "/nifty"],
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False,
        }
        return json.dumps(keyboard)

    async def get_candles(self, symbol: str) -> List:
        try:
            df = await self.dhan.get_historical_data(symbol, "15min", 2)
            if df is not None and not df.empty:
                return df.tail(30).to_dict("records")
        except:
            pass
        return []

    def calculate_indicators(self, candles: List) -> Dict:
        if len(candles) < 20:
            return None

        closes = [c.get("close", 0) for c in candles]
        highs = [c.get("high", 0) for c in candles]
        lows = [c.get("low", 0) for c in candles]

        current = closes[-1]
        ema_9 = sum(closes[-9:]) / 9
        ema_21 = sum(closes[-21:]) / 21

        delta = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gain = [d if d > 0 else 0 for d in delta]
        loss = [-d if d < 0 else 0 for d in delta]
        avg_gain = sum(gain[-14:]) / 14
        avg_loss = sum(loss[-14:]) / 14
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))

        trs = []
        for i in range(1, min(len(candles), 15)):
            h_l = highs[i] - lows[i]
            h_c = abs(highs[i] - closes[i - 1])
            l_c = abs(lows[i] - closes[i - 1])
            trs.append(max(h_l, h_c, l_c))
        atr = sum(trs) / len(trs) if trs else 1

        return {
            "current": current,
            "ema_9": ema_9,
            "ema_21": ema_21,
            "rsi": rsi,
            "atr": atr,
            "support": min(lows[-20:]),
            "resistance": max(highs[-20:]),
            "ema_bullish": ema_9 > ema_21,
            "change_pct": ((current - closes[-2]) / closes[-2] * 100)
            if len(closes) > 1
            else 0,
        }

    def generate_signal(self, indicators: Dict, symbol: str) -> Dict:
        if not indicators:
            return None

        rsi = indicators["rsi"]
        current = indicators["current"]
        atr = indicators["atr"]
        ema_bullish = indicators["ema_bullish"]

        bullish_score = 0
        bearish_score = 0

        if rsi < 30:
            bullish_score += 30
        elif rsi < 40:
            bullish_score += 15
        elif rsi > 70:
            bearish_score += 30
        elif rsi > 60:
            bearish_score += 15

        if ema_bullish:
            bullish_score += 15
        else:
            bearish_score += 15

        if indicators["change_pct"] < -1:
            bullish_score += 15
        elif indicators["change_pct"] > 1:
            bearish_score += 15

        total = bullish_score + bearish_score
        bullish_pct = (bullish_score / total * 100) if total > 0 else 50
        confidence = abs(bullish_score - bearish_score)

        signal = "NEUTRAL"
        direction = None
        entry = current
        sl = None
        target = None

        if confidence >= 25:
            if bullish_pct > 60:
                signal = "LONG"
                direction = "BUY"
                sl = current - (atr * 1.0)
                target = current + (atr * 3)
            elif bullish_pct < 40:
                signal = "SHORT"
                direction = "SELL"
                sl = current + (atr * 1.0)
                target = current - (atr * 3)

        if rsi < 25:
            signal = "STRONG LONG"
            direction = "BUY"
            sl = indicators["support"] - (atr * 0.5)
            target = current + (atr * 3)
            confidence = 85

        if rsi > 75:
            signal = "STRONG SHORT"
            direction = "SELL"
            sl = indicators["resistance"] + (atr * 0.5)
            target = current - (atr * 3)
            confidence = 85

        return {
            "symbol": symbol,
            "signal": signal,
            "direction": direction,
            "confidence": min(90, confidence),
            "entry": round(entry, 2),
            "sl": round(sl, 2) if sl else None,
            "target": round(target, 2) if target else None,
            "rsi": round(indicators["rsi"], 1),
            "atr": round(indicators["atr"], 2),
            "current": round(current, 2),
            "support": round(indicators["support"], 2),
            "resistance": round(indicators["resistance"], 2),
            "ema_bullish": ema_bullish,
        }

    def calculate_options(self, signal: Dict) -> Dict:
        if not signal or signal["signal"] == "NEUTRAL":
            return None

        symbol = signal["symbol"]
        lot = self.lot_sizes.get(symbol, 1)
        direction = signal["direction"]
        current = signal["current"]
        atr = signal["atr"]

        if direction == "BUY":
            strike_type = "CE"
            strike = int(current - (current % 50)) + 50
            entry_prem = max(atr * 0.6, current * 0.02)
        else:
            strike_type = "PE"
            strike = int(current - (current % 50))
            entry_prem = max(atr * 0.6, current * 0.02)

        sl_prem = entry_prem * 0.5
        t1_prem = entry_prem + (entry_prem * 1.5)
        t2_prem = entry_prem + (entry_prem * 3)

        return {
            "symbol": symbol,
            "strike": strike,
            "type": strike_type,
            "direction": direction,
            "entry": round(entry_prem, 2),
            "sl": round(sl_prem, 2),
            "t1": round(t1_prem, 2),
            "t2": round(t2_prem, 2),
            "lot": lot,
            "capital": round(entry_prem * lot, 2),
            "max_loss": round(sl_prem * lot, 2),
            "max_profit": round(t1_prem * lot, 2),
        }

    async def scan_single(self, symbol: str) -> Dict:
        candles = await self.get_candles(symbol)
        if candles:
            indicators = self.calculate_indicators(candles)
            signal = self.generate_signal(indicators, symbol)
            options = self.calculate_options(signal)
            return {"indicators": indicators, "signal": signal, "options": options}
        return None

    def format_signal_message(self, data: Dict) -> str:
        if not data or not data.get("signal"):
            return "No signal data available"

        s = data["signal"]
        o = data["options"]

        if not o or s["signal"] == "NEUTRAL":
            return f"*{s['symbol']}*\n\nSignal: NEUTRAL\nRSI: {s['rsi']}\nCurrent: Rs.{s['current']}\n\nNo trade setup"

        emoji = "LONG" if s["direction"] == "BUY" else "SHORT"

        msg = f"""*{s["symbol"]} {o["strike"]} {o["type"]} - {emoji}*

*TRADE*
Entry: Rs.{o["entry"]}
SL: Rs.{o["sl"]}
T1: Rs.{o["t1"]} | T2: Rs.{o["t2"]}

*LOT SIZE*
Lot: {o["lot"]}
Capital: Rs.{o["capital"]:,.0f}
Max Loss: Rs.{o["max_loss"]:,.0f}
Max Profit: Rs.{o["max_profit"]:,.0f}

*INDICATORS*
RSI: {s["rsi"]}
Support: Rs.{s["support"]}
Resistance: Rs.{s["resistance"]}
Trend: {"BULLISH" if s["ema_bullish"] else "BEARISH"}

*CONFIDENCE: {s["confidence"]:.0f}%*"""

        return msg

    async def handle_command(self, command: str, chat_id: int):
        if command == "/start":
            is_open, status = self.is_market_open()
            next_day = self.get_next_trading_day()

            msg = f"""*TRADING BOT ACTIVE*

Welcome! Automated trading assistant.

*Market Status:* {status}
{"" if is_open else f"Next trading day: {next_day}"}

*Commands:*
/scan - Scan all stocks
/signals - Current signals
/top5 - Top 5 trades
/nifty - NIFTY analysis
/accuracy - Bot accuracy
/market - Check market status
/help - All commands"""
            self.send_message(chat_id, msg)

        elif command == "/market":
            is_open, status = self.is_market_open()
            next_day = self.get_next_trading_day()

            msg = f"""*MARKET STATUS*

Status: {status}
Current time: {datetime.now().strftime("%H:%M")}

Market hours: 9:15 AM - 3:30 PM
Trading days: Mon-Fri

{"" if is_open else f"Next trading day: {next_day}"}"""
            self.send_message(chat_id, msg)

        elif command == "/help":
            msg = """*AVAILABLE COMMANDS*

/scan - Scan all stocks for signals
/signals - Show current trade setups
/top5 - Top 5 high confidence trades
/nifty - NIFTY analysis only
/accuracy - Bot accuracy stats
/help - Show this message

*Trade Setup:*
Each signal includes:
- Entry, SL, Target
- Lot size, Capital
- RSI, Support, Resistance
- Confidence score"""
            self.send_message(chat_id, msg)

        elif command == "/accuracy":
            wins = self.stats.get("wins", 0)
            losses = self.stats.get("losses", 0)
            total = wins + losses
            accuracy = (wins / total * 100) if total > 0 else 0

            msg = f"""*BOT ACCURACY*

Wins: {wins}
Losses: {losses}
Total Trades: {total}
Accuracy: {accuracy:.1f}%

Auto-execute: {"ENABLED" if accuracy >= 60 else "DISABLED"}
Target: 60% accuracy"""
            self.send_message(chat_id, msg)

        elif command == "/nifty":
            is_open, status = self.is_market_open()
            if not is_open:
                self.send_message(
                    chat_id, f"Market is {status}.\nUse /market for details."
                )
                return

            self.send_message(chat_id, "Scanning NIFTY...")
            data = await self.scan_single("NIFTY")
            if data:
                msg = self.format_signal_message(data)
                self.send_message(chat_id, msg)
            else:
                self.send_message(chat_id, "Error scanning NIFTY. Try again later.")

        elif command == "/scan":
            is_open, status = self.is_market_open()
            if not is_open:
                self.send_message(
                    chat_id, f"Market is {status}.\nUse /market for details."
                )
                return

            self.send_message(chat_id, "Scanning all stocks...")

            symbols = [
                "NIFTY",
                "BANKNIFTY",
                "RELIANCE",
                "INFY",
                "TCS",
                "KOTAKBANK",
                "HDFCBANK",
                "SBIN",
                "ITC",
                "HEROMOTOCO",
                "EICHERMOT",
            ]

            results = []
            for symbol in symbols:
                data = await self.scan_single(symbol)
                if data and data["signal"]["signal"] != "NEUTRAL":
                    if data["signal"]["confidence"] >= 50:
                        results.append(data)

            if results:
                results.sort(key=lambda x: x["signal"]["confidence"], reverse=True)

                msg = f"*SCAN COMPLETE - {len(results)} SIGNALS*\n\n"

                for i, r in enumerate(results[:5], 1):
                    s = r["signal"]
                    o = r["options"]
                    emoji = "LONG" if s["direction"] == "BUY" else "SHORT"
                    msg += f"{i}. {s['symbol']} {o['strike']} {o['type']} - {emoji}\n"
                    msg += f"   Entry: {o['entry']} | Conf: {s['confidence']:.0f}%\n\n"

                self.send_message(chat_id, msg)

                for r in results[:2]:
                    msg = self.format_signal_message(r)
                    self.send_message(chat_id, msg)
            else:
                self.send_message(chat_id, "No signals found. Market may be ranging.")

        elif command == "/signals":
            is_open, status = self.is_market_open()
            if not is_open:
                self.send_message(
                    chat_id, f"Market is {status}.\nUse /market for details."
                )
                return

            self.send_message(chat_id, "Fetching current signals...")

            symbols = [
                "NIFTY",
                "BANKNIFTY",
                "RELIANCE",
                "INFY",
                "TCS",
                "KOTAKBANK",
                "HEROMOTOCO",
            ]

            signals = []
            for symbol in symbols:
                data = await self.scan_single(symbol)
                if (
                    data
                    and data["signal"]["signal"] != "NEUTRAL"
                    and data["signal"]["confidence"] >= 55
                ):
                    signals.append(data)

            if signals:
                signals.sort(key=lambda x: x["signal"]["confidence"], reverse=True)

                for r in signals[:3]:
                    msg = self.format_signal_message(r)
                    self.send_message(chat_id, msg)
            else:
                self.send_message(
                    chat_id, "No active signals. Try /scan for full analysis."
                )

        elif command == "/top5":
            is_open, status = self.is_market_open()
            if not is_open:
                self.send_message(
                    chat_id, f"Market is {status}.\nUse /market for details."
                )
                return

            self.send_message(chat_id, "Finding top 5 trades...")

            symbols = [
                "NIFTY",
                "BANKNIFTY",
                "RELIANCE",
                "INFY",
                "TCS",
                "KOTAKBANK",
                "HDFCBANK",
                "SBIN",
                "ITC",
                "HEROMOTOCO",
                "EICHERMOT",
                "MARUTI",
            ]

            all_signals = []
            for symbol in symbols:
                data = await self.scan_single(symbol)
                if data and data["signal"]["signal"] != "NEUTRAL":
                    all_signals.append(data)

            if all_signals:
                all_signals.sort(key=lambda x: x["signal"]["confidence"], reverse=True)

                for r in all_signals[:5]:
                    msg = self.format_signal_message(r)
                    self.send_message(chat_id, msg)
            else:
                self.send_message(chat_id, "No quality trades found.")

    async def run(self):
        print("=" * 60)
        print("TELEGRAM TRADING BOT")
        print("Commands: /scan /signals /top5 /nifty /help")
        print("=" * 60)

        await self.send_message(
            int(self.chat_id),
            "*Trading Bot Online*\n\nCommands:\n/scan - Scan all\n/signals - Current signals\n/top5 - Best trades\n/nifty - NIFTY only\n/accuracy - Stats",
        )

        offset = 0

        while True:
            try:
                updates = self.get_updates(offset)

                for update in updates:
                    offset = update["update_id"] + 1

                    if "message" in update:
                        chat_id = update["message"]["chat"]["id"]
                        text = update["message"].get("text", "")

                        if text.startswith("/"):
                            print(f"Command received: {text}")
                            await self.handle_command(text.strip(), chat_id)

                await asyncio.sleep(1)

            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(5)


import asyncio

if __name__ == "__main__":
    bot = TradingTelegramBot()
    asyncio.run(bot.run())
