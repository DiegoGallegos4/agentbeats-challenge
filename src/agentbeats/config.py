"""Shared configuration models for AgentBeats scaffolding."""

import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

from .domain.finance import FINANCE_KEYWORDS


class DataPaths(BaseModel):
    predictions: Path = Field(default=Path("data/generated/predictions/latest.jsonl"))
    resolutions: Path = Field(default=Path("data/generated/resolutions/latest.jsonl"))
    events: Path = Field(default=Path("data/generated/events/latest.jsonl"))


class EvaluatorConfig(BaseModel):
    data_paths: DataPaths = Field(default_factory=DataPaths)
    metrics: List[str] = Field(default_factory=lambda: ["accuracy", "brier"])
    run_log_dir: Path = Field(default=Path("data/generated/runs"))


class IngestionConfig(BaseModel):
    fixture_events: Path = Field(default=Path("data/fixtures/resolutions/sample_events.jsonl"))
    default_output: Path = Field(default=Path("data/generated/events/latest.jsonl"))
    source: str = Field(default="polymarket")
    polymarket_limit: int = Field(default=10)
    include_active: bool = Field(default=True)
    finance_keywords: List[str] = Field(default_factory=lambda: list(FINANCE_KEYWORDS.keys()))


class PredictorConfig(BaseModel):
    events_snapshot: Path = Field(default=Path("data/generated/events/latest.jsonl"))
    fallback_events: Path = Field(default=Path("data/fixtures/resolutions/sample_events.jsonl"))
    news_fixtures: Optional[Path] = Field(default=None)
    fixture_predictions: Path = Field(default=Path("data/fixtures/predictions/sample_predictions.jsonl"))
    default_output: Path = Field(default=Path("data/generated/predictions/latest.jsonl"))
    tool_log_dir: Path = Field(default=Path("data/generated/tool_logs"))
    alpha_vantage_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("ALPHAVANTAGE_API_KEY"))
    alpha_vantage_cache_dir: Path = Field(default=Path("data/generated/tool_cache/alpha_vantage"))
