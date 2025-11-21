"""AgentBeats command-line interface."""

from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

from .config import EvaluatorConfig, IngestionConfig, PredictorConfig
from .evaluator import BaselineEvaluator
from .ingestion import EventIngestion
from .predictor import PurpleAgent, load_fixture_predictions

app = typer.Typer(help="AgentBeats evaluator/predictor utilities")


def _resolve_path(path: Optional[Path], default: Path) -> Path:
    return path if path else default


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError as exc:  # pragma: no cover - typer surfaces error
        raise typer.BadParameter("Timestamp must be ISO8601 (e.g. 2025-01-01T00:00:00Z).") from exc


@app.command("run-evaluator")
def run_evaluator(
    predictions_path: Optional[Path] = typer.Option(None, help="JSONL predictions file"),
    resolutions_path: Optional[Path] = typer.Option(None, help="JSONL resolutions file"),
    events_path: Optional[Path] = typer.Option(None, help="Event snapshot JSONL"),
):
    """Run the MVP evaluator on fixture or user-provided data."""

    config = EvaluatorConfig()
    evaluator = BaselineEvaluator(config)
    default_predictions = config.data_paths.predictions
    if not default_predictions.exists():
        default_predictions = Path("data/fixtures/predictions/sample_predictions.jsonl")
    default_resolutions = config.data_paths.resolutions
    if not default_resolutions.exists():
        default_resolutions = Path("data/fixtures/resolutions/sample_resolutions.jsonl")
    default_events = config.data_paths.events
    if not default_events.exists():
        default_events = Path("data/generated/events/latest.jsonl")
    results = evaluator.evaluate(
        predictions_path=_resolve_path(predictions_path, default_predictions),
        resolutions_path=_resolve_path(resolutions_path, default_resolutions),
        events_path=_resolve_path(events_path, default_events),
    )
    typer.echo(results)


@app.command("show-predictions")
def show_predictions(path: Optional[Path] = typer.Option(None, help="Fixture predictions JSONL")):
    """Display the currently bundled purple-agent fixture predictions."""

    config = PredictorConfig()
    payload = load_fixture_predictions(_resolve_path(path, config.fixture_predictions))
    typer.echo(payload)


@app.command("ingest-events")
def ingest_events(
    output_path: Optional[Path] = typer.Option(None, help="Where to write the event snapshot JSONL"),
    source: str = typer.Option("polymarket", help="Ingestion source (polymarket or fixture)"),
    limit: int = typer.Option(10, help="Number of events to fetch when source=polymarket"),
    include_active: bool = typer.Option(True, help="Include active markets (polymarket)"),
    keywords: Optional[str] = typer.Option(
        None,
        help="Comma-separated keywords to filter events (defaults to finance keywords)",
    ),
):
    """Run the offline ingestion pipeline to snapshot event specs."""

    keyword_list = None
    if keywords is not None:
        keyword_list = [kw.strip().lower() for kw in keywords.split(",") if kw.strip()]

    config_kwargs = {
        "source": source,
        "polymarket_limit": limit,
        "include_active": include_active,
    }
    if keyword_list is not None:
        config_kwargs["finance_keywords"] = keyword_list
    config = IngestionConfig(**config_kwargs)
    pipeline = EventIngestion(config)
    target = pipeline.run(output_path=output_path)
    typer.echo(f"Event snapshot written to {target}")


@app.command("run-predictor")
def run_predictor(
    events_path: Optional[Path] = typer.Option(None, help="Events JSONL to ingest"),
    output_path: Optional[Path] = typer.Option(None, help="Where to write predictions JSONL"),
    as_of: Optional[str] = typer.Option(
        None,
        help="ISO8601 timestamp for metadata (default: now, UTC)",
    ),
):
    """Generate predictions using the stub purple agent."""

    config = PredictorConfig()
    agent = PurpleAgent(config)
    def console_log(message: str, color: str = "cyan") -> None:
        typer.secho(message, fg=color)

    target = agent.run(
        events_path=events_path,
        output_path=output_path,
        as_of=_parse_timestamp(as_of),
        log=console_log,
    )
    typer.secho(f"Predictions written to {target}", fg="green")


if __name__ == "__main__":  # pragma: no cover
    app()
