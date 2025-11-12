"""Shared configuration models for AgentBeats scaffolding."""

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class DataPaths(BaseModel):
    predictions: Path = Field(default=Path("data/fixtures/predictions"))
    resolutions: Path = Field(default=Path("data/fixtures/resolutions"))


class EvaluatorConfig(BaseModel):
    data_paths: DataPaths = Field(default_factory=DataPaths)
    metrics: List[str] = Field(default_factory=lambda: ["accuracy", "brier"])


class PredictorConfig(BaseModel):
    fixture_predictions: Path = Field(default=Path("data/fixtures/predictions/sample_predictions.jsonl"))
    fixture_events: Optional[Path] = Field(default=Path("data/fixtures/resolutions/sample_events.jsonl"))
    default_output: Path = Field(default=Path("data/fixtures/predictions/generated_predictions.jsonl"))
