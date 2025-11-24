"""AgentBeats command-line interface."""

import typer

from .ingest import ingest_app, ingest_events
from .resolve import resolve_app, generate_resolutions, resolve_prices
from .run import run_app, run_predictor, run_evaluator
from .status import status_app, status
from .tool import tool_app, fetch_edgar, fetch_alpha

app = typer.Typer(help="AgentBeats evaluator/predictor utilities")
app.add_typer(ingest_app, name="ingest")
app.add_typer(run_app, name="run")
app.add_typer(tool_app, name="tool")
app.add_typer(resolve_app, name="resolve")
app.add_typer(status_app, name="status")

@app.callback(invoke_without_command=True)
def _main(ctx: typer.Context):
    """Entry point that shows a short quickstart when no command is provided."""
    if ctx.invoked_subcommand is None:
        typer.secho("AgentBeats CLI - no command provided.\n", fg="yellow")
        typer.echo("Common commands:")
        typer.echo("  agentbeats ingest events         # snapshot events")
        typer.echo("  agentbeats run predictor         # generate predictions")
        typer.echo("  agentbeats run evaluator         # score predictions")
        typer.echo("  agentbeats tool edgar            # pull EDGAR filings/facts")
        typer.echo("  agentbeats resolve prices        # price-close resolutions")
        typer.echo("  agentbeats status show           # show data files")
        typer.echo("  agentbeats --help                # full command list")
        raise typer.Exit()


if __name__ == "__main__":  # pragma: no cover
    app()
