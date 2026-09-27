"""Main CLI entrypoint for the Intraday Algorithmic Trading Bot."""

import argparse
import sys
import time
from pathlib import Path

# Add project root to python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.config_loader import Config
from core.logger import setup_logger, console
from engine.trading_engine import TradingEngine
from backtest.backtester import IntradayBacktester
from ui.terminal_ui import TerminalDashboard
from data.data_feed import DataFeed

logger = setup_logger("Main")


def run_paper_trading(config: Config):
    """Runs the live paper trading engine loop."""
    console.print("[bold green]Starting Intraday Algo Bot in PAPER TRADING Mode...[/bold green]")
    engine = TradingEngine(config)
    dashboard = TerminalDashboard(config, engine.broker, engine.risk_manager, engine.scheduler)

    try:
        while True:
            # Execute one engine step
            engine.step()

            # Render updated dashboard snapshot
            dashboard.print_snapshot()

            # Sleep until next check (e.g. 15 seconds)
            time.sleep(15)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Stopping Bot... Saving session records.[/bold yellow]")
        summary = engine.generate_daily_summary()
        console.print(f"[bold cyan]Daily Summary: {summary}[/bold cyan]")


def run_backtest(config: Config, symbols_str: str = None, days: int = 10):
    """Runs historical strategy backtest."""
    symbols = [s.strip() for s in symbols_str.split(",")] if symbols_str else config.symbols
    backtester = IntradayBacktester(config)
    backtester.run(symbols=symbols, days=days)


def run_scanner(config: Config):
    """One-shot scanner analyzing current market status of watchlist stocks."""
    console.print(f"[bold cyan]🔍 Scanning {len(config.symbols)} Watchlist Stocks...[/bold cyan]\n")
    data_feed = DataFeed()

    from rich.table import Table
    table = Table(title="📊 LIVE INTRADAY WATCHLIST SCANNER", header_style="bold cyan")
    table.add_column("Symbol", style="white")
    table.add_column("LTP", justify="right")
    table.add_column("VWAP", justify="right")
    table.add_column("EMA 9", justify="right")
    table.add_column("EMA 21", justify="right")
    table.add_column("RSI (14)", justify="right")
    table.add_column("Vol Surge", justify="right")
    table.add_column("Trend", justify="center")

    for sym in config.symbols:
        df = data_feed.fetch_intraday_history(sym, interval=config.timeframe, days=1, use_cache=True)
        if df.empty:
            table.add_row(sym, "N/A", "-", "-", "-", "-", "-", "[dim]No Data[/dim]")
            continue

        candle = df.iloc[-1]
        close = float(candle["close"])
        vwap = float(candle.get("vwap", close))
        ema9 = float(candle.get("ema_fast", close))
        ema21 = float(candle.get("ema_slow", close))
        rsi = float(candle.get("rsi", 50.0))
        vol_surge = float(candle.get("vol_surge", 1.0))

        is_bullish = close > vwap and ema9 > ema21
        trend_label = "[bold green]BULLISH[/bold green]" if is_bullish else "[bold red]BEARISH/NEUTRAL[/bold red]"

        table.add_row(
            sym,
            f"{close:.2f}",
            f"{vwap:.2f}",
            f"{ema9:.2f}",
            f"{ema21:.2f}",
            f"{rsi:.1f}",
            f"{vol_surge:.2f}x",
            trend_label
        )

    console.print(table)


def run_simulated_day(config: Config):
    """
    Simulates a full trading day session (09:15 to 15:30) in fast-forward,
    showing live dashboard updates as trades trigger, trail, and exit.
    """
    console.print("[bold yellow]🎬 Launching Fast-Forward Day Simulation...[/bold yellow]")
    backtester = IntradayBacktester(config)
    # Run backtest with 2 days for quick demonstration
    backtester.run(symbols=config.symbols[:5], days=2)


def main():
    parser = argparse.ArgumentParser(description="Automated Intraday Stock Buying Algo Bot")
    parser.add_argument(
        "--mode",
        choices=["paper", "backtest", "scan", "simulate-day"],
        default="paper",
        help="Bot execution mode: 'paper' (live virtual), 'backtest', 'scan' (live scanner), 'simulate-day'"
    )
    parser.add_argument("--config", type=str, default=None, help="Path to custom config.yaml")
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated stock symbols (e.g. RELIANCE.NS,TCS.NS)")
    parser.add_argument("--days", type=int, default=5, help="Number of past days for backtesting")

    args = parser.parse_args()
    config = Config.load(args.config)

    if args.mode == "paper":
        run_paper_trading(config)
    elif args.mode == "backtest":
        run_backtest(config, symbols_str=args.symbols, days=args.days)
    elif args.mode == "scan":
        run_scanner(config)
    elif args.mode == "simulate-day":
        run_simulated_day(config)


if __name__ == "__main__":
    main()
