"""AgentBeats command-line interface."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

from .config import EvaluatorConfig, IngestionConfig, PredictorConfig
from .evaluator import BaselineEvaluator
from .ingestion import EventIngestion
from .models import EventSpec
from .predictor import PurpleAgent, load_fixture_predictions
from .resolution import PriceCloseResolver
from .tools import AlphaVantageClient, EdgarEvidenceFetcher

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
    summary = results.pop("summary", None)
    if summary:
        typer.secho(f"Summary: {summary}", fg="green")
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


@app.command("generate-resolutions")
def generate_resolutions(
    events_path: Optional[Path] = typer.Option(None, help="Events JSONL to derive resolutions from"),
    output_path: Optional[Path] = typer.Option(None, help="Where to write ResolutionRecord JSONL"),
):
    """
    Produce placeholder ResolutionRecord JSONL from an events file.
    Outcomes default to 0; edit the output to set true outcomes/values.
    """
    eloc = events_path or Path("data/generated/events/latest.jsonl")
    out = output_path or Path("data/generated/resolutions/latest.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    if not eloc.exists():
        raise typer.BadParameter(f"Events file not found: {eloc}")

    with eloc.open("r", encoding="utf-8") as ev_handle, out.open("w", encoding="utf-8") as out_handle:
        for line in ev_handle:
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            resolution = {
                "id": event.get("id"),
                "outcome": 0,
                "verified_value": None,
                "verified_source": "manual",
                "resolved_at": None,
            }
            out_handle.write(json.dumps(resolution))
            out_handle.write("\n")
    typer.echo(f"Wrote placeholder resolutions to {out}")


@app.command("resolve-prices")
def resolve_prices(
    events_path: Optional[Path] = typer.Option(None, help="Events JSONL to resolve price-close questions"),
    output_path: Optional[Path] = typer.Option(None, help="Where to write ResolutionRecord JSONL"),
):
    """Resolve 'close above $X on DATE' events via Alpha Vantage (uses cache when available)."""

    cfg = PredictorConfig()
    if not cfg.alpha_vantage_api_key:
        raise typer.BadParameter("ALPHAVANTAGE_API_KEY not set; cannot resolve prices.")
    client = AlphaVantageClient(
        api_key=cfg.alpha_vantage_api_key,
        cache_dir=Path("data/generated/tool_cache/alpha_vantage"),
    )
    resolver = PriceCloseResolver(client)
    eloc = events_path or Path("data/generated/events/latest.jsonl")
    out = output_path or Path("data/generated/resolutions/latest.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    events = list(EventIngestion(IngestionConfig(fixture_events=eloc)).load_events(eloc))
    resolutions = resolver.resolve(events)
    if not resolutions:
        typer.secho("No price-close style events found to resolve.", fg="yellow")
        return
    with out.open("w", encoding="utf-8") as handle:
        for row in resolutions:
            handle.write(json.dumps(row))
            handle.write("\n")
    typer.secho(f"Resolved {len(resolutions)} events to {out}", fg="green")


@app.command("fetch-edgar")
def fetch_edgar(
    events_path: Optional[Path] = typer.Option(None, help="Events JSONL to fetch EDGAR evidence for"),
    output_path: Optional[Path] = typer.Option(None, help="Where to write EDGAR evidence JSONL"),
    forms: str = typer.Option("8-K,10-Q,10-K", help="Comma-separated form types to include"),
    fact_tags: str = typer.Option(
        "us-gaap:EarningsPerShareDiluted,us-gaap:Revenues", help="Comma-separated XBRL tags to fetch"
    ),
    limit: int = typer.Option(1, help="Max filings/facts per event"),
):
    """
    Fetch EDGAR filings + selected XBRL facts for each event and write JSONL.

    Output rows look like:
    {"id": "...", "filings": [...EvidenceItem...], "facts": [...fact dicts...]}
    """
    eloc = events_path or Path("data/generated/events/latest.jsonl")
    out = output_path or Path("data/generated/edgar/latest.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    if not eloc.exists():
        raise typer.BadParameter(f"Events file not found: {eloc}")

    form_list = [f.strip() for f in forms.split(",") if f.strip()]
    tags_list = [t.strip() for t in fact_tags.split(",") if t.strip()]

    fetcher = EdgarEvidenceFetcher()
    written = 0
    with eloc.open("r", encoding="utf-8") as ev_handle, out.open("w", encoding="utf-8") as out_handle:
        for line in ev_handle:
            line = line.strip()
            if not line:
                continue
            event = EventSpec.model_validate_json(line)
            filings = fetcher.fetch_latest(event, forms=form_list, limit=limit)
            facts = fetcher.fetch_facts(event, tags=tags_list, forms=form_list, limit=limit)
            if not filings and not facts:
                ticker_hint = (event.tags[0] if event.tags else None) or (event.source.market_id if event.source else None)
                typer.secho(f"[warn] No EDGAR data for {event.id} (ticker={ticker_hint})", fg="yellow")
            payload = {
                "id": event.id,
                "filings": [f.model_dump(mode="json") for f in filings],
                "facts": facts,
            }
            out_handle.write(json.dumps(payload, default=str))
            out_handle.write("\n")
            written += 1
    typer.secho(f"Wrote EDGAR evidence for {written} events to {out}", fg="green")

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
