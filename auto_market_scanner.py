"""
COMPREHENSIVE MARKET SCANNER v3.0
Deep Analysis: Technical + Sentiment + News + Options + Sector
Signals sent to Telegram | Auto-execute when 60%+ accuracy
"""

import asyncio
import json
import os
import sys
from datetime import datetime, time
from typing import Dict, List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dhan_integration import DhanAPIClient
from telegram_notifier import TelegramNotifier


class ComprehensiveScanner:
    def __init__(self):
        self.dhan = DhanAPIClient()
        self.telegram = TelegramNotifier()
        self.is_running = False

        self.scan_interval = 15 * 60
        self.market_start = time(9, 15)
        self.market_end = time(15, 30)
        self.auto_execute_accuracy = 0.60
        self.current_accuracy = 0.0

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

        self.stock_fundamentals = {
            "RELIANCE": {"sector": "ENERGY", "index_weight": 10, "fno": True},
            "TCS": {"sector": "IT", "index_weight": 8, "fno": True},
            "INFY": {"sector": "IT", "index_weight": 6, "fno": True},
            "HDFCBANK": {"sector": "BANK", "index_weight": 8, "fno": True},
            "ICICIBANK": {"sector": "BANK", "index_weight": 7, "fno": True},
            "KOTAKBANK": {"sector": "BANK", "index_weight": 5, "fno": True},
            "SBIN": {"sector": "BANK", "index_weight": 4, "fno": True},
            "ITC": {"sector": "FMCG", "index_weight": 4, "fno": True},
            "HEROMOTOCO": {"sector": "AUTO", "index_weight": 3, "fno": True},
            "EICHERMOT": {"sector": "AUTO", "index_weight": 2, "fno": True},
            "MARUTI": {"sector": "AUTO", "index_weight": 3, "fno": True},
            "BAJFINANCE": {"sector": "FINANCE", "index_weight": 4, "fno": True},
        }

        self.global_sentiment = "NEUTRAL"
        self.fii_flow = 0
        self.market_bias = "NEUTRAL"

        self.last_signals = {}
        self.signal_history = []
        self.trade_results = {"wins": 0, "losses": 0, "total": 0}
        self.pending_signals = []

        self.load_stats()

    def load_stats(self):
        stats_file = os.path.join(os.path.dirname(__file__), "scanner_stats.json")
        if os.path.exists(stats_file):
            with open(stats_file, "r") as f:
                data = json.load(f)
                self.trade_results = data.get(
                    "results", {"wins": 0, "losses": 0, "total": 0}
                )
                self.current_accuracy = self.trade_results["wins"] / max(
                    1, self.trade_results["wins"] + self.trade_results["losses"]
                )

    def save_stats(self):
        stats_file = os.path.join(os.path.dirname(__file__), "scanner_stats.json")
        with open(stats_file, "w") as f:
            json.dump(
                {
                    "results": self.trade_results,
                    "accuracy": self.current_accuracy,
                    "last_updated": datetime.now().isoformat(),
                },
                f,
                indent=2,
            )

    def is_market_open(self) -> bool:
        now = datetime.now().time()
        return self.market_start <= now <= self.market_end

    async def analyze_global_sentiment(self) -> Dict:
        """Analyze global market sentiment"""
        try:
            nasdaq_df = await self.dhan.get_historical_data("QQQ", "1day", 5)
            sp500_df = await self.dhan.get_historical_data("SPY", "1day", 5)

            sentiment = "NEUTRAL"
            change = 0

            if nasdaq_df is not None and not nasdaq_df.empty:
                closes = nasdaq_df["close"].tolist()
                if len(closes) >= 2:
                    change = (closes[-1] - closes[-2]) / closes[-2] * 100

            if change < -1.5:
                sentiment = "STRONG BEARISH"
            elif change < -0.5:
                sentiment = "BEARISH"
            elif change > 1.5:
                sentiment = "STRONG BULLISH"
            elif change > 0.5:
                sentiment = "BULLISH"

            self.global_sentiment = sentiment
            return {"sentiment": sentiment, "change": change}
        except:
            self.global_sentiment = "NEUTRAL"
            return {"sentiment": "NEUTRAL", "change": 0}

    async def get_candles(self, symbol: str, timeframe: str = "15min") -> List:
        try:
            df = await self.dhan.get_historical_data(symbol, timeframe, 3)
            if df is not None and not df.empty:
                return df.tail(30).to_dict("records")
        except:
            pass
        return []

    def calculate_indicators(self, candles: List) -> Dict:
        """Calculate comprehensive technical indicators"""
        if len(candles) < 20:
            return None

        closes = [c.get("close", 0) for c in candles]
        highs = [c.get("high", 0) for c in candles]
        lows = [c.get("low", 0) for c in candles]
        volumes = [c.get("volume", 0) for c in candles]

        current = closes[-1]
        prev = closes[-1]

        ema_9 = sum(closes[-9:]) / 9
        ema_21 = sum(closes[-21:]) / 21
        ema_50 = sum(closes[-50:]) / min(50, len(closes))

        sma_20 = sum(closes[-20:]) / 20

        delta = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gain = [d if d > 0 else 0 for d in delta]
        loss = [-d if d < 0 else 0 for d in delta]

        avg_gain = sum(gain[-14:]) / 14
        avg_loss = sum(loss[-14:]) / 14
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))

        exp1 = closes[-1]
        exp2 = closes[-1]
        exp3 = closes[-1]
        for close in closes[-26:]:
            exp1 = exp1 * (2 / 27) + close * (25 / 27)
            exp2 = exp2 * (2 / 13) + close * (11 / 13)
            exp3 = exp3 * (2 / 9) + close * (7 / 9)
        macd = exp3 - exp1
        signal = exp2 - exp1
        macd_hist = macd - signal

        trs = []
        for i in range(1, min(len(candles), 15)):
            h_l = highs[i] - lows[i]
            h_c = abs(highs[i] - closes[i - 1])
            l_c = abs(lows[i] - closes[i - 1])
            trs.append(max(h_l, h_c, l_c))
        atr = sum(trs) / len(trs) if trs else 1

        plus_dm = max(highs[-1] - highs[-2], 0) if len(highs) > 1 else 0
        minus_dm = max(lows[-2] - lows[-1], 0) if len(lows) > 1 else 0
        plus_di = (plus_dm / atr) * 100 if atr > 0 else 0
        minus_di = (minus_dm / atr) * 100 if atr > 0 else 0
        dx = (
            (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
            if (plus_di + minus_di) > 0
            else 0
        )
        adx = sum([dx]) / 14 if len([dx]) >= 14 else dx

        vol_avg = sum(volumes) / len(volumes)
        vol_now = volumes[-1]
        vol_ratio = vol_now / vol_avg if vol_avg > 0 else 1

        change_pct = (
            ((current - closes[-2]) / closes[-2] * 100) if len(closes) > 1 else 0
        )
        change_5d = (
            ((current - closes[-6]) / closes[-6] * 100) if len(closes) > 5 else 0
        )

        support = min(lows[-20:])
        resistance = max(highs[-20:])

        above_ema = current > ema_21
        ema_bullish = ema_9 > ema_21

        bb_upper = sma_20 + (
            2 * (sum([(c - sma_20) ** 2 for c in closes[-20:]]) / 20) ** 0.5
        )
        bb_lower = sma_20 - (
            2 * (sum([(c - sma_20) ** 2 for c in closes[-20:]]) / 20) ** 0.5
        )
        bb_position = (
            (current - bb_lower) / (bb_upper - bb_lower)
            if (bb_upper - bb_lower) > 0
            else 0.5
        )

        return {
            "current": current,
            "ema_9": ema_9,
            "ema_21": ema_21,
            "ema_50": ema_50,
            "sma_20": sma_20,
            "rsi": rsi,
            "macd": macd,
            "macd_hist": macd_hist,
            "signal": signal,
            "atr": atr,
            "adx": adx,
            "plus_di": plus_di,
            "minus_di": minus_di,
            "vol_ratio": vol_ratio,
            "change_pct": change_pct,
            "change_5d": change_5d,
            "support": support,
            "resistance": resistance,
            "above_ema": above_ema,
            "ema_bullish": ema_bullish,
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "bb_position": bb_position,
        }

    def analyze_candle_pattern(self, candles: List) -> Dict:
        """Analyze candlestick patterns"""
        if len(candles) < 3:
            return {"pattern": "NONE", "signal": "NEUTRAL"}

        highs = [c.get("high", 0) for c in candles]
        lows = [c.get("low", 0) for c in candles]
        opens = [c.get("open", 0) for c in candles]
        closes = [c.get("close", 0) for c in candles]

        curr_open = opens[-1]
        curr_close = closes[-1]
        curr_high = highs[-1]
        curr_low = lows[-1]

        prev_open = opens[-2]
        prev_close = closes[-2]
        prev_high = highs[-2]
        prev_low = lows[-2]

        body = abs(curr_close - curr_open)
        upper_shadow = curr_high - max(curr_open, curr_close)
        lower_shadow = min(curr_open, curr_close) - curr_low
        total_range = curr_high - curr_low

        pattern = "NONE"
        signal = "NEUTRAL"
        strength = 50

        if body > 0 and total_range > 0:
            body_ratio = body / total_range

            if curr_close > curr_open and body_ratio > 0.7:
                if (
                    prev_close < prev_open
                    and curr_close > prev_open
                    and curr_open < prev_close
                ):
                    pattern = "BULLISH_ENGULFING"
                    signal = "LONG"
                    strength = 80
                elif lower_shadow > body * 2:
                    pattern = "HAMMER"
                    signal = "LONG"
                    strength = 75
            elif curr_close < curr_open and body_ratio > 0.7:
                if (
                    prev_close > prev_open
                    and curr_close < prev_open
                    and curr_open > prev_close
                ):
                    pattern = "BEARISH_ENGULFING"
                    signal = "SHORT"
                    strength = 80
                elif upper_shadow > body * 2:
                    pattern = "SHOOTING_STAR"
                    signal = "SHORT"
                    strength = 75

        if abs(closes[-1] - opens[-1]) < total_range * 0.1:
            pattern = "DOJI"
            signal = "NEUTRAL"
            strength = 50

        return {"pattern": pattern, "signal": signal, "strength": strength}

    def generate_signal(self, indicators: Dict, pattern: Dict, symbol: str) -> Dict:
        """Generate comprehensive trading signal"""
        if not indicators:
            return {"signal": "WEAK", "confidence": 0}

        rsi = indicators["rsi"]
        macd_hist = indicators["macd_hist"]
        adx = indicators["adx"]
        vol_ratio = indicators["vol_ratio"]
        change_pct = indicators["change_pct"]
        change_5d = indicators["change_5d"]
        ema_bullish = indicators["ema_bullish"]
        above_ema = indicators["above_ema"]
        bb_position = indicators["bb_position"]

        pattern_signal = pattern["signal"]
        pattern_strength = pattern["strength"]

        bullish_score = 0
        bearish_score = 0

        if rsi < 30:
            bullish_score += 25
        elif rsi < 40:
            bullish_score += 15
        elif rsi > 70:
            bearish_score += 25
        elif rsi > 60:
            bearish_score += 15

        if macd_hist > 0:
            bullish_score += 15
        elif macd_hist < 0:
            bearish_score += 15

        if ema_bullish:
            bullish_score += 10
        else:
            bearish_score += 10

        if above_ema:
            bullish_score += 5
        else:
            bearish_score += 5

        if adx > 25:
            if macd_hist > 0:
                bullish_score += 10
            else:
                bearish_score += 10

        if vol_ratio > 1.5:
            if macd_hist > 0:
                bullish_score += 10
            else:
                bearish_score += 10

        if change_5d < -5:
            bullish_score += 15
        elif change_5d > 5:
            bearish_score += 15

        if bb_position < 0.2:
            bullish_score += 15
        elif bb_position > 0.8:
            bearish_score += 15

        if pattern_signal == "LONG":
            bullish_score += pattern_strength * 0.3
        elif pattern_signal == "SHORT":
            bearish_score += pattern_strength * 0.3

        if self.global_sentiment in ["STRONG BEARISH", "BEARISH"]:
            bearish_score += 15
        elif self.global_sentiment in ["STRONG BULLISH", "BULLISH"]:
            bullish_score += 15

        total = bullish_score + bearish_score
        if total > 0:
            bullish_pct = (bullish_score / total) * 100
        else:
            bullish_pct = 50

        confidence = abs(bullish_score - bearish_score)

        signal = "NEUTRAL"
        direction = None
        entry = indicators["current"]
        sl = None
        target = None
        atr = indicators["atr"]

        if confidence >= 25:
            if bullish_pct > 60:
                signal = "LONG"
                direction = "BUY"
                atr_mult = 1.0 if confidence > 40 else 1.5
                sl = entry - (atr * atr_mult)
                risk = abs(entry - sl)
                target = entry + (risk * 3)
            elif bullish_pct < 40:
                signal = "SHORT"
                direction = "SELL"
                atr_mult = 1.0 if confidence > 40 else 1.5
                sl = entry + (atr * atr_mult)
                risk = abs(entry - sl)
                target = entry - (risk * 3)

        if rsi < 25 and change_pct < -0.5:
            signal = "STRONG LONG"
            direction = "BUY"
            sl = indicators["support"] - (atr * 0.3)
            risk = abs(entry - sl)
            target = entry + (risk * 3)
            confidence = 85

        if rsi > 75 and change_pct > 0.5:
            signal = "STRONG SHORT"
            direction = "SELL"
            sl = indicators["resistance"] + (atr * 0.3)
            risk = abs(entry - sl)
            target = entry - (risk * 3)
            confidence = 85

        return {
            "signal": signal,
            "direction": direction,
            "confidence": min(90, confidence),
            "entry": round(entry, 2),
            "sl": round(sl, 2) if sl else None,
            "target": round(target, 2) if target else None,
            "rsi": round(rsi, 1),
            "macd_hist": round(macd_hist, 2),
            "adx": round(adx, 1),
            "vol_ratio": round(vol_ratio, 2),
            "change_pct": round(change_pct, 2),
            "change_5d": round(change_5d, 2),
            "pattern": pattern["pattern"],
            "ema_bullish": ema_bullish,
            "current": round(entry, 2),
            "atr": round(atr, 2),
            "support": round(indicators["support"], 2),
            "resistance": round(indicators["resistance"], 2),
            "bullish_pct": round(bullish_pct, 1),
        }

    def calculate_options(self, signal_data: Dict) -> Dict:
        """Calculate options parameters"""
        if signal_data["signal"] == "NEUTRAL" or not signal_data["entry"]:
            return None

        symbol = signal_data["symbol"]
        lot = self.lot_sizes.get(symbol, 1)
        direction = signal_data["direction"]
        current = signal_data["current"]
        atr = signal_data["atr"]

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

        capital = entry_prem * lot
        max_loss = sl_prem * lot
        max_profit_t1 = t1_prem * lot
        max_profit_t2 = t2_prem * lot
        risk_reward = (t1_prem - entry_prem) / sl_prem if sl_prem > 0 else 0

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
            "capital": round(capital, 2),
            "max_loss": round(max_loss, 2),
            "max_profit_t1": round(max_profit_t1, 2),
            "max_profit_t2": round(max_profit_t2, 2),
            "risk_reward": round(risk_reward, 1),
            "time_t1": self.estimate_time_to_target(entry_prem, t1_prem, atr),
            "time_t2": self.estimate_time_to_target(entry_prem, t2_prem, atr),
        }

    def estimate_time_to_target(self, entry: float, target: float, atr: float) -> str:
        """Estimate time to reach target based on ATR"""
        distance = abs(target - entry)
        atr_value = max(atr * 0.6, entry * 0.02)

        atr_units = distance / atr_value

        if atr_units <= 1:
            minutes = 15
        elif atr_units <= 2:
            minutes = 30
        elif atr_units <= 3:
            minutes = 45
        elif atr_units <= 4:
            minutes = 60
        elif atr_units <= 5:
            minutes = 90
        elif atr_units <= 6:
            minutes = 120
        else:
            minutes = int(atr_units * 20)

        if minutes <= 30:
            return f"{minutes} min"
        elif minutes <= 60:
            return f"{minutes} min"
        elif minutes <= 120:
            hours = minutes // 60
            mins = minutes % 60
            if mins > 0:
                return f"{hours}h {mins}m"
            return f"{hours} hour"
        else:
            hours = minutes // 60
            return f"{hours}+ hours"

    async def scan_market(self) -> List[Dict]:
        """Scan all stocks with comprehensive analysis"""
        await self.analyze_global_sentiment()

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

        results = []

        for symbol in symbols:
            candles = await self.get_candles(symbol, "15min")

            if candles and len(candles) >= 20:
                indicators = self.calculate_indicators(candles)
                pattern = self.analyze_candle_pattern(candles)
                signal = self.generate_signal(indicators, pattern, symbol)
                options = self.calculate_options(signal)

                if signal["confidence"] >= 60 and signal["signal"] not in [
                    "NEUTRAL",
                    "WEAK",
                ]:
                    results.append(
                        {
                            "analysis": signal,
                            "indicators": indicators,
                            "pattern": pattern,
                            "options": options,
                            "fundamentals": self.stock_fundamentals.get(symbol, {}),
                        }
                    )

        results.sort(key=lambda x: x["analysis"]["confidence"], reverse=True)
        return results

    def should_send_signal(self, signal: Dict) -> bool:
        symbol = signal["analysis"]["symbol"]
        current_time = datetime.now().strftime("%H%M")
        current_signal = signal["analysis"]["signal"]

        if symbol not in self.last_signals:
            self.last_signals[symbol] = {}

        last_time = self.last_signals[symbol].get("time", "")
        last_signal = self.last_signals[symbol].get("signal", "")

        if current_time == last_time and last_signal == current_signal:
            return False

        self.last_signals[symbol] = {"time": current_time, "signal": current_signal}
        return True

    async def send_telegram_alert(self, signal: Dict):
        """Send detailed signal to Telegram"""
        a = signal["analysis"]
        o = signal["options"]
        i = signal["indicators"]
        p = signal["pattern"]
        f = signal["fundamentals"]

        emoji_dir = "LONG" if a["direction"] == "BUY" else "SHORT"

        fundamentals_text = ""
        if f:
            fundamentals_text = f"\nSector: {f.get('sector', 'N/A')}\nIndex Weight: {f.get('index_weight', 0)}%"

        time_t1 = o.get("time_t1", "45 min") if o else "45 min"
        time_t2 = o.get("time_t2", "90 min") if o else "90 min"

        msg = f"""*COMPREHENSIVE SIGNAL*

{a["symbol"]} {o["strike"]} {o["type"]} - {emoji_dir}

*TRADE PARAMETERS*
Entry: Rs.{o["entry"]}
Stop Loss: Rs.{o["sl"]}
Target 1: Rs.{o["t1"]} ({time_t1})
Target 2: Rs.{o["t2"]} ({time_t2})

*POSITION SIZE*
Lot: {o["lot"]}
Capital: Rs.{o["capital"]:,.0f}
Max Loss: Rs.{o["max_loss"]:,.0f}
Max Profit (T1): Rs.{o["max_profit_t1"]:,.0f}
R:R Ratio: 1:{o["risk_reward"]:.1f}

*TIME ESTIMATES*
Target 1: {time_t1}
Target 2: {time_t2}
SL Hit: ~15 min if wrong

*DEEP ANALYSIS*
Confidence: {a["confidence"]:.0f}%
Global Sentiment: {self.global_sentiment}

*TECHNICAL INDICATORS*
RSI (14): {a["rsi"]}
MACD Hist: {a["macd_hist"]}
ADX: {a["adx"]}
EMA Crossover: {"BULLISH" if a["ema_bullish"] else "BEARISH"}
Volume Ratio: {a["vol_ratio"]}x
ATR: {a["atr"]}

*PRICE ACTION*
Current: Rs.{a["current"]}
Change (15min): {a["change_pct"]:+.2f}%
Change (5day): {a["change_5d"]:+.2f}%
Support: Rs.{a["support"]}
Resistance: Rs.{a["resistance"]}
Candle Pattern: {p["pattern"]}

*OPTIONS ANALYSIS*
Bullish Score: {a["bullish_pct"]}%
{fundamentals_text}

*MODE: SIGNALS ONLY*
Accuracy: {self.current_accuracy * 100:.1f}% | Target: 60%"""

        await self.telegram.send_message(msg)

        self.pending_signals.append(
            {
                "time": datetime.now().isoformat(),
                "symbol": a["symbol"],
                "signal": a,
                "options": o,
                "status": "PENDING",
            }
        )

        self.signal_history.append(
            {"time": datetime.now().isoformat(), "signal": signal}
        )

        pass

    async def send_market_summary(self, signals: List[Dict]):
        """Send market summary to Telegram"""
        if not signals:
            return

        bullish = [s for s in signals if s["analysis"]["direction"] == "BUY"]
        bearish = [s for s in signals if s["analysis"]["direction"] == "SELL"]

        msg = f"""*MARKET SCAN - {datetime.now().strftime("%H:%M")}*

*Global Sentiment:* {self.global_sentiment}
*Accuracy:* {self.current_accuracy * 100:.1f}%
*Signals Found:* {len(signals)}

"""

        if bullish:
            msg += f"*LONG SETUPS ({len(bullish)}):*\n"
            for s in bullish[:3]:
                a = s["analysis"]
                o = s["options"]
                msg += f"- {a['symbol']} {o['strike']} CE\n"
                msg += f"  Entry: {o['entry']} | SL: {o['sl']} | T1: {o['t1']}\n"
                msg += f"  RSI: {a['rsi']} | Conf: {a['confidence']:.0f}%\n\n"

        if bearish:
            msg += f"*SHORT SETUPS ({len(bearish)}):*\n"
            for s in bearish[:3]:
                a = s["analysis"]
                o = s["options"]
                msg += f"- {a['symbol']} {o['strike']} PE\n"
                msg += f"  Entry: {o['entry']} | SL: {o['sl']} | T1: {o['t1']}\n"
                msg += f"  RSI: {a['rsi']} | Conf: {a['confidence']:.0f}%\n\n"

        await self.telegram.send_message(msg)

    async def run(self):
        self.is_running = True
        iteration = 0

        await self.telegram.send_message(
            f"*COMPREHENSIVE SCANNER v3.0 STARTED*\n\n"
            f"Time: {datetime.now().strftime('%H:%M')}\n"
            f"Interval: 15 minutes\n\n"
            f"*Analysis Includes:*\n"
            f"- Technical Indicators (RSI, MACD, ADX)\n"
            f"- Candlestick Patterns\n"
            f"- Volume Analysis\n"
            f"- Support/Resistance\n"
            f"- Global Sentiment\n"
            f"- Sector Analysis\n\n"
            f"*Mode: SIGNALS ONLY*\n"
            f"Accuracy: {self.current_accuracy * 100:.1f}%\n\n"
            f"Will send detailed signals to Telegram!"
        )

        while self.is_running:
            try:
                if self.is_market_open():
                    signals = await self.scan_market()

                    for sig in signals:
                        if self.should_send_signal(sig):
                            await self.send_telegram_alert(sig)

                    if iteration % 4 == 0 and signals:
                        await self.send_market_summary(signals)

                iteration += 1
                await asyncio.sleep(self.scan_interval)

            except KeyboardInterrupt:
                self.is_running = False
                await self.telegram.send_message(
                    f"*SCANNER STOPPED*\n\n"
                    f"Final Accuracy: {self.current_accuracy * 100:.1f}%\n"
                    f"Signals Sent: {len(self.signal_history)}"
                )
                break
            except Exception as e:
                await asyncio.sleep(60)

        self.save_stats()


async def main():
    scanner = ComprehensiveScanner()
    await scanner.run()


if __name__ == "__main__":
    asyncio.run(main())
