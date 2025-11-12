"""AgentBeats command-line interface."""

from pathlib import Path
from typing import Optional

import typer

from .config import EvaluatorConfig, PredictorConfig
from .evaluator.mvp import EvaluatorMVP
from .predictor import PurpleAgent, load_fixture_predictions

app = typer.Typer(help="AgentBeats evaluator/predictor utilities")


def _resolve_path(path: Optional[Path], default: Path) -> Path:
    return path if path else default


@app.command("run-evaluator")
def run_evaluator(
    predictions_path: Optional[Path] = typer.Option(None, help="JSONL predictions file"),
    resolutions_path: Optional[Path] = typer.Option(None, help="JSONL resolutions file"),
):
    """Run the MVP evaluator on fixture or user-provided data."""

    config = EvaluatorConfig()
    evaluator = EvaluatorMVP(config)

    results = evaluator.evaluate(
        predictions_path=_resolve_path(predictions_path, config.data_paths.predictions / "sample_predictions.jsonl"),
        resolutions_path=_resolve_path(resolutions_path, config.data_paths.resolutions / "sample_resolutions.jsonl"),
    )
    typer.echo(results)


@app.command("show-predictions")
def show_predictions(path: Optional[Path] = typer.Option(None, help="Fixture predictions JSONL")):
    """Display the currently bundled purple-agent fixture predictions."""

    config = PredictorConfig()
    payload = load_fixture_predictions(_resolve_path(path, config.fixture_predictions))
    typer.echo(payload)


@app.command("run-predictor")
def run_predictor(
    events_path: Optional[Path] = typer.Option(None, help="Events JSONL to ingest"),
    output_path: Optional[Path] = typer.Option(None, help="Where to write predictions JSONL"),
):
    """Generate predictions using the stub purple agent."""

    config = PredictorConfig()
    agent = PurpleAgent(config)
    target = agent.run(events_path=events_path, output_path=output_path)
    typer.echo(f"Predictions written to {target}")


if __name__ == "__main__":  # pragma: no cover
    app()
