"""Realistic Paper Trading Simulator with slippage, brokerage fees, and execution tracking."""

import uuid
from datetime import datetime
from typing import Dict, List, Optional
from core.models import Order, OrderAction, OrderStatus, OrderType, Position, TradeRecord
from core.config_loader import Config
from core.logger import setup_logger
from execution.broker_base import BrokerBase

logger = setup_logger("PaperBroker")


class PaperBroker(BrokerBase):
    """
    Simulated Paper Broker:
    - Maintains virtual cash balance and margin.
    - Applies realistic slippage (0.03%) and statutory charges/brokerage (0.03%).
    - Manages open positions and records full trade lifecycle.
    """

    def __init__(self, config: Config):
        self.config = config
        self.initial_capital = config.initial_capital
        self.cash_balance = config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.trade_history: List[TradeRecord] = []
        self.slippage_pct = config.slippage_percent / 100.0
        self.commission_pct = config.commission_percent / 100.0

    def get_cash_balance(self) -> float:
        return self.cash_balance

    def get_portfolio_value(self) -> float:
        unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
        return self.cash_balance + unrealized

    def get_open_positions(self) -> Dict[str, Position]:
        return self.positions

    def execute_order(self, order: Order) -> Order:
        """Simulates market order execution with slippage and deductions."""
        if order.action == OrderAction.BUY:
            # Add slippage to entry price
            fill_price = round(order.price * (1.0 + self.slippage_pct), 2)
            turnover = fill_price * order.quantity
            commission = round(turnover * self.commission_pct, 2)
            total_cost = turnover + commission

            if self.cash_balance < total_cost:
                order.status = OrderStatus.REJECTED
                order.notes = f"Insufficient cash: Required {total_cost:.2f}, Available: {self.cash_balance:.2f}"
                logger.warning(f"❌ Order {order.order_id} REJECTED: {order.notes}")
                return order

            # Deduct cash
            self.cash_balance -= total_cost
            order.status = OrderStatus.FILLED
            order.fill_price = fill_price
            order.filled_at = datetime.now()
            order.commission = commission
            order.slippage = round(fill_price - order.price, 2)

            pos_id = f"pos_{uuid.uuid4().hex[:8]}"
            # Stop loss and target calculated in signal
            position = Position(
                position_id=pos_id,
                symbol=order.symbol,
                side=OrderAction.BUY,
                quantity=order.quantity,
                entry_price=fill_price,
                current_price=fill_price,
                stop_loss=order.price * 0.985,  # fallback
                target=order.price * 1.03,      # fallback
                trailing_sl=order.price * 0.985,
                entry_time=order.filled_at or datetime.now()
            )
            self.positions[order.symbol] = position
            self.orders[order.order_id] = order

            logger.info(
                f"🛒 BUY FILLED: {order.symbol} x {order.quantity} @ {fill_price:.2f} "
                f"(Slippage: +{order.slippage:.2f}, Comm: {commission:.2f}) | Cash Left: {self.cash_balance:.2f}"
            )
            return order

        return order

    def close_position(self, symbol: str, exit_price: float, reason: str) -> Optional[TradeRecord]:
        """Closes an open position with simulated exit slippage and commission."""
        if symbol not in self.positions:
            return None

        pos = self.positions.pop(symbol)
        # Apply exit slippage (sell lower)
        actual_exit_price = round(exit_price * (1.0 - self.slippage_pct), 2)
        turnover = actual_exit_price * pos.quantity
        exit_commission = round(turnover * self.commission_pct, 2)

        # Credit back cash from sale minus commission
        self.cash_balance += (turnover - exit_commission)

        # P&L calculations
        gross_pnl = round((actual_exit_price - pos.entry_price) * pos.quantity, 2)
        entry_commission = round(pos.entry_price * pos.quantity * self.commission_pct, 2)
        total_commission = entry_commission + exit_commission
        net_pnl = round(gross_pnl - total_commission, 2)
        return_pct = round(((actual_exit_price - pos.entry_price) / pos.entry_price) * 100.0, 2)

        exit_time = datetime.now()
        duration_minutes = round((exit_time - pos.entry_time).total_seconds() / 60.0, 1)

        trade = TradeRecord(
            trade_id=f"trd_{uuid.uuid4().hex[:8]}",
            symbol=pos.symbol,
            side=pos.side,
            quantity=pos.quantity,
            entry_price=pos.entry_price,
            exit_price=actual_exit_price,
            entry_time=pos.entry_time,
            exit_time=exit_time,
            exit_reason=reason,
            gross_pnl=gross_pnl,
            commission=total_commission,
            net_pnl=net_pnl,
            return_pct=return_pct,
            duration_minutes=duration_minutes
        )

        self.trade_history.append(trade)

        emoji = "🎯" if net_pnl >= 0 else "🛑"
        logger.info(
            f"{emoji} CLOSED {pos.symbol}: Exit @ {actual_exit_price:.2f} ({reason}) | "
            f"Net P&L: {net_pnl:+.2f} ({return_pct:+.2f}%) | Fees: {total_commission:.2f} | "
            f"Balance: {self.cash_balance:.2f}"
        )
        return trade

    def square_off_all_positions(self, latest_prices: Dict[str, float], reason: str = "Market Square-off") -> List[TradeRecord]:
        """Closes all currently open positions."""
        closed_trades = []
        symbols = list(self.positions.keys())
        for sym in symbols:
            exit_price = latest_prices.get(sym, self.positions[sym].current_price)
            trade = self.close_position(sym, exit_price, reason)
            if trade:
                closed_trades.append(trade)
        return closed_trades

    def get_trade_history(self) -> List[TradeRecord]:
        return self.trade_history
