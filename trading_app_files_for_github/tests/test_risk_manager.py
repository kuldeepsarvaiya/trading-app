"""Unit tests for Risk Management Engine."""

import pytest
from datetime import datetime
from core.models import Signal, SignalType, Position, OrderAction
from core.config_loader import Config
from risk.risk_manager import RiskManager


@pytest.fixture
def mock_config():
    config_dict = {
        "account": {"initial_capital": 100000.0, "currency": "INR"},
        "risk_management": {
            "risk_per_trade_percent": 1.0,
            "max_daily_loss_percent": 3.0,
            "max_open_positions": 2,
            "reward_to_risk_ratio": 2.0,
            "use_trailing_stop": True,
            "breakeven_trigger_r": 1.0,
            "trail_step_atr": 1.0,
            "max_capital_per_trade_percent": 30.0,
        },
    }
    return Config(config_dict)


def test_position_sizing(mock_config):
    rm = RiskManager(mock_config)
    # 1% risk on 100,000 = 1,000 INR
    # Entry: 200, SL: 190 -> SL distance = 10
    # Expected risk Qty: floor(1000 / 10) = 100
    # 30% capital cap on 100,000 = 30,000 -> 30,000 / 200 = 150
    # Final Qty: min(100, 150) = 100
    signal = Signal(
        symbol="TEST.NS",
        signal_type=SignalType.BUY,
        timestamp=datetime.now(),
        price=200.0,
        stop_loss=190.0,
        target=220.0,  # 1:2 R:R
    )
    approved, qty, reason = rm.validate_and_size_order(signal, open_positions_count=0)
    assert approved is True
    assert qty == 100

    # Test capital cap constraint: Entry 500 -> 30,000 / 500 = 60 (< 100)
    signal_cap = Signal(
        symbol="TEST.NS",
        signal_type=SignalType.BUY,
        timestamp=datetime.now(),
        price=500.0,
        stop_loss=490.0,
        target=520.0,
    )
    approved_cap, qty_cap, _ = rm.validate_and_size_order(signal_cap, open_positions_count=0)
    assert approved_cap is True
    assert qty_cap == 60


def test_circuit_breaker(mock_config):
    rm = RiskManager(mock_config)
    # Max daily loss is 3% of 100,000 = 3,000 INR
    rm.update_realized_pnl(-2000.0)
    assert rm.is_circuit_breaker_triggered is False

    rm.update_realized_pnl(-1500.0)  # Total -3,500
    assert rm.is_circuit_breaker_triggered is True

    # Any new trade must be rejected
    signal = Signal(
        symbol="TEST.NS",
        signal_type=SignalType.BUY,
        timestamp=datetime.now(),
        price=500.0,
        stop_loss=490.0,
        target=520.0,
    )
    approved, qty, reason = rm.validate_and_size_order(signal, open_positions_count=0)
    assert approved is False
    assert "Circuit Breaker" in reason


def test_max_open_positions_cap(mock_config):
    rm = RiskManager(mock_config)
    signal = Signal(
        symbol="TEST.NS",
        signal_type=SignalType.BUY,
        timestamp=datetime.now(),
        price=500.0,
        stop_loss=490.0,
        target=520.0,
    )
    # Allowed when open_positions_count = 1 (< 2)
    approved, _, _ = rm.validate_and_size_order(signal, open_positions_count=1)
    assert approved is True

    # Rejected when open_positions_count = 2 (>= 2)
    approved, _, reason = rm.validate_and_size_order(signal, open_positions_count=2)
    assert approved is False
    assert "Max open positions" in reason


def test_trailing_stop_ratchet(mock_config):
    rm = RiskManager(mock_config)
    pos = Position(
        position_id="pos_1",
        symbol="TEST.NS",
        side=OrderAction.BUY,
        quantity=50,
        entry_price=100.0,
        current_price=100.0,
        stop_loss=95.0,  # Risk dist = 5.0
        target=110.0,
        trailing_sl=95.0,
        entry_time=datetime.now(),
    )

    # 1. Price increases to 104 (less than 1R profit of 5) -> SL stays 95
    new_sl = rm.update_trailing_stop(pos, current_price=104.0, current_atr=2.0)
    assert new_sl == 95.0

    # 2. Price hits 105.5 (+1R profit reached) -> SL moves to Breakeven (~100.1)
    new_sl = rm.update_trailing_stop(pos, current_price=105.5, current_atr=2.0)
    assert new_sl >= 100.0

    # 3. Price drops back to 102 -> SL must NEVER drop below 100.0
    new_sl = rm.update_trailing_stop(pos, current_price=102.0, current_atr=2.0)
    assert new_sl >= 100.0
