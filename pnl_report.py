#!/usr/bin/env python3
"""
DAILY P&L REPORT GENERATOR
===========================
Generates profit/loss report for all trades
"""

import json
from datetime import datetime


def generate_pnl_report():
    """Generate P&L report from trades"""

    with open("options_trades.json", "r") as f:
        data = json.load(f)

    trades = data.get("trades", [])

    # Categorize
    closed = [t for t in trades if t.get("status") != "OPEN"]
    open_trades = [t for t in trades if t.get("status") == "OPEN"]

    # Closed trades stats
    targets_hit = [t for t in closed if "TARGET" in t.get("status", "")]
    sl_hit = [t for t in closed if t.get("status") == "SL_HIT"]

    total_pnl = sum(t.get("pnl", 0) for t in closed)

    # Win rate
    total_closed = len(closed)
    win_rate = (len(targets_hit) / total_closed * 100) if total_closed > 0 else 0

    print("\n" + "=" * 60)
    print("DAILY P&L REPORT")
    print("=" * 60)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\n[CLOSED TRADES: {total_closed}]")
    print(f"  Targets Hit: {len(targets_hit)}")
    print(f"  SL Hit: {len(sl_hit)}")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Total P&L: Rs {total_pnl:,.2f}")

    print("\n[CLOSED TRADE DETAILS]")
    print("-" * 60)
    for t in closed:
        status_icon = "[TARGET]" if "TARGET" in t.get("status", "") else "[SL]"
        print(f"  {status_icon} {t['symbol_format']}")
        print(
            f"      Entry: {t['entry_premium']} | Exit: {t.get('exit_premium', t.get('sl_premium'))}"
        )
        print(f"      P&L: Rs {t['pnl']:,.2f} | Status: {t['status']}")

    print(f"\n[OPEN TRADES: {len(open_trades)}]")
    for t in open_trades[:5]:
        print(f"  [OPEN] {t['symbol_format']} @ {t['entry_premium']}")

    print(f"\n[TODAY'S SIGNALS (OPEN)]")
    # Group by source
    momentum = [t for t in open_trades if "Momentum" in t.get("notes", "")]
    auto_scan = [t for t in open_trades if "Auto-scan" in t.get("notes", "")]
    manual = [t for t in open_trades if not t.get("notes")]

    print(f"  Momentum Signals: {len(momentum)}")
    print(f"  Auto Scan: {len(auto_scan)}")
    print(f"  Manual: {len(manual)}")

    # Calculate expected value
    avg_win = 0
    avg_loss = 0
    rr = 0
    expected = 0

    if closed:
        avg_win = (
            sum(t["pnl"] for t in targets_hit) / len(targets_hit) if targets_hit else 0
        )
        avg_loss = sum(t["pnl"] for t in sl_hit) / len(sl_hit) if sl_hit else 0

        print(f"\n[METRICS]")
        print(f"  Avg Win: Rs {avg_win:,.2f}")
        print(f"  Avg Loss: Rs {abs(avg_loss):,.2f}")

        if avg_loss != 0:
            rr = abs(avg_win / avg_loss)
            print(f"  Risk:Reward: 1:{rr:.2f}")

        expected = (win_rate / 100 * avg_win) + ((100 - win_rate) / 100 * avg_loss)
        print(f"  Expected Value per trade: Rs {expected:,.2f}")

    # Send to Telegram
    from telegram_notifier import TelegramNotifier

    telegram = TelegramNotifier()

    msg = f"""*DAILY P&L REPORT*

━━━━━━━━━━━━━━━━━━━━━━━━━━━
CLOSED: {total_closed} trades
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Targets Hit: {len(targets_hit)}
SL Hit: {len(sl_hit)}
Win Rate: {win_rate:.1f}%

Total P&L: Rs {total_pnl:,}

━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPEN POSITIONS: {len(open_trades)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Momentum: {len(momentum)}
Auto Scan: {len(auto_scan)}

"""

    if closed and total_closed > 0:
        msg += f"""[METRICS]
Avg Win: Rs {avg_win:,.0f}
Avg Loss: Rs {abs(avg_loss):,.0f}
R:R: 1:{rr:.1f}
Exp Value: Rs {expected:,.0f}/trade

"""

    msg += f"Generated: {datetime.now().strftime('%H:%M:%S')}"

    telegram.send_message(msg)
    print("\n[Report sent to Telegram]")


if __name__ == "__main__":
    generate_pnl_report()
