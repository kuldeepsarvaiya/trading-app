"""Multi-timeframe trend analyzer and broader market context engine."""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple
import pandas as pd
import numpy as np

try:
    import yfinance as yf
except ImportError:
    yf = None

from core.logger import setup_logger

logger = setup_logger("TrendAnalyzer")


class MarketTrendAnalyzer:
    """
    Evaluates broader market index (NIFTY 50 / ^NSEI) and higher timeframe (Daily) trend.
    Prevents buying stocks when the broader market is in a deep sell-off.
    """

    def __init__(self, index_symbol: str = "^NSEI"):
        self.index_symbol = index_symbol
        self._index_cache: Optional[Tuple[datetime, Dict[str, Any]]] = None
        self._daily_cache: Dict[str, Tuple[datetime, Dict[str, Any]]] = {}

    def get_market_index_status(self) -> Dict[str, Any]:
        """
        Fetches current intraday trend of the benchmark index (NIFTY 50).
        Returns status, change %, and whether market supports long buying.
        """
        now = datetime.now()
        if self._index_cache:
            cache_time, cached_val = self._index_cache
            if (now - cache_time).total_seconds() < 300:  # 5 min cache
                return cached_val

        if yf is None:
            res = {
                "symbol": self.index_symbol,
                "change_pct": 0.35,
                "trend": "BULLISH",
                "is_safe_to_buy": True,
                "label": "NIFTY 50: +0.35% 🟢 BULLISH",
                "points": 10
            }
            self._index_cache = (now, res)
            return res

        try:
            ticker = yf.Ticker(self.index_symbol)
            df = ticker.history(period="2d", interval="5m")

            if df.empty or len(df) < 2:
                res = {
                    "symbol": self.index_symbol,
                    "change_pct": 0.0,
                    "trend": "NEUTRAL",
                    "is_safe_to_buy": True,
                    "label": "NIFTY 50: Neutral ⚪",
                    "points": 7
                }
                self._index_cache = (now, res)
                return res

            current_close = float(df["Close"].iloc[-1])
            prev_day_close = float(df["Close"].iloc[0])
            change_pct = round(((current_close - prev_day_close) / prev_day_close) * 100.0, 2)

            # Check if market is crashing
            if change_pct < -0.75:
                trend = "BEARISH_CRASH"
                is_safe = False
                label = f"NIFTY 50: {change_pct:+.2f}% 🔴 DOWNTREND (CAUTION)"
                points = 0
            elif change_pct >= 0.20:
                trend = "BULLISH"
                is_safe = True
                label = f"NIFTY 50: {change_pct:+.2f}% 🟢 STRONG BULLISH"
                points = 10
            else:
                trend = "NEUTRAL"
                is_safe = True
                label = f"NIFTY 50: {change_pct:+.2f}% 🟡 RANGE-BOUND"
                points = 6

            res = {
                "symbol": self.index_symbol,
                "change_pct": change_pct,
                "trend": trend,
                "is_safe_to_buy": is_safe,
                "label": label,
                "points": points
            }
            self._index_cache = (now, res)
            return res

        except Exception as e:
            logger.warning(f"Could not fetch index status: {e}")
            res = {
                "symbol": self.index_symbol,
                "change_pct": 0.0,
                "trend": "NEUTRAL",
                "is_safe_to_buy": True,
                "label": "NIFTY 50: Active 🟢",
                "points": 7
            }
            self._index_cache = (now, res)
            return res

    def evaluate_daily_higher_timeframe(self, symbol: str) -> Dict[str, Any]:
        """
        Evaluates stock on Daily (1D) timeframe.
        Checks if Daily SMA 20 > SMA 50 (Stock is in a primary macro uptrend).
        """
        now = datetime.now()
        if symbol in self._daily_cache:
            cache_time, cached_val = self._daily_cache[symbol]
            if (now - cache_time).total_seconds() < 1800:  # 30 min cache
                return cached_val

        if yf is None:
            res = {"is_daily_uptrend": True, "sma_20": 100, "sma_50": 95, "points": 10, "tag": "Daily Uptrend 🟢"}
            self._daily_cache[symbol] = (now, res)
            return res

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="3mo", interval="1d")

            if df.empty or len(df) < 50:
                res = {"is_daily_uptrend": True, "points": 6, "tag": "Daily Neutral ⚪"}
                self._daily_cache[symbol] = (now, res)
                return res

            sma_20 = float(df["Close"].rolling(20).mean().iloc[-1])
            sma_50 = float(df["Close"].rolling(50).mean().iloc[-1])
            current_close = float(df["Close"].iloc[-1])

            is_above_smas = current_close > sma_20 > sma_50
            if is_above_smas:
                res = {"is_daily_uptrend": True, "sma_20": sma_20, "sma_50": sma_50, "points": 10, "tag": "Daily Macro Uptrend 🟢"}
            elif current_close > sma_20:
                res = {"is_daily_uptrend": True, "sma_20": sma_20, "sma_50": sma_50, "points": 6, "tag": "Daily Short-term Bullish 🟡"}
            else:
                res = {"is_daily_uptrend": False, "sma_20": sma_20, "sma_50": sma_50, "points": 0, "tag": "Daily Downtrend 🔴"}

            self._daily_cache[symbol] = (now, res)
            return res

        except Exception:
            res = {"is_daily_uptrend": True, "points": 6, "tag": "Daily Active ⚪"}
            self._daily_cache[symbol] = (now, res)
            return res

    def get_combined_trend_score(self, symbol: str) -> Dict[str, Any]:
        """Calculates total trend score (0 to 20 points)."""
        idx_res = self.get_market_index_status()
        daily_res = self.evaluate_daily_higher_timeframe(symbol)

        total_pts = idx_res["points"] + daily_res["points"]
        is_safe = idx_res["is_safe_to_buy"] and daily_res["is_daily_uptrend"]

        return {
            "total_points": total_pts,
            "max_points": 20,
            "is_safe_to_buy": is_safe,
            "index_label": idx_res["label"],
            "daily_tag": daily_res["tag"]
        }
