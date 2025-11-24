# AgentBeats Finance Track

Scaffolding for the FutureBench-Finance evaluator (green agent) and predictor (purple agent).

## Getting Started

1. Create a virtual environment and install dependencies:
   ```bash
   uv venv && source .venv/bin/activate
   pip install -e .
   ```
2. Run the CLI help:
   ```bash
   agentbeats --help
   ```

## CLI workflows

> Tip: set `ALPHAVANTAGE_API_KEY` in your environment if you want the purple agent to pull Alpha Vantage data.

- Snapshot latest Polymarket events (default output `data/generated/events/latest.jsonl`):
  ```bash
  agentbeats ingest-events --limit 25 --include-active true
  ```
- Generate purple-agent predictions that read the snapshot and produce `data/generated/predictions/latest.jsonl`:
  ```bash
  agentbeats run-predictor --as-of 2025-01-01T00:00:00Z
  ```
- Evaluate predictions with the baseline scorer (specify resolutions/events when available; falls back to fixtures if paths are missing):
  ```bash
  agentbeats run-evaluator \
    --predictions-path data/generated/predictions/latest.jsonl \
    --resolutions-path data/generated/resolutions/latest.jsonl \
    --events-path data/generated/events/latest.jsonl
  ```

See `docs/green-agent/plan.md` and `docs/purple-agent/responsibilities.md` for the roadmap and predictor contract, and `docs/tools/README.md` for shared tool interfaces.

## Current Status

- Ingestion: Polymarket feed available; watchlist generator (`scripts/generate_watchlist_events.py`) for ticker-specific events.
- Predictions: stub purple agent (news + optional Alpha Vantage) with colorized per-event evidence logging.
- Resolutions: generate placeholders via `agentbeats generate-resolutions` and fill outcomes manually.
- Evaluation: `agentbeats run-evaluator` computes Accuracy/Brier, prints human-readable summary + per-event explanations; runs logged under `data/generated/runs/`.

## End-to-End Flow Checklist

1. **Ingest events** (environment setup)
   - `agentbeats ingest-events --limit N --keywords "<tickers>"` for live Polymarket markets, or
   - `python scripts/generate_watchlist_events.py` for a custom ticker watchlist, then use `--events-path data/generated/events/watchlist_latest.jsonl`.
2. **Generate predictions** (purple agent)
   - `agentbeats run-predictor --events-path <events.jsonl> --as-of <ISO8601>`
   - CLI now shows colored step-by-step logs and lists evidence adapters used.
3. **Provide resolutions** (ground truth)
   - Supply a `ResolutionRecord` JSONL file (manually curated for watchlist or fetched from truth sources) via `--resolutions-path`.
4. **Evaluate** (green agent)
   - `agentbeats run-evaluator --predictions-path <preds.jsonl> --resolutions-path <res.jsonl> --events-path <events.jsonl>`
   - Outputs Accuracy/Brier plus Phase 2 metrics (ELS, Kelly, calibration) and stores run artifacts under `data/generated/runs/`.

Artifacts:
- Events: `data/generated/events/…`
- Predictions: `data/generated/predictions/…`
- Resolutions: `data/generated/resolutions/…` (populate for your watchlist or truth source)
- Run logs: `data/generated/runs/<timestamp>/`
