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
      agentbeats run predictor
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
      agentbeats run evaluator
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
