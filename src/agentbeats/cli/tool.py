import json
from pathlib import Path
from typing import Optional

import typer

from ..models import EventSpec
from ..tools import AlphaVantageClient, EdgarEvidenceFetcher
from .common import get_default_path

tool_app = typer.Typer(help="Tool debug/fetch commands")


@tool_app.command("edgar")
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

    Notes:
      - Set SEC_USER_AGENT (e.g., agentbeats/0.1 (contact: you@example.com)) to avoid SEC blocks.

    \b
    Examples:
      agentbeats tool edgar --events-path data/generated/events/latest.jsonl \\
        --output-path data/generated/edgar/latest.jsonl
    """
    eloc = events_path or get_default_path("events")
    out = output_path or get_default_path("edgar")
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


@tool_app.command("alpha-vantage")
def fetch_alpha(
    symbol: str = typer.Argument(..., help="Ticker symbol to fetch (e.g., TSLA)"),
    function: str = typer.Option("TIME_SERIES_DAILY", help="Alpha Vantage function (default: TIME_SERIES_DAILY)"),
    output_path: Optional[Path] = typer.Option(
        None, help="Optional path to write the raw JSON response (defaults to cache location)"
    ),
):
    """
    Fetch Alpha Vantage time series for debugging (uses cache if present).

    Notes:
      - Requires ALPHAVANTAGE_API_KEY in the environment.

    \b
    Examples:
      agentbeats tool alpha-vantage TSLA --function TIME_SERIES_DAILY \\
        --output-path data/generated/tool_cache/alpha_vantage/tsla_daily.json
    """

    client = AlphaVantageClient(
        cache_dir=Path("data/generated/tool_cache/alpha_vantage"),
    )
    if not client.is_configured():
        raise typer.BadParameter("ALPHAVANTAGE_API_KEY not set; cannot fetch Alpha Vantage data.")
    data = client.fetch_time_series(symbol, function=function)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle)
        typer.secho(f"Wrote Alpha Vantage response to {output_path}", fg="green")
    else:
        payload = json.dumps(data)
        typer.echo(payload[:2000] + ("..." if len(payload) > 2000 else ""))
