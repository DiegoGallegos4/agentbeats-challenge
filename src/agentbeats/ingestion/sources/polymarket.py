"""Polymarket-backed ingestion source."""

from __future__ import annotations

import json
from typing import List, Optional

from ...models import EventSource, EventSpec
from ...domain.finance import match_keywords
from ...tools import PolymarketClient
from .base import IngestionSource


class PolymarketSource(IngestionSource):
    """Generates EventSpec entries from live Polymarket markets."""

    def __init__(
        self,
        limit: int = 20,
        include_active: bool = True,
        keywords: Optional[List[str]] = None,
        client: Optional[PolymarketClient] = None,
    ):
        self.name = "polymarket"
        self.limit = limit
        self.include_active = include_active
        self.keywords = [kw.lower() for kw in (keywords or [])]
        self.client = client or PolymarketClient()

    def _baseline_probability(self, market: dict) -> Optional[float]:
        prices = market.get("outcomePrices")
        if isinstance(prices, str):
            try:
                prices = json.loads(prices)
            except json.JSONDecodeError:
                prices = []
        if prices:
            try:
                return float(prices[0])
            except (TypeError, ValueError):
                return None
        return None

    def _to_event(self, market: dict) -> EventSpec:
        source = EventSource(
            type="Polymarket",
            market_id=str(market.get("id")),
            url=f"https://polymarket.com/market/{market.get('slug','')}",
            resolution_date=market.get("endDate"),
        )
        question = market.get("question", "")
        slug = market.get("slug", "")
        category = market.get("category", "")
        description = market.get("description", "")
        text = " ".join(filter(None, [question, slug, category, description]))
        tags = match_keywords(text, allowed=self.keywords or None)
        if not tags and market.get("category"):
            tags = [market.get("category")]
        return EventSpec(
            id=f"poly_{market.get('id')}",
            question=market.get("question", ""),
            domain=market.get("category") or "markets",
            resolution_date=market.get("endDate"),
            source=source,
            ground_truth_source="Polymarket",
            tags=tags,
            baseline_probability=self._baseline_probability(market),
        )

    def fetch_events(self) -> List[EventSpec]:
        markets = self.client.fetch_markets(limit=self.limit, active_only=self.include_active)
        events: List[EventSpec] = []
        for market in markets:
            event = self._to_event(market)
            if self.keywords and not event.tags:
                continue
            events.append(event)
        return events
