"""Data models and enums for the intraday trading bot."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    EXIT_TARGET = "EXIT_TARGET"
    EXIT_SL = "EXIT_SL"
    EXIT_TRAILING_SL = "EXIT_TRAILING_SL"
    EXIT_SQUAREOFF = "EXIT_SQUAREOFF"


class OrderAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    CLOSED = "CLOSED"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"


@dataclass
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: Optional[float] = None
    ema_fast: Optional[float] = None
    ema_slow: Optional[float] = None
    rsi: Optional[float] = None
    atr: Optional[float] = None


@dataclass
class Signal:
    symbol: str
    signal_type: SignalType
    timestamp: datetime
    price: float
    stop_loss: float
    target: float
    reason: str = ""
    indicators: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Order:
    order_id: str
    symbol: str
    action: OrderAction
    quantity: int
    order_type: OrderType
    price: float
    status: OrderStatus = OrderStatus.PENDING
    placed_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    fill_price: Optional[float] = None
    commission: float = 0.0
    slippage: float = 0.0
    notes: str = ""


@dataclass
class Position:
    position_id: str
    symbol: str
    side: OrderAction  # BUY for intraday long
    quantity: int
    entry_price: float
    current_price: float
    stop_loss: float
    target: float
    trailing_sl: float
    entry_time: datetime
    status: str = "OPEN"  # OPEN or CLOSED
    highest_price: float = field(init=False)

    def __post_init__(self):
        self.highest_price = self.entry_price

    @property
    def unrealized_pnl(self) -> float:
        """Unrealized P&L in currency."""
        if self.side == OrderAction.BUY:
            return (self.current_price - self.entry_price) * self.quantity
        return (self.entry_price - self.current_price) * self.quantity

    @property
    def unrealized_pnl_percent(self) -> float:
        """Unrealized P&L in percentage."""
        if self.entry_price == 0:
            return 0.0
        return ((self.current_price - self.entry_price) / self.entry_price) * 100.0

    def update_price(self, price: float) -> None:
        """Update current price and highest price reached."""
        self.current_price = price
        if price > self.highest_price:
            self.highest_price = price


@dataclass
class TradeRecord:
    trade_id: str
    symbol: str
    side: OrderAction
    quantity: int
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    exit_reason: str
    gross_pnl: float
    commission: float
    net_pnl: float
    return_pct: float
    duration_minutes: float = 0.0


@dataclass
class DailySummary:
    date: str
    starting_capital: float
    ending_capital: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    gross_pnl: float
    total_fees: float
    net_pnl: float
    max_drawdown_pct: float
    roi_pct: float
