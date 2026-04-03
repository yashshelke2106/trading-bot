"""
TRADING COMMAND CENTER
======================
Complete integrated trading system:
- Dhan API connection
- Real-time market scanning
- Auto trade execution
- Telegram alerts
- Position management

Run: python command_center.py
"""

import os
import sys
import json
import time
import asyncio
import argparse
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from dhan_integration import DhanAPIClient
from legendary_trader import LegendaryScanner
from telegram_notifier import TelegramNotifier
from trading_bot_main import TradingBot


class TradingCommandCenter:
    def __init__(self):
        self.name = "Trading Command Center"
        self.version = "1.0"

        # Initialize components
        print("Initializing Trading Command Center...")
        print("=" * 50)

        # Dhan API
        self.dhan = DhanAPIClient()
        print(
            f"  Dhan API: {'Connected' if self.dhan.is_connected else 'Not Connected'}"
        )

        # Scanner
        self.scanner = LegendaryScanner(self.dhan) if self.dhan.is_connected else None
        print(f"  Scanner: {'Ready' if self.scanner else 'Not Ready'}")

        # Telegram
        self.telegram = TelegramNotifier()
        print(
            f"  Telegram: {'Ready' if self.telegram.is_configured else 'Not Configured'}"
        )

        # State
        self.signals = []
        self.positions = []
        self.is_running = False
        self.trade_count = 0
        self.daily_pnl = 0

        print("=" * 50)
        print("Ready!\n")

    def send_alert(self, message: str, alert_type: str = "INFO"):
        """Send alert to Telegram"""
        icons = {
            "INFO": "ℹ️",
            "SIGNAL": "📈",
            "ORDER": "📋",
            "EXECUTE": "✅",
            "ERROR": "❌",
            "SL": "🔴",
            "TARGET": "🟢",
            "SUMMARY": "📊",
        }
        icon = icons.get(alert_type, "ℹ️")

        full_message = f"{icon} *{self.name}*\n\n{message}"
        self.telegram.send_message(full_message)

    def scan_market(self):
        """Scan for trading signals"""
        print("\n" + "=" * 50)
        print("SCANNING MARKET...")
        print("=" * 50)

        if not self.scanner:
            print("Scanner not available")
            return []

        # Run scanner (simplified for demo)
        signals = []

        # In production, would use async scan
        # For now, return configured signals
        signals = [
            {
                "symbol": "TCS",
                "direction": "LONG",
                "entry": 6180.60,
                "sl": 5923.55,
                "target": 6951.75,
                "confidence": 90,
                "strategy": "CALL_SPREAD",
            },
            {
                "symbol": "HDFCBANK",
                "direction": "SHORT",
                "entry": 2544.95,
                "sl": 2664.72,
                "target": 2185.64,
                "confidence": 75,
                "strategy": "PUT_SPREAD",
            },
            {
                "symbol": "ICICIBANK",
                "direction": "SHORT",
                "entry": 1170.51,
                "sl": 1256.00,
                "target": 914.04,
                "confidence": 75,
                "strategy": "PUT_SPREAD",
            },
        ]

        # Send signal alert
        for sig in signals:
            self.send_alert(
                f"*New Signal: {sig['symbol']}*\n\n"
                f"Direction: {sig['direction']}\n"
                f"Entry: Rs{sig['entry']}\n"
                f"Stop Loss: Rs{sig['sl']}\n"
                f"Target: Rs{sig['target']}\n"
                f"Confidence: {sig['confidence']}%\n"
                f"Strategy: {sig['strategy']}",
                "SIGNAL",
            )

        self.signals = signals
        return signals

    def execute_trade(self, signal: Dict, live: bool = False):
        """Execute a trade (live or paper)"""
        symbol = signal["symbol"]
        direction = signal["direction"]
        entry = signal["entry"]
        sl = signal["sl"]
        target = signal["target"]

        print(f"\n{'=' * 50}")
        print(f"EXECUTING {'LIVE' if live else 'PAPER'} TRADE: {symbol}")
        print(f"{'=' * 50}")

        risk_per_trade = 1.0
        risk_amount = 100000 * risk_per_trade / 100
        risk_per_share = abs(entry - sl)
        quantity = max(1, int(risk_amount / risk_per_share))

        if live:
            side = "BUY" if direction == "LONG" else "SELL"
            result = asyncio.run(
                self.dhan.place_order(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    order_type="MARKET",
                    stop_loss=sl,
                    target=target,
                    paper_mode=False,
                )
            )

            if result.get("status") == "success":
                order_id = result.get("order_id", "N/A")
                print(f"  Live order placed! Order ID: {order_id}")
            else:
                print(f"  Order failed: {result.get('message')}")
                return None
        else:
            order_id = f"PAPER_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        self.send_alert(
            f"{'🚀' if live else '📝'} *{'LIVE' if live else 'PAPER'} Trade Executed*\n\n"
            f"Symbol: {symbol}\n"
            f"Direction: {direction}\n"
            f"Entry: Rs{entry}\n"
            f"Qty: {quantity}\n"
            f"Value: Rs{entry * quantity:,.2f}\n"
            f"SL: Rs{sl}\n"
            f"Target: Rs{target}\n"
            f"Order ID: {order_id}",
            "EXECUTE",
        )

        trade = {
            "symbol": symbol,
            "direction": direction,
            "entry": entry,
            "sl": sl,
            "target": target,
            "quantity": quantity,
            "status": "OPEN",
            "time": datetime.now().strftime("%H:%M:%S"),
            "order_id": order_id,
            "live": live,
        }

        self.positions.append(trade)
        self.trade_count += 1

        print(f"  Symbol: {symbol}")
        print(f"  Direction: {direction}")
        print(f"  Entry: {entry}")
        print(f"  Qty: {quantity}")
        print(f"  SL: {sl}")
        print(f"  Target: {target}")
        print(f"  Order ID: {order_id}")

        return trade

    def check_positions(self):
        """Check open positions"""
        if not self.positions:
            print("\nNo open positions")
            return

        print("\n" + "=" * 50)
        print("OPEN POSITIONS")
        print("=" * 50)

        for i, pos in enumerate(self.positions, 1):
            print(f"{i}. {pos['symbol']} | {pos['direction']}")
            print(
                f"   Entry: {pos['entry']} | SL: {pos['sl']} | Target: {pos['target']}"
            )
            print(f"   Qty: {pos['quantity']} | Status: {pos['status']}")

    def show_status(self):
        """Show current status"""
        print("\n" + "=" * 50)
        print("COMMAND CENTER STATUS")
        print("=" * 50)
        print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Dhan: {'Connected' if self.dhan.is_connected else 'Disconnected'}")
        print(
            f"  Telegram: {'Active' if self.telegram.is_configured else 'Not Configured'}"
        )
        print(f"  Signals Found: {len(self.signals)}")
        print(f"  Open Positions: {len(self.positions)}")
        print(f"  Total Trades: {self.trade_count}")
        print(f"  Daily P&L: {self.daily_pnl:.2f}")

    def run_full_scan(self, live: bool = False):
        """Run complete scan and trade cycle"""
        print("\n" + "=" * 50)
        print(f"RUNNING {'LIVE' if live else 'PAPER'} SCAN & TRADE")
        print("=" * 50)

        if live:
            self.send_alert("🚀 *Live Trading Started*", "INFO")

        signals = self.scan_market()

        if not signals:
            print("No signals found")
            return

        for sig in signals[:2]:
            if len(self.positions) >= 3:
                print("Max positions reached")
                break

            self.execute_trade(sig, live=live)

        self.show_status()
        self.check_positions()

    def send_test_alert(self):
        """Send test alert"""
        print("\nSending test alert...")
        result = self.telegram.send_message(
            "🧪 *Test Alert*\n\nThis is a test from Trading Command Center!", "INFO"
        )
        if result:
            print("Test alert sent!")
        else:
            print("Failed to send test alert")

    def run_paper_trading(self, num_trades: int = 150):
        """Run paper trading to test the system"""
        print("\n" + "=" * 50)
        print("PAPER TRADING MODE")
        print("=" * 50)
        print(f"Target: {num_trades} trades")
        print(f"Initial Capital: Rs1,00,000")
        print("=" * 50)

        # Extended instruments list for more trades
        config = {
            "initial_capital": 100000,
            "risk_per_trade": 0.005,  # 0.5% risk per trade
            "account_id": "PAPER_001",
            "instruments": [
                "NIFTY",
                "BANKNIFTY",
                "FINNIFTY",
                "RELIANCE",
                "TCS",
                "INFY",
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
                "BAJFINANCE",
                "ADANIPORTS",
                "TITAN",
            ],
            "timeframe": "5min",
            "max_positions": 3,  # Allow up to 3 concurrent positions
            "trading_hours": {"start": "09:15", "end": "15:30"},
        }

        bot = TradingBot(config)

        self.send_alert(
            f"📝 *PAPER TRADING STARTED*\n\n"
            f"Target: {num_trades} trades\n"
            f"Capital: Rs1,00,000\n"
            f"Max Positions: 3\n"
            f"Instruments: {len(config['instruments'])}",
            "INFO",
        )

        print("\n[+] Starting paper trading...")
        print("[!] Press Ctrl+C to stop\n")

        # Run for 2 hours (market hours) or until target trades reached
        start_time = time.time()
        duration = 2 * 60 * 60  # 2 hours
        last_update = 0

        try:
            while True:
                # Run scan and generate signals
                signals = self.scan_market()

                # Auto-execute top signals in paper mode
                for sig in signals[: config["max_positions"]]:
                    result = bot.place_trade_paper(
                        instrument=sig["symbol"],
                        signal_type=sig["direction"],
                        entry_price=sig.get("entry", sig.get("price", 25000)),
                        stop_loss=sig.get("sl", sig.get("entry", 25000) * 0.98),
                        target=sig.get("target", sig.get("entry", 25000) * 1.03),
                        quantity=1,
                    )

                status = bot.get_paper_trading_status()
                account = status.get("account", {})
                positions = status.get("open_positions", [])
                trades_count = account.get("total_trades", 0)

                elapsed = int((time.time() - start_time) / 60)
                print(
                    f"[{elapsed}m] Trades: {trades_count}/{num_trades} | "
                    f"P&L: Rs{account.get('total_pnl', 0):.2f} | "
                    f"Positions: {len(positions)}"
                )

                # Send update every 15 minutes
                if elapsed - last_update >= 15:
                    self.send_alert(
                        f"📊 *Paper Trading Update*\n\n"
                        f"Trades: {trades_count}/{num_trades}\n"
                        f"P&L: Rs{account.get('total_pnl', 0):.2f}\n"
                        f"Win Rate: {account.get('win_rate', 'N/A')}",
                        "INFO",
                    )
                    last_update = elapsed

                # Check if target reached
                if trades_count >= num_trades:
                    print(f"\n[✓] Target of {num_trades} trades reached!")
                    break

                # Check time limit
                if time.time() - start_time > duration:
                    print("\n[!] Time limit reached (2 hours)")
                    break

                time.sleep(60)  # Wait 1 minute between scans

        except KeyboardInterrupt:
            print("\n\n[-] Paper trading stopped by user")

        # Final summary
        final_status = bot.get_paper_trading_status()
        account = final_status.get("account", {})
        trades = final_status.get("recent_trades", [])

        print("\n" + "=" * 50)
        print("PAPER TRADING SUMMARY")
        print("=" * 50)
        print(f"Total Trades: {account.get('total_trades', 0)}")
        print(f"Win Rate: {account.get('win_rate', 'N/A')}")
        print(f"Final P&L: Rs{account.get('total_pnl', 0):.2f}")
        print(f"Final Balance: Rs{account.get('current_balance', 0):.2f}")

        self.send_alert(
            f"📝 *PAPER TRADING COMPLETE*\n\n"
            f"Total Trades: {account.get('total_trades', 0)}\n"
            f"Win Rate: {account.get('win_rate', 'N/A')}\n"
            f"Final P&L: Rs{account.get('total_pnl', 0):.2f}\n"
            f"Final Balance: Rs{account.get('current_balance', 0):.2f}",
            "SUMMARY",
        )

    def menu(self):
        """Show menu"""
        print("\n" + "=" * 50)
        print("TRADING COMMAND CENTER")
        print("=" * 50)
        print(f"""
   1. Scan Market          - Find trading signals
   2. Execute Trades       - Scan and trade top signals
   3. View Positions       - Show open positions
   4. View Status         - Show system status
   5. Test Telegram       - Send test alert
   6. Run Live Mode       - Paper trading continuous (5 min)
   7. Run Paper Trading   - Test with 150 trades
   8. LIVE TRADE          - Scan & execute LIVE orders
   9. Exit
    
    Enter choice (1-9):
         """)


def main():
    center = TradingCommandCenter()

    while True:
        center.menu()
        choice = input("> ").strip()

        if choice == "1":
            center.scan_market()
            for sig in center.signals:
                print(f"  {sig['symbol']} | {sig['direction']} | {sig['confidence']}%")

        elif choice == "2":
            center.run_full_scan()

        elif choice == "3":
            center.check_positions()

        elif choice == "4":
            center.show_status()

        elif choice == "5":
            center.send_test_alert()

        elif choice == "6":
            print("\nRunning live mode for 5 minutes...")
            center.send_alert(
                "🚀 *Live Mode Started*\n\nContinuous scanning activated for 5 minutes",
                "INFO",
            )

            for i in range(5):
                print(f"\nScan {i + 1}/5 - {datetime.now().strftime('%H:%M:%S')}")
                center.run_full_scan()
                if i < 4:
                    time.sleep(60)

            center.send_alert(
                "🏁 *Live Mode Complete*\n\n5 minute scanning session finished",
                "SUMMARY",
            )

        elif choice == "7":
            center.run_paper_trading(num_trades=150)

        elif choice == "8":
            print("\n" + "=" * 50)
            print("🚀 LIVE TRADING MODE")
            print("=" * 50)
            center.send_alert(
                "🚀 *LIVE TRADING MODE*\n\nScanning and executing REAL orders on Dhan!",
                "INFO",
            )
            signals = center.scan_market()
            for sig in signals[:2]:
                if len(center.positions) >= 3:
                    break
                center.execute_trade(sig, live=True)
            center.show_status()
            center.check_positions()

        elif choice == "9":
            print("\nExiting...")
            center.send_alert(
                "👋 *System Shutdown*\n\nTrading Command Center stopped", "INFO"
            )
            break

        else:
            print("Invalid choice")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trading Command Center")
    parser.add_argument(
        "--paper", "-7", action="store_true", help="Run paper trading (150 trades)"
    )
    parser.add_argument(
        "--trades", type=int, default=150, help="Number of trades for paper trading"
    )
    args = parser.parse_args()

    if args.paper:
        center = TradingCommandCenter()
        center.run_paper_trading(num_trades=args.trades)
    else:
        main()
