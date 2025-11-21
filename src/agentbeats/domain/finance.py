"""Finance-specific keyword/ticker utilities shared by ingestion and prediction."""

from __future__ import annotations

from typing import Dict, List

FinanceKeyword = Dict[str, str]

# Canonical mapping of keywords (lowercase) to Alpha Vantage symbols/meta.
FINANCE_KEYWORDS: Dict[str, FinanceKeyword] = {
    "tesla": {"symbol": "TSLA", "type": "equity", "aliases": ["tsla"]},
    "apple": {"symbol": "AAPL", "type": "equity", "aliases": ["aapl"]},
    "microsoft": {"symbol": "MSFT", "type": "equity", "aliases": ["msft"]},
    "amazon": {"symbol": "AMZN", "type": "equity", "aliases": ["amzn"]},
    "nvidia": {"symbol": "NVDA", "type": "equity", "aliases": ["nvda"]},
    "bitcoin": {"symbol": "BTCUSD", "type": "crypto", "aliases": ["btc", "btcusd"]},
    "btc": {"symbol": "BTCUSD", "type": "crypto", "aliases": ["bitcoin", "btcusd"]},
    "ethereum": {"symbol": "ETHUSD", "type": "crypto", "aliases": ["eth", "ethusd"]},
    "eth": {"symbol": "ETHUSD", "type": "crypto", "aliases": ["ethereum", "ethusd"]},
    "fed": {"symbol": "DGS10", "type": "macro", "aliases": ["federal reserve", "rate hike", "rate cut"]},
    "inflation": {"symbol": "CPIAUCSL", "type": "macro", "aliases": ["cpi", "consumer price"]},
    "recession": {"symbol": "GDPC1", "type": "macro", "aliases": ["gdp", "economic contraction"]},
    "tether": {"symbol": "USDTUSD", "type": "crypto", "aliases": ["usdt", "stablecoin"]},
}


def match_keywords(text: str, allowed: List[str] | None = None) -> List[str]:
    """Return finance keywords found in the provided text."""
    if not text:
        return []
    allowed_keywords = allowed or list(FINANCE_KEYWORDS.keys())
    lower = text.lower()
    matches: List[str] = []
    for keyword in allowed_keywords:
        entry = FINANCE_KEYWORDS.get(keyword)
        tokens = [keyword]
        if entry:
            tokens += entry.get("aliases", [])
        if any(token in lower for token in tokens if token):
            matches.append(keyword)
    return matches
