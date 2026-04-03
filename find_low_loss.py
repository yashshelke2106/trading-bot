"""
Find options trades with LOW LOSS PERCENTAGE (under 15%)
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

options = [
    ("NIFTY", "PE", 23500, 400, 340, 520, 640),
    ("NIFTY", "CE", 23500, 400, 340, 520, 640),
    ("BANKNIFTY", "PE", 52000, 200, 170, 260, 320),
    ("BANKNIFTY", "CE", 52000, 200, 170, 260, 320),
    ("RELIANCE", "PE", 2000, 80, 68, 104, 128),
    ("RELIANCE", "CE", 1400, 200, 170, 260, 320),
    ("TCS", "CE", 4200, 120, 102, 156, 192),
    ("TCS", "PE", 3800, 80, 68, 104, 128),
    ("INFY", "PE", 1300, 90, 77, 117, 144),
    ("INFY", "CE", 1300, 200, 170, 260, 320),
    ("HDFCBANK", "PE", 2500, 90, 77, 117, 144),
    ("HDFCBANK", "CE", 2600, 80, 68, 104, 128),
    ("ICICIBANK", "PE", 1200, 85, 72, 110, 136),
    ("KOTAKBANK", "PE", 1200, 45, 38, 58, 72),
    ("SBIN", "PE", 1000, 150, 128, 195, 240),
    ("SBIN", "CE", 1050, 80, 68, 104, 128),
    ("ITC", "CE", 5500, 180, 153, 234, 288),
    ("ITC", "PE", 5300, 100, 85, 130, 160),
    ("MARUTI", "CE", 12000, 280, 238, 364, 448),
    ("TATAMOTORS", "CE", 9000, 150, 128, 195, 240),
    ("BAJFINANCE", "CE", 9000, 120, 102, 156, 192),
    ("AXISBANK", "PE", 1200, 95, 81, 123, 152),
    ("HEROMOTOCO", "CE", 11000, 350, 298, 455, 560),
    ("EICHERMOT", "CE", 16700, 520, 442, 676, 832),
]

print("=" * 150)
print("LOW LOSS % TRADES - COMPLETE DETAILS")
print("=" * 150)

results = []
for sym, typ, strike, entry, sl, t1, t2 in options:
    lot = lots.get(sym, 1)
    loss_pct = (entry - sl) / entry * 100
    capital = entry * lot
    max_loss = (entry - sl) * lot
    max_profit = (t1 - entry) * lot
    rr = max_profit / max_loss

    if loss_pct <= 15 and max_loss <= 5000:
        results.append(
            (
                sym,
                typ,
                strike,
                lot,
                entry,
                sl,
                t1,
                t2,
                loss_pct,
                capital,
                max_loss,
                max_profit,
                rr,
            )
        )

results.sort(key=lambda x: x[9])

for (
    sym,
    typ,
    strike,
    lot,
    entry,
    sl,
    t1,
    t2,
    loss_pct,
    capital,
    max_loss,
    max_profit,
    rr,
) in results:
    option_type = "CALL" if typ == "CE" else "PUT"
    print(f"\n{'=' * 80}")
    print(f"  {sym} {strike} {option_type}")
    print(f"{'=' * 80}")
    print(f"  Strike     : {strike}")
    print(f"  Entry      : Rs.{entry}")
    print(f"  Stop Loss  : Rs.{sl}")
    print(f"  Target 1   : Rs.{t1}  |  Target 2: Rs.{t2}")
    print(f"  Lot Size   : {lot}")
    print(f"  Capital    : Rs.{capital:,}")
    print(f"  Max Loss   : Rs.{max_loss:,}  ({loss_pct:.1f}%)")
    print(f"  Max Profit : Rs.{max_profit:,}")
    print(f"  Risk:Reward : {rr:.1f}:1")
    print(f"  Trade      : BUY {sym} {strike} {typ} @ Rs.{entry}")

print(f"\n{'=' * 80}")
print(f"Total options: {len(results)}")
