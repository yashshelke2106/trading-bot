#!/usr/bin/env python3
"""
TIME TO TARGET PREDICTOR
========================
Predicts estimated time to reach target based on volatility
"""

import sys
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, "C:/Users/yashs/Documents/Trading Bot/file1")

try:
    import yfinance as yf
except:
    import subprocess

    subprocess.run([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf


def get_atr(symbol, period=14):
    """Calculate Average True Range"""
    nsymbols = {
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "RELIANCE": "RELIANCE.NS",
        "TCS": "TCS.NS",
        "INFY": "INFY.NS",
        "HDFCBANK": "HDFCBANK.NS",
        "BAJFINANCE": "BAJFINANCE.NS",
        "SBIN": "SBIN.NS",
    }
    nsym = nsymbols.get(symbol, f"{symbol}.NS")

    try:
        ticker = yf.Ticker(nsym)
        hist = ticker.history(period="1mo")

        if len(hist) >= period:
            high = hist["High"]
            low = hist["Low"]
            close = hist["Close"]

            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = tr1.combine(tr2, max).combine(tr3, max)
            atr = tr.rolling(period).mean().iloc[-1]

            return float(atr)
    except:
        pass
    return None


def estimate_time_to_target(entry, target, symbol, option_type):
    """Estimate time to reach target based on ATR and historical data"""

    # Get ATR
    atr = get_atr(symbol)

    # Calculate target distance
    target_distance_pct = ((target - entry) / entry) * 100

    if not atr:
        # If no ATR data, use rough estimate
        # Options typically move 2-4% per day in normal markets
        if target_distance_pct <= 25:  # Target 1
            return "2-4 hours"
        elif target_distance_pct <= 50:  # Target 2
            return "Same day to 1 day"
        else:  # Target 3
            return "1-2 days"

    # Get underlying price
    nsymbols = {
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "RELIANCE": "RELIANCE.NS",
        "TCS": "TCS.NS",
        "INFY": "INFY.NS",
        "HDFCBANK": "HDFCBANK.NS",
        "BAJFINANCE": "BAJFINANCE.NS",
        "SBIN": "SBIN.NS",
    }
    nsym = nsymbols.get(symbol, f"{symbol}.NS")

    try:
        ticker = yf.Ticker(nsym)
        info = ticker.info
        underlying = info.get("currentPrice") or info.get("regularMarketPreviousClose")
    except:
        underlying = 100  # fallback

    # Calculate option delta (simplified)
    # Delta is roughly the probability of expiring ITM
    # For ATM options, delta ~ 0.5

    if option_type == "CE":
        moneyness = (
            underlying - getattr(sys.modules[__name__], "strike", 22000)
        ) / underlying
    else:
        moneyness = (
            getattr(sys.modules[__name__], "strike", 22000) - underlying
        ) / underlying

    # Delta approximation
    if moneyness > 0.1:
        delta = 0.8
    elif moneyness > 0:
        delta = 0.5
    elif moneyness > -0.1:
        delta = 0.3
    else:
        delta = 0.1

    # Time estimation
    # ATR represents daily range - use this to estimate time
    daily_volatility = (atr / underlying) * 100  # as percentage

    # Option premium typically moves faster than underlying
    option_leverage = 3  # options move ~3x faster

    daily_option_move = daily_volatility * option_leverage

    # Calculate time
    target_distance = target - entry
    if daily_option_move > 0:
        days_to_target = target_distance / (entry * daily_option_move / 100)
    else:
        days_to_target = 1

    # Convert to readable format
    if days_to_target < 0.25:  # < 2 hours
        return f"{int(days_to_target * 24 * 60)} minutes"
    elif days_to_target < 1:
        hours = int(days_to_target * 24)
        return f"{hours}-{hours + 2} hours"
    elif days_to_target < 2:
        return "Same day"
    elif days_to_target < 5:
        return f"{int(days_to_target)} days"
    else:
        return f"{int(days_to_target)} days (high uncertainty)"


def calculate_probability(entry, sl, target, symbol, option_type):
    """Calculate probability of hitting target vs SL"""

    atr = get_atr(symbol)

    if not atr:
        # Default probabilities based on R:R
        risk = abs(target - entry)
        reward = abs(target - entry)

        rr = reward / risk if risk > 0 else 1

        # Lower probability for lower R:R
        if rr >= 2:
            return {"target": "65-75%", "sl": "25-35%"}
        elif rr >= 1.5:
            return {"target": "55-65%", "sl": "35-45%"}
        else:
            return {"target": "45-55%", "sl": "45-55%"}

    # Get underlying
    nsymbols = {
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "RELIANCE": "RELIANCE.NS",
        "TCS": "TCS.NS",
        "INFY": "INFY.NS",
        "HDFCBANK": "HDFCBANK.NS",
        "BAJFINANCE": "BAJFINANCE.NS",
        "SBIN": "SBIN.NS",
    }
    nsym = nsymbols.get(symbol, f"{symbol}.NS")

    try:
        ticker = yf.Ticker(nsym)
        info = ticker.info
        underlying = info.get("currentPrice") or info.get("regularMarketPreviousClose")
    except:
        underlying = 100

    # Volatility-based probability
    volatility = (atr / underlying) * 100

    # Wider ATR = more volatility = higher probability of big moves
    if volatility > 2:
        target_prob = 70
        sl_prob = 30
    elif volatility > 1.5:
        target_prob = 60
        sl_prob = 40
    else:
        target_prob = 55
        sl_prob = 45

    return {
        "target": f"{target_prob - 10}%-{target_prob}%",
        "sl": f"{sl_prob - 10}%-{sl_prob}%",
        "volatility": f"{volatility:.2f}%",
    }


def add_time_prediction_to_signal(signal):
    """Add time prediction to a signal"""

    for target in signal["targets"]:
        time_est = estimate_time_to_target(
            signal["entry"], target, signal["symbol"], signal["option_type"]
        )
        signal[f"time_to_target_{target}"] = time_est

    # Add probability
    prob = calculate_probability(
        signal["entry"],
        signal["sl"],
        signal["targets"][0],  # First target
        signal["symbol"],
        signal["option_type"],
    )
    signal["probability"] = prob

    return signal


if __name__ == "__main__":
    # Test with sample
    signal = {
        "symbol": "INFY",
        "option_type": "CE",
        "strike": 1300,
        "entry": 43,
        "sl": 32,
        "targets": [54, 65, 75],
    }

    enhanced = add_time_prediction_to_signal(signal)

    print("Signal with Time Prediction:")
    print(
        f"  Symbol: {enhanced['symbol']} {enhanced['strike']} {enhanced['option_type']}"
    )
    print(f"  Entry: {enhanced['entry']} | SL: {enhanced['sl']}")
    print(f"  Targets: {enhanced['targets']}")
    print(f"  Probability: {enhanced['probability']}")

    for t in enhanced["targets"]:
        key = f"time_to_target_{t}"
        if key in enhanced:
            print(f"  Time to {t}: {enhanced[key]}")
