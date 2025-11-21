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
