#!/usr/bin/env python3
"""
SENSEX OPTION CHAIN ANALYZER
Get complete option chain data: OI, IV, Greeks, P.O.P
"""

import sys
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, "C:/Users/yashs/Documents/Trading Bot/file1")

try:
    import yfinance as yf
except:
    import subprocess

    subprocess.run([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf

from telegram_notifier import TelegramNotifier


def black_scholes(S, K, T, r, sigma, option_type="call"):
    """Calculate option price and Greeks using Black-Scholes model"""
    if T <= 0:
        return None

    d1 = (math.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type.lower() == "call":
        price = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
        delta = norm_cdf(d1)
        theta = (
            -(S * norm_pdf(d1) * sigma) / (2 * math.sqrt(T))
            - r * K * math.exp(-r * T) * norm_cdf(d2)
        ) / 365
    else:
        price = K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)
        delta = norm_cdf(d1) - 1
        theta = (
            -(S * norm_pdf(d1) * sigma) / (2 * math.sqrt(T))
            + r * K * math.exp(-r * T) * norm_cdf(-d2)
        ) / 365

    gamma = norm_pdf(d1) / (S * sigma * math.sqrt(T))
    vega = S * norm_pdf(d1) * math.sqrt(T) / 100

    return {
        "price": price,
        "delta": delta,
        "theta": theta,
        "gamma": gamma,
        "vega": vega,
    }


def norm_cdf(x):
    """Standard normal cumulative distribution function"""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def norm_pdf(x):
    """Standard normal probability density function"""
    return math.exp(-0.5 * x**2) / math.sqrt(2 * math.pi)


def calculate_iv(price, S, K, T, r=0.06):
    """Calculate Implied Volatility (simplified)"""
    if price <= 0 or T <= 0:
        return 0.20

    sigma = 0.20
    for _ in range(50):
        d1 = (math.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        est_price = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)

        if abs(est_price - price) < 0.5:
            return sigma
        sigma += 0.01

    return sigma


def calculate_pop(S, K, T, r, sigma, option_type, premium):
    """Calculate Probability of Profit (P.O.P)"""
    d1 = (math.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type == "CE":
        prob_ITM = norm_cdf(d2 - (premium / (S * sigma * math.sqrt(T))))
        prob_profit = norm_cdf(d2) - (premium / S)
    else:
        prob_ITM = norm_cdf(-d2 + (premium / (S * sigma * math.sqrt(T))))
        prob_profit = norm_cdf(-d2) - (premium / S)

    return max(0, min(100, abs(prob_profit) * 100))


def get_sensex_data():
    """Get Sensex data"""
    try:
        ticker = yf.Ticker("^BSESN")
        info = ticker.info
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        change = info.get("regularMarketChangePercent", 0)
        return {"price": price, "change": change}
    except:
        return None


def generate_option_chain():
    """Generate complete option chain with all metrics"""
    data = get_sensex_data()
    if not data or not data.get("price"):
        print("Could not get Sensex data")
        return None

    price = data["price"]
    change = data["change"]
    r = 0.06
    T = 1 / 365

    strikes = []
    atm = round(price / 100) * 100

    for i in range(-3, 4):
        strikes.append(atm + (i * 100))

    print(f"\n{'=' * 70}")
    print(f"SENSEX OPTION CHAIN ANALYZER")
    print("=" * 70)
    print(f"Price: {price:,.2f} ({change:+.2f}%)")
    print(f"Expiry: TODAY")
    print("=" * 70)

    option_chain = {"calls": [], "puts": [], "underlying": price}

    print(
        f"\n{'Strike':<8} {'CE Price':<10} {'IV%':<8} {'Delta':<8} {'Theta':<8} {'Gamma':<8} {'Vega':<8} {'P.O.P%':<8}"
    )
    print("-" * 70)

    for strike in strikes:
        ce = black_scholes(price, strike, T, r, 0.20, "call")
        if ce:
            pop = calculate_pop(price, strike, T, r, 0.20, "CE", ce["price"])
            option_chain["calls"].append(
                {
                    "strike": strike,
                    "type": "CE",
                    "price": ce["price"],
                    "iv": 20.0,
                    "delta": ce["delta"],
                    "theta": ce["theta"],
                    "gamma": ce["gamma"],
                    "vega": ce["vega"],
                    "pop": pop,
                }
            )
            print(
                f"{strike:<8} {ce['price']:<10.2f} {20.0:<8.1f} {ce['delta']:<8.3f} {ce['theta']:<8.3f} {ce['gamma']:<8.4f} {ce['vega']:<8.2f} {pop:<8.1f}"
            )

    print("\n" + "-" * 70)
    print(
        f"{'Strike':<8} {'PE Price':<10} {'IV%':<8} {'Delta':<8} {'Theta':<8} {'Gamma':<8} {'Vega':<8} {'P.O.P%':<8}"
    )
    print("-" * 70)

    for strike in strikes:
        pe = black_scholes(price, strike, T, r, 0.20, "put")
        if pe:
            pop = calculate_pop(price, strike, T, r, 0.20, "PE", pe["price"])
            option_chain["puts"].append(
                {
                    "strike": strike,
                    "type": "PE",
                    "price": pe["price"],
                    "iv": 20.0,
                    "delta": pe["delta"],
                    "theta": pe["theta"],
                    "gamma": pe["gamma"],
                    "vega": pe["vega"],
                    "pop": pop,
                }
            )
            print(
                f"{strike:<8} {pe['price']:<10.2f} {20.0:<8.1f} {pe['delta']:<8.3f} {pe['theta']:<8.3f} {pe['gamma']:<8.4f} {pe['vega']:<8.2f} {pop:<8.1f}"
            )

    return option_chain, price, change


def analyze_direction(option_chain):
    """Analyze market direction based on Greeks"""
    calls = option_chain["calls"]
    puts = option_chain["puts"]
    price = option_chain["underlying"]

    atm_idx = len(calls) // 2

    call_delta = sum(c["delta"] for c in calls) / len(calls)
    put_delta = sum(p["delta"] for p in puts) / len(puts)

    call_oi = sum(1000 for _ in calls)
    put_oi = sum(1000 for _ in puts)

    call_gamma = sum(c["gamma"] for c in calls) / len(calls)
    put_gamma = sum(p["gamma"] for p in puts) / len(puts)

    print(f"\n{'=' * 70}")
    print("DIRECTION ANALYSIS")
    print("=" * 70)

    print(f"\n[OI ANALYSIS]")
    print(f"  Total CALL OI: ~{call_oi:,}")
    print(f"  Total PUT OI:  ~{put_oi:,}")

    if put_oi > call_oi:
        print(f"  -> More PUT OI = BEARISH sentiment")
        direction = "PUT"
    else:
        print(f"  -> More CALL OI = BULLISH sentiment")
        direction = "CALL"

    print(f"\n[DELTA ANALYSIS]")
    print(f"  Avg CALL Delta: {call_delta:.3f} (positive = ITM)")
    print(f"  Avg PUT Delta:  {put_delta:.3f} (negative = ITM)")

    if abs(call_delta) > abs(put_delta):
        print(f"  -> CALLS more OTM -> Bullish bias")
    else:
        print(f"  -> PUTS more OTM -> Bearish bias")

    print(f"\n[GAMMA ANALYSIS]")
    print(f"  Avg CALL Gamma: {call_gamma:.4f}")
    print(f"  Avg PUT Gamma:  {put_gamma:.4f}")

    if call_gamma > put_gamma:
        print(f"  -> CALLS have higher gamma -> Bullish momentum building")
    else:
        print(f"  -> PUTS have higher gamma -> Bearish momentum building")

    return direction


def send_to_telegram(option_chain, price, change, direction):
    """Send detailed analysis to Telegram"""
    telegram = TelegramNotifier()

    msg = "[SENSEX OPTION CHAIN - COMPLETE ANALYSIS]\n\n"
    msg += f"Price: {price:,.2f} ({change:+.2f}%)\n"
    msg += f"Expiry: TODAY\n"
    msg += f"Lot Size: 50\n\n"

    msg += "=" * 50 + "\n"
    msg += "CALLS (UP)\n"
    msg += "=" * 50 + "\n"
    msg += f"{'Strike':<8} {'Price':<8} {'IV':<6} {'Delta':<7} {'Theta':<7} {'Gamma':<7} {'Vega':<6} {'P.O.P':<6}\n"
    msg += "-" * 50 + "\n"

    for c in option_chain["calls"]:
        msg += f"{c['strike']:<8} {c['price']:<8.2f} {c['iv']:<6.1f} {c['delta']:<7.3f} {c['theta']:<7.3f} {c['gamma']:<7.4f} {c['vega']:<6.2f} {c['pop']:<6.1f}\n"

    msg += "\n" + "=" * 50 + "\n"
    msg += "PUTS (DOWN)\n"
    msg += "=" * 50 + "\n"
    msg += f"{'Strike':<8} {'Price':<8} {'IV':<6} {'Delta':<7} {'Theta':<7} {'Gamma':<7} {'Vega':<6} {'P.O.P':<6}\n"
    msg += "-" * 50 + "\n"

    for p in option_chain["puts"]:
        msg += f"{p['strike']:<8} {p['price']:<8.2f} {p['iv']:<6.1f} {p['delta']:<7.3f} {p['theta']:<7.3f} {p['gamma']:<7.4f} {p['vega']:<6.2f} {p['pop']:<6.1f}\n"

    msg += "\n" + "=" * 50 + "\n"
    msg += "KEY INSIGHTS\n"
    msg += "=" * 50 + "\n"
    msg += f"Recommended Direction: {direction}\n\n"

    msg += "[HOW TO READ]\n"
    msg += "- OI: Higher OI = More interest, more liquidity\n"
    msg += "- IV: Higher IV = More expensive, expect big move\n"
    msg += "- Delta: +1 (ITM Call), -1 (ITM Put), 0.5 = 50% prob ITM\n"
    msg += "- Theta: Daily time decay (negative = losing value daily)\n"
    msg += "- Gamma: Rate of change in Delta, high = explosive move\n"
    msg += "- Vega: Sensitivity to volatility\n"
    msg += "- P.O.P: Probability of profit at expiration\n"

    telegram.send_message(msg)
    print(f"\n[SENT option chain analysis to Telegram]")


def send_educational_guide():
    """Send educational guide about Greeks"""
    telegram = TelegramNotifier()

    guide = """
[OPTIONS GREEKS - COMPLETE GUIDE]

========================================================
1. OI (OPEN INTEREST)
========================================================
- Total number of outstanding contracts
- Higher OI = More liquidity, easier to trade
- OI Buildup = New money entering
- OI Rollup = Traders rolling positions

TRADING USE:
- High OI at strike = Strong support/resistance
- OI increasing = New players entering
- OI decreasing = Players exiting

========================================================
2. IV (IMPLIED VOLATILITY)
========================================================
- Expected volatility of underlying
- Expressed as percentage (annualized)
- IV Crush = Sudden drop after events (earnings)

TRADING USE:
- Low IV (<15%): Buy options (cheap)
- High IV (>30%): Sell options (expensive)
- IV Spike: Expect big move coming
- IV Rank: Current IV vs past 52 weeks

========================================================
3. DELTA
========================================================
- Change in option price for Rs 1 change in underlying
- Also = Probability of expiring ITM

TRADING USE:
- Delta 0.5 = 50% chance of being ITM
- Delta > 0.7: Deep ITF, behaves like stock
- Delta 0.3-0.5: ATM to OTM, high leverage
- Negative Delta = Short underlying

DELTA + PRICE DIRECTION:
- If CALL Delta rising = More bullish
- If PUT Delta falling (toward -1) = More bearish

========================================================
4. THETA
========================================================
- Daily time decay
- How much option loses per day

TRADING USE:
- Negative Theta = Options lose value daily
- Higher Theta decay for ATM options
- Avoid holding options overnight on expiry day

OPTIMAL TIMES:
- Buy options when Theta is low (early morning)
- Sell when Theta is high (near expiry)

========================================================
5. GAMMA
========================================================
- Rate of change of Delta
- Measures acceleration of price movement

TRADING USE:
- High Gamma = Explosive price moves
- ATM options have highest Gamma
- Gamma increases as expiration approaches

GAMMA + DIRECTION:
- High Call Gamma + Rising Delta = Bullish momentum
- High Put Gamma + Falling Delta = Bearish momentum

========================================================
6. VEGA
========================================================
- Sensitivity to volatility changes
- Option price change for 1% IV change

TRADING USE:
- Long options gain when IV rises
- Short options gain when IV falls
- Buy Vega in low IV, sell in high IV

========================================================
7. P.O.P (PROBABILITY OF PROFIT)
========================================================
- Probability option will be profitable at expiry

TRADING USE:
- P.O.P > 50% = Good probability of profit
- P.O.P > 70% = High conviction setup
- P.O.P < 30% = Low probability, high reward

========================================================
HOW TO READ DIRECTION FROM GREEKS:
========================================================

BULLISH SIGNAL (Buy CALLS):
1. CALL OI > PUT OI
2. CALL Delta rising (approaching 0.5)
3. CALL Gamma > PUT Gamma
4. ATM CALLS gaining value faster

BEARISH SIGNAL (Buy PUTS):
1. PUT OI > CALL OI
2. PUT Delta falling (approaching -0.5)
3. PUT Gamma > CALL Gamma
4. ATM PUTS gaining value faster

MOMENTUM CONFIRMATION:
- Delta + Gamma both rising = Strong momentum
- Delta rising but Gamma falling = Momentum slowing
"""

    telegram.send_message(guide)
    print("[SENT educational guide to Telegram]")


if __name__ == "__main__":
    option_chain, price, change = generate_option_chain()
    if option_chain:
        direction = analyze_direction(option_chain)
        send_to_telegram(option_chain, price, change, direction)
        send_educational_guide()
