"""Event-driven Intraday Strategy Backtester."""

from datetime import datetime, date
from typing import Any, Dict, List, Optional
import pandas as pd
from tabulate import tabulate
from rich.console import Console
from rich.table import Table

from core.models import TradeRecord
from core.config_loader import Config
from core.logger import setup_logger, console
from data.data_feed import DataFeed
from execution.paper_broker import PaperBroker
from engine.trading_engine import TradingEngine

logger = setup_logger("Backtester")


class IntradayBacktester:
    """
    Simulates the intraday bot candle-by-candle across historical market days.
    Provides realistic slippage, fee deductions, and comprehensive strategy statistics.
    """

    def __init__(self, config: Config):
        self.config = config
        self.data_feed = DataFeed()

    def run(self, symbols: Optional[List[str]] = None, days: int = 10) -> Dict[str, Any]:
        """Runs the intraday simulation across all requested stocks and days."""
        target_symbols = symbols or self.config.symbols
        logger.info(f"🚀 Starting Backtest across {len(target_symbols)} stocks for {days} days...")

        # 1. Download and prepare data per symbol
        symbol_data: Dict[str, pd.DataFrame] = {}
        for sym in target_symbols:
            df = self.data_feed.fetch_intraday_history(
                symbol=sym,
                interval=self.config.timeframe,
                days=days,
                use_cache=True
            )
            if not df.empty:
                symbol_data[sym] = df

        if not symbol_data:
            logger.error("No historical data available for backtesting.")
            return {}

        # 2. Extract unique trading days from data
        all_timestamps = []
        for df in symbol_data.values():
            all_timestamps.extend(df.index.tolist())

        trading_dates = sorted(list(set(ts.date() for ts in all_timestamps)))
        logger.info(f"Identified {len(trading_dates)} trading sessions: {[d.strftime('%Y-%m-%d') for d in trading_dates]}")

        # 3. Setup paper broker and engine
        broker = PaperBroker(self.config)
        engine = TradingEngine(self.config, broker=broker)

        equity_curve = [self.config.initial_capital]

        # 4. Iterate day by day, session by session
        for tr_date in trading_dates:
            engine.risk_manager.reset_daily_metrics()

            # Filter data for this date
            day_slices: Dict[str, pd.DataFrame] = {}
            for sym, full_df in symbol_data.items():
                day_df = full_df[full_df.index.date == tr_date]
                if not day_df.empty:
                    day_slices[sym] = day_df

            if not day_slices:
                continue

            # Find all unique candle timestamps for this day
            day_times = sorted(list(set(
                ts for sym_df in day_slices.values() for ts in sym_df.index.tolist()
            )))

            for curr_time in day_times:
                time_str = curr_time.strftime("%H:%M")

                # Prepare cumulative data up to curr_time for each stock
                step_data: Dict[str, pd.DataFrame] = {}
                for sym, day_df in day_slices.items():
                    sub_df = day_df[day_df.index <= curr_time]
                    if not sub_df.empty:
                        step_data[sym] = sub_df

                # Execute one engine step
                engine.step(current_time_str=time_str, latest_data_override=step_data)

            # Record end of day portfolio value
            equity_curve.append(broker.get_portfolio_value())

        # 5. Compile Statistics
        all_trades = broker.get_trade_history()
        stats = self._calculate_performance_metrics(all_trades, equity_curve)
        self.print_backtest_report(stats, all_trades)
        return stats

    def _calculate_performance_metrics(self, trades: List[TradeRecord], equity_curve: List[float]) -> Dict[str, Any]:
        """Calculates comprehensive trading metrics."""
        total_trades = len(trades)
        if total_trades == 0:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "net_pnl": 0.0,
                "roi_percent": 0.0,
                "profit_factor": 0.0,
                "max_drawdown_pct": 0.0,
                "trades": []
            }

        winning_trades = [t for t in trades if t.net_pnl > 0]
        losing_trades = [t for t in trades if t.net_pnl <= 0]

        gross_profit = sum(t.net_pnl for t in winning_trades)
        gross_loss = abs(sum(t.net_pnl for t in losing_trades))

        win_rate = (len(winning_trades) / total_trades) * 100.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

        total_commission = sum(t.commission for t in trades)
        net_pnl = sum(t.net_pnl for t in trades)
        roi_percent = (net_pnl / self.config.initial_capital) * 100.0

        # Maximum Drawdown calculation
        peak = equity_curve[0]
        max_dd = 0.0
        for val in equity_curve:
            if val > peak:
                peak = val
            dd = (peak - val) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        avg_trade_return = sum(t.return_pct for t in trades) / total_trades
        avg_trade_duration = sum(t.duration_minutes for t in trades) / total_trades if total_trades > 0 else 0

        return {
            "initial_capital": self.config.initial_capital,
            "ending_capital": round(equity_curve[-1], 2),
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "total_commissions": round(total_commission, 2),
            "net_pnl": round(net_pnl, 2),
            "roi_percent": round(roi_percent, 2),
            "max_drawdown_pct": round(max_dd * 100.0, 2),
            "avg_trade_return_pct": round(avg_trade_return, 2),
            "avg_trade_duration_min": round(avg_trade_duration, 1),
            "trades": trades
        }

    def print_backtest_report(self, stats: Dict[str, any], trades: List[TradeRecord]) -> None:
        """Prints a rich, formatted table of backtest results to console."""
        console.print("\n")
        table = Table(title="📊 INTRADAY ALGO BOT - BACKTEST PERFORMANCE SUMMARY", header_style="bold cyan")
        table.add_column("Metric", style="bold white", width=30)
        table.add_column("Value", style="bold yellow", justify="right")

        table.add_row("Starting Capital", f"{self.config.currency} {stats.get('initial_capital', 0):,.2f}")
        table.add_row("Ending Capital", f"{self.config.currency} {stats.get('ending_capital', 0):,.2f}")
        
        pnl_style = "bold green" if stats.get("net_pnl", 0) >= 0 else "bold red"
        table.add_row("Net Profit / Loss", f"[{pnl_style}]{self.config.currency} {stats.get('net_pnl', 0):+,.2f}[/{pnl_style}]")
        table.add_row("Return on Investment (ROI)", f"[{pnl_style}]{stats.get('roi_percent', 0):+.2f}%[/{pnl_style}]")
        table.add_row("Total Trades Executed", str(stats.get("total_trades", 0)))
        table.add_row("Win Rate", f"{stats.get('win_rate', 0):.2f}% ({stats.get('winning_trades', 0)} wins / {stats.get('losing_trades', 0)} losses)")
        table.add_row("Profit Factor", f"{stats.get('profit_factor', 0):.2f}")
        table.add_row("Max Drawdown", f"{stats.get('max_drawdown_pct', 0):.2f}%")
        table.add_row("Total Fees & Slippage", f"{self.config.currency} {stats.get('total_commissions', 0):,.2f}")
        table.add_row("Average Trade Duration", f"{stats.get('avg_trade_duration_min', 0):.1f} mins")

        console.print(table)

        # Print trade breakdown table
        if trades:
            t_table = Table(title="📝 EXECUTED TRADES BREAKDOWN", header_style="bold magenta")
            t_table.add_column("Symbol", justify="left")
            t_table.add_column("Entry", justify="right")
            t_table.add_column("Exit", justify="right")
            t_table.add_column("Qty", justify="right")
            t_table.add_column("Net P&L", justify="right")
            t_table.add_column("Return %", justify="right")
            t_table.add_column("Exit Reason", justify="left")

            for t in trades[:15]:  # Show first 15 trades
                c = "green" if t.net_pnl >= 0 else "red"
                t_table.add_row(
                    t.symbol,
                    f"{t.entry_price:.2f}",
                    f"{t.exit_price:.2f}",
                    str(t.quantity),
                    f"[{c}]{t.net_pnl:+.2f}[/{c}]",
                    f"[{c}]{t.return_pct:+.2f}%[/{c}]",
                    t.exit_reason
                )

            console.print(t_table)
            if len(trades) > 15:
                console.print(f"... and {len(trades) - 15} more trades.")
