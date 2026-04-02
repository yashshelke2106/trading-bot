trades = [
    {"type": "PUT", "strike": 73000, "buy": 19.38, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 16.57, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 19.34, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 16.69, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 19.38, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 17.04, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 18.81, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 16.94, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 19.10, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 16.99, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 19.13, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 17.02, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 18.98, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 16.85, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 18.93, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 17.21, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 18.63, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 17.51, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 18.49, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 17.40, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 18.51, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 17.61, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 18.42, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 17.43, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 19.10, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 16.85, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 19.47, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 16.72, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 19.01, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 16.80, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 19.28, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 16.80, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 18.99, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 16.99, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 19.02, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 16.92, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 19.05, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 16.82, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 19.14, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 16.98, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 19.04, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 17.01, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 19.09, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 17.05, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 19.02, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 17.61, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 18.32, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 17.90, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 17.44, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 18.32, "lots": 50},
]

BROKERAGE = 20
STT = 0.001
GST = 0.18
EXCHANGE = 0.002
SEBI = 0.0001

total_gross = 0
total_invested = 0

for i, t in enumerate(trades):
    sell_price = t["buy"] * 1.5
    buy_val = t["buy"] * t["lots"]
    sell_val = sell_price * t["lots"]
    gross = (sell_price - t["buy"]) * t["lots"]

    charges = (
        (BROKERAGE * 2)
        + (sell_val * STT)
        + ((buy_val + sell_val) * EXCHANGE)
        + ((buy_val + sell_val) * SEBI)
        + (BROKERAGE * 2 * GST)
    )
    net = gross - charges

    total_gross += gross
    total_invested += buy_val

total_charges = (
    (BROKERAGE * 2 * len(trades))
    + (total_gross * 0.001)
    + (total_invested * 0.002)
    + (total_invested * 0.0001)
    + (BROKERAGE * 2 * len(trades) * GST)
)
net_pnl = total_gross - total_charges

puts = len([t for t in trades if t["type"] == "PUT"])
calls = len([t for t in trades if t["type"] == "CALL"])

print("=" * 70)
print("          SENSEX EXPIRY SCALPER - FINAL SUMMARY")
print("=" * 70)
print()
print(f"Total Trades:         {len(trades)}")
print(f"PUT Trades:           {puts}")
print(f"CALL Trades:          {calls}")
print()
print("--- INVESTMENT ---")
print(f"Total Invested:        Rs {total_invested:,.0f}")
print(f"Avg Invested/Trade:    Rs {total_invested / len(trades):,.0f}")
print()
print("--- GROSS P&L (Before Charges) ---")
print(f"Gross P&L:             Rs {total_gross:,.0f}")
print(f"Avg P&L/Trade:         Rs {total_gross / len(trades):,.0f}")
print()
print("--- CHARGES ---")
brokerage = BROKERAGE * 2 * len(trades)
stt = total_gross * 0.001
exchange = total_invested * 0.002
sebi = total_invested * 0.0001
gst = brokerage * GST

print(f"Brokerage:             Rs {brokerage:,.0f}")
print(f"STT (0.1%):            Rs {stt:,.0f}")
print(f"Exchange (0.2%):       Rs {exchange:,.0f}")
print(f"SEBI (0.01%):          Rs {sebi:,.0f}")
print(f"GST (18%):             Rs {gst:,.0f}")
print(f"                       --------")
print(f"Total Charges:        Rs {total_charges:,.0f}")
print()
print("=" * 70)
print(f"NET P&L:               Rs {net_pnl:,.0f}")
print(f"RETURN ON INVESTMENT:  {(net_pnl / total_invested) * 100:.1f}%")
print(f"Avg Net P&L/Trade:     Rs {net_pnl / len(trades):,.0f}")
print("=" * 70)
