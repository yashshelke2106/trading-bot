#!/usr/bin/env python3
"""
INDEX EXPIRY CALENDAR & TRADER
=============================
Accurate expiry dates for all Indian indices
- NIFTY: Last Tuesday of month (Weekly: Tuesday)
- BANKNIFTY: Last Tuesday of month (Weekly: Tuesday)
- FINNIFTY: Last Tuesday of month (Weekly: Tuesday)
- SENSEX: Last Thursday of month (Weekly: Thursday)
- BANKEX: Last Thursday of month (Weekly: Thursday)
"""

import sys
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from calendar import monthcalendar

sys.path.insert(0, "C:/Users/yashs/Documents/Trading Bot/file1")

try:
    import yfinance as yf
except:
    import subprocess

    subprocess.run([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf

from telegram_notifier import TelegramNotifier

INDEXES = {
    "NIFTY": {"symbol": "^NSEI", "lot_size": 25, "expiry_day": "tuesday"},
    "BANKNIFTY": {"symbol": "^NSEBANK", "lot_size": 15, "expiry_day": "tuesday"},
    "FINNIFTY": {"symbol": "^NSEBANK", "lot_size": 40, "expiry_day": "tuesday"},
    "SENSEX": {"symbol": "^BSESN", "lot_size": 50, "expiry_day": "thursday"},
    "BANKEX": {"symbol": "^BSEBANK", "lot_size": 15, "expiry_day": "thursday"},
}

NSE_HOLIDAYS_2026 = [
    datetime(2026, 1, 26),  # Republic Day
    datetime(2026, 3, 3),  # Holi
    datetime(2026, 3, 26),  # Shri Ram Navami
    datetime(2026, 3, 31),  # Shri Mahavir Jayanti
    datetime(2026, 4, 3),  # Good Friday
    datetime(2026, 4, 14),  # Dr. Baba Saheb Ambedkar Jayanti
    datetime(2026, 5, 1),  # Maharashtra Day
    datetime(2026, 5, 28),  # Bakri Id
    datetime(2026, 6, 26),  # Muharram
    datetime(2026, 9, 14),  # Ganesh Chaturthi
    datetime(2026, 10, 2),  # Mahatma Gandhi Jayanti
    datetime(2026, 10, 20),  # Dussehra
    datetime(2026, 11, 10),  # Diwali - Balipratipada
    datetime(2026, 11, 24),  # Prakash Gurpurb Sri Guru Nanak Dev
    datetime(2026, 12, 25),  # Christmas
]


def is_holiday(date: datetime) -> bool:
    """Check if date is a market holiday"""
    return date.date() in [h.date() for h in NSE_HOLIDAYS_2026]


def get_previous_trading_day(date: datetime) -> datetime:
    """Get previous trading day if expiry falls on holiday"""
    prev_date = date - timedelta(days=1)
    while prev_date.weekday() >= 5 or is_holiday(prev_date):
        prev_date -= timedelta(days=1)
    return prev_date


def get_monthly_expiry(year: int, month: int, expiry_day: str) -> datetime:
    """Get monthly expiry date (last Tuesday/Thursday of month) - adjusted for holidays"""
    cal = monthcalendar(year, month)
    last_week = cal[-1]

    day_map = {"tuesday": 1, "wednesday": 2, "thursday": 3}
    target_day = day_map.get(expiry_day.lower(), 1)

    expiry = None
    for week in reversed(cal):
        if week[target_day] != 0:
            expiry = datetime(year, month, week[target_day])
            break

    if expiry and is_holiday(expiry):
        expiry = get_previous_trading_day(expiry)

    return expiry


def get_weekly_expiry(year: int, month: int, expiry_day: str, week_num: int = 1):
    """Get weekly expiry date (adjusted for holidays)"""
    cal = monthcalendar(year, month)
    day_map = {"tuesday": 1, "wednesday": 2, "thursday": 3}
    target_day = day_map.get(expiry_day.lower(), 1)

    count = 0
    for week in cal:
        if week[target_day] != 0:
            count += 1
            if count == week_num:
                expiry = datetime(year, month, week[target_day])
                if is_holiday(expiry):
                    return get_previous_trading_day(expiry)
                return expiry

    return None


def get_next_expiry(index_name: str) -> dict:
    """Get next expiry date for an index"""
    index = INDEXES.get(index_name.upper())
    if not index:
        return None

    now = datetime.now()
    year = now.year
    month = now.month

    monthly_exp = get_monthly_expiry(year, month, index["expiry_day"])

    if now < monthly_exp:
        return {
            "type": "MONTHLY",
            "date": monthly_exp,
            "formatted": monthly_exp.strftime("%d %b"),
            "days_left": (monthly_exp - now).days,
        }

    if month == 12:
        year += 1
        month = 1
    else:
        month += 1

    monthly_exp = get_monthly_expiry(year, month, index["expiry_day"])
    return {
        "type": "MONTHLY",
        "date": monthly_exp,
        "formatted": monthly_exp.strftime("%d %b"),
        "days_left": (monthly_exp - now).days,
    }


def get_expiry_today() -> list:
    """Check if any index expires today"""
    now = datetime.now()
    year = now.year
    month = now.month
    today_expiry = []

    for name, index in INDEXES.items():
        for week in range(1, 5):
            weekly_exp = get_weekly_expiry(year, month, index["expiry_day"], week)
            if weekly_exp and weekly_exp.date() == now.date():
                today_expiry.append(
                    {
                        "index": name,
                        "type": "WEEKLY",
                        "date": weekly_exp,
                        "formatted": weekly_exp.strftime("%d %b"),
                    }
                )

        monthly_exp = get_monthly_expiry(year, month, index["expiry_day"])
        if monthly_exp and monthly_exp.date() == now.date():
            today_expiry.append(
                {
                    "index": name,
                    "type": "MONTHLY",
                    "date": monthly_exp,
                    "formatted": monthly_exp.strftime("%d %b"),
                }
            )

    return today_expiry


def get_index_data(symbol: str) -> dict:
    """Get index data"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            "price": info.get("regularMarketPrice") or info.get("currentPrice"),
            "change": info.get("regularMarketChangePercent", 0),
            "prev": info.get("regularMarketPreviousClose"),
            "high": info.get("regularMarketDayHigh"),
            "low": info.get("regularMarketDayLow"),
        }
    except:
        return None


def calculate_option_params(underlying: float, direction: str, index_name: str) -> dict:
    """Calculate option parameters for an index"""
    index = INDEXES.get(index_name.upper())
    lot_size = index["lot_size"] if index else 25

    moneyness = -2 if direction == "PE" else 2

    if direction == "CE":
        strike = round(underlying * (1 + moneyness / 100), 0)
    else:
        strike = round(underlying * (1 - moneyness / 100), 0)

    if index_name.upper() in ["NIFTY", "BANKNIFTY", "FINNIFTY"]:
        strike = round(strike / 50) * 50
    else:
        strike = round(strike / 100) * 100

    vol = 0.15 if underlying > 10000 else 0.20
    premium = underlying * vol * 0.5

    entry = max(20, round(premium, 2))
    sl = round(entry * 0.75, 2)
    target1 = round(entry * 1.25, 2)
    target2 = round(entry * 1.50, 2)
    target3 = round(entry * 1.75, 2)

    return {
        "strike": int(strike),
        "entry": entry,
        "sl": sl,
        "targets": [target1, target2, target3],
        "lot_size": lot_size,
        "value": entry * lot_size,
    }


def generate_trades():
    """Generate trades for all major indices"""
    print("\n" + "=" * 60)
    print("INDEX EXPIRY TRADER")
    print("=" * 60)

    today_expiry = get_expiry_today()
    now = datetime.now()

    print(f"\nDate: {now.strftime('%d %b %Y')} ({now.strftime('%A')})")

    if today_expiry:
        print(f"\n[!] TODAY IS EXPIRY DAY FOR:")
        for exp in today_expiry:
            print(f"   {exp['index']} - {exp['type']}")
    else:
        print(f"\nNo index expires today")
        print("\nUpcoming Expiry Dates:")
        for name in ["NIFTY", "BANKNIFTY", "SENSEX"]:
            next_exp = get_next_expiry(name)
            if next_exp:
                print(
                    f"   {name}: {next_exp['formatted']} ({next_exp['type']}) - {next_exp['days_left']} days"
                )

    print(f"\n{'=' * 60}")
    print("INDEX DATA")
    print("=" * 60)

    trades = []

    for name, index in INDEXES.items():
        data = get_index_data(index["symbol"])

        if not data or not data.get("price"):
            continue

        print(f"\n{name}: {data['price']:,.2f} ({data['change']:+.2f}%)")

        change = data["change"]

        if change < -1:
            direction = "PE"
            print(f"  -> BEARISH -> Buy PUT")
        elif change > 1:
            direction = "CE"
            print(f"  -> BULLISH -> Buy CALL")
        else:
            direction = "PE"
            print(f"  -> SIDEWAYS -> Buy PUT")

        next_exp = get_next_expiry(name)
        expiry_str = next_exp["formatted"] if next_exp else "APR"

        option = calculate_option_params(data["price"], direction, name)

        trade = {
            "symbol": name,
            "direction": direction,
            "underlying": data["price"],
            "strike": option["strike"],
            "option_type": direction,
            "expiry": expiry_str,
            "entry": option["entry"],
            "sl": option["sl"],
            "target1": option["targets"][0],
            "target2": option["targets"][1],
            "target3": option["targets"][2],
            "lots": 1,
            "value": option["value"],
            "change": data["change"],
            "confidence": 85 if abs(change) > 1 else 70,
        }

        trades.append(trade)

        print(
            f"  Strike: {option['strike']} | Entry: Rs{option['entry']} | SL: Rs{option['sl']}"
        )

    return trades, today_expiry


def send_telegram(trades, today_expiry):
    """Send signals to Telegram"""
    telegram = TelegramNotifier()
    now = datetime.now()

    msg = "[INDEX TRADER]\n\n"
    msg += f"Date: {now.strftime('%d %b %Y')}\n"

    if today_expiry:
        msg += "\n[!] EXPIRY TODAY:\n"
        for exp in today_expiry:
            msg += f"  - {exp['index']} ({exp['type']})\n"
    else:
        next_exp = get_next_expiry("NIFTY")
        if next_exp:
            msg += f"\nNext NIFTY Expiry: {next_exp['formatted']}\n"

    msg += "\n--- TRADES ---\n"

    for trade in trades:
        msg += f"\n*{trade['symbol']}*\n"
        msg += f"Direction: {trade['direction']}\n"
        msg += f"Strike: {trade['strike']}\n"
        msg += f"Expiry: {trade['expiry']}\n"
        msg += f"Entry: Rs{trade['entry']}\n"
        msg += f"SL: Rs{trade['sl']}\n"
        msg += f"T1: Rs{trade['target1']} | T2: Rs{trade['target2']} | T3: Rs{trade['target3']}\n"
        msg += f"Lots: {trade['lots']} | Value: Rs{trade['value']:,.0f}\n"
        msg += f"Change: {trade['change']:+.2f}% | Conf: {trade['confidence']}%\n"

    telegram.send_message(msg)
    print(f"\n[SENT {len(trades)} trades to Telegram]")


if __name__ == "__main__":
    trades, today_expiry = generate_trades()
    if trades:
        send_telegram(trades, today_expiry)
