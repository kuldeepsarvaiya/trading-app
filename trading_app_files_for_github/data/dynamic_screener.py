"""Dynamic high-momentum and top-gainer intraday stock screener."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np

try:
    import yfinance as yf
except ImportError:
    yf = None

from core.logger import setup_logger
from data.data_feed import DataFeed

logger = setup_logger("DynamicScreener")


class DynamicMomentumScreener:
    """
    Scans liquid NSE momentum universe for high-probability 5% to 15% breakout runners.
    Evaluates Relative Volume (RVOL), Day High Breakouts, and VWAP dominance.
    """

    # High-beta, highly liquid NSE stocks known for strong 5% - 15% intraday momentum trends
    MOMENTUM_UNIVERSE = [
        "SUZLON.NS", "IREDA.NS", "IRFC.NS", "BEL.NS", "HAL.NS",
        "TRENT.NS", "ZOMATO.NS", "BHEL.NS", "COALINDIA.NS", "TATASTEEL.NS",
        "RELIANCE.NS", "TCS.NS", "INFY.NS", "SBIN.NS", "BHARTIARTL.NS",
        "AXISBANK.NS", "ITC.NS", "VEDL.NS", "IOC.NS", "ONGC.NS"
    ]

    def __init__(self, data_feed: Optional[DataFeed] = None):
        self.data_feed = data_feed or DataFeed()

    def scan_top_runners(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Scans momentum universe and returns top ranked stocks with high volume and breakout power.
        """
        candidates = []
        logger.info(f"🔥 Scanning {len(self.MOMENTUM_UNIVERSE)} High-Beta Momentum Stocks for 10%-15% Runners...")

        for sym in self.MOMENTUM_UNIVERSE:
            try:
                df = self.data_feed.fetch_intraday_history(sym, interval="5m", days=1, use_cache=True)
                if df.empty or len(df) < 5:
                    continue

                latest = df.iloc[-1]
                close = float(latest["close"])
                open_day = float(df["open"].iloc[0])
                day_high = float(df["high"].max())
                day_low = float(df["low"].min())
                vwap = float(latest.get("vwap", close))
                vol_surge = float(latest.get("vol_surge", 1.0))
                rsi = float(latest.get("rsi", 50.0))

                # Intraday Day Change %
                day_change_pct = round(((close - open_day) / open_day) * 100.0, 2)

                # Proximity to Day High (Within 0.5% of day high = Strong breakout momentum)
                dist_from_high_pct = round(((day_high - close) / day_high) * 100.0, 2)

                # Momentum Scoring Criteria:
                # 1. Price > VWAP (Institutional buying)
                # 2. Positive day change (>= +1.5%)
                # 3. High Volume Surge (>= 1.5x)
                # 4. Trading near Day High
                is_above_vwap = close > vwap
                is_near_high = dist_from_high_pct <= 0.8
                is_volume_strong = vol_surge >= 1.3
                is_healthy_rsi = 52.0 <= rsi <= 78.0

                momentum_score = 0
                if is_above_vwap: momentum_score += 30
                if day_change_pct >= 2.0: momentum_score += 25
                elif day_change_pct >= 1.0: momentum_score += 15
                if is_volume_strong: momentum_score += 25
                if is_near_high: momentum_score += 15
                if is_healthy_rsi: momentum_score += 5

                candidates.append({
                    "symbol": sym,
                    "ltp": close,
                    "day_change_pct": day_change_pct,
                    "day_high": day_high,
                    "vwap": vwap,
                    "vol_surge": vol_surge,
                    "rsi": rsi,
                    "dist_from_high_pct": dist_from_high_pct,
                    "momentum_score": momentum_score,
                    "is_runner_candidate": momentum_score >= 70
                })

            except Exception as e:
                logger.debug(f"Error scanning {sym}: {e}")

        # Sort by highest momentum score, then highest day change %
        candidates.sort(key=lambda x: (x["momentum_score"], x["day_change_pct"]), reverse=True)
        return candidates[:top_n]
