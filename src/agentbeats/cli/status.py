from pathlib import Path

import typer

from ..config import EvaluatorConfig
from ..models import EventSpec, ResolutionRecord
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


@status_app.command("coverage")
def coverage(
    events_path: Path = typer.Option(None, help="Events JSONL"),
    resolutions_path: Path = typer.Option(None, help="Resolutions JSONL"),
):
    """Check coverage: events missing resolutions or missing provenance/timestamps."""

    ev_path = events_path or get_default_path("events")
    res_path = resolutions_path or get_default_path("resolutions")
    if not ev_path.exists():
        typer.secho(f"✗ Events file not found: {ev_path}", fg="red")
        raise typer.Exit(code=1)
    if not res_path.exists():
        typer.secho(f"✗ Resolutions file not found: {res_path}", fg="red")
        raise typer.Exit(code=1)

    events = {}
    with ev_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                event = EventSpec.model_validate_json(line)
                events[event.id] = event
    resolutions = {}
    with res_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                try:
                    res = ResolutionRecord.model_validate_json(line)
                    resolutions[res.id] = res
                except Exception:
                    continue

    missing = [eid for eid in events.keys() if eid not in resolutions]
    weak = [
        rid
        for rid, res in resolutions.items()
        if not res.verified_source or not res.resolved_at
    ]

    typer.secho("Coverage check", fg="cyan")
    typer.echo(f"  Events: {len(events)}")
    typer.echo(f"  Resolutions: {len(resolutions)}")
    typer.echo(f"  Missing resolutions: {len(missing)}")
    if missing:
        typer.echo(f"    Sample missing: {', '.join(missing[:5])}")
    typer.echo(f"  Missing provenance/timestamps: {len(weak)}")
    if weak:
        typer.echo(f"    Sample weak: {', '.join(weak[:5])}")
