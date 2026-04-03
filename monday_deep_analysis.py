"""
MONDAY DEEP ANALYSIS
Proper strike selection based on momentum direction
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

print("=" * 90)
print("MONDAY DEEP ANALYSIS - PROPER STRIKE SELECTION")
print("=" * 90)
print()
print("Based on Friday's momentum scan (March 28)")
print("Expiry: April 3, 2026 (Thursday)")
print()

trades = [
    {
        "symbol": "RELIANCE",
        "direction": "SHORT",
        "current_price": 1958,
        "strike": 2000,
        "type": "PE",
        "entry": 59,
        "sl": 30,
        "t1": 118,
        "t2": 177,
        "reason": "RSI 72 overbought, bearish engulfing, above VWAP",
        "momentum": 70,
    },
    {
        "symbol": "RELIANCE",
        "direction": "LONG",
        "current_price": 1958,
        "strike": 1950,
        "type": "CE",
        "entry": 90,
        "sl": 55,
        "t1": 162,
        "t2": 234,
        "reason": "If bounces from support (only if RSI < 40)",
        "momentum": 50,
    },
    {
        "symbol": "EICHERMOT",
        "direction": "LONG",
        "current_price": 16727,
        "strike": 16700,
        "type": "CE",
        "entry": 502,
        "sl": 350,
        "t1": 900,
        "t2": 1300,
        "reason": "RSI <1 oversold! Strong bounce expected, down -6.7%",
        "momentum": 70,
    },
    {
        "symbol": "EICHERMOT",
        "direction": "SHORT",
        "current_price": 16727,
        "strike": 16800,
        "type": "PE",
        "entry": 350,
        "sl": 200,
        "t1": 630,
        "t2": 910,
        "reason": "Only if continues down below 16500",
        "momentum": 40,
    },
    {
        "symbol": "HEROMOTOCO",
        "direction": "LONG",
        "current_price": 10992,
        "strike": 11000,
        "type": "CE",
        "entry": 330,
        "sl": 220,
        "t1": 594,
        "t2": 858,
        "reason": "RSI 22 oversold, strong bounce, down -5.5%",
        "momentum": 70,
    },
    {
        "symbol": "HEROMOTOCO",
        "direction": "SHORT",
        "current_price": 10992,
        "strike": 11100,
        "type": "PE",
        "entry": 280,
        "sl": 150,
        "t1": 504,
        "t2": 728,
        "reason": "Only if breaks below 10700",
        "momentum": 40,
    },
    {
        "symbol": "KOTAKBANK",
        "direction": "SHORT",
        "current_price": 1216,
        "strike": 1200,
        "type": "PE",
        "entry": 45,
        "sl": 25,
        "t1": 81,
        "t2": 117,
        "reason": "RSI 77 overbought! Up +8.8%, exhausted",
        "momentum": 60,
    },
    {
        "symbol": "KOTAKBANK",
        "direction": "LONG",
        "current_price": 1216,
        "strike": 1200,
        "type": "CE",
        "entry": 70,
        "sl": 45,
        "t1": 126,
        "t2": 182,
        "reason": "Only if holds above 1200",
        "momentum": 40,
    },
    {
        "symbol": "NIFTY",
        "direction": "SHORT",
        "current_price": 22800,
        "strike": 22800,
        "type": "PE",
        "entry": 350,
        "sl": 220,
        "t1": 630,
        "t2": 910,
        "reason": "RSI 75 overbought, ranging below VWAP",
        "momentum": 60,
    },
    {
        "symbol": "NIFTY",
        "direction": "LONG",
        "current_price": 22800,
        "strike": 22700,
        "type": "CE",
        "entry": 400,
        "sl": 280,
        "t1": 720,
        "t2": 1040,
        "reason": "Only if breaks above 23000 with volume",
        "momentum": 55,
    },
    {
        "symbol": "INFY",
        "direction": "SHORT",
        "current_price": 1276,
        "strike": 12750,
        "type": "CE",
        "entry": 180,
        "sl": 110,
        "t1": 324,
        "t2": 468,
        "reason": "Only if continues up above 1300",
        "momentum": 45,
    },
    {
        "symbol": "INFY",
        "direction": "LONG",
        "current_price": 1276,
        "strike": 12750,
        "type": "PE",
        "entry": 200,
        "sl": 130,
        "t1": 360,
        "t2": 520,
        "reason": "Oversold, bounce play",
        "momentum": 60,
    },
]

print("=" * 90)
print("BEARISH SETUPS (Buy Put)")
print("=" * 90)
bearish = [t for t in trades if t["direction"] == "SHORT"]
for i, t in enumerate(bearish, 1):
    lot = lots.get(t["symbol"], 1)
    capital = t["entry"] * lot
    max_loss = (t["entry"] - t["sl"]) * lot
    max_profit = (t["t1"] - t["entry"]) * lot
    loss_pct = (t["entry"] - t["sl"]) / t["entry"] * 100

    print(f"\n#{i} {t['symbol']} - {t['direction'].upper()}")
    print(f"   Current Price : Rs.{t['current_price']}")
    print(f"   Strike        : {t['strike']} {t['type']}")
    print(f"   Entry         : Rs.{t['entry']}")
    print(f"   Stop Loss     : Rs.{t['sl']}")
    print(f"   Target 1      : Rs.{t['t1']}")
    print(f"   Target 2      : Rs.{t['t2']}")
    print(f"   Lot           : {lot}")
    print(f"   Capital       : Rs.{capital:,}")
    print(f"   Max Loss      : Rs.{max_loss:,} ({loss_pct:.0f}%)")
    print(f"   Max Profit    : Rs.{max_profit:,}")
    print(f"   Momentum      : {t['momentum']}%")
    print(f"   Reason        : {t['reason']}")

print("\n" + "=" * 90)
print("BULLISH SETUPS (Buy Call)")
print("=" * 90)
bullish = [t for t in trades if t["direction"] == "LONG"]
for i, t in enumerate(bullish, 1):
    lot = lots.get(t["symbol"], 1)
    capital = t["entry"] * lot
    max_loss = (t["entry"] - t["sl"]) * lot
    max_profit = (t["t1"] - t["entry"]) * lot
    loss_pct = (t["entry"] - t["sl"]) / t["entry"] * 100

    print(f"\n#{i} {t['symbol']} - {t['direction'].upper()}")
    print(f"   Current Price : Rs.{t['current_price']}")
    print(f"   Strike        : {t['strike']} {t['type']}")
    print(f"   Entry         : Rs.{t['entry']}")
    print(f"   Stop Loss     : Rs.{t['sl']}")
    print(f"   Target 1      : Rs.{t['t1']}")
    print(f"   Target 2      : Rs.{t['t2']}")
    print(f"   Lot           : {lot}")
    print(f"   Capital       : Rs.{capital:,}")
    print(f"   Max Loss      : Rs.{max_loss:,} ({loss_pct:.0f}%)")
    print(f"   Max Profit    : Rs.{max_profit:,}")
    print(f"   Momentum      : {t['momentum']}%")
    print(f"   Reason        : {t['reason']}")

print("\n" + "=" * 90)
print("TOP PICKS FOR MONDAY")
print("=" * 90)
top_picks = [
    ("RELIANCE 2000 PE", 29500, 15000, 29500, 70, "Short setup - RSI 72"),
    ("EICHERMOT 16700 CE", 62750, 19000, 49750, 70, "Bounce play - RSI <1"),
    ("HEROMOTOCO 11000 CE", 41250, 13750, 33000, 70, "Bounce play - RSI 22"),
    ("KOTAKBANK 1200 PE", 11250, 9000, 9000, 60, "Short setup - RSI 77"),
]
for i, (trade, capital, loss, profit, mom, reason) in enumerate(top_picks, 1):
    print(f"\n#{i} {trade}")
    print(
        f"   Capital: Rs.{capital:,} | Max Loss: Rs.{loss:,} | Max Profit: Rs.{profit:,}"
    )
    print(f"   Momentum: {mom}% | {reason}")
