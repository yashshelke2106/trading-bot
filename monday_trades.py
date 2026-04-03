"""
MONDAY MOMENTUM TRADES
Based on last scan + technical analysis
15% loss, 1:5 R:R ratio
"""

lots = {
    "NIFTY": 65,
    "BANKNIFTY": 30,
    "FINNIFTY": 25,
    "SENSEX": 10,
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
    "ASIANPAINT": 250,
    "AXISBANK": 250,
    "MARUTI": 100,
    "TATAMOTORS": 250,
    "M&M": 500,
}

print("=" * 80)
print("MONDAY MOMENTUM TRADES - 15% Loss, 1:5 R:R")
print("=" * 80)
print()

trades = [
    {
        "symbol": "NIFTY",
        "direction": "LONG",
        "strike": 23500,
        "type": "CE",
        "entry": 400,
        "sl": 340,
        "t1": 645,
        "t2": 890,
        "reason": "Bullish engulfing, RSI recovering",
        "momentum": 75,
    },
    {
        "symbol": "NIFTY",
        "direction": "SHORT",
        "strike": 23500,
        "type": "PE",
        "entry": 400,
        "sl": 340,
        "t1": 645,
        "t2": 890,
        "reason": "If market opens gap down",
        "momentum": 70,
    },
    {
        "symbol": "RELIANCE",
        "direction": "SHORT",
        "strike": 2000,
        "type": "PE",
        "entry": 80,
        "sl": 68,
        "t1": 129,
        "t2": 178,
        "reason": "RSI overbought 72, bearish setup",
        "momentum": 70,
    },
    {
        "symbol": "KOTAKBANK",
        "direction": "SHORT",
        "strike": 1200,
        "type": "PE",
        "entry": 45,
        "sl": 38,
        "t1": 73,
        "t2": 101,
        "reason": "RSI 77 overbought, uptrend exhaustion",
        "momentum": 60,
    },
    {
        "symbol": "INFY",
        "direction": "LONG",
        "strike": 1300,
        "type": "CE",
        "entry": 90,
        "sl": 77,
        "t1": 145,
        "t2": 200,
        "reason": "Oversold bounce, RSI 25",
        "momentum": 65,
    },
    {
        "symbol": "HEROMOTOCO",
        "direction": "LONG",
        "strike": 11000,
        "type": "CE",
        "entry": 330,
        "sl": 280,
        "t1": 532,
        "t2": 734,
        "reason": "RSI 22 oversold, reversal play",
        "momentum": 70,
    },
    {
        "symbol": "EICHERMOT",
        "direction": "LONG",
        "strike": 16700,
        "type": "CE",
        "entry": 500,
        "sl": 425,
        "t1": 806,
        "t2": 1112,
        "reason": "RSI <1 oversold, bounce expected",
        "momentum": 70,
    },
    {
        "symbol": "ASIANPAINT",
        "direction": "LONG",
        "strike": 16700,
        "type": "CE",
        "entry": 500,
        "sl": 425,
        "t1": 806,
        "t2": 1112,
        "reason": "RSI 22 oversold, oversold bounce",
        "momentum": 65,
    },
    {
        "symbol": "ITC",
        "direction": "LONG",
        "strike": 5500,
        "type": "CE",
        "entry": 165,
        "sl": 140,
        "t1": 266,
        "t2": 367,
        "reason": "RSI 28 oversold, bounce play",
        "momentum": 60,
    },
    {
        "symbol": "AXISBANK",
        "direction": "LONG",
        "strike": 12600,
        "type": "CE",
        "entry": 375,
        "sl": 319,
        "t1": 605,
        "t2": 835,
        "reason": "RSI 33, downtrend exhaustion",
        "momentum": 55,
    },
    {
        "symbol": "BANKNIFTY",
        "direction": "LONG",
        "strike": 52000,
        "type": "CE",
        "entry": 200,
        "sl": 170,
        "t1": 323,
        "t2": 446,
        "reason": "Support bounce play",
        "momentum": 60,
    },
    {
        "symbol": "BANKNIFTY",
        "direction": "SHORT",
        "strike": 52000,
        "type": "PE",
        "entry": 200,
        "sl": 170,
        "t1": 323,
        "t2": 446,
        "reason": "If resistance rejected",
        "momentum": 60,
    },
]

for i, t in enumerate(trades, 1):
    lot = lots.get(t["symbol"], 1)
    capital = t["entry"] * lot
    max_loss = (t["entry"] - t["sl"]) * lot
    max_profit = (t["t1"] - t["entry"]) * lot
    loss_pct = (t["entry"] - t["sl"]) / t["entry"] * 100

    print("=" * 80)
    print(f"#{i} {t['symbol']} {t['strike']} {t['type']} - {t['direction']}")
    print("=" * 80)
    print(f"  Strike     : {t['strike']}")
    print(f"  Entry      : Rs.{t['entry']}")
    print(f"  Stop Loss  : Rs.{t['sl']}")
    print(f"  Target 1   : Rs.{t['t1']}  |  Target 2: Rs.{t['t2']}")
    print(f"  Lot Size   : {lot}")
    print(f"  Capital    : Rs.{capital:,}")
    print(f"  Max Loss   : Rs.{max_loss:,}  ({loss_pct:.1f}%)")
    print(f"  Max Profit : Rs.{max_profit:,}  (at T1)")
    print(f"  Momentum   : {t['momentum']}%")
    print(f"  Reason     : {t['reason']}")
    print()
    print(f"  TRADE: BUY {t['symbol']} {t['strike']} {t['type']} @ Rs.{t['entry']}")
    print()

print("=" * 80)
print(f"Total trades: {len(trades)}")
print()
print("NOTE: Run 'python live_nifty_entry.py' during market hours for exact entries")
