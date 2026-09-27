"""Real-time financial news sentiment and catalyst analysis engine."""

import re
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import requests

try:
    import yfinance as yf
except ImportError:
    yf = None

from core.logger import setup_logger

logger = setup_logger("NewsSentiment")


class NewsSentimentAnalyzer:
    """
    Analyzes financial news headlines and identifies high-probability catalysts:
    - Order wins, contract awards, earnings beats, capacity expansion, regulatory approvals
    - Warns against fraud, SEBI notices, debt defaults, quarterly losses, or downgrades
    """

    BULLISH_KEYWORDS = {
        "order": 0.85,
        "contract": 0.85,
        "bagged": 0.80,
        "awarded": 0.80,
        "profit jumps": 0.90,
        "profit surges": 0.90,
        "profit rises": 0.75,
        "earnings beat": 0.90,
        "revenue up": 0.80,
        "approved": 0.75,
        "approval": 0.75,
        "patent": 0.80,
        "expansion": 0.70,
        "partnership": 0.70,
        "dividend": 0.65,
        "bonus": 0.75,
        "acquisition": 0.75,
        "commissioned": 0.75,
        "upgrade": 0.70,
        "outperform": 0.70,
        "record high": 0.80,
        "guidance hike": 0.85,
    }

    BEARISH_KEYWORDS = {
        "loss": -0.80,
        "penalty": -0.85,
        "fraud": -0.95,
        "investigation": -0.85,
        "sebi": -0.75,
        "probe": -0.80,
        "tax notice": -0.75,
        "resigns": -0.70,
        "resignation": -0.70,
        "downgrade": -0.75,
        "debt default": -0.95,
        "default": -0.85,
        "scam": -0.95,
        "raid": -0.90,
        "underperform": -0.70,
        "slumps": -0.75,
        "plunges": -0.75,
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self._cache: Dict[str, Tuple[datetime, Dict]] = {}

    def analyze_symbol_news(self, symbol: str) -> Dict[str, Any]:
        """
        Fetches latest news for the symbol and calculates sentiment & catalyst tag.
        Cached for 15 minutes to avoid rate limits.
        """
        # Check cache (15 mins)
        now = datetime.now()
        if symbol in self._cache:
            cache_time, cached_val = self._cache[symbol]
            if (now - cache_time).total_seconds() < 900:
                return cached_val

        clean_symbol = symbol.replace(".NS", "").replace(".BO", "")
        headlines = self._fetch_headlines(symbol, clean_symbol)

        if not headlines:
            result = {
                "symbol": symbol,
                "sentiment_score": 0.0,
                "sentiment_label": "NEUTRAL",
                "catalyst_tag": "⚪ Neutral (No News)",
                "catalyst_found": False,
                "has_negative_news": False,
                "headlines": [],
                "points": 10  # Baseline neutral score
            }
            self._cache[symbol] = (now, result)
            return result

        # Score headlines
        bullish_score = 0.0
        bearish_score = 0.0
        found_catalysts = []
        found_warnings = []

        for h in headlines:
            h_lower = h.lower()

            for kw, weight in self.BULLISH_KEYWORDS.items():
                if re.search(r'\b' + re.escape(kw) + r'\b', h_lower):
                    bullish_score = max(bullish_score, weight)
                    found_catalysts.append(kw.title())

            for kw, weight in self.BEARISH_KEYWORDS.items():
                if re.search(r'\b' + re.escape(kw) + r'\b', h_lower):
                    bearish_score = min(bearish_score, weight)
                    found_warnings.append(kw.title())

        # Net sentiment
        net_score = bullish_score + bearish_score
        net_score = max(-1.0, min(1.0, net_score))

        has_neg = len(found_warnings) > 0 or net_score < -0.3
        has_pos = len(found_catalysts) > 0 or net_score > 0.4

        if has_neg:
            sentiment_label = "BEARISH"
            catalyst_tag = f"🔴 Warning: {', '.join(set(found_warnings[:2]))}"
            points = 0  # Zero points for negative news!
        elif has_pos:
            sentiment_label = "BULLISH"
            catalyst_tag = f"🟢 Catalyst: {', '.join(set(found_catalysts[:2]))} (+{int(bullish_score*100)}%)"
            points = 20  # Full 20/20 points for positive news catalyst
        else:
            sentiment_label = "NEUTRAL"
            catalyst_tag = "⚪ Neutral Trend"
            points = 10  # 10/20 points for clean neutral chart

        result = {
            "symbol": symbol,
            "sentiment_score": round(net_score, 2),
            "sentiment_label": sentiment_label,
            "catalyst_tag": catalyst_tag,
            "catalyst_found": has_pos,
            "has_negative_news": has_neg,
            "headlines": headlines[:3],
            "points": points
        }

        self._cache[symbol] = (now, result)
        return result

    def _fetch_headlines(self, symbol: str, clean_symbol: str) -> List[str]:
        """Fetches news headlines from Yahoo Finance or Google News RSS."""
        headlines = []

        # 1. Try Yahoo Finance Ticker news
        if yf is not None:
            try:
                t = yf.Ticker(symbol)
                news_list = t.news
                if news_list:
                    for item in news_list:
                        # yfinance news can have 'title' or nested 'content'
                        title = item.get("title") or item.get("content", {}).get("title")
                        if title:
                            headlines.append(title)
            except Exception:
                pass

        # 2. Try Google News RSS for Indian stocks if needed
        if len(headlines) < 2:
            try:
                query = urllib.parse.quote_plus(f"{clean_symbol} stock share price NSE")
                url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
                resp = self.session.get(url, timeout=3)
                if resp.status_code == 200:
                    matches = re.findall(r'<title><!\[CDATA\[(.*?)\]\]></title>', resp.text)
                    if not matches:
                        matches = re.findall(r'<title>(.*?)</title>', resp.text)
                    for m in matches[1:5]:  # Skip first title (feed title)
                        if " - " in m:
                            m = m.rsplit(" - ", 1)[0]
                        headlines.append(m)
            except Exception:
                pass

        return headlines
