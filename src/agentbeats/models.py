"""Shared Pydantic data models for FutureBench-Finance artifacts."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class EvidenceItem(BaseModel):
    """Minimal representation of supporting evidence for a prediction."""

    model_config = ConfigDict(extra="ignore")

    type: str
    source: str
    snippet: Optional[str] = None
    timestamp: Optional[datetime] = None


class PredictionPayload(BaseModel):
    """Probability payload emitted by the purple agent."""

    model_config = ConfigDict(extra="ignore")

    probability: float = Field(ge=0.0, le=1.0)
    rationale: Optional[list[EvidenceItem]] = None


class PredictionMetadata(BaseModel):
    """Metadata describing the predictor instance."""

    model_config = ConfigDict(extra="ignore")

    model: str
    timestamp: datetime
    version: Optional[str] = None


class PredictionRecord(BaseModel):
    """Top-level JSONL entry produced by the purple agent."""

    model_config = ConfigDict(extra="ignore")

    id: str
    prediction: PredictionPayload
    metadata: Optional[PredictionMetadata] = None


class EventSpec(BaseModel):
    """Input event description consumed by the purple agent."""

    model_config = ConfigDict(extra="ignore")

    id: str
    question: str
    domain: Optional[str] = None
    resolution_date: Optional[datetime] = None


class ResolutionRecord(BaseModel):
    """Ground-truth resolution entries for the evaluator."""

    model_config = ConfigDict(extra="ignore")

    id: str
    outcome: int = Field(ge=0, le=1)
    verified_value: Optional[float] = None
    verified_source: Optional[str] = None
