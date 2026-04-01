#!/usr/bin/env python3
"""
NEWS & EVENTS IMPACT ANALYZER
=============================
Analyzes news sentiment and events to impact trade decisions
Uses Alpha Vantage for better news coverage
"""

import sys
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, "C:/Users/yashs/Documents/Trading Bot/file1")

try:
    import yfinance as yf
except:
    import subprocess

    subprocess.run([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf

# Alpha Vantage API - FREE tier (100 calls/day)
ALPHA_VANTAGE_KEY = "4SC3JS903A9K88BR"

# Symbol mapping for Alpha Vantage (NSE stocks)
SYMBOL_MAP = {
    "INFY": "INFY",
    "TCS": "TCS",
    "RELIANCE": "RELIANCE",
    "HDFCBANK": "HDFCBANK",
    "BAJFINANCE": "BAJFINANCE",
    "SBIN": "SBIN",
    "KOTAKBANK": "KOTAKBANK",
    "ICICIBANK": "ICICIBANK",
    "AXISBANK": "AXISBANK",
    "LT": "LT",
    "TITAN": "TITAN",
    "SUNPHARMA": "SUNPHARMA",
    "WIPRO": "WIPRO",
    "HINDUNILVR": "HINDUNILVR",
    "NIFTY": "NIFTY",
    "BANKNIFTY": "BANKNIFTY",
}


def get_alpha_vantage_news_sentiment(symbol):
    """Get news sentiment from Alpha Vantage API"""
    try:
        av_symbol = SYMBOL_MAP.get(symbol, symbol)
        url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={av_symbol}&apikey={ALPHA_VANTAGE_KEY}"

        response = requests.get(url, timeout=10)
        data = response.json()

        if "feed" in data:
            articles = data["feed"][:3] if len(data["feed"]) > 3 else data["feed"]

            # Get overall sentiment
            overall_sentiment = data.get("sentiment_score", 0)

            # Get individual article summaries
            summaries = []
            for article in articles:
                summary = article.get("title", "")[:100]
                summaries.append(summary)

            return {
                "articles": summaries,
                "overall_sentiment": overall_sentiment,
                "source": "Alpha Vantage",
            }
    except Exception as e:
        print(f"Alpha Vantage error: {e}")

    return None


def get_stock_news(symbol):
    """Get latest news for a stock"""
    try:
        # Using yfinance news
        ticker = yf.Ticker(f"{symbol}.NS")
        news = ticker.news

        if news:
            return news[:3]  # Return top 3 news
    except:
        pass
    return []


def analyze_sentiment(news_list):
    """Analyze news sentiment - returns score -1 to 1"""
    if not news_list:
        return 0, "No news"

    positive_words = [
        "surge",
        "rally",
        "gain",
        "profit",
        "growth",
        "upgrade",
        "beat",
        "bullish",
        "high",
        "rise",
    ]
    negative_words = [
        "fall",
        "drop",
        "loss",
        "miss",
        "downgrade",
        "bearish",
        "low",
        "decline",
        "warning",
        "risk",
    ]

    score = 0
    total = 0

    for news in news_list:
        title = news.get("title", "").lower()

        for word in positive_words:
            if word in title:
                score += 1
                total += 1

        for word in negative_words:
            if word in title:
                score -= 1
                total += 1

    if total == 0:
        return 0, "Neutral"

    sentiment = score / total

    if sentiment > 0.3:
        return sentiment, "BULLISH"
    elif sentiment < -0.3:
        return sentiment, "BEARISH"
    else:
        return sentiment, "NEUTRAL"


def check_events(symbol):
    """Check for upcoming events (earnings, board meetings, etc.)"""
    events = []

    # Common NSE event dates (approximate - would need real data in production)
    # This is a simplified version

    return events


def get_earning_dates(symbol):
    """Get upcoming earnings dates"""
    earning_dates = {
        "INFY": "2025-04-15",  # Approximate
        "TCS": "2025-04-10",
        "RELIANCE": "2025-04-20",
        "HDFCBANK": "2025-04-18",
    }
    return earning_dates.get(symbol, None)


def analyze_impact(symbol):
    """Complete impact analysis for a symbol"""
    # Try Alpha Vantage first (better data)
    av_data = get_alpha_vantage_news_sentiment(symbol)

    if av_data and av_data.get("overall_sentiment") is not None:
        # Use Alpha Vantage data
        sentiment_score = av_data["overall_sentiment"]

        if sentiment_score > 0.2:
            sentiment_label = "BULLISH"
        elif sentiment_score < -0.2:
            sentiment_label = "BEARISH"
        else:
            sentiment_label = "NEUTRAL"

        impact_score = 0
        reasons = []

        if sentiment_score > 0.3:
            impact_score += 20
            reasons.append(f"Positive news (Alpha Vantage: {sentiment_score:.2f})")
        elif sentiment_score < -0.3:
            impact_score -= 20
            reasons.append(f"Negative news (Alpha Vantage: {sentiment_score:.2f})")

        earnings = get_earning_dates(symbol)

        if earnings:
            days_until = (datetime.fromisoformat(earnings) - datetime.now()).days
            if days_until > 0 and days_until <= 7:
                impact_score -= 10
                reasons.append(f"Earnings in {days_until} days")

        return {
            "sentiment": sentiment_label,
            "sentiment_score": sentiment_score,
            "impact_score": impact_score,
            "reasons": reasons,
            "news": av_data.get("articles", []),
            "earnings_date": earnings,
            "source": "Alpha Vantage",
        }

    # Fallback to yfinance
    news = get_stock_news(symbol)
    sentiment, sentiment_label = analyze_sentiment(news)
    earnings = get_earning_dates(symbol)

    impact_score = 0
    reasons = []

    if sentiment > 0.3:
        impact_score += 20
        reasons.append(f"Positive news ({sentiment_label})")
    elif sentiment < -0.3:
        impact_score -= 20
        reasons.append(f"Negative news ({sentiment_label})")

    if earnings:
        days_until = (datetime.fromisoformat(earnings) - datetime.now()).days
        if days_until > 0 and days_until <= 7:
            impact_score -= 10
            reasons.append(f"Earnings in {days_until} days")

    return {
        "sentiment": sentiment_label,
        "sentiment_score": sentiment,
        "impact_score": impact_score,
        "reasons": reasons,
        "news": news,
        "earnings_date": earnings,
        "source": "yfinance",
    }


def adjust_signal_based_on_news(signal, impact):
    """Adjust trade parameters based on news impact"""

    # If negative news, tighten SL
    if impact["sentiment"] == "BEARISH":
        # Wider SL to avoid noise
        signal["sl"] = round(signal["entry"] * 0.80, 2)  # 20% SL instead of 25%
        signal["adjusted"] = True
        signal["adjustment_reason"] = "Negative news - wider protection"
    elif impact["sentiment"] == "BULLISH":
        # Normal parameters
        signal["adjusted"] = False

    # Add impact info to signal
    signal["impact"] = impact

    return signal


def get_market_wide_news():
    """Get overall market news"""
    try:
        nifty = yf.Ticker("^NSEI")
        news = nifty.news
        if news:
            return news[:2]
    except:
        pass
    return []


def analyze_market_sentiment():
    """Analyze overall market sentiment"""
    news = get_market_wide_news()
    sentiment, label = analyze_sentiment(news)

    return {"sentiment": label, "score": sentiment, "news": news}


if __name__ == "__main__":
    # Test with INFY
    print("Analyzing INFY...")
    impact = analyze_impact("INFY")

    print(f"  Sentiment: {impact['sentiment']}")
    print(f"  Score: {impact['sentiment_score']}")
    print(f"  Impact: {impact['impact_score']}")
    print(f"  Reasons: {impact['reasons']}")

    # Test market sentiment
    print("\nMarket Sentiment:")
    market = analyze_market_sentiment()
    print(f"  Sentiment: {market['sentiment']}")
    print(f"  Score: {market['score']}")
