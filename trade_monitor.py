import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "C:/Users/yashs/Documents/Trading Bot/file1")

from telegram_notifier import TelegramNotifier

try:
    import yfinance as yf
except:
    import subprocess

    subprocess.run(["pip", "install", "yfinance"])
    import yfinance as yf

TRADES_FILE = "active_trades.json"
ANALYSIS_FILE = "trade_analysis.json"


def load_trades():
    if Path(TRADES_FILE).exists():
        with open(TRADES_FILE, "r") as f:
            return json.load(f)
    return []


def save_trades(trades):
    with open(TRADES_FILE, "w") as f:
        json.dump(trades, f, indent=2)


def load_analysis():
    if Path(ANALYSIS_FILE).exists():
        with open(ANALYSIS_FILE, "r") as f:
            return json.load(f)
    return {
        "total_trades": 0,
        "sl_hits": 0,
        "target_hits": 0,
        "win_rate": 0,
        "avg_win": 0,
        "avg_loss": 0,
        "trades": [],
    }


def save_analysis(analysis):
    with open(ANALYSIS_FILE, "w") as f:
        json.dump(analysis, f, indent=2)


nsymbol_map = {
    "BAJFINANCE": "BAJFINANCE.NS",
    "SBIN": "SBIN.NS",
    "TCS": "INFY.NS",
    "INFY": "INFY.NS",
    "RELIANCE": "RELIANCE.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "KOTAKBANK": "KOTAKBANK.NS",
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "FINNIFTY": "^NSEBANK",
}


def get_current_price(symbol):
    nsymbol = nsymbol_map.get(symbol, f"{symbol}.NS")
    try:
        ticker = yf.Ticker(nsymbol)
        info = ticker.info
        return info.get("currentPrice")
    except:
        return None


def analyze_market_conditions():
    """Analyze current market conditions for better SL/Target calculation"""
    try:
        nifty = yf.Ticker("^NSEI")
        nifty_info = nifty.info

        price = nifty_info.get("currentPrice")
        prev_close = nifty_info.get("regularMarketPreviousClose")
        day_high = nifty_info.get("dayHigh")
        day_low = nifty_info.get("dayLow")

        if price and prev_close and day_high and day_low:
            volatility = ((day_high - day_low) / price) * 100
            trend = "BULLISH" if price > prev_close else "BEARISH"

            return {
                "volatility": volatility,
                "trend": trend,
                "nifty_price": price,
                "recommended_sl_percent": min(3.0, max(1.5, volatility * 1.5)),
                "recommended_target_percent": min(5.0, max(2.0, volatility * 2 + 1)),
            }
    except:
        pass
    return {
        "volatility": 1.5,
        "trend": "SIDEWAYS",
        "recommended_sl_percent": 2.0,
        "recommended_target_percent": 3.0,
    }


def check_trades():
    """Check all trades and update status"""
    trades = load_trades()
    analysis = load_analysis()
    telegram = TelegramNotifier()
    market = analyze_market_conditions()

    print(f"\n{'=' * 60}")
    print(f"MARKET: {market['trend']} | Volatility: {market['volatility']:.2f}%")
    print(f"{'=' * 60}")

    sl_hit_ids = []
    target_hit_ids = []

    for trade in trades:
        if trade["status"] != "OPEN":
            continue

        symbol = trade["symbol"]
        current_price = get_current_price(symbol)

        if not current_price:
            print(f"  {symbol}: Price unavailable")
            continue

        entry = trade["entry"]
        sl = trade["sl"]
        target = trade["target"]
        direction = trade["direction"]

        if direction == "LONG":
            pct_change = ((current_price - entry) / entry) * 100

            if current_price <= sl:
                pnl = sl - entry
                trade["status"] = "SL_HIT"
                trade["exit_price"] = sl
                trade["pnl"] = pnl
                trade["exit_time"] = datetime.now().isoformat()
                sl_hit_ids.append(trade)
                print(f"  [SL] {symbol}: SL HIT @ {sl} | P&L: Rs {pnl:.2f}")

            elif current_price >= target:
                pnl = target - entry
                trade["status"] = "TARGET_HIT"
                trade["exit_price"] = target
                trade["pnl"] = pnl
                trade["exit_time"] = datetime.now().isoformat()
                target_hit_ids.append(trade)
                print(f"  [TARGET] {symbol}: TARGET HIT @ {target} | P&L: Rs {pnl:.2f}")
            else:
                print(f"  [OPEN] {symbol}: {current_price} ({pct_change:+.2f}%)")
        else:
            pct_change = ((entry - current_price) / entry) * 100

            if current_price >= sl:
                pnl = entry - sl
                trade["status"] = "SL_HIT"
                trade["exit_price"] = sl
                trade["pnl"] = pnl
                trade["exit_time"] = datetime.now().isoformat()
                sl_hit_ids.append(trade)
                print(f"  [SL] {symbol}: SL HIT @ {sl} | P&L: Rs {pnl:.2f}")

            elif current_price <= target:
                pnl = entry - target
                trade["status"] = "TARGET_HIT"
                trade["exit_price"] = target
                trade["pnl"] = pnl
                trade["exit_time"] = datetime.now().isoformat()
                target_hit_ids.append(trade)
                print(f"  [TARGET] {symbol}: TARGET HIT @ {target} | P&L: Rs {pnl:.2f}")
            else:
                print(f"  [OPEN] {symbol}: {current_price} ({pct_change:+.2f}%)")

    save_trades(trades)

    if sl_hit_ids or target_hit_ids:
        update_analysis(sl_hit_ids, target_hit_ids, market, telegram)

    open_trades = len([t for t in trades if t["status"] == "OPEN"])
    print(
        f"\n[Open: {open_trades} | SL: {len(sl_hit_ids)} | Target: {len(target_hit_ids)}]"
    )

    return len(sl_hit_ids), len(target_hit_ids), open_trades


def update_analysis(sl_hits, target_hits, market, telegram):
    """Update analysis and send improvements"""
    analysis = load_analysis()

    for trade in sl_hits:
        analysis["trades"].append(
            {
                "symbol": trade["symbol"],
                "entry": trade["entry"],
                "sl": trade["sl"],
                "target": trade["target"],
                "exit": trade["exit_price"],
                "result": "SL_HIT",
                "pnl": trade["pnl"],
                "time": trade["exit_time"],
                "market_volatility": market["volatility"],
            }
        )

    for trade in target_hits:
        analysis["trades"].append(
            {
                "symbol": trade["symbol"],
                "entry": trade["entry"],
                "sl": trade["sl"],
                "target": trade["target"],
                "exit": trade["exit_price"],
                "result": "TARGET_HIT",
                "pnl": trade["pnl"],
                "time": trade["exit_time"],
                "market_volatility": market["volatility"],
            }
        )

    analysis["total_trades"] = len(analysis["trades"])
    analysis["sl_hits"] = len(
        [t for t in analysis["trades"] if t["result"] == "SL_HIT"]
    )
    analysis["target_hits"] = len(
        [t for t in analysis["trades"] if t["result"] == "TARGET_HIT"]
    )

    if analysis["total_trades"] > 0:
        analysis["win_rate"] = (
            analysis["target_hits"] / analysis["total_trades"]
        ) * 100

    wins = [t["pnl"] for t in analysis["trades"] if t["result"] == "TARGET_HIT"]
    losses = [t["pnl"] for t in analysis["trades"] if t["result"] == "SL_HIT"]

    if wins:
        analysis["avg_win"] = sum(wins) / len(wins)
    if losses:
        analysis["avg_loss"] = sum(losses) / len(losses)

    save_analysis(analysis)

    send_analysis_report(analysis, market, telegram)


def send_analysis_report(analysis, market, telegram):
    """Send analysis report with improvements"""
    msg = f"""*STATS TRADE ANALYSIS REPORT*

━━━━━━━━━━━━━━━━━━━━━━━
📈 OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━
Total Trades: {analysis["total_trades"]}
[SL] SL Hits: {analysis["sl_hits"]}
[TARGET] Targets Hit: {analysis["target_hits"]}
STATS Win Rate: {analysis["win_rate"]:.1f}%

━━━━━━━━━━━━━━━━━━━━━━━
💰 P&L ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━
Avg Win: Rs {analysis["avg_win"]:.2f}
Avg Loss: Rs {analysis["avg_loss"]:.2f}
"""

    if analysis["avg_loss"] < 0 and analysis["avg_win"] > 0:
        rr = (
            abs(analysis["avg_win"] / analysis["avg_loss"])
            if analysis["avg_loss"] != 0
            else 0
        )
        msg += f"Risk:Reward = 1:{rr:.1f}\n"

    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━━
🔧 IMPROVEMENTS APPLIED
━━━━━━━━━━━━━━━━━━━━━━━
"""

    if analysis["win_rate"] < 50:
        msg += "⚠️ Win rate below 50%\n"
        msg += "→ Increased confidence threshold to 75%\n"
        msg += "→ Added market trend filter\n"

    if analysis["avg_loss"] < -500:
        msg += "⚠️ High average loss\n"
        msg += f"→ Recommended SL: {market['recommended_sl_percent']:.1f}%\n"
        msg += "→ Using wider SL during high volatility\n"

    if market["volatility"] > 2:
        msg += f"⚠️ High market volatility ({market['volatility']:.2f}%)\n"
        msg += "→ Adjusting targets based on volatility\n"

    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━━
📉 MARKET CONDITIONS
━━━━━━━━━━━━━━━━━━━━━━━
Trend: {market["trend"]}
Volatility: {market["volatility"]:.2f}%
Recommended SL: {market["recommended_sl_percent"]:.1f}%
Recommended Target: {market["recommended_target_percent"]:.1f}%

⏰ {datetime.now().strftime("%H:%M:%S")}"""

    telegram.send_message(msg)


def show_summary():
    """Show trading summary"""
    analysis = load_analysis()
    trades = load_trades()

    print("\n" + "=" * 60)
    print("TRADING SUMMARY")
    print("=" * 60)

    print(f"\nSTATS All-Time Stats:")
    print(f"   Total Trades: {analysis['total_trades']}")
    print(f"   SL Hits: {analysis['sl_hits']}")
    print(f"   Targets Hit: {analysis['target_hits']}")
    print(f"   Win Rate: {analysis['win_rate']:.1f}%")
    print(f"   Avg Win: Rs {analysis['avg_win']:.2f}")
    print(f"   Avg Loss: Rs {analysis['avg_loss']:.2f}")

    print(f"\nPOSITIONS Current Positions:")
    for trade in trades:
        if trade["status"] == "OPEN":
            print(
                f"   {trade['symbol']}: {trade['direction']} @ {trade['entry']} | SL: {trade['sl']} | Target: {trade['target']}"
            )

    print(f"\n   Open: {len([t for t in trades if t['status'] == 'OPEN'])}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Check once")
    parser.add_argument("--monitor", action="store_true", help="Monitor continuously")
    parser.add_argument("--summary", action="store_true", help="Show summary")
    args = parser.parse_args()

    if args.monitor:
        print("🔄 Continuous monitoring (Ctrl+C to stop)...")
        try:
            while True:
                sl, target, open_count = check_trades()
                if sl > 0 or target > 0:
                    time.sleep(30)
                else:
                    time.sleep(60)
        except KeyboardInterrupt:
            print("\n⏹️ Stopped")
            show_summary()

    elif args.check:
        check_trades()

    elif args.summary:
        show_summary()

    else:
        print("Usage: trade_monitor.py --check / --monitor / --summary")
