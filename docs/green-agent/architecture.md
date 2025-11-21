# Agentifying FutureBench-Finance: High-Level Architecture

The goal is to “agentify” the FutureBench-Finance benchmark so that every stage operates like an autonomous agent: collecting events, reasoning over evidence, generating forecasts, and evaluating outcomes. This mirrors the FutureX philosophy (ingestion → agentic prediction → automated evaluation) while specializing it for finance.

## 1. Tools Layer

- **Definition:** External capabilities agents rely on: news search (critical), EDGAR/XBRL (medium), Alpha Vantage (high priority), Polymarket snapshots/questions (low priority).
- **Purpose:** Provide verifiable signals for reasoning, with provenance metadata for downstream audits.
- **Design Goal:** Expose each tool via a consistent interface (inputs, outputs, timestamps) so both purple-agent reasoning and future audit agents can replay calls. Tool adapters sit between raw APIs and agent logic.

## 2. Automation Layer

- **Definition:** Orchestrated workflows that keep the benchmark live end-to-end.
- **Responsibilities:**
  - **Ingestion automation:** collect/filter/normalize events into `EventSpec` snapshots on a schedule.
  - **Prediction automation:** trigger purple-agent runs (or external agents) with the latest snapshots, enforcing time budgets per event.
  - **Resolution automation:** fetch outcomes from Polymarket/EDGAR and store `ResolutionRecord` entries.
  - **Evaluation automation:** run scoring + audits automatically, update leaderboards, and surface alerts.
- **Design Goal:** Make the benchmark self-sustaining (Phase 4 of `docs/evaluator-plan.md`), so a new agent can be evaluated without manual intervention.

## 3. Scoring & Audit Layer (Green Evaluator)

- **Definition:** The proctor/judge system described in `docs/evaluator-plan.md`—computes metrics and audits reasoning quality.
- **Responsibilities:** Accuracy, Brier, ELS, calibration, economic metrics, evidence coverage, attribution precision, reasoning-trace quality, leakage checks.
- **Design Goal:** Provide trustworthy, automated evaluation output (scores + explanations) and feed insights back to both tools and automations (e.g., flagging missing evidence or stale events).

## Agentified Loop

1. **Tools** supply evidence and event streams.
2. **Automations** orchestrate ingestion → prediction → resolution → evaluation.
3. **Scoring** (green evaluator) judges the outputs, informs leaderboards, and drives audits/alerts.

Everything we build (purple agent, ingestion CLI, Baseline evaluator) is scaffolding toward this architecture: a benchmark composed of autonomous tool-wielding agents, automated pipelines, and a comprehensive evaluator that embodies the “green agent” vision.

## Evaluator Agent Responsibilities

To fully “agentify” the benchmark, the green agent must:

1. **Curate the environment:** ingest/normalize finance events into `EventSpec` packets (daily/weekly cadence).
2. **Manage tools/execution:** expose evidence tools (news, EDGAR, Alpha Vantage, Polymarket) and trigger predictor runs on schedule.
3. **Collect resolutions:** harvest ground truth from Polymarket/EDGAR and maintain `ResolutionRecord` logs.
4. **Score + audit:** compute metrics (Accuracy/Brier → ELS/calibration → Kelly PnL) and run evidence audits (EC/AP/RTQ, leakage control).
5. **Report + alert:** publish leaderboards/dashboards and flag missing evidence, stale events, or other anomalies back to ingestion/predictor agents.

These tasks map directly to the phases in `docs/evaluator-plan.md` and ensure the assessor agent covers environment management, execution orchestration, and automated scoring in one loop.

By turning each stage into an autonomous agent (rather than a static script), the benchmark becomes:
- **Live:** Events and predictions refresh continually.
- **Evidence-grounded:** Every prediction ties to verifiable signals.
- **Self-evaluating:** The evaluator agent automatically scores outcomes and reasoning quality.
- **Extensible:** New agents (e.g., specialized evidence fetchers or anomaly detectors) can plug into the loop without re-architecting the benchmark.
