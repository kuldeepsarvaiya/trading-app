"""Unit tests for 360° Confluence Strategy, News Sentiment, and Market Trend."""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from core.models import SignalType
from core.config_loader import Config
from data.news_sentiment import NewsSentimentAnalyzer
from strategies.trend_analyzer import MarketTrendAnalyzer
from strategies.confluence_strategy import ConfluenceStrategy


@pytest.fixture
def mock_config():
    config_dict = {
        "market": {
            "session_open": "09:15",
            "entry_start": "09:30",
            "entry_cutoff": "11:30",
            "square_off_time": "15:15",
            "session_close": "15:30",
        },
        "strategy": {
            "name": "360_Confluence_Momentum",
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


def test_news_sentiment_catalyst_detection():
    analyzer = NewsSentimentAnalyzer()

    # Synthetic positive headline
    test_headlines = ["Reliance bags massive ₹5,000 crore contract order for green energy"]
    analyzer._fetch_headlines = lambda sym, clean: test_headlines

    res = analyzer.analyze_symbol_news("RELIANCE.NS")
    assert res["sentiment_label"] == "BULLISH"
    assert res["catalyst_found"] is True
    assert res["has_negative_news"] is False
    assert res["points"] == 20
    assert "Order" in res["catalyst_tag"] or "Contract" in res["catalyst_tag"]


def test_news_sentiment_negative_warning():
    analyzer = NewsSentimentAnalyzer()

    # Synthetic negative headline
    test_headlines = ["SEBI issues penalty notice over accounting fraud investigation"]
    analyzer._fetch_headlines = lambda sym, clean: test_headlines

    res = analyzer.analyze_symbol_news("TEST.NS")
    assert res["sentiment_label"] == "BEARISH"
    assert res["has_negative_news"] is True
    assert res["points"] == 0


def test_trend_analyzer_market_index():
    analyzer = MarketTrendAnalyzer()
    res = analyzer.get_market_index_status()
    assert "trend" in res
    assert "points" in res
    assert "is_safe_to_buy" in res


def test_confluence_rejection_on_negative_news(mock_config):
    strategy = ConfluenceStrategy(mock_config)

    # Force negative news on symbol
    strategy.news_analyzer.analyze_symbol_news = lambda sym: {
        "points": 0,
        "has_negative_news": True,
        "catalyst_tag": "🔴 Warning: Fraud Notice",
        "sentiment_label": "BEARISH",
    }

    # Generate synthetic bullish candle dataframe
    df = pd.DataFrame([{
        "open": 100.0, "high": 105.0, "low": 99.0, "close": 104.0, "volume": 100000,
        "vwap": 101.0, "ema_fast": 103.0, "ema_slow": 101.5, "rsi": 62.0, "atr": 2.0, "vol_surge": 2.5
    }])
    df.index = [datetime(2026, 9, 25, 9, 45)]

    # Must reject trade due to negative news
    signal = strategy.evaluate_entry("TEST.NS", df)
    assert signal is None
