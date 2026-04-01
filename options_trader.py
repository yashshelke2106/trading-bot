#!/usr/bin/env python3
"""
OPTIONS TRADING SYSTEM
======================
Index: Nifty 22550 PE, Banknifty 52000 CE, Finnifty 22500 PE
Stock: Amber 6700 CE, Tata 4200 CE, Reliance 3000 PE

Format: SYMBOL STRIKE TYPE (CE/PE) EXPIRY
Example: NIFTY 22550 PE 24APR, RELIANCE 3000 CE 24APR
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import yfinance as yf
except:
    import subprocess

    subprocess.run([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf

from telegram_notifier import TelegramNotifier

OPTIONS_FILE = "options_trades.json"

# Option expiry dates (NSE F&O)
EXPIRY_DATES = {
    "24APR": "2024-04-25",
    "24MAY": "2024-05-30",
    "24JUN": "2024-06-27",
    "25APR": "2025-04-24",
    "25MAY": "2025-05-29",
    "25JUN": "2025-06-26",
}

# NSE Symbol mapping for options
INDEX_MAP = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "FINNIFTY": "^NSEBANK",
}

STOCK_MAP = {
    "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "INFY": "INFY.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "KOTAKBANK": "KOTAKBANK.NS",
    "BAJFINANCE": "BAJFINANCE.NS",
    "SBIN": "SBIN.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "AXISBANK": "AXISBANK.NS",
    "LT": "LT.NS",
    "TITAN": "TITAN.NS",
    "AMBER": "AMBUJACEM.NS",  # Ambuja Cement
    "AMBUJACEM": "AMBUJACEM.NS",
    "ADANI": "ADANIPOWER.NS",
    "ADANIPOWER": "ADANIPOWER.NS",
    "SUNPHARMA": "SUNPHARMA.NS",
    "CIPLA": "CIPLA.NS",
    "TATASTEEL": "TATASTEEL.NS",
    "WIPRO": "WIPRO.NS",
}


def load_options_trades():
    if Path(OPTIONS_FILE).exists():
        with open(OPTIONS_FILE, "r") as f:
            return json.load(f)
    return {"trades": [], "closed": []}


def save_options_trades(data):
    with open(OPTIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_underlying_price(symbol):
    """Get current price of underlying"""
    if symbol in INDEX_MAP:
        nsymbol = INDEX_MAP[symbol]
    elif symbol in STOCK_MAP:
        nsymbol = STOCK_MAP[symbol]
    else:
        nsymbol = f"{symbol}.NS"

    try:
        ticker = yf.Ticker(nsymbol)
        info = ticker.info
        return info.get("currentPrice") or info.get("regularMarketPreviousClose")
    except:
        return None


def calculate_option_premium(underlying, strike, option_type, days_to_expiry=30):
    """Calculate approximate option premium using Black-Scholes approximation"""
    import math

    # Simplified estimation based on Moneyness
    if option_type == "CE":
        moneyness = (underlying - strike) / strike
    else:  # PE
        moneyness = (strike - underlying) / strike

    # Time value based on days to expiry
    time_factor = math.sqrt(days_to_expiry / 365)

    # Volatility approximation (Nifty ~15%, Stocks ~25-35%)
    if symbol in INDEX_MAP:
        vol = 0.15
    else:
        vol = 0.30

    # Simple premium estimation
    if moneyness > 0.1:  # Deep ITM
        premium = underlying * 0.03
    elif moneyness > 0:  # ITM
        premium = underlying * vol * time_factor * 0.5
    elif moneyness > -0.05:  # ATM
        premium = underlying * vol * time_factor * 0.8
    else:  # OTM
        premium = underlying * vol * time_factor * 0.3

    return max(5, round(premium, 2))


def add_option_trade(
    symbol,
    strike,
    option_type,
    expiry,
    direction,
    entry_premium,
    sl_premium,
    targets_list,
    lots=1,
    notes="",
):
    """Add an options trade"""
    data = load_options_trades()

    underlying = get_underlying_price(symbol)

    trade = {
        "id": len(data["trades"]) + 1,
        "symbol": symbol,
        "strike": strike,
        "type": option_type.upper(),  # CE or PE
        "expiry": expiry,
        "direction": direction.upper(),  # BUY or SELL
        "entry_premium": entry_premium,
        "sl_premium": sl_premium,
        "targets": targets_list,  # [150, 170, 200] or [205, 235, 255]
        "lots": lots,
        "underlying_price": underlying,
        "entry_time": datetime.now().isoformat(),
        "status": "OPEN",
        "pnl": 0,
        "notes": notes,
        "symbol_format": f"{symbol} {strike} {option_type.upper()} {expiry}",
    }

    data["trades"].append(trade)
    save_options_trades(data)

    return trade


def check_options_trades():
    """Check all options trades for SL/Target hits"""
    data = load_options_trades()
    telegram = TelegramNotifier()
    market = get_underlying_price("NIFTY") or 22000

    print(f"\n[Checking Options Trades | Nifty: {market}]")

    sl_hits = []
    target_hits = []
    updates = []

    for trade in data["trades"]:
        if trade["status"] != "OPEN":
            continue

        symbol = trade["symbol"]
        strike = trade["strike"]
        option_type = trade["type"]

        # Get current underlying price
        underlying = get_underlying_price(symbol)
        if not underlying:
            print(f"  {trade['symbol_format']}: Price unavailable")
            continue

        # Estimate current premium (simplified)
        current_premium = calculate_option_premium(underlying, strike, option_type)

        entry = trade["entry_premium"]
        sl = trade["sl_premium"]
        direction = trade["direction"]

        if direction == "BUY":
            # For BUY options, SL hit when premium drops below SL
            if current_premium <= sl:
                trade["status"] = "SL_HIT"
                trade["pnl"] = (sl - entry) * trade["lots"] * 75  # 75 is lot size
                trade["exit_premium"] = current_premium
                trade["exit_time"] = datetime.now().isoformat()
                sl_hits.append(trade)
                print(
                    f"  [SL] {trade['symbol_format']}: Premium {current_premium} <= SL {sl}"
                )

            # Check each target
            elif any(current_premium >= t for t in trade["targets"]):
                hit_target = min([t for t in trade["targets"] if current_premium >= t])
                trade["status"] = f"TARGET_{hit_target}"
                trade["pnl"] = (hit_target - entry) * trade["lots"] * 75
                trade["exit_premium"] = current_premium
                trade["exit_time"] = datetime.now().isoformat()
                target_hits.append(trade)
                print(f"  [TARGET] {trade['symbol_format']}: Hit {hit_target}")
            else:
                pnl = (current_premium - entry) * trade["lots"] * 75
                print(
                    f"  [OPEN] {trade['symbol_format']}: Premium {current_premium} | P&L: Rs {pnl}"
                )

        else:  # SELL
            if current_premium >= sl:
                trade["status"] = "SL_HIT"
                trade["pnl"] = (entry - sl) * trade["lots"] * 75
                trade["exit_premium"] = current_premium
                trade["exit_time"] = datetime.now().isoformat()
                sl_hits.append(trade)
                print(f"  [SL] {trade['symbol_format']}")

            elif any(current_premium <= t for t in trade["targets"]):
                hit_target = min([t for t in trade["targets"] if current_premium <= t])
                trade["status"] = f"TARGET_{hit_target}"
                trade["pnl"] = (entry - hit_target) * trade["lots"] * 75
                trade["exit_premium"] = current_premium
                trade["exit_time"] = datetime.now().isoformat()
                target_hits.append(trade)
                print(f"  [TARGET] {trade['symbol_format']}")

    save_options_trades(data)

    # Send Telegram alerts
    if sl_hits:
        msg = "*OPTIONS SL HIT*\n\n"
        for t in sl_hits:
            msg += f"{t['symbol_format']}\nP&L: Rs {t['pnl']}\n"
        telegram.send_message(msg)

    if target_hits:
        msg = "*OPTIONS TARGET HIT*\n\n"
        for t in target_hits:
            msg += f"{t['symbol_format']}\nP&L: Rs {t['pnl']}\n"
        telegram.send_message(msg)

    return len(sl_hits), len(target_hits)


def show_options_trades():
    """Show all options trades"""
    data = load_options_trades()

    print("\n" + "=" * 60)
    print("OPTIONS TRADING PORTFOLIO")
    print("=" * 60)

    print("\n[OPEN POSITIONS]")
    for t in data["trades"]:
        if t["status"] == "OPEN":
            print(f"  {t['symbol_format']}")
            print(f"    Direction: {t['direction']}")
            print(f"    Entry: {t['entry_premium']} | SL: {t['sl_premium']}")
            print(f"    Targets: {t['targets']}")
            print(f"    Lots: {t['lots']}")

    print(f"\nTotal Open: {len([t for t in data['trades'] if t['status'] == 'OPEN'])}")


# Quick add examples
def add_example_trades():
    """Add example trades for demonstration"""
    # Nifty PE 22550 - Buy at 190, SL 180, Targets 205, 235, 255
    add_option_trade(
        symbol="NIFTY",
        strike=22550,
        option_type="PE",
        expiry="25APR",
        direction="BUY",
        entry_premium=190,
        sl_premium=180,
        targets_list=[205, 235, 255],
        lots=1,
        notes="Nifty Put 22550",
    )

    # Amber 6700 CE - Buy at 130, SL 105, Targets 150, 170+
    add_option_trade(
        symbol="AMBUJACEM",
        strike=6700,
        option_type="CE",
        expiry="25APR",
        direction="BUY",
        entry_premium=130,
        sl_premium=105,
        targets_list=[150, 170, 200],
        lots=1,
        notes="Ambuja Cement Call 6700",
    )

    print("Example trades added")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--add",
        nargs="+",
        help="Add: SYMBOL STRIKE CE/PE EXPIRY BUY/SELL ENTRY SL TARGET1 TARGET2...",
    )
    parser.add_argument("--check", action="store_true", help="Check all options")
    parser.add_argument("--list", action="store_true", help="List all trades")
    parser.add_argument("--examples", action="store_true", help="Add example trades")
    args = parser.parse_args()

    if args.add:
        # Usage: python options_trader.py --add NIFTY 22550 PE 25APR BUY 190 180 205 235 255
        symbol = args.add[0]
        strike = int(args.add[1])
        opt_type = args.add[2]
        expiry = args.add[3]
        direction = args.add[4]
        entry = float(args.add[5])
        sl = float(args.add[6])
        targets = [float(t) for t in args.add[7:]]

        trade = add_option_trade(
            symbol, strike, opt_type, expiry, direction, entry, sl, targets
        )
        print(f"Added: {trade['symbol_format']}")

    elif args.examples:
        add_example_trades()

    elif args.check:
        check_options_trades()

    elif args.list:
        show_options_trades()

    else:
        print("Options Trading Commands:")
        print("  --add SYMBOL STRIKE CE/PE EXPIRY BUY/SELL ENTRY SL TARGET1 TARGET2...")
        print("  --check (check SL/Target)")
        print("  --list (show all trades)")
        print("  --examples (add demo trades)")
        print("\nExample:")
        print(
            "  python options_trader.py --add NIFTY 22550 PE 25APR BUY 190 180 205 235 255"
        )
