#!/usr/bin/env python3
"""
AUTONOMOUS SIGNAL GENERATOR
===========================
Automatically scans market and sends trade opportunities to Telegram
"""

import sys
import json
import math
import time
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
from options_trader import add_option_trade

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
        "scan_interval_minutes": 60,
    }


def get_market_data():
    """Get comprehensive market data"""
    try:
        nifty = yf.Ticker("^NSEI")
        nifty_info = nifty.info

        # Handle cases where currentPrice might be None
        price = nifty_info.get("currentPrice") or nifty_info.get("dayHigh") or 22300
        prev = nifty_info.get("regularMarketPreviousClose") or price
        day_high = nifty_info.get("dayHigh") or price * 1.005
        day_low = nifty_info.get("dayLow") or price * 0.995

        if price and prev:
            change = ((price - prev) / prev) * 100
            volatility = ((day_high - day_low) / price) * 100

            if change > 0.2:
                trend = "BULLISH"
            elif change < -0.2:
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
        "day_high": 22200,
        "day_low": 21800,
    }


def get_stock_data(symbol):
    """Get stock data"""
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        info = ticker.info
        return {
            "price": info.get("currentPrice") or info.get("regularMarketPreviousClose"),
            "change": (
                (
                    info.get("currentPrice", 0)
                    - info.get("regularMarketPreviousClose", 0)
                )
                / info.get("regularMarketPreviousClose", 1)
            )
            * 100,
            "volume": info.get("volume", 0),
            "high": info.get("dayHigh"),
            "low": info.get("dayLow"),
        }
    except:
        return None


def check_volume_spike(stock_data):
    """Check for volume spike"""
    if not stock_data:
        return False
    return stock_data.get("change", 0) > 2  # >2% move = high volume


def calculate_option_params(underlying, direction, settings):
    """Calculate optimal option parameters"""
    moneyness_limit = settings.get("options_min_moneyness", -2)
    sl_percent = settings.get("options_sl_percent", 25) / 100

    if direction == "CE":
        strike = round(underlying * (1 + moneyness_limit / 100), 0)
    else:
        strike = round(underlying * (1 - moneyness_limit / 100), 0)

    # Round strike appropriately
    if underlying > 10000:
        strike = round(strike / 50) * 50
    else:
        strike = round(strike / 100) * 100

    # Estimate premium
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


def scan_for_signals():
    """Scan market for trading opportunities"""
    settings = load_settings()
    market = get_market_data()
    telegram = TelegramNotifier()

    print(f"\n[Scanning Market...]")
    print(f"  Nifty: {market['nifty']} ({market['change']:+.2f}%)")
    print(f"  Trend: {market['trend']} | Volatility: {market['volatility']:.2f}%")

    signals = []

    # Only scan in directional markets
    if market["trend"] == "SIDEWAYS":
        print("  [SKIP] Market sideways - no directional trades")

        msg = f"""*MARKET SCAN*

Nifty: {market["nifty"]} ({market["change"]:+.2f}%)
Trend: SIDEWAYS
Volatility: {market["volatility"]:.2f}%

No clear directional opportunities.
Waiting for clear trend...


Time: {datetime.now().strftime("%H:%M:%S")}"""
        telegram.send_message(msg)
        return []

    # Determine option type based on trend
    option_type = "CE" if market["trend"] == "BULLISH" else "PE"
    direction = "BUY"

    # Scan indices
    indices = {
        "NIFTY": market["nifty"],
        "BANKNIFTY": get_stock_data("BANKNIFTY").get("price")
        if get_stock_data("BANKNIFTY")
        else 50000,
    }

    print("\n[Scanning Indices]")
    for symbol, price in indices.items():
        if not price:
            continue

        params = calculate_option_params(price, direction, settings)

        # Check if strike is valid (within 2% of underlying)
        if abs(params["moneyness"]) > 3:
            print(f"  [SKIP] {symbol}: moneyness {params['moneyness']}% too far")
            continue

        signal = {
            "type": "INDEX",
            "symbol": symbol,
            "option_type": option_type,
            "strike": params["strike"],
            "entry": params["entry"],
            "sl": params["sl"],
            "targets": params["targets"],
            "moneyness": params["moneyness"],
            "underlying": price,
            "direction": direction,
        }
        signals.append(signal)
        print(f"  [SIGNAL] {symbol} {params['strike']} {option_type}")

    # Scan stocks with momentum
    print("\n[Scanning Stocks]")
    stocks = ["INFY", "TCS", "RELIANCE", "HDFCBANK", "BAJFINANCE", "SBIN", "KOTAKBANK"]

    for stock in stocks:
        data = get_stock_data(stock)
        if not data or not data.get("price"):
            continue

        # Only pick stocks with strong move (>1.5%)
        if abs(data.get("change", 0)) < 1.5:
            continue

        params = calculate_option_params(data["price"], direction, settings)

        if abs(params["moneyness"]) > 3:
            continue

        signal = {
            "type": "STOCK",
            "symbol": stock,
            "option_type": option_type,
            "strike": params["strike"],
            "entry": params["entry"],
            "sl": params["sl"],
            "targets": params["targets"],
            "moneyness": params["moneyness"],
            "underlying": data["price"],
            "direction": direction,
        }
        signals.append(signal)
        print(
            f"  [SIGNAL] {stock} {params['strike']} {option_type} ({data['change']:+.2f}%)"
        )

    return signals


def send_signal_alert(signals):
    """Send signal alerts to Telegram"""
    if not signals:
        return

    telegram = TelegramNotifier()

    # Save to log
    log = {"signals": []}
    if Path(SIGNALS_LOG).exists():
        with open(SIGNALS_LOG, "r") as f:
            log = json.load(f)

    msg = f"""*NEW TRADE OPPORTUNITIES*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Market: {signals[0].get("direction", "BUY")} {signals[0].get("option_type", "")}
Signals Found: {len(signals)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""

    for sig in signals[:5]:  # Max 5 signals
        expiry = "25MAY" if datetime.now().day < 20 else "25JUN"

        msg += f"""📊 {sig["symbol"]} {sig["strike"]} {sig["option_type"]}
   Entry: Rs {sig["entry"]}
   SL: Rs {sig["sl"]}
   Targets: {sig["targets"][0]} | {sig["targets"][1]} | {sig["targets"][2]}
   Moneyness: {sig["moneyness"]}%
   Underlying: Rs {sig["underlying"]}

"""

        # Add to portfolio
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
            notes=f"Auto-scan: {sig['moneyness']}%",
        )

        log["signals"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "symbol": sig["symbol"],
                "strike": sig["strike"],
                "type": sig["option_type"],
            }
        )

    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Time: {datetime.now().strftime("%H:%M:%S")}

Reply with '/accept' to take trade
Reply with '/skip' to ignore
"""

    with open(SIGNALS_LOG, "w") as f:
        json.dump(log, f, indent=2)

    telegram.send_message(msg)
    print(f"\n[Sent {len(signals)} signals to Telegram]")
    print("[Added to portfolio]")


def run_autonomous_scan():
    """Run autonomous scanning loop"""
    settings = load_settings()
    interval = settings.get("scan_interval_minutes", 60)

    print(f"\n{'=' * 60}")
    print(f"AUTONOMOUS SIGNAL SCANNER")
    print(f"Interval: {interval} minutes")
    print(f"{'=' * 60}")

    while True:
        try:
            signals = scan_for_signals()

            if signals:
                send_signal_alert(signals)

            print(f"\n[Next scan in {interval} minutes...]")
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
        run_autonomous_scan()
    elif args.scan:
        signals = scan_for_signals()
        if signals:
            send_signal_alert(signals)
        else:
            print("No signals found")
    else:
        print("Usage: python auto_signal.py --scan / --monitor")
