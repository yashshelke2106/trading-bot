"""
NSE F&O LOT SIZES
Updated: April 2026
"""

LOT_SIZES = {
    "NIFTY": 65,
    "BANKNIFTY": 30,
    "FINNIFTY": 25,
    "SENSEX": 10,
    "MIDCPNIFTY": 75,
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
    "WIPRO": 250,
    "HINDUNILVR": 125,
    "SUNPHARMA": 125,
    "TATASTEEL": 750,
    "ADANIPOWER": 1500,
    "BHARTIARTL": 250,
    "DIVISLAB": 125,
    "TITAN": 125,
    "BAJAJFINSV": 125,
    "HDFCLIFE": 250,
    "SBILIFE": 250,
    "INDUSINDBK": 250,
    "LT": 125,
    "COFORGE": 125,
    "PERSISTENT": 125,
    "LTI": 125,
    "TECHM": 250,
    "BAJAJ-AUTO": 125,
    "VEDL": 1000,
    "HINDALCO": 500,
    "ADANIENT": 500,
    "SUZLON": 3000,
    "NTPC": 500,
    "ADANIENSOL": 500,
    "HAL": 125,
    "RVNL": 500,
    "DMART": 125,
    "TRENT": 125,
    "ZOMATO": 500,
    "PAYTM": 250,
    "NYKAA": 250,
    "LIC": 250,
    "GAIL": 750,
    "ONGC": 1250,
    "BPCL": 350,
    "IOC": 750,
    "HCLTECH": 200,
    "WIPRO": 250,
    "TECHM": 250,
    "MINDTREE": 125,
    "LTIM": 125,
    "MPHASIS": 125,
}


def get_lot_size(symbol: str) -> int:
    """Get lot size for a symbol"""
    return LOT_SIZES.get(symbol.upper(), 1)


if __name__ == "__main__":
    print("NSE F&O Lot Sizes:")
    print("=" * 40)
    for k, v in sorted(LOT_SIZES.items()):
        print(f"{k:20} : {v}")
