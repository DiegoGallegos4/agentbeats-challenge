"""Stub implementation of the purple (predictor) agent."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Type, TypeVar
import random

from pydantic import BaseModel

from ..config import PredictorConfig
from ..models import (
    EventSpec,
    PredictionMetadata,
    PredictionPayload,
    PredictionRecord,
)

T_Model = TypeVar("T_Model", bound=BaseModel)


class PurpleAgent:
    """Fixture-driven predictor that emits schema-compliant JSONL outputs."""

    def __init__(self, config: PredictorConfig, seed: int = 42):
        self.config = config
        self._rng = random.Random(seed)

    def _load_jsonl(self, path: Path, model: Type[T_Model]) -> Iterable[T_Model]:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                yield model.model_validate_json(line)

    def ingest_events(self, events_path: Optional[Path] = None) -> List[EventSpec]:
        path = events_path or self.config.fixture_events
        if not path:
            msg = "Event path must be provided via CLI or config."
            raise ValueError(msg)
        return list(self._load_jsonl(path, EventSpec))

    def predict(self, events: List[EventSpec]) -> List[PredictionRecord]:
        now = datetime.now(timezone.utc)
        predictions: List[PredictionRecord] = []
        for idx, event in enumerate(events):
            probability = round(self._rng.uniform(0.2, 0.8), 2)
            predictions.append(
                PredictionRecord(
                    id=event.id,
                    prediction=PredictionPayload(probability=probability),
                    metadata=PredictionMetadata(
                        model="purple_stub",
                        timestamp=now,
                        version="0.1.0",
                    ),
                )
            )
        return predictions

    def write_predictions(
        self, predictions: List[PredictionRecord], output_path: Path
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            for record in predictions:
                handle.write(record.model_dump_json())
                handle.write("\n")
        return output_path

    def run(
        self,
        events_path: Optional[Path] = None,
        output_path: Optional[Path] = None,
    ) -> Path:
        events = self.ingest_events(events_path)
        predictions = self.predict(events)
        target = output_path or self.config.default_output
        return self.write_predictions(predictions, target)
