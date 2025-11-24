from datetime import datetime
from pathlib import Path
from typing import Optional

import typer


def parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError as exc:  # pragma: no cover - typer surfaces error
        raise typer.BadParameter("Timestamp must be ISO8601 (e.g. 2025-01-01T00:00:00Z).") from exc


def get_default_path(data_type: str) -> Path:
    """Return smart defaults for common data types with fixture fallback."""
    defaults = {
        "events": Path("data/generated/events/latest.jsonl"),
        "predictions": Path("data/generated/predictions/latest.jsonl"),
        "resolutions": Path("data/generated/resolutions/latest.jsonl"),
        "edgar": Path("data/generated/edgar/latest.jsonl"),
    }
    fixtures = {
        "events": Path("data/fixtures/resolutions/sample_events.jsonl"),
        "predictions": Path("data/fixtures/predictions/sample_predictions.jsonl"),
        "resolutions": Path("data/fixtures/resolutions/sample_resolutions.jsonl"),
        "edgar": Path("data/generated/edgar/latest.jsonl"),
    }
    candidate = defaults.get(data_type)
    if candidate and candidate.exists():
        return candidate
    fixture = fixtures.get(data_type)
    if fixture and fixture.exists():
        typer.secho(
            f"[warn] {data_type} file missing; falling back to fixture {fixture}",
            fg="yellow",
        )
        return fixture
    return candidate or Path(".")


def stat_file(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        lines = sum(1 for _ in path.open("r", encoding="utf-8"))
    except Exception:
        lines = None
    mtime = datetime.fromtimestamp(path.stat().st_mtime).isoformat()
    return {"exists": True, "lines": lines, "mtime": mtime}
