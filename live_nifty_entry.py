"""
LIVE NIFTY ENTRY FINDER
Real-time analysis for exact entry positions
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dhan_integration import DhanAPIClient


class LiveEntryFinder:
    def __init__(self):
        self.dhan = DhanAPIClient()
        self.is_running = False

    async def get_live_candle(self, symbol: str) -> dict:
        try:
            df = await self.dhan.get_historical_data(symbol, "1min", 20)
            if df is not None and not df.empty:
                return df.tail(20).to_dict("records")
            return []
        except Exception as e:
            print(f"Error: {e}")
            return []

    def analyze_entry(self, candles: list, position: int = 0) -> dict:
        if len(candles) < 15:
            return {"signal": "waiting", "reason": "Collecting data..."}

        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        volumes = [c.get("volume", 0) for c in candles]

        # Moving averages
        ema_9 = sum(closes[-9:]) / 9
        ema_21 = sum(closes[-21:]) / 21

        # RSI
        delta = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gain = [d if d > 0 else 0 for d in delta]
        loss = [-d if d < 0 else 0 for d in delta]
        avg_gain = sum(gain[-14:]) / 14
        avg_loss = sum(loss[-14:]) / 14
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))

        # ATR
        trs = []
        for i in range(1, len(candles)):
            h_l = highs[i] - lows[i]
            h_c = abs(highs[i] - closes[i - 1])
            l_c = abs(lows[i] - closes[i - 1])
            trs.append(max(h_l, h_c, l_c))
        atr = sum(trs[-14:]) / 14 if len(trs) >= 14 else trs[-1]

        # Volume analysis
        vol_avg = sum(volumes[-20:]) / 20
        vol_now = volumes[-1]
        vol_ratio = vol_now / vol_avg if vol_avg > 0 else 1

        # Current price
        current_price = closes[-1]
        prev_close = closes[-2]
        change = (current_price - prev_close) / prev_close * 100

        # Entry levels
        support = min(lows[-5:])
        resistance = max(highs[-5:])

        # Signals
        signal = "NEUTRAL"
        entry_price = None
        stop_loss = None
        target = None
        confidence = 0
        direction = None

        # Bullish conditions
        if ema_9 > ema_21 and rsi < 70 and rsi > 40:
            if change > 0.1:
                signal = "LONG"
                direction = "BUY"
                entry_price = current_price + (atr * 0.3)
                stop_loss = current_price - (atr * 1.0)
                risk = abs(entry_price - stop_loss)
                target = entry_price + (risk * 5)  # 1:5 R:R
                confidence = min(90, 50 + (ema_9 - ema_21) + (50 - abs(50 - rsi)))

        # Bearish conditions
        elif ema_9 < ema_21 and rsi > 30 and rsi < 60:
            if change < -0.1:
                signal = "SHORT"
                direction = "SELL"
                entry_price = current_price - (atr * 0.3)
                stop_loss = current_price + (atr * 1.0)
                risk = abs(entry_price - stop_loss)
                target = entry_price - (risk * 5)  # 1:5 R:R
                confidence = min(90, 50 + (ema_21 - ema_9) + (50 - abs(50 - rsi)))

        # Strong buy signal
        if rsi < 35 and change < -0.5:
            signal = "STRONG BUY"
            direction = "BUY"
            entry_price = current_price
            stop_loss = support - (atr * 0.5)
            risk = abs(entry_price - stop_loss)
            target = entry_price + (risk * 5)  # 1:5 R:R
            confidence = 85

        # Strong sell signal
        if rsi > 65 and change > 0.5:
            signal = "STRONG SELL"
            direction = "SELL"
            entry_price = current_price
            stop_loss = resistance + (atr * 0.5)
            risk = abs(entry_price - stop_loss)
            target = entry_price - (risk * 5)  # 1:5 R:R
            confidence = 85

        return {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "symbol": "NIFTY",
            "current_price": round(current_price, 2),
            "change_pct": round(change, 2),
            "ema_9": round(ema_9, 2),
            "ema_21": round(ema_21, 2),
            "rsi": round(rsi, 1),
            "atr": round(atr, 2),
            "volume_ratio": round(vol_ratio, 2),
            "signal": signal,
            "direction": direction,
            "entry": round(entry_price, 2) if entry_price else None,
            "stop_loss": round(stop_loss, 2) if stop_loss else None,
            "target": round(target, 2) if target else None,
            "support": round(support, 2),
            "resistance": round(resistance, 2),
            "confidence": round(confidence, 0),
        }

    async def run_live(self):
        print("=" * 70)
        print("LIVE NIFTY ENTRY FINDER")
        print("=" * 70)
        print("Monitoring NIFTY for exact entry positions...")
        print("Press Ctrl+C to stop")
        print("=" * 70)

        self.is_running = True
        iteration = 0

        while self.is_running:
            try:
                candles = await self.get_live_candle("NIFTY")
                if candles:
                    analysis = self.analyze_entry(candles)

                    os.system("cls" if os.name == "nt" else "clear")

                    print("=" * 70)
                    print(f"  LIVE NIFTY ANALYSIS - {analysis['timestamp']}")
                    print("=" * 70)
                    print(
                        f"  Price: {analysis['current_price']} ({analysis['change_pct']:+.2f}%)"
                    )
                    print(
                        f"  EMA 9: {analysis['ema_9']} | EMA 21: {analysis['ema_21']}"
                    )
                    print(f"  RSI: {analysis['rsi']} | ATR: {analysis['atr']}")
                    print(f"  Volume: {analysis['volume_ratio']:.1f}x avg")
                    print("-" * 70)
                    print(
                        f"  Signal: {analysis['signal']} (Confidence: {analysis['confidence']:.0f}%)"
                    )
                    print("-" * 70)

                    if analysis["entry"]:
                        risk = abs(analysis["entry"] - analysis["stop_loss"])
                        reward = abs(analysis["target"] - analysis["entry"])
                        print(f"  DIRECTION: {analysis['direction']}")
                        print(f"  Entry: {analysis['entry']}")
                        print(f"  Stop Loss: {analysis['stop_loss']}")
                        print(f"  Target: {analysis['target']}")
                        print(f"  Risk: {risk:.2f} pts")
                        print(f"  Reward: {reward:.2f} pts")
                        print(f"  R:R = 1:{reward / risk:.1f}  [1:5 TARGET]")
                    else:
                        print(f"  No entry signal - {analysis['reason']}")

                    print("-" * 70)
                    print(
                        f"  Support: {analysis['support']} | Resistance: {analysis['resistance']}"
                    )
                    print("=" * 70)
                    print("  Next update in 30 seconds...")

                iteration += 1
                await asyncio.sleep(30)

            except KeyboardInterrupt:
                print("\n[STOPPED] Live analysis stopped.")
                self.is_running = False
                break
            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(10)


async def main():
    finder = LiveEntryFinder()
    await finder.run_live()


if __name__ == "__main__":
    asyncio.run(main())
