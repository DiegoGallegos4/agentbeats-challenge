import typer

from ..config import EvaluatorConfig
from .common import get_default_path, stat_file

status_app = typer.Typer(help="Data status")


@status_app.command("show")
def status():
    """Show available data files and basic stats."""

    typer.secho("Data status", fg="cyan")
    entries = [
        ("events", get_default_path("events")),
        ("predictions", get_default_path("predictions")),
        ("resolutions", get_default_path("resolutions")),
        ("edgar", get_default_path("edgar")),
    ]
    for label, path in entries:
        info = stat_file(path)
        if not info["exists"]:
            typer.secho(f"- {label}: missing ({path})", fg="yellow")
        else:
            typer.echo(
                f"- {label}: {path} (lines={info.get('lines')}, mtime={info.get('mtime')})"
            )
    runs_dir = EvaluatorConfig().run_log_dir
    run_count = len(list(runs_dir.glob("*"))) if runs_dir.exists() else 0
    typer.echo(f"- runs: {runs_dir} ({run_count} run(s) logged)")
