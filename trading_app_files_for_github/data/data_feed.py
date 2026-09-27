"""Unified market data feed for historical intraday bars and live candle streaming."""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

try:
    import yfinance as yf
except ImportError:
    yf = None

from core.logger import setup_logger
from data.indicators import enrich_intraday_data

logger = setup_logger("DataFeed")


class DataFeed:
    """Handles intraday data retrieval from yfinance with local caching and offline simulation."""

    def __init__(self, cache_dir: str = "data_cache"):
        self.cache_dir = Path(__file__).resolve().parent.parent / cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_intraday_history(
        self,
        symbol: str,
        interval: str = "5m",
        days: int = 5,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Fetches historical intraday candles for a given symbol and interval.
        yfinance supports up to 60 days of 5m/15m data and 7 days of 1m data.
        """
        cache_file = self.cache_dir / f"{symbol}_{interval}_{days}d.parquet"

        if use_cache and cache_file.exists():
            # Check cache age (valid if updated within last 10 minutes)
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - mtime < timedelta(minutes=10):
                try:
                    df = pd.read_parquet(cache_file)
                    return enrich_intraday_data(df)
                except Exception:
                    pass

        logger.info(f"Downloading {interval} data for {symbol} (period={days}d)...")
        if yf is None:
            logger.warning("yfinance is not installed, returning mock intraday data")
            return self.generate_mock_intraday_data(symbol, days=days, interval_minutes=5)

        try:
            ticker = yf.Ticker(symbol)
            period_str = f"{days}d"
            df = ticker.history(period=period_str, interval=interval, auto_adjust=True)

            if df.empty:
                logger.warning(f"No data returned for {symbol}. Generating synthetic data.")
                return self.generate_mock_intraday_data(symbol, days=days, interval_minutes=5)

            # Normalize column names
            df.columns = [col.lower() for col in df.columns]
            if "stock splits" in df.columns:
                df = df.drop(columns=["stock splits"], errors="ignore")
            if "dividends" in df.columns:
                df = df.drop(columns=["dividends"], errors="ignore")

            # Save to cache
            try:
                df.to_parquet(cache_file)
            except Exception:
                pass

            return enrich_intraday_data(df)

        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol} from yfinance: {e}. Falling back to mock data.")
            return self.generate_mock_intraday_data(symbol, days=days, interval_minutes=5)

    def fetch_latest_candle(self, symbol: str, interval: str = "5m") -> Optional[pd.Series]:
        """Fetches the latest completed candle for real-time paper trading."""
        df = self.fetch_intraday_history(symbol, interval=interval, days=1, use_cache=False)
        if df.empty:
            return None
        return df.iloc[-1]

    def generate_mock_intraday_data(
        self,
        symbol: str,
        days: int = 5,
        interval_minutes: int = 5,
        base_price: float = 2500.0
    ) -> pd.DataFrame:
        """
        Generates realistic intraday candle sequence with opening range,
        breakout trends, volume spikes, and mean-reversion pullbacks for offline testing.
        """
        records = []
        now = datetime.now()
        start_date = (now - timedelta(days=days)).date()

        for d in range(days + 1):
            curr_date = start_date + timedelta(days=d)
            if curr_date.weekday() >= 5:  # Skip weekends
                continue

            # Trading hours: 09:15 to 15:30 (NSE)
            start_dt = datetime(curr_date.year, curr_date.month, curr_date.day, 9, 15)
            end_dt = datetime(curr_date.year, curr_date.month, curr_date.day, 15, 30)

            curr_dt = start_dt
            current_price = base_price * (1 + np.random.normal(0, 0.01))

            while curr_dt <= end_dt:
                volatility = current_price * 0.002
                price_change = np.random.normal(0.0002, volatility)
                
                # Introduce occasional breakout trends
                if 9 < curr_dt.hour < 11 and np.random.random() < 0.2:
                    price_change += volatility * 1.5

                o = current_price
                c = o + price_change
                h = max(o, c) + abs(np.random.normal(0, volatility * 0.5))
                l = min(o, c) - abs(np.random.normal(0, volatility * 0.5))
                base_vol = 50000
                vol = int(base_vol * np.random.uniform(0.5, 2.5))
                if price_change > volatility:
                    vol *= 2  # Volume surge on strong candle

                records.append({
                    "timestamp": curr_dt,
                    "open": round(o, 2),
                    "high": round(h, 2),
                    "low": round(l, 2),
                    "close": round(c, 2),
                    "volume": vol
                })

                current_price = c
                curr_dt += timedelta(minutes=interval_minutes)

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df.set_index("timestamp", inplace=True)
        return enrich_intraday_data(df)
