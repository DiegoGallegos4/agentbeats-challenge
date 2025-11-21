"""Interfaces for ingestion sources feeding EventSpec snapshots."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ...models import EventSpec


class IngestionSource(ABC):
    """Abstract base class for ingestion sources (e.g., Polymarket, SEC)."""

    name: str

    @abstractmethod
    def fetch_events(self) -> List[EventSpec]:
        """Return the latest events as EventSpec objects."""
