"""Unit tests for technical indicators."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data.indicators import (
    calculate_intraday_vwap,
    calculate_ema,
    calculate_rsi,
    calculate_atr,
    calculate_volume_ma,
    calculate_opening_range,
    enrich_intraday_data,
)


@pytest.fixture
def sample_ohlcv():
    """Generates 1 day of 5-minute candles."""
    base_time = datetime(2026, 9, 25, 9, 15)
    records = []
    price = 1000.0

    for i in range(75):  # 75 5-minute candles in a 6.25 hr session
        t = base_time + timedelta(minutes=5 * i)
        high = price + 2.0
        low = price - 2.0
        close = price + 0.5
        vol = 10000 + i * 100
        records.append({
            "timestamp": t,
            "open": price,
            "high": high,
            "low": low,
            "close": close,
            "volume": vol
        })
        price = close

    df = pd.DataFrame(records).set_index("timestamp")
    return df


def test_calculate_intraday_vwap(sample_ohlcv):
    vwap = calculate_intraday_vwap(sample_ohlcv)
    assert not vwap.empty
    assert len(vwap) == len(sample_ohlcv)
    assert not vwap.isna().all()
    # VWAP should be close to price
    assert abs(vwap.iloc[-1] - sample_ohlcv["close"].iloc[-1]) < 50.0


def test_calculate_ema(sample_ohlcv):
    ema9 = calculate_ema(sample_ohlcv["close"], 9)
    assert len(ema9) == len(sample_ohlcv)
    assert not ema9.isna().any()


def test_calculate_rsi(sample_ohlcv):
    rsi = calculate_rsi(sample_ohlcv["close"], 14)
    assert len(rsi) == len(sample_ohlcv)
    # RSI values bounded between 0 and 100
    valid_rsi = rsi.dropna()
    assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()


def test_calculate_atr(sample_ohlcv):
    atr = calculate_atr(sample_ohlcv, 14)
    assert len(atr) == len(sample_ohlcv)
    assert (atr > 0).all()


def test_calculate_opening_range(sample_ohlcv):
    or_high, or_low = calculate_opening_range(sample_ohlcv, "09:15", "09:30")
    assert or_high is not None
    assert or_low is not None
    assert or_high >= or_low


def test_enrich_intraday_data(sample_ohlcv):
    enriched = enrich_intraday_data(sample_ohlcv)
    expected_cols = ["vwap", "ema_fast", "ema_slow", "rsi", "atr", "vol_ma", "vol_surge"]
    for col in expected_cols:
        assert col in enriched.columns
