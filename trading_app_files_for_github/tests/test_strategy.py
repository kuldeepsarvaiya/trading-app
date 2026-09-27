"""Unit tests for ORB + VWAP Strategy."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.models import SignalType, Position, OrderAction
from core.config_loader import Config
from strategies.orb_vwap_strategy import ORBVWAPStrategy


@pytest.fixture
def strategy_config():
    config_dict = {
        "market": {
            "session_open": "09:15",
            "entry_start": "09:30",
            "entry_cutoff": "11:30",
            "square_off_time": "15:15",
            "session_close": "15:30",
        },
        "strategy": {
            "name": "ORB_VWAP_Momentum",
            "timeframe": "5m",
            "orb_window_minutes": 15,
            "ema_fast": 9,
            "ema_slow": 21,
            "rsi_period": 14,
            "rsi_min": 50.0,
            "rsi_max": 75.0,
            "volume_surge_multiplier": 1.2,
            "atr_period": 14,
            "atr_sl_multiplier": 1.5,
        },
        "risk_management": {
            "reward_to_risk_ratio": 2.0,
        },
    }
    return Config(config_dict)


def test_orb_vwap_strategy_exit_squareoff(strategy_config):
    strategy = ORBVWAPStrategy(strategy_config)
    pos = Position(
        position_id="p1",
        symbol="TEST.NS",
        side=OrderAction.BUY,
        quantity=10,
        entry_price=100.0,
        current_price=101.0,
        stop_loss=98.0,
        target=105.0,
        trailing_sl=98.0,
        entry_time=datetime(2026, 9, 25, 10, 0),
    )

    candle = pd.Series({"high": 102.0, "low": 100.5, "close": 101.5})
    # Time is 15:20 (after 15:15 square off)
    exit_sig = strategy.evaluate_exit(pos, candle, current_time_str="15:20")
    assert exit_sig is not None
    assert exit_sig.signal_type == SignalType.EXIT_SQUAREOFF


def test_orb_vwap_strategy_exit_target(strategy_config):
    strategy = ORBVWAPStrategy(strategy_config)
    pos = Position(
        position_id="p1",
        symbol="TEST.NS",
        side=OrderAction.BUY,
        quantity=10,
        entry_price=100.0,
        current_price=104.0,
        stop_loss=98.0,
        target=105.0,
        trailing_sl=98.0,
        entry_time=datetime(2026, 9, 25, 10, 0),
    )

    # High hits 105.5 (exceeds target of 105.0)
    candle = pd.Series({"high": 105.5, "low": 103.0, "close": 105.0})
    exit_sig = strategy.evaluate_exit(pos, candle, current_time_str="10:45")
    assert exit_sig is not None
    assert exit_sig.signal_type == SignalType.EXIT_TARGET
    assert exit_sig.price == 105.0


def test_orb_vwap_strategy_exit_stoploss(strategy_config):
    strategy = ORBVWAPStrategy(strategy_config)
    pos = Position(
        position_id="p1",
        symbol="TEST.NS",
        side=OrderAction.BUY,
        quantity=10,
        entry_price=100.0,
        current_price=99.0,
        stop_loss=98.0,
        target=105.0,
        trailing_sl=98.0,
        entry_time=datetime(2026, 9, 25, 10, 0),
    )

    # Low hits 97.5 (drops below trailing SL of 98.0)
    candle = pd.Series({"high": 99.5, "low": 97.5, "close": 98.0})
    exit_sig = strategy.evaluate_exit(pos, candle, current_time_str="10:30")
    assert exit_sig is not None
    assert exit_sig.signal_type in [SignalType.EXIT_SL, SignalType.EXIT_TRAILING_SL]
