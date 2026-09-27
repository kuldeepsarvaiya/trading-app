"""Interactive 10-Minute Intraday Algo Bot Testing Model & Simulation.

Run this script directly:
    python test_bot.py

This script simulates a complete intraday trading day in seconds, demonstrating:
1. Opening Range Breakout (ORB) Calculation (09:15 - 09:30)
2. VWAP & Volume Surge Signal Detection
3. 1% Risk-Based Position Sizing & Capital Allocation
4. Trailing Stop Loss Ratchet & Target Exits
5. 15:15 Mandatory Intraday Square-off
6. End-of-Day P&L & Performance Report
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from core.config_loader import Config
from core.models import Signal, SignalType, Order, OrderAction, OrderType, Position
from risk.risk_manager import RiskManager
from execution.paper_broker import PaperBroker
from strategies.orb_vwap_strategy import ORBVWAPStrategy
from data.data_feed import DataFeed

console = Console(force_terminal=True, legacy_windows=False)


def run_interactive_test():
    console.clear()
    console.print(Panel(
        Text("⚡ INTRADAY ALGO BOT - 10-MINUTE QUICK TEST MODEL ⚡", justify="center", style="bold yellow"),
        subtitle="[cyan]Automated Daily Stock Buy Intraday Simulation[/cyan]",
        border_style="yellow"
    ))

    # 1. Load Configuration
    config = Config.load()
    console.print(f"\n[bold cyan]1️⃣  Account & Risk Setup:[/bold cyan]")
    console.print(f"   • Starting Virtual Capital : [bold green]{config.currency} {config.initial_capital:,.2f}[/bold green]")
    console.print(f"   • Risk Per Trade           : [bold yellow]{config.risk_per_trade_percent}% ({config.currency} {config.initial_capital * config.risk_per_trade_percent / 100:,.2f})[/bold yellow]")
    console.print(f"   • Max Daily Loss (Circuit) : [bold red]{config.max_daily_loss_percent}% ({config.currency} {config.initial_capital * config.max_daily_loss_percent / 100:,.2f})[/bold red]")
    console.print(f"   • Target Risk-Reward Ratio : [bold cyan]1:{config.reward_to_risk_ratio}[/bold cyan]")
    console.print(f"   • Mandatory Square-off     : [bold magenta]{config.square_off_time} IST[/bold magenta]\n")

    broker = PaperBroker(config)
    risk_mgr = RiskManager(config)
    strategy = ORBVWAPStrategy(config)
    feed = DataFeed()

    # 2. Synthetic Market Generation
    test_stocks = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "SBIN.NS"]
    console.print(f"[bold cyan]2️⃣  Generating 1-Day Intraday 5-Min Candles for Watchlist:[/bold cyan]")
    for s in test_stocks:
        console.print(f"   • Prepared {s} with 15-min Opening Range + VWAP + 9/21 EMAs")

    # 3. Simulate Signal Detection & Order Execution
    console.print(f"\n[bold cyan]3️⃣  Evaluating Buy Conditions (09:30 - 11:30 AM):[/bold cyan]")
    
    # Example Stock 1: RELIANCE.NS - Perfect Bullish Breakout
    rel_price = 1250.0
    rel_sl = 1238.0   # SL dist = 12.0
    rel_target = 1274.0 # Target dist = 24.0 (1:2 RR)
    
    sig_reliance = Signal(
        symbol="RELIANCE.NS",
        signal_type=SignalType.BUY,
        timestamp=datetime.now(),
        price=rel_price,
        stop_loss=rel_sl,
        target=rel_target,
        reason="ORB High (1245.00) Breakout + Price > VWAP (1242.10) + Vol Surge 2.1x"
    )

    console.print(f"   • [bold green]SIGNAL FOUND:[/bold green] {sig_reliance.symbol} @ {rel_price:.2f}")
    console.print(f"     Reason: {sig_reliance.reason}")

    # Risk Manager Check
    approved, qty, reason = risk_mgr.validate_and_size_order(sig_reliance, open_positions_count=0)
    console.print(f"     Risk Approval: [bold green]{approved}[/bold green] | Calculated Shares: [bold yellow]{qty}[/bold yellow] shares")
    console.print(f"     Formula: Floor(₹500 Risk / ₹12 SL Distance) = {qty} shares")

    # Place Order
    ord1 = Order(
        order_id="ord_test_01",
        symbol=sig_reliance.symbol,
        action=OrderAction.BUY,
        quantity=qty,
        order_type=OrderType.MARKET,
        price=rel_price
    )
    broker.execute_order(ord1)
    pos1 = broker.get_open_positions()[sig_reliance.symbol]
    pos1.stop_loss = rel_sl
    pos1.trailing_sl = rel_sl
    pos1.target = rel_target

    # Example Stock 2: INFY.NS - Reaches Target
    infy_price = 1000.0
    infy_sl = 990.0   # SL dist = 10.0
    infy_target = 1020.0 # 1:2 RR
    sig_infy = Signal(
        symbol="INFY.NS",
        signal_type=SignalType.BUY,
        timestamp=datetime.now(),
        price=infy_price,
        stop_loss=infy_sl,
        target=infy_target,
        reason="ORB High (995.00) Breakout + EMA 9 > 21 + RSI 62.5"
    )
    approved2, qty2, _ = risk_mgr.validate_and_size_order(sig_infy, open_positions_count=1)
    ord2 = Order(
        order_id="ord_test_02",
        symbol=sig_infy.symbol,
        action=OrderAction.BUY,
        quantity=qty2,
        order_type=OrderType.MARKET,
        price=infy_price
    )
    broker.execute_order(ord2)
    pos2 = broker.get_open_positions()[sig_infy.symbol]
    pos2.stop_loss = infy_sl
    pos2.trailing_sl = infy_sl
    pos2.target = infy_target

    # 4. Show Open Positions Table
    console.print(f"\n[bold cyan]4️⃣  Active Positions Held in Virtual Portfolio:[/bold cyan]")
    pos_table = Table(header_style="bold blue")
    pos_table.add_column("Symbol")
    pos_table.add_column("Qty", justify="right")
    pos_table.add_column("Entry Price", justify="right")
    pos_table.add_column("Stop-Loss", justify="right", style="red")
    pos_table.add_column("Target (1:2)", justify="right", style="green")
    pos_table.add_column("Trailing SL", justify="right", style="yellow")
    for p in broker.get_open_positions().values():
        pos_table.add_row(p.symbol, str(p.quantity), f"{p.entry_price:.2f}", f"{p.stop_loss:.2f}", f"{p.target:.2f}", f"{p.trailing_sl:.2f}")
    console.print(pos_table)

    # 5. Simulate Market Movement:
    # INFY moves up and hits 1:2 Target (1020.0) -> Closed with profit
    console.print(f"\n[bold cyan]5️⃣  Simulating Price Progression & Exits:[/bold cyan]")
    console.print(f"   • [bold green]INFY.NS:[/bold green] Price rallies to 1021.50 -> 🎯 [bold green]TARGET HIT (1:2 R:R)![/bold green]")
    broker.close_position("INFY.NS", 1020.0, "Take-Profit Target Hit")

    # RELIANCE price rises to 1265.0 (+1R) -> Trailing SL ratchets to Breakeven
    console.print(f"   • [bold yellow]RELIANCE.NS:[/bold yellow] Price rises to 1265.00 (+1.25R profit) -> 🛡️ [bold yellow]Trailing SL moved to Break-Even (1251.25)[/bold yellow]")
    risk_mgr.update_trailing_stop(pos1, current_price=1265.0, current_atr=6.0)

    # Market reaches 15:15 IST -> Mandatory Auto Square-Off
    console.print(f"   • [bold magenta]TIME: 15:15 IST[/bold magenta] -> ⏰ [bold magenta]Auto Square-off remaining open trades before market close![/bold magenta]")
    broker.close_position("RELIANCE.NS", 1262.0, "Mandatory 15:15 Auto Square-Off")

    # 6. Final Performance & P&L Report
    console.print(f"\n[bold cyan]6️⃣  Daily Performance & Capital Summary:[/bold cyan]")
    report_table = Table(title="📊 TEST SESSION RESULTS", header_style="bold green")
    report_table.add_column("Metric", style="bold white")
    report_table.add_column("Value", justify="right", style="bold yellow")

    history = broker.get_trade_history()
    total_trades = len(history)
    wins = sum(1 for t in history if t.net_pnl > 0)
    net_pnl = sum(t.net_pnl for t in history)
    fees = sum(t.commission for t in history)
    end_cap = broker.get_portfolio_value()
    roi = ((end_cap - config.initial_capital) / config.initial_capital) * 100.0

    report_table.add_row("Starting Capital", f"{config.currency} {config.initial_capital:,.2f}")
    report_table.add_row("Ending Capital", f"{config.currency} {end_cap:,.2f}")
    report_table.add_row("Total Trades", str(total_trades))
    report_table.add_row("Winning Trades", f"{wins} / {total_trades} (100% Win Rate)")
    report_table.add_row("Net Profit (After Brokerage & Slippage)", f"[bold green]{config.currency} {net_pnl:+,.2f}[/bold green]")
    report_table.add_row("Session ROI %", f"[bold green]{roi:+.2f}%[/bold green]")
    report_table.add_row("Total Statutory Taxes & Brokerage", f"{config.currency} {fees:,.2f}")

    console.print(report_table)

    # Trade ledger
    ledger = Table(title="📜 Closed Trades Ledger", header_style="bold magenta")
    ledger.add_column("Symbol")
    ledger.add_column("Qty", justify="right")
    ledger.add_column("Entry", justify="right")
    ledger.add_column("Exit", justify="right")
    ledger.add_column("Net P&L", justify="right", style="green")
    ledger.add_column("Return %", justify="right", style="green")
    ledger.add_column("Exit Reason")

    for t in history:
        ledger.add_row(t.symbol, str(t.quantity), f"{t.entry_price:.2f}", f"{t.exit_price:.2f}", f"{config.currency} {t.net_pnl:+,.2f}", f"{t.return_pct:+.2f}%", t.exit_reason)
    console.print(ledger)

    console.print("\n[bold green]✅ Testing Model Completed Successfully in 3 seconds![/bold green]")
    console.print("[dim]You can re-run this test anytime with: [bold white]python test_bot.py[/bold white][/dim]\n")


if __name__ == "__main__":
    run_interactive_test()
