"""Configuration loader and validator."""

import os
from pathlib import Path
from typing import Any, Dict
import yaml


class Config:
    """Singleton wrapper for configuration dictionary."""

    def __init__(self, config_dict: Dict[str, Any]):
        self._raw = config_dict

    @classmethod
    def load(cls, path: str = None) -> "Config":
        """Load configuration from YAML file path."""
        if path is None:
            # Default to config/config.yaml relative to project root
            base_dir = Path(__file__).resolve().parent.parent
            path = base_dir / "config" / "config.yaml"
        else:
            path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Config file not found at: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return cls(data)

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get nested value via dot notation, e.g. 'account.initial_capital'."""
        keys = key_path.split(".")
        val = self._raw
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    @property
    def raw(self) -> Dict[str, Any]:
        return self._raw

    # Account
    @property
    def initial_capital(self) -> float:
        return float(self.get("account.initial_capital", 50000.0))

    @property
    def currency(self) -> str:
        return str(self.get("account.currency", "INR"))

    # Risk Management
    @property
    def risk_per_trade_percent(self) -> float:
        return float(self.get("risk_management.risk_per_trade_percent", 1.0))

    @property
    def max_daily_loss_percent(self) -> float:
        return float(self.get("risk_management.max_daily_loss_percent", 3.0))

    @property
    def max_open_positions(self) -> int:
        return int(self.get("risk_management.max_open_positions", 3))

    @property
    def reward_to_risk_ratio(self) -> float:
        return float(self.get("risk_management.reward_to_risk_ratio", 2.0))

    @property
    def use_trailing_stop(self) -> bool:
        return bool(self.get("risk_management.use_trailing_stop", True))

    @property
    def breakeven_trigger_r(self) -> float:
        return float(self.get("risk_management.breakeven_trigger_r", 1.0))

    @property
    def trail_step_atr(self) -> float:
        return float(self.get("risk_management.trail_step_atr", 1.0))

    @property
    def max_capital_per_trade_percent(self) -> float:
        return float(self.get("risk_management.max_capital_per_trade_percent", 30.0))

    # Market
    @property
    def market_name(self) -> str:
        return str(self.get("market.name", "NSE"))

    @property
    def timezone(self) -> str:
        return str(self.get("market.timezone", "Asia/Kolkata"))

    @property
    def session_open(self) -> str:
        return str(self.get("market.session_open", "09:15"))

    @property
    def entry_start(self) -> str:
        return str(self.get("market.entry_start", "09:30"))

    @property
    def entry_cutoff(self) -> str:
        return str(self.get("market.entry_cutoff", "11:30"))

    @property
    def square_off_time(self) -> str:
        return str(self.get("market.square_off_time", "15:15"))

    @property
    def session_close(self) -> str:
        return str(self.get("market.session_close", "15:30"))

    # Strategy
    @property
    def orb_window_minutes(self) -> int:
        return int(self.get("strategy.orb_window_minutes", 15))

    @property
    def timeframe(self) -> str:
        return str(self.get("strategy.timeframe", "5m"))

    @property
    def ema_fast(self) -> int:
        return int(self.get("strategy.ema_fast", 9))

    @property
    def ema_slow(self) -> int:
        return int(self.get("strategy.ema_slow", 21))

    @property
    def rsi_period(self) -> int:
        return int(self.get("strategy.rsi_period", 14))

    @property
    def rsi_min(self) -> float:
        return float(self.get("strategy.rsi_min", 52.0))

    @property
    def rsi_max(self) -> float:
        return float(self.get("strategy.rsi_max", 75.0))

    @property
    def volume_surge_multiplier(self) -> float:
        return float(self.get("strategy.volume_surge_multiplier", 1.3))

    @property
    def atr_period(self) -> int:
        return int(self.get("strategy.atr_period", 14))

    @property
    def atr_sl_multiplier(self) -> float:
        return float(self.get("strategy.atr_sl_multiplier", 1.5))

    # Execution
    @property
    def execution_mode(self) -> str:
        return str(self.get("execution.mode", "paper"))

    @property
    def slippage_percent(self) -> float:
        return float(self.get("execution.slippage_percent", 0.03))

    @property
    def commission_percent(self) -> float:
        return float(self.get("execution.commission_percent", 0.03))

    @property
    def symbols(self) -> list:
        return list(self.get("symbols", ["RELIANCE.NS", "TCS.NS", "INFY.NS"]))
