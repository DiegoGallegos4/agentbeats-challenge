"""News-based evidence module."""

from __future__ import annotations

from typing import List

from ...models import EventSpec, EvidenceItem
from ...tools import NewsEvidenceFetcher
from .base import EvidencePayload


class NewsEvidenceModule:
    """Uses NewsEvidenceFetcher to provide article citations + sentiment."""

    def __init__(self, fetcher: NewsEvidenceFetcher):
        self.fetcher = fetcher

    def gather(self, event: EventSpec) -> EvidencePayload:
        articles = self.fetcher.fetch_articles(event)
        evidence = [self.fetcher.to_evidence(article) for article in articles]
        sentiment = self.fetcher.aggregate_sentiment(articles)
        message = f"News: {len(evidence)} article(s)"
        return EvidencePayload(evidence=evidence, signal=sentiment, messages=[message])
