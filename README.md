# FutureFinanceX

FutureFinanceX bench is a finance-focused forecasting and evaluation pipeline built for the AgentBeats competition. It targets developers and researchers who want to ingest real or fixture finance events, generate structured predictions, resolve outcomes, and score them with standard metrics (Accuracy/Brier). 

Out of the box, you get CLI-driven ingestion, a stub predictor with evidence hooks (news/Alpha Vantage/EDGAR), resolution helpers (placeholders and price-close), and a green evaluator that produces run artifacts for reproducibility. Use it to prototype finance prediction agents, validate prediction quality on JSONL datasets, and extend the tooling (LLM-based evidence validation, custom resolvers) for deeper audits and leaderboard-ready outputs.

Abstract: The evaluator scores two parallel tracks: portfolio forecasts (PnL, hit rate, exposure, Sharpe) and FinanceX task predictions. FinanceX tasks follow four levels: Basic (Level 1) yes/no close-above-threshold, Wide Search (Level 2) multi-choice ticker sets, Deep Search (Level 3) numeric close-price, and Super Agent (Level 4) numeric range (high-low). The purple agent emits either portfolio weights or per-task predictions, and the green agent computes per-level scores with the FutureX scoring rules.

| Task Level | Type | Example |
| --- | --- | --- |
| Level 1 (Basic) | Yes/No price outcome | Will AAPL close above $270.97 on 2025-12-22? |
| Level 2 (Wide Search) | Multi-choice ticker set | Which tickers closed above their previous close on 2025-12-22? Select all: AAPL, MSFT, GOOGL, AMZN, TSLA. |
| Level 3 (Deep Search) | Numeric close price | What was the closing price of MSFT on 2025-12-22? Provide USD to 2 decimals. |
| Level 4 (Super Agent) | Numeric intraday range | What was the intraday range (high-low) for TSLA on 2025-12-22? Provide USD to 2 decimals. |

## Table of Contents

- [Getting Started](#getting-started)
- [Quickstart](#quickstart)
- [CLI commands](#cli-commands)
  - [Ingesting events](#ingesting-events)
- [Running predictor (purple)](#running-predictor-purple)
- [Running evaluator (green)](#running-evaluator-green)
- [Audits](#audits)
- [Pipeline](#pipeline)
- [Resolutions](#resolutions)
- [Tools](#tools)
- [Status](#status)
- [Flows (sequence)](#flows-sequence)
- [Glossary](#glossary)

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

## Quickstart

Minimal end-to-end run using fixtures (no API keys required):
```bash
agentbeats ingest events --source fixture
agentbeats run predictor
agentbeats resolve placeholders  # or skip if you already have resolutions
agentbeats run evaluator
```

For live data: add keys to `config/agentbeats.toml` (see `config/agentbeats.example.toml`), then run `agentbeats run pipeline --source polymarket`. Env vars remain optional fallbacks.

## CLI commands

Configuration:
- Primary config lives at `config/agentbeats.toml` (copy from `config/agentbeats.example.toml`).
- Keys of interest: `tools.alpha_vantage.api_key`, `tools.edgar.user_agent` (with contact info), cache dirs, and tool log dirs.
- Env vars such as `ALPHAVANTAGE_API_KEY` / `SEC_USER_AGENT` are optional fallbacks if the TOML value is empty.

### Ingesting events
Snapshot events from Polymarket or fixtures into a JSONL file (`data/generated/events/latest.jsonl`).

| Option | Description |
| --- | --- |
| `--source` | STRING: `polymarket` or `fixture` (default: polymarket) |
| `--limit` | INT: number of events to fetch (polymarket) |
| `--include-active/--no-include-active` | BOOL: include active markets (default: include) |
| `--keywords` | STRING: comma-separated filters (defaults to finance keywords) |
| `--output-path` | PATH: override output path |
Default keywords live in `src/agentbeats/domain/finance.py`. Defaults to `data/generated/events/latest.jsonl` if `--output-path` is omitted (falls back to fixtures with a warning if missing).

#### Use case 1: Polymarket snapshot
Fetch 10 events from Polymarket and write to `data/generated/events/latest.jsonl` (default).
```bash
agentbeats ingest events --source polymarket --limit 10
```

#### Use case 2: Offline fixture snapshot
Copy fixture events to `data/generated/events/latest.jsonl` (works offline).
```bash
agentbeats ingest events \
  --source fixture \
  --output-path data/generated/events/latest.jsonl
```

### Running predictor (purple)
Generate stub purple predictions and write them to JSONL (`data/generated/predictions/latest.jsonl`).

| Option | Description |
| --- | --- |
| `--events-path` | PATH: events JSONL (default: generated or fixtures) |
| `--output-path` | PATH: predictions JSONL output |
| `--as-of` | STRING: ISO8601 timestamp for metadata |

#### Use case 1: Default paths
Read default events (or fixture fallback) and write predictions to `data/generated/predictions/latest.jsonl`.
```bash
agentbeats run predictor
```

#### Use case 2: Explicit timestamp
Read events from the default path and stamp predictions with a fixed time.
```bash
agentbeats run predictor \
  --events-path data/generated/events/latest.jsonl \
  --as-of 2025-01-01T00:00:00Z
```

### Running evaluator (green)
Score predictions against resolutions (Accuracy/Brier) and write run artifacts.

| Option | Description |
| --- | --- |
| `--predictions-path` | PATH: predictions JSONL |
| `--resolutions-path` | PATH: resolutions JSONL |
| `--events-path` | PATH: events JSONL |

#### Use case 1: Default paths (falls back to fixtures)
Evaluate using defaults (or fixtures if missing); prints summary and writes run artifacts under `data/generated/runs/`.
```bash
agentbeats run evaluator
```

#### Use case 2: Explicit paths
Evaluate using explicit inputs.
```bash
agentbeats run evaluator \
  --predictions-path data/generated/predictions/latest.jsonl \
  --resolutions-path data/generated/resolutions/latest.jsonl \
  --events-path data/generated/events/latest.jsonl
```

#### Running the green agent server (A2A)
Start the green agent service directly:
```bash
python src/green/server.py --host 127.0.0.1 --port 19009
```
Run a full scenario (green + purple) with the bundled scenario file:
```bash
python scripts/run_scenario.py scenario.toml
```

### Audits
Run a lightweight audit that reports citation counts/types per prediction and a basic evidence coverage score (1 if any citation present, else 0). LLM mode (Ollama via LiteLLM) is available for richer judging when configured.

| Option | Description |
| --- | --- |
| `--predictions-path` | PATH: predictions JSONL |
| `--mode` | STRING: `simple` (default) or `llm` (requires Ollama running and LLM config) |

Use case: Audit fixture predictions quickly.
```bash
agentbeats run audit \
  --predictions-path data/generated/predictions/latest.jsonl
```
LLM mode (Ollama via LiteLLM; ensure Ollama is running and config/agentbeats.toml has llm.* set):
```bash
agentbeats run audit --mode llm \
  --predictions-path data/generated/predictions/latest.jsonl
```
Outputs audit JSONL under `data/generated/runs/<run_id>/audits/`.

### Pipeline
Run the end-to-end loop (ingest, predict, optionally resolve price-close events, then evaluate) with optional skips.

| Option | Description |
| --- | --- |
| `--source` | STRING: ingest source (polymarket or fixture) |
| `--limit` | INT: ingest limit (default: 10) |
| `--as-of` | STRING: prediction timestamp (ISO8601) |
| `--skip-ingest` / `--skip-resolve` | BOOL: skip steps if data already exists |
| `--events-path` | PATH: override events path (default: `data/generated/events/latest.jsonl`, falls back to fixtures if missing) |
| `--predictions-path` | PATH: override predictions output (default: `data/generated/predictions/latest.jsonl`) |
| `--resolutions-path` | PATH: override resolutions output (default: `data/generated/resolutions/latest.jsonl`) |
Default source: `fixture`; default limit: `10`; skips default to false.

#### Use case 1: Full pipeline with fixtures
Ingest fixture events, predict, try price resolutions (if key set), then evaluate.
```bash
agentbeats run pipeline \
  --source fixture \
  --limit 5
```

#### Use case 2: Reuse existing events, skip resolution
Skip ingest and resolution, reuse existing events/resolutions, run predict + evaluate.
```bash
agentbeats run pipeline \
  --skip-ingest \
  --skip-resolve \
  --events-path data/generated/events/latest.jsonl
```

### Resolutions
Create placeholder resolutions or resolve price-close events via Alpha Vantage (`data/generated/resolutions/latest.jsonl`).

| Command | Notes |
| --- | --- |
| `agentbeats resolve placeholders` | Writes editable ResolutionRecord JSONL (defaults to `data/generated/resolutions/latest.jsonl`) |
| `agentbeats resolve prices` | Uses Alpha Vantage (configure `tools.alpha_vantage.api_key` in `config/agentbeats.toml`, env fallback allowed); resolves “close above $X on DATE” by filling ResolutionRecord JSONL (defaults to generated resolutions path) |

#### Use case 1: Generate editable placeholders
Create a resolutions file with outcome=0 stubs to fill manually.
```bash
agentbeats resolve placeholders \
  --events-path data/generated/events/latest.jsonl \
  --output-path data/generated/resolutions/latest.jsonl
```

#### Use case 2: Resolve price-close events
Fill resolutions for questions like “close above $X on DATE” using Alpha Vantage; writes outcomes/values.
```bash
agentbeats resolve prices \
  --events-path data/generated/events/latest.jsonl \
  --output-path data/generated/resolutions/latest.jsonl
```

### Tools
Available tools:

| Command | Notes |
| --- | --- |
| `agentbeats tool edgar` | Configure `tools.edgar.user_agent` in `config/agentbeats.toml`; writes EDGAR JSONL (`data/generated/edgar/latest.jsonl`); default forms: 8-K/10-Q/10-K; default fact tags: EPS diluted, revenues; default limit: 1. (SEC docs: https://www.sec.gov/edgar/sec-api-documentation) |
| `agentbeats tool alpha-vantage` | Configure `tools.alpha_vantage.api_key` in `config/agentbeats.toml` (env fallback supported); fetches raw time series (cached); default function: `TIME_SERIES_DAILY`. (Docs: https://www.alphavantage.co/documentation/) |

Use case: Fetch EDGAR filings/facts
```bash
agentbeats tool edgar \
  --events-path data/generated/events/latest.jsonl \
  --output-path data/generated/edgar/latest.jsonl
```

Use case: Debug Alpha Vantage time series
```bash
agentbeats tool alpha-vantage TSLA \
  --function TIME_SERIES_DAILY \
  --output-path data/generated/tool_cache/alpha_vantage/tsla_daily.json
```

### Status
Check data availability and coverage.

| Command | Notes |
| --- | --- |
| `agentbeats status show` | Lists events/predictions/resolutions/edgar paths + run logs |
| `agentbeats status coverage` | Flags missing resolutions or missing provenance/timestamps |

#### Use case 1: Show data files
Lists line counts, mtimes, and run log count.
```bash
agentbeats status show
```

#### Use case 2: Coverage check
Counts missing/provenance issues for resolutions.
```bash
agentbeats status coverage \
  --events-path data/generated/events/latest.jsonl \
  --resolutions-path data/generated/resolutions/latest.jsonl
```

## Flows (sequence)

### Purple (predictor) flow
Predictor flow (purple): CLI reads events, gathers evidence with tools, and writes predictions JSONL for the evaluator.

Step-by-step:
- Dev runs `agentbeats run predictor --events-path ...`.
- CLI loads `EventSpec` rows from events JSONL (defaults/fixtures if not provided).
- CLI calls tools (news, Alpha Vantage, EDGAR) to gather evidence/signals.
- Tools return evidence items; CLI builds `PredictionRecord` with probability + rationale.
- CLI writes predictions to JSONL (`data/generated/predictions/latest.jsonl` by default).
- CLI returns path to predictions for downstream evaluation.
```mermaid
sequenceDiagram
    participant Dev as You
    participant CLI as agentbeats run predictor
    participant Events as Events JSONL
    participant Tools as Tools (News, Alpha Vantage, EDGAR)
    participant Output as Predictions JSONL

    Dev->>CLI: agentbeats run predictor --events-path ...
    CLI->>Events: read EventSpec rows
    CLI->>Tools: fetch evidence (news, alpha, edgar)
    Tools-->>CLI: evidence + signals
    CLI->>Output: write PredictionRecord JSONL (prob + rationale)
    CLI-->>Dev: path to predictions
```

### Green (evaluator) flow
Evaluator flow (green): CLI loads predictions, resolutions, and events, computes Accuracy/Brier, and stores run artifacts.

Step-by-step:
- Dev runs `agentbeats run evaluator --predictions-path ... --resolutions-path ... --events-path ...`.
- CLI loads `PredictionRecord` JSONL, `ResolutionRecord` JSONL, and `EventSpec` (for baseline probabilities/questions).
- CLI joins by `id`, computes Accuracy and Brier, and builds per-event explanations.
- CLI writes run artifacts under `data/generated/runs/<timestamp>/` (metrics, records, inputs).
- CLI prints a summary and sample events, returning the run log directory.
```mermaid
sequenceDiagram
    participant Dev as You
    participant CLI as agentbeats run evaluator
    participant Preds as Predictions JSONL
    participant Res as Resolutions JSONL
    participant Events as Events JSONL
    participant Metrics as Accuracy/Brier + logs

    Dev->>CLI: agentbeats run evaluator --predictions-path ... --resolutions-path ...
    CLI->>Preds: load PredictionRecord rows
    CLI->>Res: load ResolutionRecord rows
    CLI->>Events: load EventSpec (baseline prob, question)
    CLI->>CLI: join by id, compute accuracy/brier
    CLI->>Metrics: write run artifacts under data/generated/runs/...
    CLI-->>Dev: summary + sample events + run log dir
```

## Docker

Build and run the green or purple agent images using the dedicated Dockerfiles. Use distinct tags so both images can coexist (`:green` and `:purple`), with `:latest` as an alias for green.
You can also run `scripts/build_agents.sh` to build both locally using the same tags.
For CI publishing, see `docs/deployment/github-actions.md`.

Build green:
```bash
docker build -f Dockerfile.green \
  -t ghcr.io/diegogallegos4/agentbeats-challenge:latest \
  -t ghcr.io/diegogallegos4/agentbeats-challenge:green .
```

Run green:
```bash
docker run --rm -p 9009:9009 ghcr.io/diegogallegos4/agentbeats-challenge:green
```

Build purple:
```bash
docker build -f Dockerfile.purple -t ghcr.io/diegogallegos4/agentbeats-challenge:purple .
```

Run purple:
```bash
docker run --rm -p 9010:9009 ghcr.io/diegogallegos4/agentbeats-challenge:purple
```

Run both at once on different ports:
```bash
docker run --rm -p 9009:9009 ghcr.io/diegogallegos4/agentbeats-challenge:green
docker run --rm -p 9010:9009 ghcr.io/diegogallegos4/agentbeats-challenge:purple
```

## Glossary
- **EventSpec**: Canonical event/task packet (id, question, resolution_date, source, tags, baseline_probability).
- **PredictionRecord**: Purple agent output (probability + rationale/evidence + metadata) keyed by EventSpec.id.
- **ResolutionRecord**: Ground truth (outcome 0/1, optional verified value/source/timestamp) keyed by EventSpec.id.
- **Purple agent (predictor)**: Generates probabilities and rationales over EventSpec inputs.
- **Green agent (evaluator)**: Scores predictions against resolutions (Accuracy, Brier) and manages evidence/audit pipelines.
- **Tool adapters**: Shared external data fetchers (news, Alpha Vantage, EDGAR, Polymarket) used by predictors/resolvers.
- **Run artifacts**: Evaluation outputs stored under `data/generated/runs/<timestamp>/` (metrics, per-event records, inputs).

See [docs/green-agent/plan.md](docs/green-agent/plan.md) and [docs/purple-agent/responsibilities.md](docs/purple-agent/responsibilities.md) for the roadmap and predictor contract, and [docs/tools/README.md](docs/tools/README.md) for shared tool interfaces.
