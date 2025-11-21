# Green (Evaluator) Agent Responsibilities

This document distills what the green agent must deliver to “agentify” the FutureBench-Finance benchmark. It pairs with `docs/architecture.md`, `docs/benchmark-definition.md`, and the roadmap in `docs/evaluator-plan.md`.

## Mission & Judging Criteria Alignment

Act as the autonomous assessor (Goal & Novelty) that defines the environment, issues tasks, manages tools, and computes evaluation metrics. The benchmark must:
- Demonstrate clear importance/novelty by covering finance forecasting (Goal & Novelty).
- Span multiple domains/time horizons to ensure reliable conclusions (Scope & Scale).
- Offer high-quality, consistent metrics and judges (Evaluator Quality).
- Include spot checks / manual validation of outputs (Validation).
- Run robustly inside AgentBeats without flaky scripts (Reliability).
- Incorporate bias/leakage/contamination guards (Quality Assurance).
- Reflect realistic workloads (live Polymarket/EDGAR/Alpha Vantage feeds) rather than toy tasks (Realism).
- Be reusable and well-documented (Impact).

## Responsibilities

1. **Environment Curation**
   - Build and maintain the event stream (`EventSpec` packets) via automated ingestion/curation.
   - Ensure events cover finance domains (Polymarket, EDGAR, macro) with proper metadata, tags, and resolution timelines.

2. **Tool & Execution Management**
   - Expose evidence tools (news, EDGAR/XBRL, Alpha Vantage, Polymarket) through consistent interfaces (A2A/MCP).
   - Schedule/trigger predictor runs, enforcing time budgets (≤30 min/question) and logging execution metadata.

3. **Resolution Capture**
   - Harvest ground truth from authoritative sources (Polymarket resolutions, EDGAR filings) and persist `ResolutionRecord` entries with provenance.
   - Handle delayed or missing answers via retries and status tracking.

4. **Scoring & Auditing**
   - Compute quantitative metrics (Accuracy, Brier, ELS, calibration, Kelly PnL) and qualitative audits (Evidence Coverage, Attribution Precision, Reasoning Trace Quality, leakage checks).
   - Run spot validations/manual checks on assessor outputs to guarantee Evaluator Quality & Validation.
   - Store per-run artifacts (`model × event × time` logs, tool traces) for reproducibility and later inspection (Reliability & Impact).

5. **Reporting & Alerts**
   - Produce dashboards/leaderboards, publish run summaries, and surface alerts when tasks lack evidence, events go stale, or agents misbehave.
   - Provide APIs/CLI endpoints so assessee agents and operators can retrieve results; document bias/leakage mitigations (Quality Assurance).

## Interfaces

- **Inputs:** Prediction JSONL (`PredictionRecord`), ingestion snapshots (`EventSpec`), resolution feeds, tool outputs.
- **Outputs:** Score bundles, audit reports, event snapshots, and monitoring signals (alerts/logs) consumable by both predictor teams and platform ops.

## Alignment with Phases

- *Phase 1:* initial environment + baseline scoring.
- *Phase 2:* tool integration + metric expansion.
- *Phase 3:* evidence audits + leakage defenses.
- *Phase 4:* full automation + reporting infrastructure.

This responsibilities outline keeps the green agent focused on being a self-sufficient assessor so independent teams can develop assessee agents in parallel.
