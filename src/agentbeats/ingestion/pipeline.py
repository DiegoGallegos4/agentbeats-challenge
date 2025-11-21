"""Simple ingestion pipeline that snapshots event specs for the purple agent."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, TypeVar

from pydantic import BaseModel

from ..config import IngestionConfig
from ..models import EventSpec
from .sources.base import IngestionSource
from .sources.polymarket import PolymarketSource

T_Model = TypeVar("T_Model", bound=BaseModel)


class EventIngestion:
    """Loads curated event specs and writes them to a snapshot file."""

    def __init__(self, config: IngestionConfig):
        self.config = config
        keywords = [kw.lower() for kw in config.finance_keywords]
        self.sources: dict[str, IngestionSource] = {
            "polymarket": PolymarketSource(
                limit=config.polymarket_limit,
                include_active=config.include_active,
                keywords=keywords,
            )
        }

    def _load_jsonl(self, path: Path, model: type[T_Model]) -> Iterable[T_Model]:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                yield model.model_validate_json(line)

    def load_events(self, path: Optional[Path] = None) -> List[EventSpec]:
        source_name = self.config.source
        if source_name in self.sources:
            return self.sources[source_name].fetch_events()
        source = path or self.config.fixture_events
        return list(self._load_jsonl(source, EventSpec))

    def write_snapshot(
        self,
        events: List[EventSpec],
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            for event in events:
                handle.write(event.model_dump_json())
                handle.write("\n")
        return output_path

    def run(self, output_path: Optional[Path] = None) -> Path:
        events = self.load_events()
        target = output_path or self.config.default_output
        return self.write_snapshot(events, target)
