# Trading Bot - Auto Deploy Setup

## GitHub Actions Auto-Deploy to PythonAnywhere

### Setup Instructions:

### Step 1: Generate SSH Key for PythonAnywhere

On your local PC (PowerShell):
```powershell
ssh-keygen -t rsa -b 4096 -C "trading-bot"
```

This will create:
- Private key: `~/.ssh/id_rsa`
- Public key: `~/.ssh/id_rsa.pub`

### Step 2: Add SSH Key to PythonAnywhere

1. Go to [PythonAnywhere Consoles](https://www.pythonanywhere.com/consoles/)
2. Open a Bash console
3. Run:
```bash
mkdir -p ~/.ssh
cat >> ~/.ssh/authorized_keys
# Paste your PUBLIC key (id_rsa.pub content)
# Press Ctrl+D to save
```

### Step 3: Add Secrets to GitHub

1. Go to your GitHub repo: https://github.com/yashshelke2106/trading-bot
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add:

| Secret Name | Value |
|-------------|-------|
| `PYTHONANYWHERE_SSH_KEY` | Your PRIVATE key (id_rsa content) |
| `PYTHONANYWHERE_HOST` | `username.pythonanywhere.com` |
| `PYTHONANYWHERE_USER` | Your PythonAnywhere username |

### Step 4: Get Your PythonAnywhere Credentials

In PythonAnywhere Bash:
```bash
echo $HOSTNAME  # Shows: username.pythonanywhere.com
whoami          # Shows: your username
```

### Step 5: Push Workflow to GitHub

```bash
cd "C:\Users\yashs\Documents\Trading Bot\file1"
git add .github/
git commit -m "Add auto-deploy workflow"
git push origin main
```

### Step 6: Trigger Deployment

1. Go to GitHub repo → **Actions** tab
2. Click **Deploy to PythonAnywhere**
3. Click **Run workflow**

---

## How It Works:

```
You push code to GitHub
        ↓
GitHub Actions detects push
        ↓
Automatically:
  1. Stops old bot on PythonAnywhere
  2. Syncs new files
  3. Installs dependencies
  4. Restarts bot
        ↓
Bot running with new code!
```

---

## Manual Deploy (Alternative):

If auto-deploy fails, manually deploy:

```bash
# On PythonAnywhere Bash:
cd ~/trading_bot
git pull
pkill -f telegram_bot.py
nohup python telegram_bot.py > bot.log 2>&1 &
```

---

## Files Required on PythonAnywhere:

- `telegram_bot.py`
- `auto_market_scanner.py`
- `dhan_integration.py`
- `telegram_notifier.py`
- `telegram_config.json`
- `lot_sizes.py`

---

## Bot Commands:

| Command | Description |
|---------|-------------|
| `/scan` | Scan all stocks |
| `/signals` | Current setups |
| `/top5` | Top 5 trades |
| `/nifty` | NIFTY analysis |
| `/accuracy` | Win/loss stats |
| `/help` | Help menu |

---

## Troubleshooting:

### Bot not responding?
```bash
# Check bot status
ps aux | grep telegram_bot

# Check logs
cat ~/trading_bot/bot.log

# Restart bot
cd ~/trading_bot
python telegram_bot.py
```

### Deploy failed?
1. Check GitHub Actions logs
2. Verify SSH key is correct
3. Make sure PythonAnywhere is running

---

## Update Workflow:

```
1. Edit code on PC
2. Commit & push to GitHub
3. Auto-deploy triggers
4. Bot updates automatically!
```
