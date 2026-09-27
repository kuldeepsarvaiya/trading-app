"""Rich Terminal Dashboard for Real-time Monitoring."""

from datetime import datetime
from typing import Dict, List, Optional
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from core.models import Position, TradeRecord
from core.config_loader import Config
from core.logger import console
from execution.broker_base import BrokerBase
from risk.risk_manager import RiskManager
from engine.scheduler import MarketScheduler


class TerminalDashboard:
    """Terminal-based real-time dashboard displaying portfolio, live positions, and trades."""

    def __init__(self, config: Config, broker: BrokerBase, risk_manager: RiskManager, scheduler: MarketScheduler):
        self.config = config
        self.broker = broker
        self.risk_manager = risk_manager
        self.scheduler = scheduler

    def render_header(self) -> Panel:
        """Renders header banner with system status and market state."""
        time_str = self.scheduler.get_current_time_str()
        is_open = self.scheduler.is_market_open(time_str)
        is_entry = self.scheduler.is_entry_allowed(time_str)
        is_sq = self.scheduler.is_square_off_time(time_str)

        market_status = "[bold green]ACTIVE TRADING[/bold green]" if is_entry else (
            "[bold yellow]POSITION MANAGEMENT ONLY[/bold yellow]" if is_open else "[bold red]MARKET CLOSED[/bold red]"
        )
        if is_sq:
            market_status = "[bold magenta]SQUARE-OFF CUTOFF[/bold magenta]"

        breaker_status = "[bold red]TRIGGERED (HALTED)[/bold red]" if self.risk_manager.is_circuit_breaker_triggered else "[bold green]SAFE (ACTIVE)[/bold green]"

        title_text = Text(
            f"⚡ INTRADAY ALGO BOT v{self.config.get('app.version', '1.0.0')} | "
            f"Market: {self.config.market_name} | Mode: {self.config.execution_mode.upper()}",
            style="bold cyan"
        )
        content = (
            f"🕒 [white]Time:[/white] [yellow]{time_str}[/yellow]   |   "
            f"🏢 [white]Session:[/white] {market_status}   |   "
            f"🛡️ [white]Circuit Breaker:[/white] {breaker_status}   |   "
            f"💰 [white]Max Risk/Trade:[/white] [green]{self.config.risk_per_trade_percent}%[/green]"
        )
        return Panel(content, title=title_text, border_style="cyan")

    def render_portfolio_panel(self) -> Panel:
        """Renders portfolio cash, equity, and daily P&L metrics."""
        cash = self.broker.get_cash_balance()
        portfolio_val = self.broker.get_portfolio_value()
        realized_pnl = self.risk_manager.realized_pnl_today

        open_positions = self.broker.get_open_positions()
        unrealized_pnl = sum(p.unrealized_pnl for p in open_positions.values())
        total_pnl = realized_pnl + unrealized_pnl
        total_roi = ((portfolio_val - self.config.initial_capital) / self.config.initial_capital) * 100.0

        pnl_color = "green" if total_pnl >= 0 else "red"

        table = Table.grid(expand=True)
        table.add_column(justify="center", ratio=1)
        table.add_column(justify="center", ratio=1)
        table.add_column(justify="center", ratio=1)
        table.add_column(justify="center", ratio=1)

        table.add_row(
            f"[dim]Starting Capital[/dim]\n[bold]{self.config.currency} {self.config.initial_capital:,.2f}[/bold]",
            f"[dim]Available Cash[/dim]\n[bold]{self.config.currency} {cash:,.2f}[/bold]",
            f"[dim]Portfolio Equity[/dim]\n[bold]{self.config.currency} {portfolio_val:,.2f}[/bold]",
            f"[dim]Today's Total P&L[/dim]\n[bold {pnl_color}]{self.config.currency} {total_pnl:+,.2f} ({total_roi:+.2f}%)[/bold {pnl_color}]"
        )

        return Panel(table, title="💼 Portfolio & Capital Health", border_style="green")

    def render_positions_table(self) -> Table:
        """Renders currently open positions."""
        table = Table(title="📈 Active Open Positions", expand=True, header_style="bold blue")
        table.add_column("Symbol", style="white", justify="left")
        table.add_column("Qty", justify="right")
        table.add_column("Entry Price", justify="right")
        table.add_column("LTP", justify="right")
        table.add_column("Trailing SL", justify="right", style="yellow")
        table.add_column("Target (1:2)", justify="right", style="cyan")
        table.add_column("Unrealized P&L", justify="right")
        table.add_column("Return %", justify="right")

        positions = self.broker.get_open_positions()
        if not positions:
            table.add_row("[dim]No active positions currently held[/dim]", "-", "-", "-", "-", "-", "-", "-")
            return table

        for p in positions.values():
            color = "green" if p.unrealized_pnl >= 0 else "red"
            table.add_row(
                p.symbol,
                str(p.quantity),
                f"{p.entry_price:.2f}",
                f"{p.current_price:.2f}",
                f"{p.trailing_sl:.2f}",
                f"{p.target:.2f}",
                f"[{color}]{self.config.currency} {p.unrealized_pnl:+,.2f}[/{color}]",
                f"[{color}]{p.unrealized_pnl_percent:+.2f}%[/{color}]"
            )

        return table

    def render_trade_history_table(self) -> Table:
        """Renders completed trades for today."""
        table = Table(title="📜 Today's Closed Trades Audit", expand=True, header_style="bold magenta")
        table.add_column("Symbol", justify="left")
        table.add_column("Qty", justify="right")
        table.add_column("Entry", justify="right")
        table.add_column("Exit", justify="right")
        table.add_column("Net P&L", justify="right")
        table.add_column("Return %", justify="right")
        table.add_column("Fees", justify="right")
        table.add_column("Exit Reason", justify="left")

        history = self.broker.get_trade_history()
        if not history:
            table.add_row("[dim]No trades closed yet today[/dim]", "-", "-", "-", "-", "-", "-", "-")
            return table

        for t in history[-8:]:  # Show latest 8 trades
            color = "green" if t.net_pnl >= 0 else "red"
            table.add_row(
                t.symbol,
                str(t.quantity),
                f"{t.entry_price:.2f}",
                f"{t.exit_price:.2f}",
                f"[{color}]{self.config.currency} {t.net_pnl:+,.2f}[/{color}]",
                f"[{color}]{t.return_pct:+.2f}%[/{color}]",
                f"{t.commission:.2f}",
                t.exit_reason
            )

        return table

    def print_snapshot(self) -> None:
        """Prints full snapshot of the dashboard to the console."""
        console.clear()
        console.print(self.render_header())
        console.print(self.render_portfolio_panel())
        console.print(self.render_positions_table())
        console.print(self.render_trade_history_table())
