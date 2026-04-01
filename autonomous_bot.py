#!/usr/bin/env python3
"""
AUTONOMOUS TRADING BOT - CLOUD READY
====================================
- Runs 24/7 on cloud
- Auto-learns from trade results
- Self-improving system
- Supports both Equity and Options
"""

import json
import sys
import time
import os
import math
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify
import random

try:
    import yfinance as yf
except:
    import subprocess

    subprocess.run([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf

try:
    from telegram_notifier import TelegramNotifier
except:
    TelegramNotifier = None

app = Flask(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"
app.template_folder = str(TEMPLATE_DIR)


def get_dashboard_data():
    """Generate dashboard data from trade files"""
    total_pnl = "₹0"
    open_trades = 0
    win_rate = 33
    signals_today = 0
    trades = []
    signals = []
    market_sentiment = "sideways"
    volatility = 1.5

    try:
        if Path("options_trades.json").exists():
            with open("options_trades.json", "r") as f:
                options_trades = json.load(f)
                closed = [
                    t
                    for t in options_trades
                    if t.get("status")
                    in ["TARGET_HIT", "SL_HIT", "TARGET_205", "TARGET_180"]
                ]
                targets = len([t for t in closed if "TARGET" in t.get("status", "")])
                sls = len([t for t in closed if "SL" in t.get("status", "")])
                total = targets + sls
                if total > 0:
                    win_rate = int((targets / total) * 100)

                pnl = sum(t.get("pnl", 0) for t in closed)
                total_pnl = f"₹{pnl:,.0f}" if pnl >= 0 else f"-₹{abs(pnl):,.0f}"
                signals_today = len(options_trades)
    except:
        pass

    try:
        if Path("active_trades.json").exists():
            with open("active_trades.json", "r") as f:
                active = json.load(f)
                open_trades = len([t for t in active if t.get("status") == "OPEN"])
                for t in active[:6]:
                    current_price = t.get("entry", t.get("entry", 0))
                    pnl_val = (
                        (current_price - t.get("entry", 0)) / t.get("entry", 1) * 100
                    )
                    trades.append(
                        {
                            "symbol": t.get("symbol", "N/A"),
                            "direction": t.get("direction", "LONG"),
                            "entry": f"{t.get('entry', 0):.2f}",
                            "current": f"{current_price:.2f}",
                            "pnl": f"{pnl_val:+.2f}%",
                            "pnl_class": "positive" if pnl_val >= 0 else "negative",
                            "status": t.get("status", "OPEN"),
                        }
                    )
    except:
        pass

    return {
        "total_pnl": total_pnl,
        "open_trades": open_trades,
        "win_rate": win_rate,
        "signals_today": signals_today,
        "active_today": open_trades,
        "trades": trades,
        "signals": signals,
        "market_sentiment": market_sentiment,
        "market_sentiment_label": "Sideways",
        "volatility": volatility,
        "pnl_change": "0%",
        "pnl_change_class": "positive",
        "pnl_change_icon": "arrow-up",
    }


@app.route("/api/dashboard")
def api_dashboard():
    return jsonify(get_dashboard_data())


@app.route("/")
def index():
    return render_template("dashboard.html", **get_dashboard_data())


@app.route("/health")
def health():
    return {"status": "healthy"}


TRADES_FILE = "active_trades.json"
OPTIONS_FILE = "options_trades.json"
ANALYSIS_FILE = "trade_analysis.json"
SETTINGS_FILE = "bot_settings.json"

# Symbol mappings
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

option_underlying_map = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "FINNIFTY": "^NSEBANK",
    "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "INFY": "INFY.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "KOTAKBANK": "KOTAKBANK.NS",
    "BAJFINANCE": "BAJFINANCE.NS",
    "SBIN": "SBIN.NS",
    "AMBUJACEM": "AMBUJACEM.NS",
}


def load_settings():
    if Path(SETTINGS_FILE).exists():
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {
        "confidence_threshold": 65,
        "sl_percent": 2.0,
        "target_percent": 3.0,
        "max_trades_per_day": 10,
        "learning_enabled": True,
    }


def get_current_price(symbol):
    nsymbol = nsymbol_map.get(symbol, f"{symbol}.NS")
    try:
        ticker = yf.Ticker(nsymbol)
        info = ticker.info
        return info.get("currentPrice")
    except:
        return None


def get_underlying_price(symbol):
    nsymbol = option_underlying_map.get(symbol, f"{symbol}.NS")
    try:
        ticker = yf.Ticker(nsymbol)
        info = ticker.info
        return info.get("currentPrice") or info.get("regularMarketPreviousClose")
    except:
        return None


def calculate_option_premium(
    underlying, strike, option_type, instrument_type="STOCK", days_to_expiry=30
):
    if not underlying:
        return 50  # Default

    if option_type == "CE":
        moneyness = (underlying - strike) / strike
    else:
        moneyness = (strike - underlying) / strike

    time_factor = math.sqrt(days_to_expiry / 365)
    vol = 0.15 if instrument_type in ["NIFTY", "BANKNIFTY", "FINNIFTY"] else 0.30

    if moneyness > 0.1:
        premium = underlying * 0.03
    elif moneyness > 0:
        premium = underlying * vol * time_factor * 0.5
    elif moneyness > -0.05:
        premium = underlying * vol * time_factor * 0.8
    else:
        premium = underlying * vol * time_factor * 0.3

    return max(5, round(premium, 2))


def analyze_market():
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


# ============ EQUITY TRADING ============


def load_trades():
    if Path(TRADES_FILE).exists():
        with open(TRADES_FILE, "r") as f:
            return json.load(f)
    return []


def save_trades(trades):
    with open(TRADES_FILE, "w") as f:
        json.dump(trades, f, indent=2)


# ============ OPTIONS TRADING ============


def load_options_trades():
    if Path(OPTIONS_FILE).exists():
        with open(OPTIONS_FILE, "r") as f:
            return json.load(f)
    return {"trades": [], "closed": []}


def save_options_trades(data):
    with open(OPTIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def check_equity_trades():
    """Check equity trades"""
    trades = load_trades()
    market = analyze_market()

    print(f"\n[Checking EQUITY Trades | Market: {market['trend']}]")

    sl_hits = []
    target_hits = []

    for trade in trades:
        if trade.get("status") != "OPEN":
            continue

        symbol = trade.get("symbol")
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
                trade["pnl"] = sl - entry
                sl_hits.append(trade)
                print(f"  [SL] {symbol}")
            elif current >= target:
                trade["status"] = "TARGET_HIT"
                trade["pnl"] = target - entry
                target_hits.append(trade)
                print(f"  [TARGET] {symbol} | P&L: Rs {trade['pnl']:.2f}")
            else:
                pct = ((current - entry) / entry) * 100
                print(f"  [OPEN] {symbol}: {current} ({pct:+.2f}%)")
        else:
            if current >= sl:
                trade["status"] = "SL_HIT"
                trade["pnl"] = entry - sl
                sl_hits.append(trade)
                print(f"  [SL] {symbol}")
            elif current <= target:
                trade["status"] = "TARGET_HIT"
                trade["pnl"] = entry - target
                target_hits.append(trade)
                print(f"  [TARGET] {symbol}")

    save_trades(trades)
    return sl_hits, target_hits


def check_options_trades():
    """Check options trades"""
    data = load_options_trades()
    market_price = get_underlying_price("NIFTY") or 22000

    print(f"\n[Checking OPTIONS Trades | Nifty: {market_price}]")

    sl_hits = []
    target_hits = []

    for trade in data["trades"]:
        if trade.get("status") != "OPEN":
            continue

        symbol = trade.get("symbol")
        strike = trade.get("strike")
        opt_type = trade.get("type")

        underlying = get_underlying_price(symbol)
        if not underlying:
            print(f"  {trade.get('symbol_format')}: Price unavailable")
            continue

        current_premium = calculate_option_premium(underlying, strike, opt_type)

        entry = trade["entry_premium"]
        sl = trade["sl_premium"]
        direction = trade["direction"]

        if direction == "BUY":
            if current_premium <= sl:
                trade["status"] = "SL_HIT"
                trade["pnl"] = (sl - entry) * trade["lots"] * 75
                sl_hits.append(trade)
                print(f"  [SL] {trade['symbol_format']}")
            elif any(current_premium >= t for t in trade["targets"]):
                hit_target = min([t for t in trade["targets"] if current_premium >= t])
                trade["status"] = f"TARGET_{hit_target}"
                trade["pnl"] = (hit_target - entry) * trade["lots"] * 75
                target_hits.append(trade)
                print(f"  [TARGET] {trade['symbol_format']} @ {hit_target}")
            else:
                pnl = (current_premium - entry) * trade["lots"] * 75
                print(
                    f"  [OPEN] {trade['symbol_format']}: Premium {current_premium} | P&L: Rs {pnl}"
                )

    save_options_trades(data)
    return sl_hits, target_hits


def check_all_trades():
    """Check both equity and options trades"""
    telegram = TelegramNotifier()
    market = analyze_market()

    print(f"\n{'=' * 60}")
    print(f"AUTONOMOUS BOT - {datetime.now().strftime('%H:%M:%S')}")
    print(f"Market: {market['trend']} | Volatility: {market['volatility']:.2f}%")
    print(f"{'=' * 60}")

    # Check equity
    eq_sl, eq_target = check_equity_trades()

    # Check options
    opt_sl, opt_target = check_options_trades()

    total_sl = len(eq_sl) + len(opt_sl)
    total_target = len(eq_target) + len(opt_target)

    # Send Telegram alerts
    if total_sl > 0 or total_target > 0:
        msg = f"*TRADE UPDATE*\n\n"
        if eq_sl or eq_sl:
            msg += f"Equity: {len(eq_sl)} SL, {len(eq_target)} Target\n"
        if opt_sl or opt_target:
            msg += f"Options: {len(opt_sl)} SL, {len(opt_target)} Target\n"
        telegram.send_message(msg)

    print(f"\n[Summary: {total_sl} SL hits, {total_target} targets hit]")
    return total_sl, total_target


def main():
    import argparse
    import threading
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Check all trades once")
    parser.add_argument("--monitor", action="store_true", help="Run continuously")
    parser.add_argument("--equity", action="store_true", help="Check equity only")
    parser.add_argument("--options", action="store_true", help="Check options only")
    parser.add_argument(
        "--server",
        action="store_true",
        help="Run as web server with background monitoring",
    )
    args = parser.parse_args()

    # Run background monitoring in a thread
    def background_monitor():
        while True:
            try:
                check_all_trades()
            except Exception as e:
                print(f"Monitor error: {e}")
            time.sleep(60)

    # Run momentum scanner in background
    def background_signal_scanner():
        while True:
            try:
                # Import and run momentum scanner
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                from auto_signal import scan_for_momentum, send_signal_alert

                signals = scan_for_momentum()
                if signals:
                    send_signal_alert(signals)
            except Exception as e:
                print(f"Signal scan error: {e}")
            time.sleep(900)  # 15 min

    if args.server or os.environ.get("RENDER"):
        # Run as web server on Render with both monitors
        monitor_thread = threading.Thread(target=background_monitor, daemon=True)
        monitor_thread.start()

        signal_thread = threading.Thread(target=background_signal_scanner, daemon=True)
        signal_thread.start()

        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)

    elif args.monitor:
        print("Starting 24/7 autonomous trading...")
        print("Monitoring both Equity and Options")
        print("Ctrl+C to stop")
        try:
            while True:
                check_all_trades()
                time.sleep(60)
        except KeyboardInterrupt:
            print("\nStopped")

    elif args.equity:
        check_equity_trades()

    elif args.options:
        check_options_trades()

    elif args.check:
        check_all_trades()


if __name__ == "__main__":
    main()
