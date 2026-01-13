"""Minimal evidence audit utilities (placeholder, citation-count based)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Type, TypeVar

import litellm
from pydantic import BaseModel

from .config import LLMConfig
from .models import PredictionRecord

T_Model = TypeVar("T_Model", bound=BaseModel)


@dataclass
class SimpleAuditRow:
    event_id: str
    citations_count: int
    citation_types: List[str]
    ec_score: float

    def to_json(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "citations_count": self.citations_count,
            "citation_types": self.citation_types,
            "ec_score": self.ec_score,
        }


class SimpleAuditor:
    """Lightweight audit that reports citation counts/types and a basic EC score."""

    def __init__(self, run_log_dir: Path):
        self.run_log_dir = run_log_dir
        self.run_log_dir.mkdir(parents=True, exist_ok=True)

    def _load_jsonl(self, path: Path, model: Type[T_Model]) -> Iterable[T_Model]:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                yield model.model_validate_json(line)

    def _audit_record(self, record: PredictionRecord) -> SimpleAuditRow:
        citations = list(record.prediction.rationale or [])
        citation_types = [c.type for c in citations if c.type]  # type: ignore[attr-defined]
        ec_score = 1.0 if citations else 0.0
        return SimpleAuditRow(
            event_id=record.id,
            citations_count=len(citations),
            citation_types=citation_types,
            ec_score=ec_score,
        )

    def _persist(self, rows: List[SimpleAuditRow], inputs: Dict[str, Optional[str]]) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        run_dir = self.run_log_dir / timestamp / "audits"
        run_dir.mkdir(parents=True, exist_ok=True)
        rows_path = run_dir / "evidence.jsonl"
        with rows_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row.to_json()))
                handle.write("\n")
        with (run_dir / "inputs.json").open("w", encoding="utf-8") as handle:
            json.dump(inputs, handle, indent=2)
        return run_dir

    def audit(self, predictions_path: Path) -> Dict[str, Any]:
        records = list(self._load_jsonl(predictions_path, PredictionRecord))
        rows = [self._audit_record(rec) for rec in records]
        avg_ec = sum(row.ec_score for row in rows) / len(rows) if rows else 0.0
        summary = {
            "events": len(rows),
            "avg_ec": round(avg_ec, 2),
            "with_citations": sum(1 for row in rows if row.citations_count > 0),
        }
        run_dir = self._persist(
            rows,
            {
                "predictions_path": str(predictions_path),
            },
        )
        return {
            "summary": summary,
            "run_log_dir": str(run_dir),
            "rows": rows,
        }


class LLMAuditor(SimpleAuditor):
    """LLM-backed audit that asks a local provider (e.g., Ollama via LiteLLM) to judge coverage."""

    def __init__(self, run_log_dir: Path, config: Optional[LLMConfig] = None):
        super().__init__(run_log_dir)
        self.config = config or LLMConfig()

    def _build_prompt(self, record: PredictionRecord) -> str:
        citations = list(record.prediction.rationale or [])
        lines = [f"Event ID: {record.id}", f"Citations ({len(citations)}):"]
        for idx, cit in enumerate(citations, start=1):
            lines.append(f"{idx}. type={getattr(cit, 'type', '')} source={getattr(cit, 'source', '')} snippet={getattr(cit, 'snippet', '')}")
        lines.append(
            "Return JSON only: {\"event_id\":\"...\",\"citations_count\":N,\"citation_types\":[...],\"ec_score\":0-1,\"notes\":\"short\"}"
        )
        return "\n".join(lines)

    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        # Suppress LiteLLM stdout noise (provider list, debug)
        litellm.set_verbose = False
        if hasattr(litellm, "suppress_debug_logs"):
            litellm.suppress_debug_logs = True  # type: ignore[attr-defined]

        completion = litellm.completion(
            model=self.config.model,
            messages=[
                {"role": "system", "content": "You are an evidence auditor. Only return JSON."},
                {"role": "user", "content": prompt},
            ],
            api_base=self.config.endpoint,
            temperature=self.config.temperature,
        )
        text = completion.choices[0].message["content"]  # type: ignore[index]
        try:
            return json.loads(text)
        except Exception:
            return {"raw": text}

    def _audit_record_llm(self, record: PredictionRecord) -> SimpleAuditRow:
        prompt = self._build_prompt(record)
        try:
            result = self._call_llm(prompt)
            ec_score = float(result.get("ec_score", 1.0 if record.prediction.rationale else 0.0))
            citations_count = int(result.get("citations_count", len(record.prediction.rationale or [])))
            citation_types = result.get("citation_types") or []
            if not isinstance(citation_types, list):
                citation_types = [str(citation_types)]
        except Exception as exc:  # noqa: BLE001
            ec_score = 1.0 if record.prediction.rationale else 0.0
            citations_count = len(record.prediction.rationale or [])
            citation_types = ["error"]
            result = {"error": str(exc)}

        return SimpleAuditRow(
            event_id=record.id,
            citations_count=citations_count,
            citation_types=citation_types,
            ec_score=ec_score,
        )

    def audit(self, predictions_path: Path) -> Dict[str, Any]:
        records = list(self._load_jsonl(predictions_path, PredictionRecord))
        rows: List[SimpleAuditRow] = []
        call_logs: List[Dict[str, Any]] = []
        for rec in records:
            row = self._audit_record_llm(rec)
            rows.append(row)
            call_logs.append({"event_id": rec.id, "citation_count": len(rec.prediction.rationale or []), "ec_score": row.ec_score})
        avg_ec = sum(row.ec_score for row in rows) / len(rows) if rows else 0.0
        summary = {
            "events": len(rows),
            "avg_ec": round(avg_ec, 2),
            "with_citations": sum(1 for row in rows if row.citations_count > 0),
        }
        run_dir = self._persist(
            rows,
            {
                "predictions_path": str(predictions_path),
                "llm_provider": self.config.provider,
                "llm_model": self.config.model,
                "llm_endpoint": self.config.endpoint,
            },
        )
        # Write LLM call logs
        calls_path = Path(run_dir) / "llm_calls.jsonl"
        with calls_path.open("w", encoding="utf-8") as handle:
            for log in call_logs:
                handle.write(json.dumps(log))
                handle.write("\n")
        return {
            "summary": summary,
            "run_log_dir": str(run_dir),
            "rows": rows,
        }
