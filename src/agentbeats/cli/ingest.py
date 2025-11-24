from pathlib import Path
from typing import Optional

import typer

from ..config import IngestionConfig
from ..ingestion import EventIngestion
from .common import get_default_path

ingest_app = typer.Typer(help="Ingestion commands (green agent)")


@ingest_app.command("events")
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
    """
    Run the offline ingestion pipeline to snapshot event specs.

    Examples:
      agentbeats ingest events --source polymarket --limit 10
      agentbeats ingest events --source fixture --output-path data/generated/events/latest.jsonl
    """

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
    target = pipeline.run(output_path=output_path or get_default_path("events"))
    typer.echo(f"Event snapshot written to {target}")
