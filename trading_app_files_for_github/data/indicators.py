"""Vectorized technical indicators tailored for intraday trading."""

import pandas as pd
import numpy as np
from typing import Tuple, Optional


def calculate_intraday_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Computes intraday Volume Weighted Average Price (VWAP).
    Resets at each new trading day session.
    Expects df to have: 'high', 'low', 'close', 'volume', and DatetimeIndex.
    """
    if df.empty or "volume" not in df.columns:
        return pd.Series(dtype=float)

    # Typical price
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    price_volume = typical_price * df["volume"]

    # If index is DatetimeIndex, group by date to reset daily
    if isinstance(df.index, pd.DatetimeIndex):
        dates = df.index.date
        cum_pv = price_volume.groupby(dates).cumsum()
        cum_vol = df["volume"].groupby(dates).cumsum()
    else:
        cum_pv = price_volume.cumsum()
        cum_vol = df["volume"].cumsum()

    # Avoid zero division
    vwap = cum_pv / cum_vol.replace(0, np.nan)
    return vwap.ffill()


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calculates Exponential Moving Average."""
    if series.empty or len(series) < period:
        return pd.Series(index=series.index, dtype=float)
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculates Relative Strength Index (RSI) using Wilder's smoothing."""
    if series.empty or len(series) <= period:
        return pd.Series(np.nan, index=series.index, dtype=float)

    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculates Average True Range (ATR).
    Expects 'high', 'low', 'close' columns.
    """
    if df.empty or len(df) < period:
        return pd.Series(np.nan, index=df.index, dtype=float)

    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    return atr.bfill()


def calculate_volume_ma(volume: pd.Series, period: int = 20) -> pd.Series:
    """Calculates Simple Moving Average of Volume."""
    if volume.empty:
        return pd.Series(dtype=float)
    return volume.rolling(window=period, min_periods=1).mean()


def calculate_opening_range(
    df: pd.DataFrame,
    start_time_str: str = "09:15",
    end_time_str: str = "09:30"
) -> Tuple[Optional[float], Optional[float]]:
    """
    Identifies the Opening Range High and Low for the current trading day.
    df must have DatetimeIndex in local market timezone.
    Returns: (or_high, or_low)
    """
    if df.empty or not isinstance(df.index, pd.DatetimeIndex):
        return None, None

    # Get today's or latest date from the data
    latest_date = df.index[-1].date()
    today_df = df[df.index.date == latest_date]

    if today_df.empty:
        return None, None

    # Filter between start_time and end_time
    try:
        or_df = today_df.between_time(start_time_str, end_time_str, inclusive="both")
    except Exception:
        # Fallback if between_time has issue
        or_df = today_df.iloc[:3]  # First 3 candles if 5-min bars

    if or_df.empty:
        return None, None

    or_high = float(or_df["high"].max())
    or_low = float(or_df["low"].min())
    return or_high, or_low


def enrich_intraday_data(
    df: pd.DataFrame,
    ema_fast_period: int = 9,
    ema_slow_period: int = 21,
    rsi_period: int = 14,
    atr_period: int = 14,
    vol_period: int = 20
) -> pd.DataFrame:
    """
    Enriches a raw OHLCV DataFrame with all intraday strategy indicators.
    Normalizes column names to lowercase.
    """
    if df.empty:
        return df

    data = df.copy()
    data.columns = [col.lower() for col in data.columns]

    data["vwap"] = calculate_intraday_vwap(data)
    data["ema_fast"] = calculate_ema(data["close"], ema_fast_period)
    data["ema_slow"] = calculate_ema(data["close"], ema_slow_period)
    data["rsi"] = calculate_rsi(data["close"], rsi_period)
    data["atr"] = calculate_atr(data, atr_period)
    data["vol_ma"] = calculate_volume_ma(data["volume"], vol_period)
    data["vol_surge"] = data["volume"] / data["vol_ma"].replace(0, np.nan)

    return data
