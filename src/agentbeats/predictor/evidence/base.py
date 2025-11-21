"""Interfaces for evidence modules used by the purple agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol

from ...models import EventSpec, EvidenceItem


@dataclass
class EvidencePayload:
    evidence: List[EvidenceItem]
    signal: float
    market_probability: Optional[float] = None


class EvidenceModule(Protocol):
    """Protocol for plug-and-play evidence modules."""

    def gather(self, event: EventSpec) -> EvidencePayload:
        """Return evidence, signal, and optional metadata (e.g., market probability)."""
