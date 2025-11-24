# AGENTS.md

## Repository expectations

- `docs/research/research-spec.md` is the overall specification for the FutureBench-Finance track (pipeline, metrics, milestones).
- `docs/green-agent/plan.md` summarizes the phased roadmap for the green evaluator; Phase 1 is done, Phase 2 has Accuracy/Brier + run logging live (resolution pipeline added), optional baseline metrics are skipped by default.
- `docs/purple-agent/responsibilities.md` defines the purple agent contract (FutureX-aligned responsibilities, interfaces).
- `docs/purple-agent/data-models.md` documents the JSONL schema (EventSpec → PredictionRecord → ResolutionRecord) and lifecycle.
- `docs/tools/README.md` describes the shared tool adapters (news live fetcher, Alpha Vantage with caching; Polymarket adapter present but not used for evidence).
- Source layout:
  - `src/agentbeats/predictor/` contains the purple agent scaffold (fixture ingestion, rationale output, CLI hook).
- `src/agentbeats/evaluator/` holds the baseline evaluator tested via `agentbeats run-evaluator` (prints summary + per-event explanations). Primary metrics: Accuracy/Brier.
- CLI workflows (`agentbeats run-predictor`, `agentbeats run-evaluator`, `agentbeats show-predictions`) are described in `README.md`.
- Make a plan with milestones and come back to update those once those are completed.
- Document public utilities in `docs/` when you change behavior and use documents from there as context.
