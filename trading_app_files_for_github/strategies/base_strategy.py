"""Abstract Base Strategy class defining common strategy interface."""

from abc import ABC, abstractmethod
from typing import List, Optional
import pandas as pd
from core.models import Signal, Position


class BaseStrategy(ABC):
    """Abstract Strategy interface for intraday trading."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def evaluate_entry(self, symbol: str, df: pd.DataFrame) -> Optional[Signal]:
        """
        Evaluates the latest market data to determine if a new trade entry should be taken.
        Returns a Signal if entry triggered, else None.
        """
        pass

    @abstractmethod
    def evaluate_exit(self, position: Position, current_candle: pd.Series, current_time_str: str) -> Optional[Signal]:
        """
        Evaluates an active open position against current price bar to check for target,
        stop-loss, trailing SL, or intraday time-based square-off.
        Returns an EXIT Signal if position should be closed, else None.
        """
        pass
