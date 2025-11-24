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

- Ingestion CLI + automation hooks publishing `EventSpec` snapshots (fixtures + Polymarket feed).
- Reference tool adapters (live news, optional Alpha Vantage) and purple-agent interface.
- Baseline evaluator scoring Accuracy/Brier live via `agentbeats run-evaluator` with summary + per-event explanations.
- Deliverable: end-to-end loop (ingest → predict → evaluate) operating on snapshots with docs/CLI support.

### Phase 2 – Metrics & Data Pipeline Hardening (in progress)

- Expand tools to include Alpha Vantage (with on-disk cache); log tool calls with provenance.
- Persist structured run logs (`model × event × time`) for leaderboard and reproducibility.
- Optional metrics (ELS/Information Ratio, calibration, Kelly) skipped by default without a baseline; primary metrics remain Accuracy/Brier.
- Resolutions pipeline: `agentbeats generate-resolutions` creates placeholder `ResolutionRecord` JSONL from any event snapshot for downstream scoring.
- Deliverable: evaluator run produces stored artifacts for every prediction cycle; defaults to Accuracy/Brier, awaiting real resolutions to close the phase.

Phase 2 task breakdown:
- [ ] Resolution fetchers: implement per-pattern resolvers (e.g., price close fetcher for ticker questions; manual/EPS fetcher stub for earnings-type questions) writing `ResolutionRecord` JSONL.
- [ ] Resolution CLI: add a command to run resolution acquisition over an events file and persist to `data/generated/resolutions/latest.jsonl`.
- [ ] Coverage check: add a simple validator that flags events without resolutions or missing provenance/timestamps.
- [ ] Logging: ensure resolution runs write logs/artifacts to `data/generated/runs/` alongside evaluator runs.

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
- **Phase 2 (in progress):** Accuracy + Brier are the primary metrics. Optional metrics (ELS/Information Ratio, calibration, Kelly) are skipped unless a baseline probability is present.
- **Phase 3:** Evidence Coverage, Attribution Precision, Reasoning Trace Quality, leakage/contamination checks powered by audit agents.
- **Phase 4:** Automated dashboards/leaderboards summarizing all metrics and surfacing reliability/QA alerts.

## Resolution Pipeline (Phase 2 Close-out)

- Use `agentbeats generate-resolutions` (or `scripts/generate_resolutions.py`) to create placeholder `ResolutionRecord` JSONL from any event snapshot; edit outcomes/values as truth arrives.
- Wire resolution acquisition (manual/scripted) for watchlist/live events so scoring is unblocked without fixtures.

## Next Steps

1. Finalize the resolution pipeline and mark Phase 2 complete with Accuracy/Brier as defaults.
2. Keep optional metrics disabled unless a baseline is provided; treat them as Phase 3+ enhancements.
