"""Minimal evaluator implementation covering Accuracy + Brier metrics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Type, TypeVar

from pydantic import BaseModel

from ..config import EvaluatorConfig
from ..models import PredictionRecord, ResolutionRecord

T_Model = TypeVar("T_Model", bound=BaseModel)


@dataclass
class Prediction:
    event_id: str
    probability: float
    outcome: int


class EvaluatorMVP:
    """Barebones evaluator that computes Accuracy and Brier Score."""

    def __init__(self, config: EvaluatorConfig):
        self.config = config

    def _load_jsonl(self, path: Path, model: Type[T_Model]) -> Iterable[T_Model]:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                yield model.model_validate_json(line)

    def _merge(
        self, predictions: Iterable[PredictionRecord], resolutions: Dict[str, int]
    ) -> List[Prediction]:
        merged: List[Prediction] = []
        for entry in predictions:
            event_id = entry.id
            if event_id not in resolutions:
                continue
            merged.append(
                Prediction(
                    event_id=event_id,
                    probability=float(entry.prediction.probability),
                    outcome=int(resolutions[event_id]),
                )
            )
        return merged

    def _accuracy(self, rows: List[Prediction]) -> float:
        correct = sum(1 for row in rows if round(row.probability) == row.outcome)
        return correct / len(rows) if rows else 0.0

    def _brier(self, rows: List[Prediction]) -> float:
        if not rows:
            return 0.0
        return sum((row.probability - row.outcome) ** 2 for row in rows) / len(rows)

    def evaluate(
        self, predictions_path: Path, resolutions_path: Path
    ) -> Dict[str, float]:
        predictions = list(self._load_jsonl(predictions_path, PredictionRecord))
        resolution_rows = {
            row.id: row.outcome
            for row in self._load_jsonl(resolutions_path, ResolutionRecord)
        }
        merged = self._merge(predictions, resolution_rows)
        return {
            "events": len(merged),
            "accuracy": self._accuracy(merged),
            "brier": self._brier(merged),
        }
