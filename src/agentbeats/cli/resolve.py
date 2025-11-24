from pathlib import Path
from typing import Optional

import typer

from ..models import EventSpec
from ..resolution import PriceCloseResolver
from ..config import IngestionConfig, PredictorConfig
from ..ingestion import EventIngestion
from ..tools import AlphaVantageClient
from .common import get_default_path
import json

resolve_app = typer.Typer(help="Resolvers for ground truth")


@resolve_app.command("placeholders")
def generate_resolutions(
    events_path: Optional[Path] = typer.Option(None, help="Events JSONL to derive resolutions from"),
    output_path: Optional[Path] = typer.Option(None, help="Where to write ResolutionRecord JSONL"),
):
    """
    Produce placeholder ResolutionRecord JSONL from an events file.
    Outcomes default to 0; edit the output to set true outcomes/values.
    """
    eloc = events_path or get_default_path("events")
    out = output_path or get_default_path("resolutions")
    out.parent.mkdir(parents=True, exist_ok=True)
    if not eloc.exists():
        typer.secho(f"✗ Events file not found: {eloc}", fg="red")
        typer.echo("  Try running: agentbeats ingest events")
        raise typer.Exit(code=1)

    try:
        with eloc.open("r", encoding="utf-8") as ev_handle, out.open("w", encoding="utf-8") as out_handle:
            for line in ev_handle:
                line = line.strip()
                if not line:
                    continue
                event = EventSpec.model_validate_json(line)
                resolution = {
                    "id": event.id,
                    "outcome": 0,
                    "verified_value": None,
                    "verified_source": "manual",
                    "resolved_at": None,
                }
                out_handle.write(json.dumps(resolution))
                out_handle.write("\n")
        typer.echo(f"Wrote placeholder resolutions to {out}")
    except Exception as exc:
        typer.secho(f"✗ Error generating resolutions: {exc}", fg="red")
        raise typer.Exit(code=1)


@resolve_app.command("prices")
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
    eloc = events_path or get_default_path("events")
    out = output_path or get_default_path("resolutions")
    out.parent.mkdir(parents=True, exist_ok=True)
    if not eloc.exists():
        typer.secho(f"✗ Events file not found: {eloc}", fg="red")
        typer.echo("  Try running: agentbeats ingest events")
        raise typer.Exit(code=1)
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
