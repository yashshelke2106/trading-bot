#!/usr/bin/env python3
"""
SENSEX Scalper - Detailed Report with Charges
"""

trades = [
    {"type": "PUT", "strike": 73000, "buy": 17.64, "sell": 26.46, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 17.89, "sell": 26.84, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 18.73, "sell": 28.10, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 17.34, "sell": 26.01, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 18.60, "sell": 27.90, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 18.02, "sell": 27.03, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 17.69, "sell": 26.54, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 18.15, "sell": 27.23, "lots": 50},
    {"type": "PUT", "strike": 73000, "buy": 17.94, "sell": 26.91, "lots": 50},
    {"type": "CALL", "strike": 73200, "buy": 17.99, "sell": 26.99, "lots": 50},
]

BROKERAGE = 20
STT = 0.001
GST = 0.18
EXCHANGE = 0.002
SEBI = 0.0001

print("=" * 80)
print("              SENSEX SCALPER - DETAILED CHARGES REPORT")
print("=" * 80)
print()
print("| # | Type | Strike | Buy   | Sell  | Lots | Gross   | Charges | Net P&L |")
print("|" + "-" * 77 + "|")

total_gross = 0
total_charges = 0

for i, t in enumerate(trades, 1):
    buy_val = t["buy"] * t["lots"]
    sell_val = t["sell"] * t["lots"]
    gross = (t["sell"] - t["buy"]) * t["lots"]

    charges = (
        (BROKERAGE * 2)
        + (sell_val * STT)
        + ((buy_val + sell_val) * EXCHANGE)
        + ((buy_val + sell_val) * SEBI)
        + (BROKERAGE * 2 * GST)
    )
    net = gross - charges

    total_gross += gross
    total_charges += charges

    print(
        f"| {i:>2} | {t['type']:<4} | {t['strike']:<6} | {t['buy']:<5} | {t['sell']:<5} | {t['lots']:<4} | Rs {gross:<6.0f} | Rs {charges:<6.0f} | Rs {net:<6.0f} |"
    )

print("|" + "=" * 77 + "|")

total_invested = sum(t["buy"] * t["lots"] for t in trades)
net_pnl = total_gross - total_charges

print()
print("--- CHARGES BREAKUP (per 10 trades) ---")
brokerage_all = BROKERAGE * 2 * len(trades)
stt_all = sum(t["sell"] * t["lots"] * STT for t in trades)
exchange_all = sum((t["buy"] + t["sell"]) * t["lots"] * EXCHANGE for t in trades)
sebi_all = sum((t["buy"] + t["sell"]) * t["lots"] * SEBI for t in trades)
gst_all = brokerage_all * GST

print(f"Brokerage (Buy+Sell): Rs {brokerage_all:,.0f}")
print(f"STT (0.1% on sell):    Rs {stt_all:,.0f}")
print(f"Exchange (0.2%):       Rs {exchange_all:,.0f}")
print(f"SEBI (0.01%):          Rs {sebi_all:,.0f}")
print(f"GST (18%):             Rs {gst_all:,.0f}")
print(f"                       --------")
print(f"Total Charges:         Rs {total_charges:,.0f}")
print()
print("=" * 65)
print(f"TOTAL INVESTED:        Rs {total_invested:,.0f}")
print(f"GROSS P&L:             Rs {total_gross:,.0f}")
print(f"CHARGES:               Rs {total_charges:,.0f}")
print(f"NET P&L:               Rs {net_pnl:,.0f}")
print(f"RETURN:                {(net_pnl / total_invested) * 100:.1f}%")
print("=" * 65)
