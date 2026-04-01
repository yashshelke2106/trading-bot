#!/usr/bin/env python3
"""
AUTONOMOUS SIGNAL SCANNER - MOMENTUM TRADING
============================================
Automatically scans market for momentum setups and sends to Telegram
"""

import sys
import json
import math
import time
import os
import threading
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "C:/Users/yashs/Documents/Trading Bot/file1")

try:
    import yfinance as yf
except:
    import subprocess

    subprocess.run([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf

from telegram_notifier import TelegramNotifier

SETTINGS_FILE = "bot_settings.json"
SIGNALS_LOG = "signals_log.json"


def load_settings():
    if Path(SETTINGS_FILE).exists():
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {
        "options_sl_percent": 25,
        "options_min_moneyness": -2,
        "options_min_confidence": 70,
        "momentum_threshold": 1.5,  # Minimum % move to trigger
        "scan_interval_minutes": 15,  # Scan every 15 min
    }


def get_market_data():
    """Get comprehensive market data"""
    try:
        nifty = yf.Ticker("^NSEI")
        nifty_info = nifty.info

        price = nifty_info.get("currentPrice") or nifty_info.get("dayHigh") or 22300
        prev = nifty_info.get("regularMarketPreviousClose") or price
        day_high = nifty_info.get("dayHigh") or price * 1.005
        day_low = nifty_info.get("dayLow") or price * 0.995

        if price and prev:
            change = ((price - prev) / prev) * 100
            volatility = ((day_high - day_low) / price) * 100

            if change > 0.3:
                trend = "BULLISH"
            elif change < -0.3:
                trend = "BEARISH"
            else:
                trend = "SIDEWAYS"

            return {
                "nifty": price,
                "change": change,
                "volatility": volatility,
                "trend": trend,
                "day_high": day_high,
                "day_low": day_low,
            }
    except:
        pass
    return {
        "nifty": 22300,
        "change": 0,
        "volatility": 1.5,
        "trend": "SIDEWAYS",
        "day_high": 22500,
        "day_low": 22100,
    }


def get_stock_data(symbol):
    """Get stock data"""
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        info = ticker.info
        price = info.get("currentPrice") or info.get("regularMarketPreviousClose")
        prev = info.get("regularMarketPreviousClose") or price

        change = ((price - prev) / prev) * 100 if price and prev else 0

        return {
            "price": price,
            "prev": prev,
            "change": change,
            "high": info.get("dayHigh"),
            "low": info.get("dayLow"),
            "volume": info.get("volume", 0),
        }
    except:
        return None


def calculate_option_params(underlying, direction, settings):
    """Calculate optimal option parameters"""
    moneyness_limit = settings.get("options_min_moneyness", -2)
    sl_percent = settings.get("options_sl_percent", 25) / 100

    if direction == "CE":
        strike = round(underlying * (1 + moneyness_limit / 100), 0)
    else:
        strike = round(underlying * (1 - moneyness_limit / 100), 0)

    if underlying > 10000:
        strike = round(strike / 50) * 50
    else:
        strike = round(strike / 100) * 100

    vol = 0.15 if underlying > 10000 else 0.30
    moneyness = (
        (underlying - strike) / strike
        if direction == "CE"
        else (strike - underlying) / strike
    )

    if moneyness > 0.03:
        premium = underlying * 0.03
    elif moneyness > 0:
        premium = underlying * vol * 0.5
    elif moneyness > -0.02:
        premium = underlying * vol * 0.8
    else:
        premium = underlying * vol * 0.4

    entry = max(20, round(premium, 2))
    sl = round(entry * (1 - sl_percent), 2)
    target1 = round(entry * 1.25, 2)
    target2 = round(entry * 1.50, 2)
    target3 = round(entry * 1.75, 2)

    return {
        "strike": int(strike),
        "entry": entry,
        "sl": sl,
        "targets": [target1, target2, target3],
        "moneyness": round(moneyness * 100, 2),
    }


def get_monthly_expiry():
    """Get next monthly expiry date in Indian format"""
    from datetime import datetime, timedelta

    today = datetime.now()
    year = today.year

    # Monthly expiry dates for NSE (usually last Thursday of month)
    expiry_dates = [
        ("JAN", datetime(year, 1, 25)),
        ("FEB", datetime(year, 2, 22)),
        ("MAR", datetime(year, 3, 28)),
        ("APR", datetime(year, 4, 25)),
        ("MAY", datetime(year, 5, 30)),
        ("JUN", datetime(year, 6, 27)),
        ("JUL", datetime(year, 7, 31)),
        ("AUG", datetime(year, 8, 29)),
        ("SEP", datetime(year, 9, 26)),
        ("OCT", datetime(year, 10, 31)),
        ("NOV", datetime(year, 11, 28)),
        ("DEC", datetime(year, 12, 26)),
    ]

    # Find next expiry
    for month_name, expiry in expiry_dates:
        if today <= expiry + timedelta(days=3):
            # Format: "28 APR" or use month abbreviation
            return f"{month_name}'25"  # e.g., "APR'25"

    # If past all dates, use next year's Jan
    return f"JAN'{year + 1}"


def scan_for_momentum():
    """Scan for momentum-based trading opportunities"""
    settings = load_settings()
    market = get_market_data()
    telegram = TelegramNotifier()

    expiry = get_monthly_expiry()
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Scanning...")
    print(f"  Market: {market['trend']} ({market['change']:+.2f}%)")
    print(f"  Next Expiry: {expiry}")

    signals = []
    momentum_stocks = []

    # Scan stocks with momentum
    stocks = [
        "INFY",
        "TCS",
        "RELIANCE",
        "HDFCBANK",
        "BAJFINANCE",
        "SBIN",
        "KOTAKBANK",
        "ICICIBANK",
        "AXISBANK",
        "LT",
        "TITAN",
        "SUNPHARMA",
        "WIPRO",
        "HINDUNILVR",
    ]

    for stock in stocks:
        data = get_stock_data(stock)
        if not data or not data.get("price"):
            continue

        change = data.get("change", 0)

        # Check if stock has momentum
        if abs(change) >= settings.get("momentum_threshold", 1.5):
            momentum_stocks.append(
                {"symbol": stock, "price": data["price"], "change": change}
            )

    if not momentum_stocks:
        print(
            f"  No momentum stocks found (threshold: {settings.get('momentum_threshold', 1.5)}%)"
        )
        return []

    print(f"  Found {len(momentum_stocks)} momentum stocks")

    # Determine direction
    if market["trend"] == "BULLISH":
        direction = "BUY"
        option_type = "CE"
    elif market["trend"] == "BEARISH":
        direction = "BUY"
        option_type = "PE"
    else:
        # For sideways, use strongest momentum direction
        avg_change = sum(s["change"] for s in momentum_stocks) / len(momentum_stocks)
        if avg_change > 0:
            direction = "BUY"
            option_type = "CE"
        else:
            direction = "BUY"
            option_type = "PE"

    # Generate signals for momentum stocks
    for stock_data in momentum_stocks[:5]:  # Max 5
        params = calculate_option_params(stock_data["price"], direction, settings)

        if abs(params["moneyness"]) > 3:
            continue

        signal = {
            "type": "MOMENTUM",
            "symbol": stock_data["symbol"],
            "option_type": option_type,
            "strike": params["strike"],
            "entry": params["entry"],
            "sl": params["sl"],
            "targets": params["targets"],
            "moneyness": params["moneyness"],
            "underlying": stock_data["price"],
            "direction": direction,
            "stock_change": stock_data["change"],
        }
        signals.append(signal)
        print(
            f"    {stock_data['symbol']}: {stock_data['change']:+.2f}% -> {params['strike']} {option_type}"
        )

    return signals


def send_signal_alert(signals):
    """Send signal alerts to Telegram immediately"""
    if not signals:
        return

    telegram = TelegramNotifier()

    # Save to log
    log = {"signals": [], "last_sent": None}
    if Path(SIGNALS_LOG).exists():
        with open(SIGNALS_LOG, "r") as f:
            log = json.load(f)

    # Check if we already sent recently (avoid spam)
    last_sent = log.get("last_sent")
    if last_sent:
        last_time = datetime.fromisoformat(last_sent)
        if (datetime.now() - last_time).seconds < 300:  # 5 min cooldown
            print("  [SKIP] Already sent recently")
            return

    msg = f"""*MOMENTUM TRADE ALERT*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Market Trend: {signals[0].get("option_type", "")}
Signals Found: {len(signals)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""

    for sig in signals:
        expiry = get_monthly_expiry()

        # Add to portfolio
        try:
            from options_trader import add_option_trade

            add_option_trade(
                symbol=sig["symbol"],
                strike=sig["strike"],
                option_type=sig["option_type"],
                expiry=expiry,
                direction=sig["direction"],
                entry_premium=sig["entry"],
                sl_premium=sig["sl"],
                targets_list=sig["targets"],
                lots=1,
                notes=f"Momentum: {sig['stock_change']:+.2f}%",
            )
        except:
            pass

        msg += f"""[MOMENTUM: {sig["stock_change"]:+.2f}%]

{sig["symbol"]} {sig["strike"]} {sig["option_type"]} {expiry}
   Entry: Rs {sig["entry"]}
   SL: Rs {sig["sl"]}
   Targets: {sig["targets"][0]} | {sig["targets"][1]} | {sig["targets"][2]}
   Moneyness: {sig["moneyness"]}%

"""

    msg += f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Auto-generated based on momentum
Time: {datetime.now().strftime("%H:%M:%S")}"""

    log["signals"].append(
        {
            "timestamp": datetime.now().isoformat(),
            "signals_count": len(signals),
            "symbols": [s["symbol"] for s in signals],
        }
    )
    log["last_sent"] = datetime.now().isoformat()

    with open(SIGNALS_LOG, "w") as f:
        json.dump(log, f, indent=2)

    telegram.send_message(msg)
    print(f"\n[SENT {len(signals)} signals to Telegram]")


def run_continuous_scan():
    """Run continuous scanning loop"""
    settings = load_settings()
    interval = settings.get("scan_interval_minutes", 15)

    print(f"\n{'=' * 60}")
    print(f"MOMENTUM SCANNER - ACTIVE")
    print(f"Scanning every {interval} minutes")
    print(f"{'=' * 60}")

    while True:
        try:
            signals = scan_for_momentum()

            if signals:
                send_signal_alert(signals)

            time.sleep(interval * 60)

        except KeyboardInterrupt:
            print("\n[Stopped]")
            break
        except Exception as e:
            print(f"[Error: {e}]")
            time.sleep(60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--scan", action="store_true", help="Scan once")
    parser.add_argument("--monitor", action="store_true", help="Run continuously")
    args = parser.parse_args()

    if args.monitor:
        run_continuous_scan()
    elif args.scan:
        signals = scan_for_momentum()
        if signals:
            send_signal_alert(signals)
        else:
            print("No momentum signals found")
    else:
        # Default: run continuous
        run_continuous_scan()
