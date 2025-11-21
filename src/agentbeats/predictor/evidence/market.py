"""Polymarket-based evidence module."""

from __future__ import annotations

import json
from typing import List, Optional

from ...models import EventSpec, EvidenceItem
from ...tools import PolymarketClient
from .base import EvidencePayload


class MarketEvidenceModule:
    """Provides baseline odds evidence from Polymarket markets."""

    def __init__(self, client: PolymarketClient):
        self.client = client

    def _fetch_probability(self, event: EventSpec) -> Optional[float]:
        if event.baseline_probability is not None:
            return event.baseline_probability
        if not event.source or not event.source.market_id:
            return None
        market = self.client.fetch_market(str(event.source.market_id))
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

    def gather(self, event: EventSpec) -> EvidencePayload:
        probability = self._fetch_probability(event)
        if probability is None:
            return EvidencePayload(evidence=[], signal=0.0, market_probability=None)
        evidence = []
        if event.source and event.source.url:
            evidence.append(
                EvidenceItem(
                    type="market_snapshot",
                    source=event.source.url,
                    snippet=f"Polymarket baseline {probability:.2f}",
                )
            )
        # Market evidence contributes towards sentiment (positive if odds are high).
        signal = probability - 0.5
        return EvidencePayload(evidence=evidence, signal=signal, market_probability=probability)
