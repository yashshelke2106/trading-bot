"""
SCHEDULED MARKET SCANNER
Run via cron every 15 minutes on PythonAnywhere
Sends signals to Telegram automatically
"""

import asyncio
import json
import os
import sys
from datetime import datetime, time, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dhan_integration import DhanAPIClient
from telegram_notifier import TelegramNotifier


class ScheduledScanner:
    def __init__(self):
        self.dhan = DhanAPIClient()
        self.telegram = TelegramNotifier()

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

        self.load_last_signals()

    def load_last_signals(self):
        file = "last_signals.json"
        if os.path.exists(file):
            with open(file, "r") as f:
                self.last_signals = json.load(f)
        else:
            self.last_signals = {}

    def save_last_signals(self):
        with open("last_signals.json", "w") as f:
            json.dump(self.last_signals, f)

    def is_market_hours(self) -> bool:
        now = datetime.now()
        now_time = now.time()

        if now.weekday() >= 5:
            return False

        market_start = time(9, 15)
        market_end = time(15, 30)

        if not (market_start <= now_time <= market_end):
            return False

        if self.is_market_holiday(now):
            return False

        return True

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
        date_str = date.strftime("%Y-%m-%d")
        return date_str in holidays_2026

    def get_next_trading_day(self) -> str:
        now = datetime.now()
        days_ahead = 1
        while days_ahead <= 7:
            next_day = now + timedelta(days=days_ahead)
            if next_day.weekday() < 5 and not self.is_market_holiday(next_day):
                return next_day.strftime("%A, %d %B")
            days_ahead += 1
        return "Monday"

    async def get_candles(self, symbol: str) -> list:
        try:
            df = await self.dhan.get_historical_data(symbol, "15min", 3)
            if df is not None and not df.empty:
                return df.tail(30).to_dict("records")
        except:
            pass
        return []

    def calculate_indicators(self, candles: list) -> dict:
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

    def generate_signal(self, indicators: dict, symbol: str) -> dict:
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

        if confidence >= 25:
            if bullish_pct > 60:
                signal = "LONG"
                direction = "BUY"
            elif bullish_pct < 40:
                signal = "SHORT"
                direction = "SELL"

        if rsi < 25:
            signal = "STRONG LONG"
            direction = "BUY"
            confidence = 85
        elif rsi > 75:
            signal = "STRONG SHORT"
            direction = "SELL"
            confidence = 85

        return {
            "symbol": symbol,
            "signal": signal,
            "direction": direction,
            "confidence": min(90, confidence),
            "current": current,
            "rsi": indicators["rsi"],
            "atr": atr,
            "support": indicators["support"],
            "resistance": indicators["resistance"],
            "ema_bullish": ema_bullish,
        }

    def calculate_options(self, signal: dict) -> dict:
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

    def should_send(self, symbol: str, signal_type: str) -> bool:
        current_time = datetime.now().strftime("%H%M")
        key = f"{symbol}_{signal_type}"

        if key not in self.last_signals:
            self.last_signals[key] = {"time": "", "sent": False}

        last_time = self.last_signals[key].get("time", "")

        if current_time != last_time:
            self.last_signals[key] = {"time": current_time, "sent": True}
            self.save_last_signals()
            return True

        return False

    async def scan_and_send(self):
        now = datetime.now()
        now_time = now.time()

        if now.weekday() >= 5:
            if now_time.hour == 9 and now_time.minute < 30:
                next_day = self.get_next_trading_day()
                self.telegram.send_message(
                    f"*MARKET CLOSED*\n\n"
                    f"Today is weekend\n"
                    f"Next trading day: {next_day}\n\n"
                    f"Will resume signals on market open!"
                )
            return

        if self.is_market_holiday(now):
            if now_time.hour == 9 and now_time.minute < 30:
                next_day = self.get_next_trading_day()
                self.telegram.send_message(
                    f"*MARKET HOLIDAY*\n\n"
                    f"Today is a market holiday\n"
                    f"Next trading day: {next_day}\n\n"
                    f"Will resume signals on market open!"
                )
            return

        market_start = time(9, 15)
        market_end = time(15, 30)

        if now_time < market_start:
            if now_time.hour == 9 and now_time.minute < 30:
                self.telegram.send_message(
                    f"*MARKET OPENING SOON*\n\n"
                    f"Current time: {now.strftime('%H:%M')}\n"
                    f"Market opens: 9:15 AM\n"
                    f"First scan in 15 minutes!"
                )
            return

        if now_time > market_end:
            self.telegram.send_message(
                f"*MARKET CLOSED*\n\n"
                f"Trading session ended\n"
                f"Next scan: Tomorrow 9:15 AM\n"
                f"Next trading day: {self.get_next_trading_day()}"
            )
            return

        symbols = [
            "NIFTY",
            "BANKNIFTY",
            "RELIANCE",
            "INFY",
            "TCS",
            "KOTAKBANK",
            "HEROMOTOCO",
            "HDFCBANK",
        ]

        strong_signals = []

        for symbol in symbols:
            candles = await self.get_candles(symbol)
            if candles:
                indicators = self.calculate_indicators(candles)
                signal = self.generate_signal(indicators, symbol)
                options = self.calculate_options(signal)

                if (
                    signal
                    and signal["signal"] not in ["NEUTRAL"]
                    and signal["confidence"] >= 60
                ):
                    if self.should_send(symbol, signal["signal"]):
                        strong_signals.append({"signal": signal, "options": options})

        if strong_signals:
            strong_signals.sort(key=lambda x: x["signal"]["confidence"], reverse=True)

            header = f"*MARKET SCAN - {now.strftime('%H:%M')}*\n\n"
            header += f"Signals: {len(strong_signals)}\n"
            header += f"Market: OPEN\n\n"

            self.telegram.send_message(header)

            for sig in strong_signals[:3]:
                s = sig["signal"]
                o = sig["options"]

                if not o:
                    continue

                emoji = "LONG" if s["direction"] == "BUY" else "SHORT"

                msg = f"""*{s["symbol"]} {o["strike"]} {o["type"]} - {emoji}*

*TRADE*
Entry: Rs.{o["entry"]}
SL: Rs.{o["sl"]}
T1: Rs.{o["t1"]} | T2: Rs.{o["t2"]}

*LOT*
Lot: {o["lot"]}
Capital: Rs.{o["capital"]:,.0f}
Max Loss: Rs.{o["max_loss"]:,.0f}

*INDICATORS*
RSI: {s["rsi"]:.1f}
Support: Rs.{s["support"]}
Resistance: Rs.{s["resistance"]}
Trend: {"BULLISH" if s["ema_bullish"] else "BEARISH"}

*CONF: {s["confidence"]:.0f}%*"""

                self.telegram.send_message(msg)
        else:
            if now_time.hour == 10 and now_time.minute < 15:
                self.telegram.send_message(
                    f"*MARKET SCAN - {now.strftime('%H:%M')}*\n\n"
                    f"No quality signals\n"
                    f"Market: OPEN\n"
                    f"RSI levels: Neutral"
                )


async def main():
    scanner = ScheduledScanner()
    await scanner.scan_and_send()


if __name__ == "__main__":
    asyncio.run(main())
