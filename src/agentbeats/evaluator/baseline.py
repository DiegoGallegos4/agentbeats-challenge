"""Baseline evaluator implementation covering Accuracy + Brier metrics."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Type, TypeVar

from pydantic import BaseModel

from ..config import EvaluatorConfig
from ..models import EventSpec, PredictionRecord, ResolutionRecord
from .metrics import (
    accuracy as metric_accuracy,
    brier_score,
    calibration_bins,
    els_information_ratio,
    kelly_metrics,
)

T_Model = TypeVar("T_Model", bound=BaseModel)


@dataclass
class Prediction:
    event_id: str
    probability: float
    outcome: int
    market_probability: Optional[float]
    model: Optional[str]
    prediction_timestamp: Optional[str]


class BaselineEvaluator:
    """Computes finance benchmark metrics (Accuracy/Brier + Phase 2 metrics)."""

    def __init__(self, config: EvaluatorConfig):
        self.config = config
        self.run_log_dir = config.run_log_dir
        self.run_log_dir.mkdir(parents=True, exist_ok=True)

    def _load_jsonl(self, path: Path, model: Type[T_Model]) -> Iterable[T_Model]:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                yield model.model_validate_json(line)

    def _merge(
        self,
        predictions: Iterable[PredictionRecord],
        resolutions: Dict[str, int],
        events: Dict[str, EventSpec],
    ) -> List[Prediction]:
        merged: List[Prediction] = []
        for entry in predictions:
            event_id = entry.id
            if event_id not in resolutions:
                continue
            event = events.get(event_id)
            market_probability = event.baseline_probability if event else None
            metadata = entry.metadata
            timestamp = None
            model_name = None
            if metadata:
                model_name = metadata.model
                if metadata.timestamp:
                    timestamp = metadata.timestamp.isoformat()
            merged.append(
                Prediction(
                    event_id=event_id,
                    probability=float(entry.prediction.probability),
                    outcome=int(resolutions[event_id]),
                    market_probability=market_probability,
                    model=model_name,
                    prediction_timestamp=timestamp,
                )
            )
        return merged

    def _serialize_rows(self, rows: List[Prediction]) -> List[Dict[str, Any]]:
        return [
            {
                "event_id": row.event_id,
                "probability": row.probability,
                "outcome": row.outcome,
                "market_probability": row.market_probability,
                "model": row.model,
                "timestamp": row.prediction_timestamp,
            }
            for row in rows
        ]

    def _persist_run(
        self,
        predictions_path: Path,
        resolutions_path: Path,
        events_path: Optional[Path],
        metrics: Dict[str, Any],
        rows: List[Prediction],
    ) -> None:
        """Write metrics + per-event records for reproducibility/debugging."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        run_dir = self.run_log_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        with (run_dir / "metrics.json").open("w", encoding="utf-8") as handle:
            json.dump(metrics, handle, indent=2)
        records_path = run_dir / "records.jsonl"
        with records_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(
                    json.dumps(
                        {
                            "event_id": row.event_id,
                            "probability": row.probability,
                            "outcome": row.outcome,
                            "market_probability": row.market_probability,
                            "model": row.model,
                            "timestamp": row.prediction_timestamp,
                        }
                    )
                )
                handle.write("\n")
        metadata = {
            "predictions_path": str(predictions_path),
            "resolutions_path": str(resolutions_path),
            "events_path": str(events_path) if events_path else None,
            "records_path": str(records_path),
        }
        with (run_dir / "inputs.json").open("w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2)

    def evaluate(
        self,
        predictions_path: Path,
        resolutions_path: Path,
        events_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        predictions = list(self._load_jsonl(predictions_path, PredictionRecord))

        resolution_rows = {
            row.id: row.outcome
            for row in self._load_jsonl(resolutions_path, ResolutionRecord)
        }
        # ResolutionRecord = ground-truth outcome fetched from Polymarket/EDGAR after the event settles.
        events_map: Dict[str, EventSpec] = {}
        if events_path and events_path.exists():
            events = list(self._load_jsonl(events_path, EventSpec))
            events_map = {event.id: event for event in events}

        merged = self._merge(predictions, resolution_rows, events_map)
        serialized = self._serialize_rows(merged)
        metrics: Dict[str, Any] = {
            "events": len(serialized),
            "accuracy": metric_accuracy(serialized),
            "brier": brier_score(serialized),
        }
        metrics.update(els_information_ratio(serialized))
        metrics.update(kelly_metrics(serialized))
        metrics["calibration"] = calibration_bins(serialized)
        self._persist_run(predictions_path, resolutions_path, events_path, metrics, merged)
        return metrics
