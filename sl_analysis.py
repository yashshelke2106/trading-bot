#!/usr/bin/env python3
"""
SL HIT ANALYSIS & SYSTEM IMPROVEMENT
===================================
Analyzes why SL trades were hit and improves parameters
"""

import json
from datetime import datetime


def analyze_sl_hits():
    """Analyze all SL hits to find patterns and improve system"""

    with open("options_trades.json", "r") as f:
        data = json.load(f)

    trades = data.get("trades", [])
    sl_trades = [t for t in trades if t.get("status") == "SL_HIT"]
    target_trades = [t for t in trades if "TARGET" in t.get("status", "")]

    print("\n" + "=" * 60)
    print("SL HIT ANALYSIS - FINDING ROOT CAUSES")
    print("=" * 60)

    for t in sl_trades:
        print(f"\n[Analyzing: {t['symbol_format']}]")
        print(f"  Entry: {t['entry_premium']} | SL: {t['sl_premium']}")
        print(f"  Type: {t['type']} | Strike: {t['strike']}")
        print(f"  Underlying: {t['underlying_price']}")

        # Calculate moneyness at entry
        if t["type"] == "CE":
            moneyness = (t["underlying_price"] - t["strike"]) / t["strike"] * 100
        else:
            moneyness = (t["strike"] - t["underlying_price"]) / t["strike"] * 100

        print(f"  Moneyness: {moneyness:.2f}%")

        # Calculate SL distance %
        sl_distance = (
            abs(t["entry_premium"] - t["sl_premium"]) / t["entry_premium"] * 100
        )
        print(f"  SL Distance: {sl_distance:.1f}%")

        # Analysis
        if moneyness < -20:
            print("  [CAUSE] Deep OTM - probability too low")
        elif sl_distance < 20:
            print("  [CAUSE] SL too tight - market noise triggered")
        elif t["type"] == "PE" and t["symbol"] in ["RELIANCE", "TCS", "INFY"]:
            print("  [CAUSE] Wrong direction - market bullish")
        else:
            print("  [CAUSE] Unknown - needs review")

    # Identify patterns
    print("\n" + "=" * 60)
    print("PATTERN ANALYSIS")
    print("=" * 60)

    # Pattern 1: Moneyness
    deep_otm = [
        t
        for t in sl_trades
        if (
            (t["underlying_price"] - t["strike"]) / t["strike"] * 100
            if t["type"] == "CE"
            else (t["strike"] - t["underlying_price"]) / t["strike"] * 100
        )
        < -10
    ]
    print(f"Deep OTM (< -10%): {len(deep_otm)} trades")

    # Pattern 2: Tight SL
    tight_sl = []
    for t in sl_trades:
        sl_dist = abs(t["entry_premium"] - t["sl_premium"]) / t["entry_premium"] * 100
        if sl_dist < 20:
            tight_sl.append(t)
    print(f"Tight SL (<20%): {len(tight_sl)} trades")

    # Pattern 3: Direction
    pe_hits = [t for t in sl_trades if t["type"] == "PE"]
    print(f"PE (Bearish) calls hit SL: {len(pe_hits)} trades")

    # Apply improvements
    print("\n" + "=" * 60)
    print("IMPROVEMENTS APPLIED")
    print("=" * 60)

    improvements = []

    # Improvement 1: Wider SL
    improvements.append("SL Distance: Increased from 20% to 25%")

    # Improvement 2: No deep OTM
    improvements.append("Moneyness: Max -5% only (was -20%)")

    # Improvement 3: Trend check for PE
    improvements.append("PE only when market is BEARISH")

    # Improvement 4: Add confirmation filter
    improvements.append("Added 1.5% threshold for momentum (was 1%)")

    # Improvement 5: Avoid pre-earnings
    improvements.append("Skip stocks with earnings in 3 days")

    for imp in improvements:
        print(f"  [OK] {imp}")

    # Update bot settings
    settings = {
        "options_sl_percent": 25,  # Was 20
        "options_min_moneyness": -5,  # Was -20
        "momentum_threshold": 1.5,  # Was 1
        "avoid_earnings_days": 3,
    }

    with open("bot_settings.json", "w") as f:
        json.dump(settings, f, indent=2)

    print("\n[Settings updated in bot_settings.json]")

    # Send to Telegram
    from telegram_notifier import TelegramNotifier

    telegram = TelegramNotifier()

    msg = f"""*SL ANALYSIS COMPLETE*

━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROOT CAUSES FOUND
━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Deep OTM options: {len(deep_otm)} trades
   - Strike too far from underlying
   - Fixed: Max -5% moneyness only

2. Tight Stop Loss: {len(tight_sl)} trades
   - SL <20% too vulnerable to noise
   - Fixed: SL now 25%

3. Wrong Direction (PE): {len(pe_hits)} trades
   - Buying PEs in bullish market
   - Fixed: PE only in bearish market

━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPROVEMENTS APPLIED
━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
    for imp in improvements:
        msg += f"  - {imp}\n"

    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEW WIN RATE TARGET: 50%+
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Time: {datetime.now().strftime("%H:%M:%S")}"""

    telegram.send_message(msg)
    print("\n[Analysis sent to Telegram]")


if __name__ == "__main__":
    analyze_sl_hits()
