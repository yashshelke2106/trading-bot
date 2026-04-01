#!/usr/bin/env python3
"""
AUTONOMOUS TRADING BOT - CLOUD READY
=====================================
- Runs 24/7 on cloud
- Auto-learns from trade results
- Self-improving system

Cloud Options:
1. PythonAnywhere.com - Free tier, easiest setup
2. Heroku.com - Free tier, requires some config
3. Render.com - Free tier, good for Python
4. Railway.com - Paid but reliable

Setup Instructions:
==================

OPTION 1: PythonAnywhere (Easiest - Free)
-----------------------------------------
1. Go to pythonanywhere.com
2. Create free account
3. Upload these files to Files tab
4. Open Bash console, run:
   pip install yfinance requests
5. Schedule task to run every 5 minutes:
   python trade_monitor.py --check

OPTION 2: Heroku (Free)
-----------------------
1. Install Heroku CLI
2. Create Procfile with content:
   worker: python trade_monitor.py --monitor
3. Push to Heroku

OPTION 3: Render (Recommended)
-------------------------------
1. Connect GitHub repo to Render
2. Set build command: pip install -r requirements.txt
3. Set start command: python trade_monitor.py --monitor
"""

import json
import sys
import time
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import yfinance as yf
except:
    import subprocess

    subprocess.run([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf

from telegram_notifier import TelegramNotifier

TRADES_FILE = "active_trades.json"
ANALYSIS_FILE = "trade_analysis.json"
SETTINGS_FILE = "bot_settings.json"


def load_settings():
    if Path(SETTINGS_FILE).exists():
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {
        "confidence_threshold": 65,
        "sl_percent": 2.0,
        "target_percent": 3.0,
        "max_trades_per_day": 10,
        "min_volatility": 0.5,
        "max_volatility": 3.0,
        "atr_multiplier": 1.5,
        "trailing_start_percent": 50,
        "learning_enabled": True,
    }


def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


nsymbol_map = {
    "BAJFINANCE": "BAJFINANCE.NS",
    "SBIN": "SBIN.NS",
    "TCS": "TCS.NS",
    "INFY": "INFY.NS",
    "RELIANCE": "RELIANCE.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "KOTAKBANK": "KOTAKBANK.NS",
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
}


def get_current_price(symbol):
    nsymbol = nsymbol_map.get(symbol, f"{symbol}.NS")
    try:
        ticker = yf.Ticker(nsymbol)
        info = ticker.info
        return info.get("currentPrice")
    except:
        return None


def get_atr(symbol, period=14):
    """Calculate ATR for dynamic SL"""
    nsymbol = nsymbol_map.get(symbol, f"{symbol}.NS")
    try:
        ticker = yf.Ticker(nsymbol)
        hist = ticker.history(period="15d")
        if len(hist) >= period:
            high = hist["High"]
            low = hist["Low"]
            close = hist["Close"]
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = tr1.combine(tr2, max).combine(tr3, max)
            atr = tr.rolling(period).mean().iloc[-1]
            return atr
    except:
        pass
    return None


def analyze_market():
    """Get current market conditions"""
    try:
        nifty = yf.Ticker("^NSEI")
        info = nifty.info
        price = info.get("currentPrice")
        prev_close = info.get("regularMarketPreviousClose")
        day_high = info.get("dayHigh")
        day_low = info.get("dayLow")

        if all([price, prev_close, day_high, day_low]):
            volatility = ((day_high - day_low) / price) * 100
            trend = (
                "BULLISH"
                if price > prev_close
                else "BEARISH"
                if price < prev_close
                else "SIDEWAYS"
            )
            return {"price": price, "volatility": volatility, "trend": trend}
    except:
        pass
    return {"price": 0, "volatility": 1.5, "trend": "SIDEWAYS"}


def load_trades():
    if Path(TRADES_FILE).exists():
        with open(TRADES_FILE, "r") as f:
            return json.load(f)
    return []


def save_trades(trades):
    with open(TRADES_FILE, "w") as f:
        json.dump(trades, f, indent=2)


def load_analysis():
    if Path(ANALYSIS_FILE).exists():
        with open(ANALYSIS_FILE, "r") as f:
            return json.load(f)
    return {"sl_hits": [], "target_hits": [], "total": 0, "improvements": []}


def save_analysis(analysis):
    with open(ANALYSIS_FILE, "w") as f:
        json.dump(analysis, f, indent=2)


def auto_learn():
    """Autonomous learning from trade history"""
    settings = load_settings()
    analysis = load_analysis()

    sl_trades = analysis.get("sl_hits", [])
    target_trades = analysis.get("target_hits", [])

    if len(sl_trades) + len(target_trades) < 5:
        return "Insufficient data for learning"

    total = len(sl_trades) + len(target_trades)
    win_rate = (len(target_trades) / total) * 100 if total > 0 else 0

    improvements = []

    if win_rate < 40:
        settings["confidence_threshold"] += 5
        improvements.append(
            f"Increased confidence threshold to {settings['confidence_threshold']}%"
        )

    if win_rate > 70:
        settings["sl_percent"] = min(3.0, settings["sl_percent"] + 0.2)
        improvements.append(f"Adjusted SL to {settings['sl_percent']}%")

    avg_sl_loss = (
        sum(t.get("loss", 0) for t in sl_trades) / len(sl_trades) if sl_trades else 0
    )
    if avg_sl_loss < -200:
        settings["sl_percent"] += 0.3
        improvements.append(f"Wider SL to reduce hit rate: {settings['sl_percent']}%")

    if len(target_trades) > 0:
        avg_target_gain = sum(t.get("gain", 0) for t in target_trades) / len(
            target_trades
        )
        avg_sl_loss = (
            abs(sum(t.get("loss", 0) for t in sl_trades) / len(sl_trades))
            if sl_trades
            else 1
        )
        rr_ratio = avg_target_gain / avg_sl_loss if avg_sl_loss > 0 else 0

        if rr_ratio < 1.5:
            settings["target_percent"] += 0.5
            improvements.append(
                f"Increased target to {settings['target_percent']}% for better R:R"
            )

    save_settings(settings)
    return improvements


def check_trades():
    """Check all trades"""
    trades = load_trades()
    analysis = load_analysis()
    settings = load_settings()
    market = analyze_market()
    telegram = TelegramNotifier()

    print(
        f"\n[{datetime.now().strftime('%H:%M:%S')}] Market: {market['trend']} | Vol: {market['volatility']:.2f}%"
    )

    sl_hits = []
    target_hits = []

    for trade in trades:
        if trade["status"] != "OPEN":
            continue

        symbol = trade["symbol"]
        current = get_current_price(symbol)

        if not current:
            continue

        entry, sl, target, direction = (
            trade["entry"],
            trade["sl"],
            trade["target"],
            trade["direction"],
        )

        if direction == "LONG":
            if current <= sl:
                trade["status"] = "SL_HIT"
                trade["exit_price"] = sl
                trade["pnl"] = sl - entry
                trade["exit_time"] = datetime.now().isoformat()
                sl_hits.append(trade)
                print(f"  [SL] {symbol}")
            elif current >= target:
                trade["status"] = "TARGET_HIT"
                trade["exit_price"] = target
                trade["pnl"] = target - entry
                trade["exit_time"] = datetime.now().isoformat()
                target_hits.append(trade)
                print(f"  [TARGET] {symbol} | P&L: Rs {trade['pnl']:.2f}")
            else:
                pct = ((current - entry) / entry) * 100
                print(f"  [OPEN] {symbol}: {current} ({pct:+.2f}%)")
        else:
            if current >= sl:
                trade["status"] = "SL_HIT"
                trade["exit_price"] = sl
                trade["pnl"] = entry - sl
                trade["exit_time"] = datetime.now().isoformat()
                sl_hits.append(trade)
                print(f"  [SL] {symbol}")
            elif current <= target:
                trade["status"] = "TARGET_HIT"
                trade["exit_price"] = target
                trade["pnl"] = entry - target
                trade["exit_time"] = datetime.now().isoformat()
                target_hits.append(trade)
                print(f"  [TARGET] {symbol} | P&L: Rs {trade['pnl']:.2f}")

    save_trades(trades)

    if sl_hits or target_hits:
        for t in sl_hits:
            analysis["sl_hits"].append(
                {
                    "symbol": t["symbol"],
                    "loss": t["pnl"],
                    "sl_percent": abs((t["sl"] - t["entry"]) / t["entry"]) * 100,
                    "market_vol": market["volatility"],
                    "time": t["exit_time"],
                }
            )
        for t in target_hits:
            analysis["target_hits"].append(
                {
                    "symbol": t["symbol"],
                    "gain": t["pnl"],
                    "target_percent": abs((t["target"] - t["entry"]) / t["entry"])
                    * 100,
                    "market_vol": market["volatility"],
                    "time": t["exit_time"],
                }
            )
        analysis["total"] = len(analysis["sl_hits"]) + len(analysis["target_hits"])
        save_analysis(analysis)

        if settings.get("learning_enabled"):
            improvements = auto_learn()
            msg = f"""*AUTONOMOUS LEARNING*

Trades analyzed: {len(sl_hits)} SL, {len(target_hits)} Target
Total analyzed: {analysis["total"]}

Improvements applied:
"""
            if isinstance(improvements, list):
                for imp in improvements:
                    msg += f"  - {imp}\n"
            else:
                msg += f"  - {improvements}\n"

            msg += f"\nCurrent Settings:"
            msg += f"\n  Confidence: {settings['confidence_threshold']}%"
            msg += f"\n  SL: {settings['sl_percent']}%"
            msg += f"\n  Target: {settings['target_percent']}%"

            telegram.send_message(msg)

    return (
        len(sl_hits),
        len(target_hits),
        len([t for t in trades if t["status"] == "OPEN"]),
    )


def generate_signal(symbol, direction):
    """Generate signal with dynamic SL/Target based on settings"""
    settings = load_settings()
    market = analyze_market()

    current = get_current_price(symbol)
    if not current:
        return None

    atr = get_atr(symbol)
    if atr:
        sl_price = (
            current - (atr * settings["atr_multiplier"])
            if direction == "LONG"
            else current + (atr * settings["atr_multiplier"])
        )
    else:
        sl_percent = settings["sl_percent"] / 100
        sl_price = (
            current * (1 - sl_percent)
            if direction == "LONG"
            else current * (1 + sl_percent)
        )

    target_percent = settings["target_percent"] / 100
    target_price = (
        current * (1 + target_percent)
        if direction == "LONG"
        else current * (1 - target_percent)
    )

    return {
        "symbol": symbol,
        "direction": direction,
        "entry": current,
        "sl": round(sl_price, 2),
        "target": round(target_price, 2),
        "confidence": settings["confidence_threshold"],
    }


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Check trades once")
    parser.add_argument("--monitor", action="store_true", help="Run continuously")
    parser.add_argument("--signal", help="Generate signal for symbol")
    parser.add_argument("--settings", action="store_true", help="Show current settings")
    args = parser.parse_args()

    if args.settings:
        settings = load_settings()
        print("\nCurrent Bot Settings:")
        for k, v in settings.items():
            print(f"  {k}: {v}")

    elif args.signal:
        sig = generate_signal(args.signal, "LONG")
        if sig:
            print(f"\nSignal: {sig}")
            telegram = TelegramNotifier()
            telegram.send_message(f"""Generated Signal:

Symbol: {sig["symbol"]}
Entry: {sig["entry"]}
SL: {sig["sl"]}
Target: {sig["target"]}
Confidence: {sig["confidence"]}%""")

    elif args.monitor:
        print("Starting 24/7 autonomous trading...")
        print("Ctrl+C to stop")
        try:
            while True:
                check_trades()
                time.sleep(60)
        except KeyboardInterrupt:
            print("\nStopped")

    elif args.check:
        check_trades()


if __name__ == "__main__":
    main()
