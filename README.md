# NSE F&O Autonomous Trading System

A production-grade autonomous trading system for Indian equity derivatives (NSE F&O), built with Python, FastAPI, and the Dhan broker API.

## What It Does

- **Real-time market scanning** across NIFTY and BANKNIFTY options chains
- **Multi-module weighted signal engine** combining technical, options flow, and institutional data
- **Autonomous order execution** via Dhan API with WebSocket connectivity
- **Telegram alerts** for trade signals and position updates
- **Live monitoring dashboard** with P&L tracking

## Architecture
┌─────────────────────────────────────────────────┐
│                 Command Center                   │
│            (command_center.py)                    │
├──────────┬──────────┬──────────┬────────────────┤
│  Market  │  Signal  │ Options  │    Dhan API    │
│ Scanner  │  Engine  │ Trader   │  Integration   │
│          │          │          │                │
│ • OHLCV  │ • RSI    │ • Greeks │ • WebSocket    │
│ • Volume │ • EMA    │ • PCR    │ • Order Mgmt   │
│ • Trends │ • VWAP   │ • MaxPain│ • Position     │
│          │ • Custom │ • Gamma  │   Tracking     │
├──────────┴──────────┴──────────┴────────────────┤
│              Telegram Notifier                   │
│          (telegram_notifier.py)                   │
└─────────────────────────────────────────────────┘

## Core Modules

| Module | Description | Lines |
|--------|-------------|-------|
| `autonomous_bot.py` | Main trading engine with async execution loop | ~400 |
| `auto_signal.py` | Multi-indicator signal generation (RSI, EMA, VWAP, custom) | ~300 |
| `auto_market_scanner.py` | Real-time NIFTY/BANKNIFTY scanner | ~200 |
| `options_trader.py` | Options-specific trading logic (Greeks, PCR, Max Pain) | ~250 |
| `dhan_integration.py` | Dhan broker API wrapper (orders, positions, WebSocket) | ~200 |
| `live_scanner.py` | Live market data feed and processing | ~150 |
| `trade_monitor.py` | Position monitoring and risk management | ~150 |
| `telegram_notifier.py` | Alert system via Telegram Bot API | ~100 |
| `scheduled_scanner.py` | Cron-based market scanning scheduler | ~80 |
| `command_center.py` | Unified control interface for all modules | ~100 |

## India-Specific Features

- **NSE lot sizes** and contract specifications baked in
- **India VIX regime detection** for volatility-adjusted position sizing
- **FII/DII institutional flow scoring** for directional bias
- **Gift Nifty gap analysis** for pre-market edge
- **PCR / Max Pain / Gamma Wall** options chain analytics
- **Expiry-day specific rules** (weekly and monthly expiry handling)
- **Indian F&O cost modeling** (STT, brokerage, exchange charges, slippage)

## Tech Stack

- **Language:** Python 3.10+
- **Framework:** FastAPI (async)
- **Broker API:** Dhan (REST + WebSocket)
- **Data:** Real-time NSE market data via Dhan feeds
- **Alerts:** Telegram Bot API
- **Frontend:** HTML templates (monitoring dashboard)

## Setup

```bash
# Clone
git clone https://github.com/yashshelke2106/trading-bot.git
cd trading-bot

# Install dependencies
pip install -r requirements.txt

# Configure (create .env file)
DHAN_CLIENT_ID=your_client_id
DHAN_ACCESS_TOKEN=your_token
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Run
python command_center.py
```

## Backtesting Results

Separate backtesting engine (~800 lines) with walk-forward optimization:

| Index | Edge | Recommendation |
|-------|------|----------------|
| NIFTY | Positive (profitable after costs) | Deploy |
| BANKNIFTY | Negative (loses after costs) | Skip |

*Backtesting includes realistic Indian F&O costs: STT, brokerage, exchange charges, and estimated slippage.*

## Status

- ✅ Signal engine (production-ready)
- ✅ Broker integration (Dhan API)
- ✅ Telegram alerts
- ✅ Backtesting validation
- 🔄 Paper trading (in progress)
- ⬚ Live deployment (pending capital)

## Disclaimer

This is a personal project for educational and research purposes. Not financial advice. Trading derivatives involves substantial risk of loss. Past backtest performance does not guarantee future results.

## Author

**Yash Shelke** — [LinkedIn](https://linkedin.com/in/21-yashshelke) | [GitHub](https://github.com/yashshelke2106)
