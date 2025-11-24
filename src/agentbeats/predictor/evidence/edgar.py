"""EDGAR evidence module using the EdgarEvidenceFetcher."""

from __future__ import annotations

from datetime import datetime
from typing import List, Sequence

from ...models import EventSpec, EvidenceItem
from ...tools import EdgarEvidenceFetcher
from .base import EvidencePayload


class EdgarEvidenceModule:
    """Pulls filing and XBRL fact evidence from the SEC companyfacts feed."""

    def __init__(self, fetcher: EdgarEvidenceFetcher, fact_tags: Sequence[str] | None = None):
        self.fetcher = fetcher
        self.fact_tags = list(fact_tags or ["us-gaap:EarningsPerShareDiluted", "us-gaap:Revenues"])

    def gather(self, event: EventSpec) -> EvidencePayload:
        evidence: List[EvidenceItem] = []
        messages: List[str] = []

        try:
            filings = self.fetcher.fetch_latest(event, forms=("8-K", "10-Q", "10-K"), limit=1)
            evidence.extend(filings)
        except Exception as exc:  # noqa: BLE001
            messages.append(f"EDGAR filings error: {exc}")

        facts_payload = []
        try:
            facts_payload = self.fetcher.fetch_facts(event, tags=self.fact_tags, forms=("10-Q", "10-K", "8-K"), limit=2)
        except Exception as exc:  # noqa: BLE001
            messages.append(f"EDGAR facts error: {exc}")

        for fact in facts_payload:
            snippet = f"{fact.get('tag')} {fact.get('value')} [{fact.get('period_start')}→{fact.get('period_end')}]"
            filed_at = fact.get("filed_at")
            filed_ts = None
            if filed_at:
                try:
                    filed_ts = datetime.fromisoformat(filed_at)
                except ValueError:
                    filed_ts = None
            evidence.append(
                EvidenceItem(
                    type="xbrl_fact",
                    source=fact.get("source_url", "https://data.sec.gov"),
                    snippet=snippet,
                    timestamp=filed_ts,
                )
            )

        # No numeric signal baked in yet; leave as 0.0 and rely on downstream logic.
        return EvidencePayload(evidence=evidence, signal=0.0, messages=messages)
