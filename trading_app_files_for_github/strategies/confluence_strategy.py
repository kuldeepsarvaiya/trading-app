"""360-Degree Confluence Strategy combining Technicals, Trend, and Real-Time News Catalysts."""

from datetime import datetime
from typing import Any, Dict, Optional
import pandas as pd

from core.models import Signal, SignalType, Position
from core.config_loader import Config
from core.logger import setup_logger
from strategies.base_strategy import BaseStrategy
from strategies.orb_vwap_strategy import ORBVWAPStrategy
from strategies.trend_analyzer import MarketTrendAnalyzer
from data.news_sentiment import NewsSentimentAnalyzer

logger = setup_logger("ConfluenceStrategy")


class ConfluenceStrategy(BaseStrategy):
    """
    360° Confluence Scoring Engine (0 to 100 points):
    1. Technical Breakout & VWAP (Max 35 points)
    2. Volume Explosion & RVOL (Max 25 points)
    3. Market & Higher Timeframe Trend (Max 20 points)
    4. News Catalysts & Sentiment (Max 20 points)
    
    Decision Rule: Trade ONLY executed when Composite Confluence Score >= 75!
    """

    def __init__(self, config: Config):
        super().__init__(name="360_Confluence_Momentum")
        self.config = config
        self.tech_strategy = ORBVWAPStrategy(config)
        self.trend_analyzer = MarketTrendAnalyzer()
        self.news_analyzer = NewsSentimentAnalyzer()
        self.min_confluence_score = 75  # High-probability quality threshold

    def evaluate_entry(self, symbol: str, df: pd.DataFrame) -> Optional[Signal]:
        """Evaluates entry with multi-factor confluence score."""
        # 1. Base Technical Signal Evaluation
        tech_signal = self.tech_strategy.evaluate_entry(symbol, df)
        if not tech_signal:
            return None

        # 2. Score Technical Breakdown (Max 35 pts)
        tech_pts = 0
        indicators = tech_signal.indicators
        if indicators.get("vol_surge", 0) >= 1.5:
            tech_pts += 15
        else:
            tech_pts += 10

        if indicators.get("ema_fast", 0) > indicators.get("ema_slow", 0):
            tech_pts += 10
        if 55.0 <= indicators.get("rsi", 0) <= 72.0:
            tech_pts += 10
        else:
            tech_pts += 5

        # 3. Score Volume Surge (Max 25 pts)
        vol_pts = 0
        vol_surge = indicators.get("vol_surge", 1.0)
        if vol_surge >= 2.0:
            vol_pts = 25
        elif vol_surge >= 1.5:
            vol_pts = 20
        elif vol_surge >= 1.2:
            vol_pts = 15
        else:
            vol_pts = 5

        # 4. Score Market Trend & Daily Chart (Max 20 pts)
        trend_res = self.trend_analyzer.get_combined_trend_score(symbol)
        trend_pts = trend_res.get("total_points", 12)

        # Immediate filter: If broader market is in severe crash, do NOT buy
        if not trend_res.get("is_safe_to_buy", True):
            logger.warning(f"🚫 {symbol} REJECTED: Broader Market ({trend_res.get('index_label')}) is in downtrend!")
            return None

        # 5. Score News Catalysts & Sentiment (Max 20 pts)
        news_res = self.news_analyzer.analyze_symbol_news(symbol)
        news_pts = news_res.get("points", 10)

        # Immediate filter: If stock has active negative warnings (SEBI, fraud, penalty, loss)
        if news_res.get("has_negative_news", False):
            logger.warning(f"🚫 {symbol} REJECTED: Negative news detected ({news_res.get('catalyst_tag')})!")
            return None

        # 6. Calculate Total Composite Confluence Score
        composite_score = tech_pts + vol_pts + trend_pts + news_pts

        logger.info(
            f"🎯 360° Confluence Evaluation for {symbol}: "
            f"Tech={tech_pts}/35, Vol={vol_pts}/25, Trend={trend_pts}/20, News={news_pts}/20 | "
            f"Total = {composite_score}/100"
        )

        if composite_score < self.min_confluence_score:
            logger.debug(f"Signal for {symbol} rejected: Score {composite_score} < {self.min_confluence_score}")
            return None

        # Attach confluence metadata to signal
        tech_signal.indicators["confluence"] = {
            "composite_score": composite_score,
            "tech_points": tech_pts,
            "vol_points": vol_pts,
            "trend_points": trend_pts,
            "news_points": news_pts,
            "catalyst_tag": news_res.get("catalyst_tag", "⚪ Neutral"),
            "trend_label": trend_res.get("index_label", "")
        }
        tech_signal.reason = (
            f"[Confluence Score: {composite_score}/100 ⭐] "
            f"{tech_signal.reason} | {news_res.get('catalyst_tag')}"
        )
        return tech_signal

    def evaluate_exit(self, position: Position, current_candle: pd.Series, current_time_str: str) -> Optional[Signal]:
        """Delegates exit conditions to base strategy (target, trailing SL, auto square-off)."""
        return self.tech_strategy.evaluate_exit(position, current_candle, current_time_str)
