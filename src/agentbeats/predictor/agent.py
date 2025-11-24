"""Stub implementation of the purple (predictor) agent."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Type, TypeVar
import random

from pydantic import BaseModel

from ..config import PredictorConfig
from ..domain.finance import FINANCE_KEYWORDS
from ..models import (
    EventSpec,
    EvidenceItem,
    PredictionMetadata,
    PredictionPayload,
    PredictionRecord,
)
from ..tools import AlphaVantageClient, EdgarEvidenceFetcher, NewsEvidenceFetcher
from .evidence.alpha import AlphaVantageEvidenceModule
from .evidence.base import EvidencePayload
from .evidence.edgar import EdgarEvidenceModule
from .evidence.news import NewsEvidenceModule

T_Model = TypeVar("T_Model", bound=BaseModel)


LogFn = Callable[[str, str], None]


class PurpleAgent:
    """Fixture-driven predictor that emits schema-compliant JSONL outputs."""

    def __init__(
        self,
        config: PredictorConfig,
        seed: int = 42,
        news_fetcher: NewsEvidenceFetcher | None = None,
    ):
        self.config = config
        self._rng = random.Random(seed)
        self.news_fetcher = news_fetcher or NewsEvidenceFetcher(self.config.news_fixtures)
        self.alpha_client = (
            AlphaVantageClient(api_key=self.config.alpha_vantage_api_key)
            if self.config.alpha_vantage_api_key
            else None
        )
        self.edgar_fetcher = EdgarEvidenceFetcher()
        self.evidence_modules = self._build_evidence_modules()

    def _build_evidence_modules(self):
        modules = [NewsEvidenceModule(self.news_fetcher)]
        if self.alpha_client and self.alpha_client.is_configured():
            modules.append(
                AlphaVantageEvidenceModule(
                    self.alpha_client,
                    {k: (v["symbol"], v["type"]) for k, v in FINANCE_KEYWORDS.items()},
                )
            )
        modules.append(EdgarEvidenceModule(self.edgar_fetcher))
        return modules

    def _load_jsonl(self, path: Path, model: Type[T_Model]) -> Iterable[T_Model]:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                yield model.model_validate_json(line)

    def ingest_events(self, events_path: Optional[Path] = None) -> List[EventSpec]:
        candidates = [
            events_path,
            self.config.events_snapshot,
            self.config.fallback_events,
        ]
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return list(self._load_jsonl(candidate, EventSpec))
        raise FileNotFoundError("No event snapshot available. Run `agentbeats ingest-events` first.")

    def gather_evidence(self, event: EventSpec) -> tuple[List[EvidenceItem], float, Optional[float], List[str]]:
        evidence: List[EvidenceItem] = []
        sentiment = 0.0
        market_probability: Optional[float] = event.baseline_probability
        logs: List[str] = []
        for module in self.evidence_modules:
            payload: EvidencePayload = module.gather(event)
            evidence.extend(payload.evidence)
            sentiment += payload.signal
            if payload.market_probability is not None:
                market_probability = payload.market_probability
            logs.append(
                f"{module.__class__.__name__}: {len(payload.evidence)} evidence item(s), signal {payload.signal:+.2f}"
            )
            if payload.messages:
                logs.extend([f"   {msg}" for msg in payload.messages])
        return evidence, sentiment, market_probability, logs

    def analyze_event(self, event: EventSpec, sentiment: float, evidence: List[EvidenceItem]) -> str:
        if not evidence:
            return f"No fresh evidence for {event.question}; defaulting to prior."
        polarity = "supportive" if sentiment >= 0 else "headwind"
        return (
            f"{polarity.title()} news flow ({sentiment:+.2f}) "
            f"based on {len(evidence)} article(s) covering {', '.join(event.tags or ['general trends'])}."
        )

    def predict(
        self,
        events: List[EventSpec],
        as_of: Optional[datetime] = None,
        log: Optional[LogFn] = None,
    ) -> List[PredictionRecord]:
        timestamp = as_of or datetime.now(timezone.utc)
        predictions: List[PredictionRecord] = []
        for idx, event in enumerate(events):
            if log:
                log(f"• [{event.id}] {event.question}", "yellow")
            evidence, sentiment, market_prob, evidence_logs = self.gather_evidence(event)
            if log:
                for entry in evidence_logs:
                    log(f"   - {entry}", "cyan")
            base_prob = self._rng.uniform(0.2, 0.8)
            probability = round(min(max(base_prob + sentiment * 0.1, 0.05), 0.95), 2)
            if market_prob is not None:
                probability = round((probability + market_prob) / 2, 2)
            analysis = self.analyze_event(event, sentiment, evidence)
            predictions.append(
                PredictionRecord(
                    id=event.id,
                    prediction=PredictionPayload(
                        probability=probability,
                        rationale=evidence,
                        analysis=analysis,
                    ),
                    metadata=PredictionMetadata(
                        model="purple_stub",
                        timestamp=timestamp,
                        version="0.1.0",
                        predictor_id="purple_stub_v0",
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
        as_of: Optional[datetime] = None,
        log: Optional[LogFn] = None,
    ) -> Path:
        def log_step(message: str, color: str = "cyan") -> None:
            if log:
                log(message, color)

        log_step("📥 Loading events...", "cyan")
        events = self.ingest_events(events_path)
        log_step(f"   → Loaded {len(events)} events", "cyan")
        log_step("🧠 Generating predictions...", "cyan")
        predictions = self.predict(events, as_of=as_of, log=log_step)
        log_step("   → Predictions computed", "cyan")
        target = output_path or self.config.default_output
        log_step(f"💾 Writing output to {target}", "cyan")
        result = self.write_predictions(predictions, target)
        log_step("✅ Done", "green")
        return result
