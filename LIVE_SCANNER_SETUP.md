# LIVE SCANNER SETUP - EVERY 15 MINUTES

## Files Created:
- `live_scanner.py` - Main scanner
- `run_live_scan.bat` - Batch runner

---

## STEP 1: Manual Setup (Task Scheduler)

1. Press `Win + R` → Type `taskschd.msc` → Enter

2. Click **Create Basic Task**

3. Name: `Live Trading Scanner`

4. Trigger: **Daily** → Start time: **9:15 AM**

5. Action: **Start a program**
   - Program: `C:\Users\yashs\Documents\Trading Bot\file1\run_live_scan.bat`

6. Click **Finish**

7. Right-click task → **Properties** → **Triggers** → **Edit**
   - Check: `Repeat task every: 15 minutes, for a duration of: 1 day`

---

## STEP 2: Alternative - Run Directly

```bash
cd "C:\Users\yashs\Documents\Trading Bot\file1"
python live_scanner.py --live
```

This runs continuously every 15 minutes.

---

## WHAT YOU GET EVERY 15 MINUTES

### Telegram Message 1: Sentiment Update
```
MARKET SENTIMENT - 09:15
Market: BEARISH
Avg RSI: 55.2

RSI < 40 = Oversold (Buy)
RSI > 60 = Overbought (Sell)
```

### Telegram Message 2: Trade Alerts (if found)
```
TRADE ALERTS - 09:15

Found 3 potential trades!

1. BHEL PUT
   Price: 240.45
   Strike: 235 PE
   Entry: 10.3 | SL: 6.5 | Target: 20
   RSI: 25 | Momentum: -2.5%
   Score: 75
```

---

## SCANNING PARAMETERS

| Indicator | Points | Condition |
|-----------|--------|-----------|
| RSI > 55 (Bear) | +25 | Overbought |
| MACD < Signal | +25 | Bearish |
| Momentum < -1% | +15 | Downtrend |
| Volume > 1.3x | +10 | High activity |

**Minimum Score: 40** to send alert

---

## TEST NOW

```bash
cd "C:\Users\yashs\Documents\Trading Bot\file1"
python live_scanner.py --scan
```
