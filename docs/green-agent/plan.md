# FutureBench-Finance Evaluator Roadmap

This document translates the requirements in `docs/research/research-spec.md` into an iterative delivery plan for the green (Evaluator) agent. It treats the public AgentBeats tutorial (<https://github.com/agentbeats/tutorial>) only as a toy example for scaffolding ideas; all authoritative requirements come from the research spec.

## Guiding Principles

- **Spec-first:** Every milestone ties back to the pipeline, schema, and metrics spelled out in `docs/research/research-spec.md` (§3–§10).
- **Iterative:** Deliver the smallest end-to-end slice that exercises ingestion → scoring → reporting, then expand capabilities.
- **Documented utilities:** Whenever evaluator behavior or helper tooling changes, update this file and any relevant `docs/` references per `AGENTS.md`.

## Phase Breakdown (Aligned with `docs/benchmark-definition.md` + `docs/architecture.md`)

### Phase 0 – Architecture & Schema Lock

- Finalize benchmark definition (goal/task/env/data/eval) and tooling map.
- Lock shared schemas (`EventSpec`, `PredictionRecord`, `ResolutionRecord`) and document the agentified architecture.
- Deliverable: signed-off design docs + config scaffolding; no runtime required.

### Phase 1 – Environment & Baseline Scoring ✅ *completed*

- Stand up ingestion CLI + automation hooks that publish `EventSpec` snapshots from curated sources.
- Provide reference tool adapters (news fixture now) and a purple-agent interface so predictors can connect.
- Implement Baseline evaluator scoring Accuracy/Brier, expose CLI/API (`agentbeats run-evaluator`).
- Deliverable: end-to-end loop (ingest → predict → evaluate) operating on fixtures with documentation on how to run agents.

### Phase 2 – Metrics & Data Pipeline Hardening

- Expand tools to include Alpha Vantage + Polymarket data extraction; log all tool calls with provenance.
- Persist structured run logs (`model × event × time`) for leaderboard and reproducibility.
- Add market-aware metrics (ELS, Information Ratio), calibration curves, Kelly PnL simulations.
- Deliverable: evaluator run produces comprehensive metric bundle + stored artifacts for every prediction cycle.

### Phase 3 – Evidence & Audit Agents

- Integrate EDGAR/XBRL adapters + evidence validation agents (DeepResearch-style) to score EC/AP/RTQ.
- Enforce leakage controls (timestamp checks, provenance hashing) and automated anomaly detection (missing evidence, fake pages).
- Provide audit reports + alerts that feed back into ingestion/predictor agents.
- Deliverable: evaluator outputs quantitative scores plus qualitative evidence audits per event.

### Phase 4 – Automation & Release

- Automate the full AAA loop: scheduled ingestion, predictor orchestration (A2A/MCP endpoints), resolution fetching, scoring, dashboards.
- Publish public leaderboards, documentation for new assessee agents, and ops runbooks.
- Deliverable: production-ready green agent that continuously curates tasks, manages tools, evaluates agents, and reports results without manual intervention.

## Cross-Agent & External Dependencies

- **Tool adapters:** news (critical), Alpha Vantage (high), EDGAR (medium), Polymarket (low) per `docs/architecture.md`.
- **Assessee agents:** purple-agent reference stays in repo for testing; external agents must speak the shared schema/A2A protocol.
- **Standards:** align with AgentBeats AAA (task/env/eval) requirements and MCP for tool access as they come online.

## Scoring & Metrics Roadmap

- **Phase 1 (done):** Accuracy + Brier computed from prediction/resolution JSONL via `agentbeats run-evaluator`.
- **Phase 2:** Add Excess Log Score, Information Ratio, calibration curves, Kelly PnL; persist structured logs for reproducibility.
- **Phase 3:** Evidence Coverage, Attribution Precision, Reasoning Trace Quality, leakage/contamination checks powered by audit agents.
- **Phase 4:** Automated dashboards/leaderboards summarizing all metrics and surfacing reliability/QA alerts.

## Next Steps

1. Close Phase 0 by confirming benchmark definition + architecture docs with stakeholders.
2. Execute Phase 1 deliverables: ingestion snapshot automation, tool interface stubs, Baseline evaluator CLI.
