"""Main Trading Engine coordinating data feed, strategy evaluation, risk validation, and broker execution."""

import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd

from core.models import Order, OrderAction, OrderType, Signal, SignalType, Position, DailySummary, TradeRecord
from core.config_loader import Config
from core.logger import setup_logger
from data.data_feed import DataFeed
from risk.risk_manager import RiskManager
from strategies.orb_vwap_strategy import ORBVWAPStrategy
from strategies.confluence_strategy import ConfluenceStrategy
from execution.broker_base import BrokerBase
from execution.paper_broker import PaperBroker
from execution.live_broker import LiveBrokerAdapter
from engine.scheduler import MarketScheduler

logger = setup_logger("TradingEngine")


class TradingEngine:
    """
    Intraday Trading Engine.
    Executes the entire daily trading lifecycle:
    1. Scan watchlist candles
    2. Manage existing open positions (Trailing SL, Target, Square-off)
    3. Evaluate new ORB+VWAP breakout signals
    4. Enforce strict risk limits & calculate dynamic position size
    5. Execute orders via Paper or Live broker
    6. Perform end-of-day square-off and P&L audit
    """

    def __init__(self, config: Config, broker: Optional[BrokerBase] = None):
        self.config = config
        self.scheduler = MarketScheduler(config)
        self.data_feed = DataFeed()
        self.strategy = ConfluenceStrategy(config) if config.get("strategy.use_confluence", True) else ORBVWAPStrategy(config)
        self.risk_manager = RiskManager(config)

        if broker is not None:
            self.broker = broker
        elif config.execution_mode == "live":
            self.broker = LiveBrokerAdapter(config, broker_name=config.get("execution.broker_type", "zerodha"))
        else:
            self.broker = PaperBroker(config)

        self.symbols: List[str] = config.symbols
        self.is_running = False

    def step(self, current_time_str: Optional[str] = None, latest_data_override: Optional[Dict[str, pd.DataFrame]] = None) -> Dict[str, Any]:
        """
        Executes one full iteration cycle of the trading engine.
        Can be called by live loop or historical simulation.
        """
        now_time_str = current_time_str or self.scheduler.get_current_time_str()
        results = {
            "time": now_time_str,
            "positions_count": len(self.broker.get_open_positions()),
            "cash_balance": self.broker.get_cash_balance(),
            "portfolio_value": self.broker.get_portfolio_value(),
            "signals": [],
            "closed_trades": []
        }

        # -------------------------------------------------------------
        # STEP 1: Fetch latest market data for watchlist symbols
        # -------------------------------------------------------------
        market_data: Dict[str, pd.DataFrame] = {}
        target_symbols = list(latest_data_override.keys()) if latest_data_override else self.symbols
        for symbol in target_symbols:
            if latest_data_override and symbol in latest_data_override:
                market_data[symbol] = latest_data_override[symbol]
            else:
                market_data[symbol] = self.data_feed.fetch_intraday_history(
                    symbol=symbol,
                    interval=self.config.timeframe,
                    days=1,
                    use_cache=True
                )

        # -------------------------------------------------------------
        # STEP 2: Manage existing open positions
        # -------------------------------------------------------------
        open_positions = dict(self.broker.get_open_positions())
        total_unrealized_pnl = 0.0

        for symbol, position in open_positions.items():
            df = market_data.get(symbol)
            if df is None or df.empty:
                continue

            current_candle = df.iloc[-1]
            current_close = float(current_candle["close"])
            current_atr = float(current_candle.get("atr", current_close * 0.01))

            # Update position price
            position.update_price(current_close)
            total_unrealized_pnl += position.unrealized_pnl

            # Update Trailing Stop Loss
            self.risk_manager.update_trailing_stop(position, current_close, current_atr)

            # Evaluate Exit Conditions (Target, Stop Loss, Trailing SL, Square-Off)
            exit_signal = self.strategy.evaluate_exit(position, current_candle, now_time_str)

            if exit_signal:
                trade = self.broker.close_position(symbol, exit_signal.price, exit_signal.reason)
                if trade:
                    self.risk_manager.update_realized_pnl(trade.net_pnl)
                    results["closed_trades"].append(trade)

        # -------------------------------------------------------------
        # STEP 3: Mandatory Auto Square-Off Check
        # -------------------------------------------------------------
        if self.scheduler.is_square_off_time(now_time_str):
            remaining_positions = self.broker.get_open_positions()
            if remaining_positions:
                logger.warning(f"⏰ Mandatory square-off reached ({now_time_str}). Closing all {len(remaining_positions)} open positions!")
                latest_prices = {s: float(market_data[s].iloc[-1]["close"]) for s in remaining_positions if s in market_data and not market_data[s].empty}
                sq_trades = self.broker.square_off_all_positions(latest_prices, reason="Auto Square-Off at Market Cutoff")
                for t in sq_trades:
                    self.risk_manager.update_realized_pnl(t.net_pnl)
                    results["closed_trades"].extend(sq_trades)
            return results

        # -------------------------------------------------------------
        # STEP 4: Evaluate New Trade Entries (Only during entry window)
        # -------------------------------------------------------------
        can_enter = self.scheduler.is_entry_allowed(now_time_str)
        if not can_enter:
            return results

        for symbol in target_symbols:
            # Skip if we already hold an open position in this stock
            if symbol in self.broker.get_open_positions():
                continue

            df = market_data.get(symbol)
            if df is None or df.empty:
                continue

            signal = self.strategy.evaluate_entry(symbol, df)
            if not signal or signal.signal_type != SignalType.BUY:
                continue

            results["signals"].append(signal)

            # Validate with Risk Manager
            is_approved, quantity, reason = self.risk_manager.validate_and_size_order(
                signal=signal,
                open_positions_count=len(self.broker.get_open_positions()),
                unrealized_pnl=total_unrealized_pnl
            )

            if not is_approved:
                logger.debug(f"Risk rejection for {symbol}: {reason}")
                continue

            # Place Order
            order = Order(
                order_id=f"ord_{uuid.uuid4().hex[:8]}",
                symbol=symbol,
                action=OrderAction.BUY,
                quantity=quantity,
                order_type=OrderType.MARKET,
                price=signal.price,
                notes=signal.reason
            )

            filled_order = self.broker.execute_order(order)
            if filled_order.status == "FILLED" and symbol in self.broker.get_open_positions():
                # Set accurate target & stop loss on the active position
                pos = self.broker.get_open_positions()[symbol]
                pos.stop_loss = signal.stop_loss
                pos.trailing_sl = signal.stop_loss
                pos.target = signal.target

        return results

    def generate_daily_summary(self, date_str: Optional[str] = None) -> DailySummary:
        """Calculates final daily P&L and trading performance metrics."""
        history = self.broker.get_trade_history()
        today = date_str or datetime.now().strftime("%Y-%m-%d")

        total_trades = len(history)
        winning_trades = sum(1 for t in history if t.net_pnl > 0)
        losing_trades = sum(1 for t in history if t.net_pnl < 0)
        win_rate = (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0

        gross_pnl = sum(t.gross_pnl for t in history)
        total_fees = sum(t.commission for t in history)
        net_pnl = sum(t.net_pnl for t in history)
        ending_capital = self.broker.get_portfolio_value()
        roi_pct = ((ending_capital - self.config.initial_capital) / self.config.initial_capital) * 100.0

        return DailySummary(
            date=today,
            starting_capital=self.config.initial_capital,
            ending_capital=ending_capital,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=round(win_rate, 2),
            gross_pnl=round(gross_pnl, 2),
            total_fees=round(total_fees, 2),
            net_pnl=round(net_pnl, 2),
            max_drawdown_pct=0.0,
            roi_pct=round(roi_pct, 2)
        )
