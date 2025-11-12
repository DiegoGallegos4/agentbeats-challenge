# FutureBench-Finance Evaluator Roadmap

This document translates the requirements in `docs/research-spec.md` into an iterative delivery plan for the green (Evaluator) agent. It treats the public AgentBeats tutorial (<https://github.com/agentbeats/tutorial>) only as a toy example for scaffolding ideas; all authoritative requirements come from the research spec.

## Guiding Principles

- **Spec-first:** Every milestone ties back to the pipeline, schema, and metrics spelled out in `docs/research-spec.md` (§3–§10).
- **Iterative:** Deliver the smallest end-to-end slice that exercises ingestion → scoring → reporting, then expand capabilities.
- **Documented utilities:** Whenever evaluator behavior or helper tooling changes, update this file and any relevant `docs/` references per `AGENTS.md`.

## Phase Breakdown

### Phase 0 – Research & Scaffolding

- Extract evaluator-specific responsibilities from `docs/research-spec.md` (§3 pipeline block, §7–§8 metrics/procedure).
- Decide on baseline data fixtures (static predictor submissions + Polymarket/EDGAR resolutions) for offline development.
- Outline CLI/API surface for the evaluator (inputs, outputs, config), and capture open questions in this document.
- Deliverable: updated roadmap + clarified assumptions; no runtime code required yet.

### Phase 1 – v0.1 Evaluator MVP

- Implement ingestion of predictor outputs + event resolutions conforming to the task schema (`docs/research-spec.md:115-143`).
- Compute Accuracy and Brier Score only, matching the “Prediction Quality” block (§7).
- Provide a CLI/script that runs locally on the Phase 0 fixtures and emits a minimal report/JSONL.
- Ship paired Typer commands (`agentbeats run-predictor`, `agentbeats run-evaluator`) that exercise the fixtures end-to-end.
- Deliverable: reproducible MVP run plus documentation for required input file formats.

### Phase 2 – v0.2 Scoring Suite

- Extend storage to structured logs (JSONL/Parquet) covering `model × event × time` entries (`docs/research-spec.md:203-211`).
- Add Excess Log Score (ELS) and Information Ratio vs Polymarket baselines.
- Introduce calibration analyses (ECE, sharpness) with simple plotting or tabular summaries.
- Deliverable: evaluator run that outputs expanded metrics bundle and persists logs for leaderboard aggregation.

### Phase 3 – v0.3 Evidence Auditor

- Integrate a citation-checking helper (DeepResearch-like) to score Evidence Coverage (EC), Attribution Precision (AP), and Reasoning Trace Quality (RTQ) per §7.
- Enforce leakage controls ensuring all evidence timestamps precede event resolution (§7 Robustness).
- Coordinate with the purple agent (predictor) if richer rationales are needed; stub data is acceptable until then.
- Deliverable: evaluator report that includes evidence metrics and flags leakage violations.

### Phase 4 – v1.0 Automation & Release

- Automate the rolling evaluation loop (§8): scheduled ingestion, auto-resolution fetching, Kelly PnL/Sharpe computation.
- Produce leaderboard + rationale-audit outputs described in §10 (tables, plots, or dashboard-ready exports).
- Harden documentation (this file + any utility references) and define contributor guidelines for adding new agents or metrics.
- Deliverable: production-grade evaluator harness suitable for the competition track release.

## Cross-Agent & External Dependencies

- **Purple agent:** Keep as simple fixtures through Phase 2; plan a joint milestone with predictor updates before Phase 3 to ensure rationales are rich enough for auditing.
- **External services:** Polymarket API, EDGAR/EdgarAgent calls, and any DeepResearch sub-agent tooling; decide early which ones need mocks vs live access per phase.

## Next Steps

1. Close Phase 0 by validating assumptions with stakeholders and enumerating fixture requirements.
2. Start implementing the Phase 1 MVP in a dedicated module, updating this document as milestones complete.
