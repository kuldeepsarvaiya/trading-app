"""Abstract base broker interface defining order management and portfolio tracking."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from core.models import Order, Position, TradeRecord


class BrokerBase(ABC):
    """Abstract interface for paper or live brokers."""

    @abstractmethod
    def get_cash_balance(self) -> float:
        """Returns currently available cash balance."""
        pass

    @abstractmethod
    def get_portfolio_value(self) -> float:
        """Returns total portfolio value (cash + unrealized P&L)."""
        pass

    @abstractmethod
    def get_open_positions(self) -> Dict[str, Position]:
        """Returns dict of active open positions keyed by symbol."""
        pass

    @abstractmethod
    def execute_order(self, order: Order) -> Order:
        """Executes an order and returns the filled order with details."""
        pass

    @abstractmethod
    def close_position(self, symbol: str, exit_price: float, reason: str) -> Optional[TradeRecord]:
        """Closes an open position and records trade P&L."""
        pass

    @abstractmethod
    def square_off_all_positions(self, latest_prices: Dict[str, float], reason: str = "Market Square-off") -> List[TradeRecord]:
        """Closes all open positions simultaneously."""
        pass

    @abstractmethod
    def get_trade_history(self) -> List[TradeRecord]:
        """Returns history of closed trades for the day."""
        pass
