from pathlib import Path
from typing import Optional

import typer
from pydantic import ValidationError

from ..config import EvaluatorConfig, PredictorConfig
from ..evaluator import BaselineEvaluator
from ..predictor import PurpleAgent
from .common import get_default_path, parse_timestamp

run_app = typer.Typer(help="Run commands (purple/green)")


@run_app.command("predictor")
def run_predictor(
    events_path: Optional[Path] = typer.Option(None, help="Events JSONL to ingest"),
    output_path: Optional[Path] = typer.Option(None, help="Where to write predictions JSONL"),
    as_of: Optional[str] = typer.Option(
        None,
        help="ISO8601 timestamp for metadata (default: now, UTC)",
    ),
):
    """
    Generate predictions using the stub purple agent.

    Examples:
      # Default paths (uses fixtures if missing)
      agentbeats run predictor

      # Explicit inputs with timestamp
      agentbeats run predictor --events-path data/generated/events/latest.jsonl --as-of 2025-01-01T00:00:00Z
    """

    config = PredictorConfig()
    agent = PurpleAgent(config)

    def console_log(message: str, color: str = "cyan") -> None:
        typer.secho(message, fg=color)

    target = agent.run(
        events_path=events_path or get_default_path("events"),
        output_path=output_path or get_default_path("predictions"),
        as_of=parse_timestamp(as_of),
        log=console_log,
    )
    typer.secho(f"Predictions written to {target}", fg="green")


@run_app.command("evaluator")
def run_evaluator(
    predictions_path: Optional[Path] = typer.Option(None, help="JSONL predictions file"),
    resolutions_path: Optional[Path] = typer.Option(None, help="JSONL resolutions file"),
    events_path: Optional[Path] = typer.Option(None, help="Event snapshot JSONL"),
):
    """
    Run the MVP evaluator on fixture or user-provided data.

    Examples:
      # Default paths (falls back to fixtures if missing)
      agentbeats run evaluator

      # Explicit paths
      agentbeats run evaluator --predictions-path data/generated/predictions/latest.jsonl \\
        --resolutions-path data/generated/resolutions/latest.jsonl \\
        --events-path data/generated/events/latest.jsonl
    """

    config = EvaluatorConfig()
    evaluator = BaselineEvaluator(config)
    default_predictions = get_default_path("predictions")
    default_resolutions = get_default_path("resolutions")
    default_events = get_default_path("events")
    pred_path = predictions_path or default_predictions
    res_path = resolutions_path or default_resolutions
    ev_path = events_path or default_events
    missing = [("predictions", pred_path), ("resolutions", res_path), ("events", ev_path)]
    missing_paths = [(label, p) for label, p in missing if not p.exists()]
    if missing_paths:
        typer.secho("✗ Required files not found:", fg="red")
        for label, path in missing_paths:
            typer.echo(f"  - {label}: {path}")
        typer.echo("  Try regenerating with: agentbeats ingest / run predictor / resolve or generate-resolutions")
        raise typer.Exit(code=1)
    try:
        results = evaluator.evaluate(
            predictions_path=pred_path,
            resolutions_path=res_path,
            events_path=ev_path,
        )
    except ValidationError as exc:
        typer.secho("✗ Evaluation failed: invalid JSONL schema.", fg="red")
        typer.echo(f"  resolutions: {res_path}")
        for err in exc.errors():
            loc = ".".join(str(x) for x in err.get("loc", []))
            typer.echo(f"  - {loc}: {err.get('msg')}")
        typer.echo("  Expected ResolutionRecord fields: id, outcome (0/1), verified_value?, verified_source?, resolved_at?.")
        raise typer.Exit(code=1)
    except Exception as exc:  # noqa: BLE001
        typer.secho("✗ Evaluation failed.", fg="red")
        typer.echo(f"  predictions: {pred_path}")
        typer.echo(f"  resolutions: {res_path}")
        typer.echo(f"  events:      {ev_path}")
        typer.echo(f"  error: {exc}")
        typer.echo("  Hint: ensure resolutions are ResolutionRecord JSONL (id/outcome fields).")
        raise typer.Exit(code=1)

    summary = results.pop("summary", None)
    run_dir = results.pop("run_log_dir", None)
    if summary:
        typer.secho("Results Summary", fg="green")
        typer.echo(f"  {summary}")
    typer.echo(f"  Events evaluated: {results.get('events', 0)}")
    typer.echo(f"  Accuracy: {results.get('accuracy', 0):.2f}")
    typer.echo(f"  Brier: {results.get('brier', 0):.4f}")
    if run_dir:
        typer.echo(f"  Run artifacts: {run_dir}")
    explanations = results.get("explanations", []) or []
    if explanations:
        typer.echo("  Sample events:")
        for row in explanations[:5]:
            typer.echo(
                f"    - {row.get('event_id')}: prob={row.get('predicted_prob')}, outcome={row.get('outcome')}, brier={row.get('brier_component'):.4f}"
            )


@run_app.command("pipeline")
def run_pipeline(
    limit: int = typer.Option(10, help="Number of events to ingest when using Polymarket source"),
    source: str = typer.Option("fixture", help="Ingestion source (polymarket or fixture)"),
    as_of: Optional[str] = typer.Option(None, help="ISO8601 timestamp for prediction metadata"),
    skip_ingest: bool = typer.Option(False, help="Skip ingestion step"),
    skip_resolve: bool = typer.Option(False, help="Skip resolution step"),
    events_path: Optional[Path] = typer.Option(None, help="Override events path"),
    predictions_path: Optional[Path] = typer.Option(None, help="Override predictions output"),
    resolutions_path: Optional[Path] = typer.Option(None, help="Override resolutions output"),
):
    """
    Run the pipeline: ingest -> predict -> (optional) resolve prices -> evaluate.

    Notes:
      - Set ALPHAVANTAGE_API_KEY to enable price resolutions.
      - Set SEC_USER_AGENT to enable EDGAR fetches (used by other commands).

    Examples:
      # Full pipeline with fixtures
      agentbeats run pipeline --source fixture --limit 5

      # Skip ingest (reuse existing events) and skip resolve
      agentbeats run pipeline --skip-ingest --skip-resolve --events-path data/generated/events/latest.jsonl
    """
    # Ingest
    ev_path = events_path or get_default_path("events")
    if not skip_ingest:
        typer.secho("⠋ Ingesting events...", fg="cyan")
        from ..ingestion import EventIngestion
        from ..config import IngestionConfig

        pipeline = EventIngestion(IngestionConfig(source=source, polymarket_limit=limit))
        ev_path = pipeline.run(output_path=ev_path)
        typer.secho(f"✓ Events written to {ev_path}", fg="green")
    else:
        typer.secho(f"↷ Skipping ingest (using {ev_path})", fg="yellow")

    # Predict
    typer.secho("⠋ Generating predictions...", fg="cyan")
    pred_path = predictions_path or get_default_path("predictions")
    agent = PurpleAgent(PredictorConfig())
    preds_out = agent.run(
        events_path=ev_path,
        output_path=pred_path,
        as_of=parse_timestamp(as_of),
        log=lambda msg, color="cyan": typer.secho(msg, fg=color),
    )
    typer.secho(f"✓ Predictions written to {preds_out}", fg="green")

    # Resolve (optional price-close)
    res_path = resolutions_path or get_default_path("resolutions")
    if not skip_resolve:
        try:
            from ..resolution import PriceCloseResolver
            from ..tools import AlphaVantageClient
            cfg = PredictorConfig()
            client = AlphaVantageClient(
                api_key=cfg.alpha_vantage_api_key,
                cache_dir=Path("data/generated/tool_cache/alpha_vantage"),
            )
            resolver = PriceCloseResolver(client)
            events = list(EventIngestion(IngestionConfig(fixture_events=ev_path)).load_events(ev_path))
            resolutions = resolver.resolve(events)
            if resolutions:
                res_path.parent.mkdir(parents=True, exist_ok=True)
                with res_path.open("w", encoding="utf-8") as handle:
                    import json
                    for row in resolutions:
                        handle.write(json.dumps(row))
                        handle.write("\n")
                typer.secho(f"✓ Resolved {len(resolutions)} price events to {res_path}", fg="green")
            else:
                typer.secho("↷ No price-close events found to resolve.", fg="yellow")
        except Exception as exc:  # noqa: BLE001
            typer.secho(f"✗ Price resolution skipped due to error: {exc}", fg="red")
            typer.secho(f"↷ Using existing/placeholder resolutions at {res_path}", fg="yellow")
    else:
        typer.secho(f"↷ Skipping resolution (using {res_path})", fg="yellow")

    # Evaluate
    typer.secho("⠋ Evaluating predictions...", fg="cyan")
    evaluator = BaselineEvaluator(EvaluatorConfig())
    results = evaluator.evaluate(
        predictions_path=preds_out,
        resolutions_path=res_path,
        events_path=ev_path,
    )
    summary = results.get("summary")
    typer.secho("✓ Evaluation complete", fg="green")
    if summary:
        typer.echo(summary)
    typer.echo(f"Run artifacts: {results.get('run_log_dir')}")
