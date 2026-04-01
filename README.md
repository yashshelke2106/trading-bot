# Trading Bot - Autonomous System

## Quick Start on Render.com

### 1. Upload Files to GitHub First
If not already done, upload these files to your GitHub repo:
- `autonomous_bot.py` (main bot)
- `telegram_notifier.py` 
- `telegram_config.json`
- `active_trades.json`
- `trade_analysis.json`
- `bot_settings.json`

### 2. Setup on Render

1. Go to: https://render.com
2. Click: **New Web Service**
3. Connect: Select your GitHub account
4. Select: Repository `trading-bot`
5. Settings:
   - **Name**: trading-bot
   - **Region**: Mumbai (or closest)
   - **Branch**: main
   - **Build Command**: `pip install yfinance requests`
   - **Start Command**: `python autonomous_bot.py --monitor`
6. Click: **Create Web Service**

### 3. Important Configuration

The bot reads from:
- `active_trades.json` - current open trades
- `trade_analysis.json` - trade history for learning
- `bot_settings.json` - bot parameters

**To update trades from your PC:**
1. Edit `active_trades.json` locally
2. Push changes to GitHub
3. Render will auto-update on next check

### 4. Telegram Setup
The bot sends alerts to your configured Telegram. Make sure `telegram_config.json` has:
- `bot_token`: Your Telegram bot token
- `chat_id`: Your chat ID

### 5. Monitor Logs
After deployment, check Render dashboard for:
- Live trade monitoring output
- SL/Target hit alerts
- Auto-learning notifications

## Features
- 24/7 autonomous trading
- Auto-learns from losses
- Dynamic SL (ATR-based)
- Telegram notifications
- Self-improving system
- Market volatility adaptation

## Commands (for reference)
```
--check      Check trades once
--monitor    Run continuously (24/7)
--settings   Show current settings
--signal     Generate signal for symbol
```

## Support
Check Render logs if issues occur. The bot runs every 60 seconds.