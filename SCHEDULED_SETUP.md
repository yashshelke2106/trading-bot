# AUTO SCANNER SETUP - 24/7 Signals on Telegram

## PythonAnywhere Setup

### Step 1: Create Account
1. Go to https://www.pythonanywhere.com
2. Sign up (free tier)
3. Verify email

### Step 2: Open Bash Console
1. Click "New Console" → "Bash"

### Step 3: Setup Folder & Install
```bash
cd ~
mkdir trading_bot
cd trading_bot
pip install pandas numpy requests websockets dhanhq-py --quiet
```

### Step 4: Upload Files
Upload these files to `~/trading_bot/`:
- `scheduled_scanner.py`
- `dhan_integration.py`
- `telegram_notifier.py`
- `telegram_config.json`

### Step 5: Test Scanner
```bash
cd ~/trading_bot
python scheduled_scanner.py
```
Check Telegram for signals!

### Step 6: Schedule Cron Job (Every 15 Minutes)
1. Go to **Tasks** tab
2. Click **Add a new scheduled task**
3. Set:
   - Command: `python /home/yourusername/trading_bot/scheduled_scanner.py`
   - Schedule: `Every 15 minutes` (select from dropdown)

### Step 7: Verify Setup
- Wait for next 15-minute interval
- Check Telegram for signal
- If no signal, check console output

---

## How It Works:

```
Every 15 minutes:
  1. Scanner checks if market is open (9:15 AM - 3:30 PM)
  2. Scans all stocks (NIFTY, BANKNIFTY, etc.)
  3. Generates signals based on RSI, EMA, MACD
  4. Sends to Telegram ONLY if:
     - Confidence >= 60%
     - Signal is NEW (not repeated in same 15-min window)
```

---

## Signals You Receive:

```
MARKET SCAN - 09:45

Signals: 2
Market: OPEN

---

RELIANCE 2000 PE - SHORT

*TRADE*
Entry: Rs.59
SL: Rs.30
T1: Rs.118 | T2: Rs.177

*LOT*
Lot: 500
Capital: Rs.29,500
Max Loss: Rs.14,500

*INDICATORS*
RSI: 72
Support: Rs.1,920
Resistance: Rs.1,980
Trend: BEARISH

*CONF: 75%*
```

---

## Bot Commands (Also Available):

| Command | Description |
|---------|-------------|
| `/scan` | Full market scan |
| `/signals` | Current setups |
| `/top5` | Best 5 trades |
| `/nifty` | NIFTY analysis |
| `/help` | Help menu |

---

## Troubleshooting:

### Bot not sending signals?
```bash
# Test manually
cd ~/trading_bot
python scheduled_scanner.py
```

### Check logs
```bash
python -c "from scheduled_scanner import *; import asyncio; asyncio.run(ScheduledScanner().scan_and_send())"
```

### Restart scheduler
- Go to Tasks → Delete old task
- Add new scheduled task

---

## Update Code:

To update scanner:
1. Edit code on your PC
2. Upload new file to PythonAnywhere
3. Or use git pull if repo connected

---

## Files:

| File | Purpose |
|------|---------|
| `scheduled_scanner.py` | Main scanner (runs every 15 min) |
| `telegram_bot.py` | On-demand commands |
| `dhan_integration.py` | Market data |
| `telegram_notifier.py` | Telegram notifications |
| `telegram_config.json` | Your bot config |
