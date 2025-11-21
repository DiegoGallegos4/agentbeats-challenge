"""Alpha Vantage-based evidence module."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ...models import EventSpec, EvidenceItem
from ...tools import AlphaVantageClient
from .base import EvidencePayload


class AlphaVantageEvidenceModule:
    """Fetches simple price momentum signals via Alpha Vantage."""

    def __init__(self, client: AlphaVantageClient, symbol_map: dict[str, tuple[str, str]]):
        self.client = client
        self.symbol_map = symbol_map

    def _symbol_for_event(self, event: EventSpec) -> str | None:
        tags = [tag.lower() for tag in (event.tags or [])]
        question = event.question.lower()
        for keyword, (symbol, _data_type) in self.symbol_map.items():
            if keyword in tags or keyword in question:
                return symbol
        return None

    def gather(self, event: EventSpec) -> EvidencePayload:
        if not self.client or not self.client.is_configured():
            return EvidencePayload(evidence=[], signal=0.0)
        symbol = self._symbol_for_event(event)
        if not symbol:
            return EvidencePayload(evidence=[], signal=0.0)
        try:
            series = self.client.fetch_time_series(symbol)
            key = "Time Series (Daily)"
            points = series.get(key, {})
            ordered_dates = sorted(points.keys(), reverse=True)
            closes = [float(points[date]["4. close"]) for date in ordered_dates[:5]]
            if len(closes) < 2:
                return EvidencePayload(evidence=[], signal=0.0)
            latest = closes[0]
            avg = sum(closes[1:]) / (len(closes) - 1)
            delta = (latest - avg) / avg if avg else 0.0
            evidence = EvidenceItem(
                type="alpha_vantage",
                source="Alpha Vantage",
                snippet=f"{symbol} close {latest:.2f} ({delta:+.2%} vs 4-day avg)",
                timestamp=datetime.now(timezone.utc),
            )
            return EvidencePayload(evidence=[evidence], signal=delta)
        except Exception:
            return EvidencePayload(evidence=[], signal=0.0)
