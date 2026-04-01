"""
TELEGRAM NOTIFICATIONS FOR TRADING BOT
======================================
Sends alerts when signals trigger

Setup:
1. Create Telegram Bot: @BotFather -> /newbot -> get TOKEN
2. Get Chat ID: Message your bot, then visit https://api.telegram.org/bot<TOKEN>/getUpdates
3. Update config below with your TOKEN and CHAT_ID
"""

import requests
import json
import os
from datetime import datetime
from typing import Dict, List, Optional


class TelegramNotifier:
    def __init__(self, token: str = None, chat_id: str = None):
        self.load_config()

        self.token = token or self.bot_token
        self.chat_id = chat_id or self.chat_id
        self.is_configured = bool(self.token and self.chat_id)

        if self.is_configured:
            print(f"[TELEGRAM] Configured - Chat ID: {self.chat_id}")
        else:
            print("[TELEGRAM] Not configured - alerts disabled")

    def load_config(self):
        """Load config from file"""
        config_file = os.path.join(os.path.dirname(__file__), "telegram_config.json")
        config = {"bot_token": "", "chat_id": ""}

        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                config = json.load(f)

        self.bot_token = config.get("bot_token", "")
        self.chat_id = config.get("chat_id", "")

    def save_config(self):
        """Save config to file"""
        config_file = os.path.join(os.path.dirname(__file__), "telegram_config.json")
        with open(config_file, "w") as f:
            json.dump(
                {"bot_token": self.bot_token, "chat_id": self.chat_id}, f, indent=2
            )

    def test_connection(self) -> bool:
        """Test if Telegram is configured correctly"""
        if not self.is_configured:
            return False

        try:
            url = f"https://api.telegram.org/bot{self.token}/getMe"
            response = requests.get(url, timeout=10)
            result = response.json()
            if result.get("ok"):
                bot_name = result.get("result", {}).get("first_name", "Unknown")
                print(f"[TELEGRAM] Connected! Bot: @{bot_name}")
                return True
        except Exception as e:
            print(f"[TELEGRAM] Connection failed: {e}")
        return False

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Send a message to Telegram"""
        if not self.is_configured:
            return False

        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            data = {"chat_id": self.chat_id, "text": text, "parse_mode": parse_mode}
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            return result.get("ok", False)
        except Exception as e:
            print(f"[TELEGRAM] Send failed: {e}")
            return False

    def send_signal_alert(
        self,
        symbol: str,
        direction: str,
        entry: float,
        sl: float,
        target: float,
        confidence: int,
        strategy: str = "",
    ):
        """Send trading signal alert"""
        emoji = "📈" if direction == "LONG" else "📉"

        message = f"""
{emoji} *NEW SIGNAL ALERT*

*{symbol} - {direction}*

Entry: {entry:.2f}
Stop Loss: {sl:.2f}
Target: {target:.2f}
Risk: {abs(entry - sl):.2f}
Reward: {abs(target - entry):.2f}
R:R: 1:{abs(target - entry) / abs(entry - sl):.1f}

Confidence: {confidence}%
Strategy: {strategy}

⏰ {datetime.now().strftime("%H:%M:%S")}
"""
        return self.send_message(message)

    def send_order_executed(
        self, symbol: str, direction: str, quantity: int, price: float
    ):
        """Send order execution alert"""
        emoji = "✅" if direction == "BUY" else "❌"

        message = f"""
{emoji} *ORDER EXECUTED*

*{symbol}*

Action: {direction}
Quantity: {quantity}
Price: {price:.2f}
Value: ₹{quantity * price:,.2f}

⏰ {datetime.now().strftime("%H:%M:%S")}
"""
        return self.send_message(message)

    def send_sl_hit(self, symbol: str, pnl: float):
        """Send stop loss hit alert"""
        message = f"""
🔴 *STOP LOSS HIT*

*{symbol}*

P&L: ₹{pnl:.2f}

📊 Reviewing position...
"""
        return self.send_message(message)

    def send_target_hit(self, symbol: str, pnl: float):
        """Send target hit alert"""
        message = f"""
🟢 *TARGET HIT!*

*{symbol}*

P&L: ₹{pnl:.2f}

🎯 Perfect trade!
"""
        return self.send_message(message)

    def send_daily_summary(self, trades: List[Dict], total_pnl: float):
        """Send daily summary"""
        wins = [t for t in trades if t.get("pnl", 0) > 0]
        losses = [t for t in trades if t.get("pnl", 0) <= 0]

        message = f"""
📊 *DAILY SUMMARY*

Trades: {len(trades)}
Wins: {len(wins)} | Losses: {len(losses)}
Win Rate: {len(wins) / len(trades) * 100:.0f}% if trades else 0%

Total P&L: ₹{total_pnl:.2f}

⏰ {datetime.now().strftime("%Y-%m-%d %H:%M")}
"""
        return self.send_message(message)

    def send_error(self, error_msg: str):
        """Send error alert"""
        message = f"""
⚠️ *ERROR ALERT*

{error_msg}

⏰ {datetime.now().strftime("%H:%M:%S")}
"""
        return self.send_message(message)

    def send_market_open(self, index: str, price: float):
        """Send market open alert"""
        message = f"""
🔔 *MARKET OPEN*

{index}: {price:,.2f}

Happy Trading! 🎯
"""
        return self.send_message(message)


def setup_telegram():
    """Interactive setup for Telegram"""
    print("\n" + "=" * 50)
    print("TELEGRAM SETUP")
    print("=" * 50)

    print("\nFollow these steps:")
    print("1. Open Telegram and search for @BotFather")
    print("2. Send /newbot")
    print("3. Give your bot a name (e.g., Trading Alerts)")
    print("4. Give it a username (e.g., mytradingbot)")
    print("5. Copy the TOKEN BotFather gives you")
    print("\n6. Search for your bot username and start chat")
    print("7. Send any message to your bot")
    print("8. Visit: https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates")
    print("9. Copy your Chat ID from the JSON response")
    print()

    token = input("Enter Bot Token: ").strip()
    chat_id = input("Enter Chat ID: ").strip()

    config_file = os.path.join(os.path.dirname(__file__), "telegram_config.json")
    with open(config_file, "w") as f:
        json.dump({"bot_token": token, "chat_id": chat_id}, f, indent=2)

    print(f"\nSaved to {config_file}")

    # Test connection
    notifier = TelegramNotifier(token, chat_id)
    if notifier.test_connection():
        print("\n✅ Telegram configured successfully!")
        return True
    else:
        print("\n❌ Connection failed. Check token and chat ID.")
        return False


# Example usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Telegram Notifier")
    parser.add_argument("--setup", action="store_true", help="Setup Telegram")
    parser.add_argument("--test", action="store_true", help="Test connection")
    args = parser.parse_args()

    if args.setup:
        setup_telegram()
    elif args.test:
        notifier = TelegramNotifier()
        notifier.test_connection()
    else:
        print("Commands:")
        print("  python telegram_notifier.py --setup  # Setup Telegram")
        print("  python telegram_notifier.py --test   # Test connection")
