#!/usr/bin/env python3
"""
SENSEX EXPIRY TRADER
Today is expiry - generate Sensex trades
"""

import sys
import json
import math
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

SENSEX_SYMBOL = "^BSESN"


def get_sensex_data():
    """Get current Sensex data"""
    try:
        ticker = yf.Ticker(SENSEX_SYMBOL)
        info = ticker.info

        price = info.get("regularMarketPrice") or info.get("currentPrice")
        prev = info.get("regularMarketPreviousClose")
        change = info.get("regularMarketChangePercent", 0)

        return {
            "price": price,
            "prev": prev,
            "change": change,
            "day_high": info.get("regularMarketDayHigh"),
            "day_low": info.get("regularMarketDayLow"),
        }
    except Exception as e:
        print(f"Error: {e}")
        return None


def calculate_sensex_options(underlying, direction, expiry="APR"):
    """Calculate Sensex option parameters"""
    lot_size = 50

    moneyness = -2 if direction == "PE" else 2
    if direction == "CE":
        strike = round(underlying * (1 + moneyness / 100), 0)
    else:
        strike = round(underlying * (1 - moneyness / 100), 0)

    strike = round(strike / 100) * 100

    vol = 0.15
    premium = underlying * vol * 0.5

    entry = max(50, round(premium, 2))
    sl = round(entry * 0.75, 2)
    target1 = round(entry * 1.25, 2)
    target2 = round(entry * 1.50, 2)
    target3 = round(entry * 1.75, 2)

    return {
        "symbol": f"SENSEX",
        "underlying": underlying,
        "strike": int(strike),
        "type": direction,
        "expiry": f"{expiry}'26",
        "entry": entry,
        "sl": sl,
        "targets": [target1, target2, target3],
        "lot_size": lot_size,
    }


def generate_trades():
    """Generate Sensex trades for today"""
    data = get_sensex_data()

    if not data or not data.get("price"):
        print("Could not get Sensex data")
        return []

    price = data["price"]
    change = data["change"]

    print(f"\n{'=' * 50}")
    print(f"SENSEX: {price:,.2f} ({change:+.2f}%)")
    print(f"EXPIRY: TODAY (APR'26)")
    print(f"{'=' * 50}")

    trades = []

    if change < -1:
        direction = "PE"
        print(f"Market BEARISH ({change:.2f}%) -> Buy SENSEX PUT")
    elif change > 1:
        direction = "CE"
        print(f"Market BULLISH ({change:.2f}%) -> Buy SENSEX CALL")
    else:
        direction = "PE"
        print(f"Market SIDEWAYS -> Buy SENSEX PUT")

    option = calculate_sensex_options(price, direction, "APR")

    trade = {
        "symbol": "SENSEX",
        "direction": direction,
        "underlying": price,
        "strike": option["strike"],
        "option_type": option["type"],
        "expiry": option["expiry"],
        "entry": option["entry"],
        "sl": option["sl"],
        "target1": option["targets"][0],
        "target2": option["targets"][1],
        "target3": option["targets"][2],
        "lots": 1,
        "value": option["entry"] * option["lot_size"],
        "confidence": 85 if abs(change) > 1 else 70,
    }

    trades.append(trade)

    if abs(change) < 0.5:
        hedge = {
            "symbol": "SENSEX",
            "direction": "CE" if direction == "PE" else "PE",
            "underlying": price,
            "strike": option["strike"] + 500
            if direction == "PE"
            else option["strike"] - 500,
            "option_type": "CE" if direction == "PE" else "PE",
            "expiry": option["expiry"],
            "entry": round(option["entry"] * 0.3, 2),
            "sl": round(option["entry"] * 0.2, 2),
            "target1": round(option["entry"] * 0.5, 2),
            "target2": round(option["entry"] * 0.7, 2),
            "target3": round(option["entry"] * 1.0, 2),
            "lots": 1,
            "value": round(option["entry"] * 0.3 * option["lot_size"], 2),
            "confidence": 60,
            "type": "HEDGE",
        }
        trades.append(hedge)

    return trades


def send_telegram_signals(trades):
    """Send signals to Telegram"""
    telegram = TelegramNotifier()

    msg = "📈 *SENSEX EXPIRY TRADES*\n\n"
    msg += f"Expiry: TODAY (APR'26)\n"
    msg += f"Generated: {datetime.now().strftime('%H:%M:%S')}\n\n"

    for trade in trades:
        msg += f"--- {trade.get('type', 'MAIN')} ---\n"
        msg += f"Direction: {trade['direction']}\n"
        msg += f"Strike: {trade['strike']}\n"
        msg += f"Option: {trade['option_type']}\n"
        msg += f"Entry: Rs{trade['entry']}\n"
        msg += f"SL: Rs{trade['sl']}\n"
        msg += f"T1: Rs{trade['target1']} | T2: Rs{trade['target2']} | T3: Rs{trade['target3']}\n"
        msg += f"Lots: {trade['lots']} | Value: Rs{trade['value']:,.0f}\n"
        msg += f"Confidence: {trade['confidence']}%\n\n"

    telegram.send_message(msg)
    print(f"\n[SENT {len(trades)} trades to Telegram]")


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("SENSEX EXPIRY TRADER")
    print("=" * 50)

    trades = generate_trades()

    if trades:
        send_telegram_signals(trades)

        print("\nGenerated Trades:")
        for t in trades:
            print(
                f"  {t['direction']} {t['strike']} {t['option_type']} @ Rs{t['entry']} (SL: Rs{t['sl']})"
            )
    else:
        print("No trades generated")
