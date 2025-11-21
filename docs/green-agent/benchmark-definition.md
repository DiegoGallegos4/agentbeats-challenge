# FutureBench-Finance Benchmark Definition

Following the AgentBeats framing (see AAA blog and Tau-Bench/CyberGym examples), every benchmark description should answer five questions: **goal, task, environment, data generation pipeline, and evaluation.** This document captures our answers so the green agent remains aligned with the competition requirements.

## Goal

Provide a live, evidence-grounded assessment of financial forecasting agents. The benchmark measures how well predictor agents combine market signals (Polymarket), regulatory filings (EDGAR/XBRL), macro indicators (Alpha Vantage), and news to produce calibrated beliefs about future events. Success criteria mirror FutureX: automation, reproducibility, and transparent reasoning.

## Tasks

- Binary finance predictions (e.g., “Will Tesla beat Q3 EPS guidance?” “Will BTC close above $100K by Dec 2025?”).
- Tasks arrive daily/weekly with metadata: domain, resolution date, source identifiers, evidence requirements.
- Each task demands (1) pre-resolution probability, (2) structured rationale citing evidence, and (3) analysis text summarizing the reasoning.

## Environment

- Managed by the green agent (see `docs/architecture.md`): includes ingestion pipelines, tool adapters (news, EDGAR, Alpha Vantage, Polymarket), MPC/A2A endpoints, and scheduling automation.
- Provides task packets (`EventSpec` JSONL), tool credentials, and execution budgets (≤30 min/question) to predictor agents.
- Maintains provenance/logging so the evaluator can replay any interaction.

## Data Generation Pipeline

1. **Ingestion:** crawl/monitor high-quality finance sources (Polymarket markets, SEC calendars, macro feeds) → normalize into `EventSpec` + `EventSource`.
2. **Curation:** filter for uniqueness, attach tags (earnings, crypto, macro), and randomize variables (forecast horizons, tickers) to avoid memorization.
3. **Snapshotting:** publish daily event packets for agents (`agentbeats ingest-events` currently generates fixtures; future versions wire into live feeds).
4. **Resolution acquisition:** fetch ground truth automatically from Polymarket or EDGAR filings (mirroring FutureX answer acquisition).

## Evaluation

- **Quantitative metrics (Phase 1→2):** Accuracy, Brier, Excess Log Score, Information Ratio, calibration profiles, Kelly PnL.
- **Evidence/Reasoning audits (Phase 3):** Evidence Coverage, Attribution Precision, Reasoning Trace Quality, leakage checks; relies on stored tool traces/rationales.
- **Automation (Phase 4):** continuous evaluation loop with dashboards/leaderboards, alerting when agents miss evidence or events go stale.

This componentized view (goal/task/env/data pipeline/eval) mirrors the AAA/Tau-Bench/CyberGym pattern, ensuring the FutureBench-Finance benchmark is described at the right abstraction level for AgentBeats integration.
