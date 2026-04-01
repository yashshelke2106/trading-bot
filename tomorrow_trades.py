#!/usr/bin/env python3
"""
TOMORROW'S TRADES PREDICTOR
===========================
Analyzes today's market data to predict tomorrow's best trades
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, "C:/Users/yashs/Documents/Trading Bot/file1")

try:
    import yfinance as yf
except:
    import subprocess

    subprocess.run([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf

from telegram_notifier import TelegramNotifier
from time_predictor import estimate_time_to_target, calculate_probability
from news_analyzer import analyze_impact


def get_tomorrow_expiry():
    """Get next expiry date"""
    today = datetime.now()
    month = today.strftime("%b").upper()
    return f"{month}'25"


def analyze_today_performance():
    """Analyze today's market to find tomorrow's opportunities"""

    stocks_to_analyze = [
        "INFY",
        "TCS",
        "RELIANCE",
        "HDFCBANK",
        "BAJFINANCE",
        "SBIN",
        "KOTAKBANK",
        "ICICIBANK",
        "AXISBANK",
        "LT",
        "TITAN",
        "SUNPHARMA",
        "WIPRO",
        "HINDUNILVR",
        "ADANIPOWER",
        "CIPLA",
    ]

    stock_data = []

    print("\n" + "=" * 60)
    print("ANALYZING TODAY'S MARKET FOR TOMORROW'S TRADES")
    print("=" * 60)

    for stock in stocks_to_analyze:
        try:
            ticker = yf.Ticker(f"{stock}.NS")
            info = ticker.info

            price = info.get("currentPrice") or info.get("regularMarketPreviousClose")
            prev = info.get("regularMarketPreviousClose")

            if not price or not prev:
                continue

            # Today's metrics
            change = ((price - prev) / prev) * 100
            day_high = info.get("dayHigh", price)
            day_low = info.get("dayLow", price)
            volume = info.get("volume", 0)

            # Calculate strength metrics
            # 1. Price momentum (today's move)
            momentum_score = abs(change)

            # 2. Range strength (how far it moved)
            day_range = ((day_high - day_low) / price) * 100

            # 3. Volume indicator
            volume_score = 1 if volume > 500000 else 0.5

            # 4. Combined score
            total_score = momentum_score + (day_range * 0.5) + (volume_score * 5)

            stock_data.append(
                {
                    "symbol": stock,
                    "price": price,
                    "change": change,
                    "momentum": momentum_score,
                    "range": day_range,
                    "volume": volume,
                    "score": total_score,
                }
            )

        except Exception as e:
            pass

    # Sort by score
    stock_data.sort(key=lambda x: x["score"], reverse=True)

    return stock_data[:10]  # Top 10


def generate_tomorrow_trades():
    """Generate trades for tomorrow based on today's analysis"""

    print("\n[Generating tomorrow's trades based on today...]")

    # Get today's analysis
    today_stocks = analyze_today_performance()

    if not today_stocks:
        print("No stocks to analyze")
        return []

    # Determine market direction
    avg_change = sum(s["change"] for s in today_stocks) / len(today_stocks)

    if avg_change > 0.5:
        market_direction = "CE"  # Bullish
    elif avg_change < -0.5:
        market_direction = "PE"  # Bearish
    else:
        market_direction = "CE"  # Neutral - slight bullish bias

    print(f"\nMarket Direction: {market_direction} (Avg Change: {avg_change:+.2f}%)")

    # Generate signals for top stocks
    signals = []

    for stock in today_stocks[:8]:  # Top 8
        price = stock["price"]

        # Calculate option parameters
        strike = int(round(price / 100) * 100)  # Nearest 100

        # Premium estimate
        if price > 10000:  # Index
            entry = price * 0.005  # 0.5% for ATM
        else:
            entry = max(30, price * 0.03)  # ~3% for stocks

        # Calculate SL and targets (wider for tomorrow's trades)
        sl = entry * 0.80  # 20% SL - wider for overnight risk
        target1 = entry * 1.30  # 30% gain
        target2 = entry * 1.60  # 60% gain
        target3 = entry * 2.00  # 100% gain

        # Get news impact
        try:
            impact = analyze_impact(stock["symbol"])
            news = impact["sentiment"]
        except:
            news = "N/A"

        # Get probability
        prob = calculate_probability(
            entry, sl, target1, stock["symbol"], market_direction
        )

        # Time estimate
        time_est = "Overnight to 1 day"

        signal = {
            "symbol": stock["symbol"],
            "type": market_direction,
            "strike": strike,
            "entry": round(entry, 2),
            "sl": round(sl, 2),
            "targets": [round(target1, 2), round(target2, 2), round(target3, 2)],
            "today_change": stock["change"],
            "momentum_score": round(stock["score"], 2),
            "news": news,
            "probability": prob,
            "time": time_est,
            "reason": f"Today: {stock['change']:+.2f}%, Range: {stock['range']:.2f}%",
        }

        signals.append(signal)
        print(
            f"  {stock['symbol']}: {stock['change']:+.2f}% -> Score: {stock['score']:.1f}"
        )

    return signals


def send_tomorrow_signals(signals):
    """Send tomorrow's trades to Telegram"""

    if not signals:
        return

    telegram = TelegramNotifier()
    expiry = get_tomorrow_expiry()

    msg = f"""*TOMORROW'S TRADES SETUP*

Based on Today's Market Analysis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Signals: {len(signals)}
Expiry: {expiry}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""

    for sig in signals:
        msg += f"""📊 {sig["symbol"]} {sig["strike"]} {sig["type"]} {expiry}
   Today's Move: {sig["today_change"]:+.2f}%
   Entry: Rs {sig["entry"]} | SL: Rs {sig["sl"]}
   
   Targets: {sig["targets"][0]} | {sig["targets"][1]} | {sig["targets"][2]}
   
   Time: {sig["time"]}
   News: {sig["news"]}
   Win Prob: {sig["probability"]["target"]}
   Reason: {sig["reason"]}

"""

    msg += """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use these setups for tomorrow's market
Monitor opening 15 min for best entry

Time: {}""".format(datetime.now().strftime("%H:%M:%S"))

    telegram.send_message(msg)
    print(f"\n[Sent {len(signals)} tomorrow trades to Telegram]")


def main():
    print("=" * 60)
    print("TOMORROW'S TRADES PREDICTOR")
    print("=" * 60)

    signals = generate_tomorrow_trades()

    if signals:
        send_tomorrow_signals(signals)
    else:
        print("No signals generated")


if __name__ == "__main__":
    main()
