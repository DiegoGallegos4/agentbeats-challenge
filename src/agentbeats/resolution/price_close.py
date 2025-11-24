"""Resolve price-close style questions using Alpha Vantage time series."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models import EventSpec
from ..tools import AlphaVantageClient

_PRICE_PATTERN = re.compile(r"close above \$([0-9]+(?:\.[0-9]+)?) on (\d{4}-\d{2}-\d{2})", re.IGNORECASE)


class PriceCloseResolver:
    """Resolves events phrased as 'Will TICKER close above $X on YYYY-MM-DD?'."""

    def __init__(self, client: AlphaVantageClient):
        self.client = client

    def _extract(self, question: str) -> Optional[tuple[float, str]]:
        match = _PRICE_PATTERN.search(question)
        if not match:
            return None
        target = float(match.group(1))
        date_str = match.group(2)
        return target, date_str

    def _get_close(self, symbol: str, date_str: str) -> Optional[float]:
        """Fetch close price for symbol on or before date_str (YYYY-MM-DD)."""
        series = self.client.fetch_time_series(symbol)
        key = "Time Series (Daily)"
        points: Dict[str, Any] = series.get(key, {})
        if not points:
            return None
        target_date = datetime.fromisoformat(date_str)
        # Try target date, then walk back up to 5 days (skip weekends/holidays)
        for delta in range(0, 6):
            check_date = target_date - timedelta(days=delta)
            key_str = check_date.strftime("%Y-%m-%d")
            if key_str in points:
                try:
                    return float(points[key_str]["4. close"])
                except (KeyError, TypeError, ValueError):
                    return None
        return None

    def resolve(self, events: List[EventSpec]) -> List[Dict[str, Any]]:
        resolutions: List[Dict[str, Any]] = []
        for event in events:
            extracted = self._extract(event.question)
            if not extracted:
                continue
            target, date_str = extracted
            symbol = event.tags[0].upper() if event.tags else event.source.market_id if event.source else None
            if not symbol:
                continue
            try:
                close_price = self._get_close(symbol, date_str)
            except Exception:
                close_price = None
            outcome = None
            if close_price is not None:
                outcome = 1 if close_price > target else 0
            resolutions.append(
                {
                    "id": event.id,
                    "outcome": outcome if outcome is not None else 0,
                    "verified_value": close_price,
                    "verified_source": "alpha_vantage" if close_price is not None else "alpha_vantage_failed",
                    "resolved_at": datetime.now(timezone.utc).isoformat(),
                    "debug": {
                        "target_price": target,
                        "target_date": date_str,
                        "symbol": symbol,
                    },
                }
            )
        return resolutions
