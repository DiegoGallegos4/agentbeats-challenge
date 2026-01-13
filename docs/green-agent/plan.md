# FutureBench-Finance Evaluator Roadmap

This document translates the requirements in [docs/research/research-spec.md](../research/research-spec.md) into an iterative delivery plan for the green (Evaluator) agent. It treats the public AgentBeats tutorial (<https://github.com/agentbeats/tutorial>) only as a toy example for scaffolding ideas; all authoritative requirements come from the research spec.

## Guiding Principles

- **Spec-first:** Every milestone ties back to the pipeline, schema, and metrics spelled out in [docs/research/research-spec.md](../research/research-spec.md) (§3–§10).
- **Iterative:** Deliver the smallest end-to-end slice that exercises ingestion → scoring → reporting, then expand capabilities.
- **Documented utilities:** Whenever evaluator behavior or helper tooling changes, update this file and any relevant `docs/` references per `AGENTS.md`.

## Glossary
- **Evidence Coverage (EC):** Are the key facts supporting a prediction present and cited?
- **Attribution Precision (AP):** Do cited facts truly support the claim (accurate, relevant, non-misleading)?
- **Reasoning Trace Quality (RTQ):** Clarity/coherence of the reasoning chain that links evidence to the claim.
- **Excess Log Score (ELS):** Model log score minus market/baseline log score.
- **MCP (Model Context Protocol):** Interface for exposing tools/endpoints to external agents.
- **A2A (Agent-to-Agent):** Protocol for connecting external purple agents to the green evaluator.

## Phase Breakdown (Aligned with [docs/green-agent/benchmark-definition.md](benchmark-definition.md) + [docs/green-agent/architecture.md](architecture.md))

### Phase 0 – Architecture & Schema Lock

- Finalize benchmark definition (goal/task/env/data/eval) and tooling map.
- Lock shared schemas (`EventSpec`, `PredictionRecord`, `ResolutionRecord`) and document the agentified architecture.
- Deliverable: signed-off design docs + config scaffolding; no runtime required.

### Phase 1 – Environment & Baseline Scoring ✅ *completed*

- Ingestion CLI + automation hooks publishing `EventSpec` snapshots (fixtures + Polymarket feed).
- Reference tool adapters (live news, optional Alpha Vantage) and purple-agent interface.
- Baseline evaluator scoring Accuracy/Brier live via `agentbeats run-evaluator` with summary + per-event explanations.
- Deliverable: end-to-end loop (ingest → predict → evaluate) operating on snapshots with docs/CLI support.

### Phase 2 – Metrics & Data Pipeline Hardening ✅ *completed*

- Expand tools to include Alpha Vantage (with on-disk cache); log tool calls with provenance.
- Persist structured run logs (`model × event × time`) for leaderboard and reproducibility.
- Optional metrics (ELS/Information Ratio, calibration, Kelly) skipped by default without a baseline; primary metrics remain Accuracy/Brier.
- Resolutions pipeline: `agentbeats generate-resolutions` creates placeholder `ResolutionRecord` JSONL from any event snapshot for downstream scoring.
- Deliverable: evaluator run produces stored artifacts for every prediction cycle; defaults to Accuracy/Brier, awaiting real resolutions to close the phase.

Phase 2 task breakdown:
- [x] Resolution fetchers: implement per-pattern resolvers (price close via Alpha Vantage; EDGAR evidence fetcher) writing Resolution-like JSONL.
- [x] Resolution CLI: commands to run price resolutions and generate placeholders (plus EDGAR evidence) with outputs under `data/generated/resolutions/` / `data/generated/edgar/`.
- [x] Coverage check: add a simple validator that flags events without resolutions or missing provenance/timestamps (see `agentbeats status coverage`).
- [x] Logging: evaluator runs persist artifacts to `data/generated/runs/`; tool logs/cache added for EDGAR/Alpha Vantage.

### Phase 3 – Evidence & Audit Agents

- Integrate EDGAR/XBRL adapters + evidence validation agents (DeepResearch-style) to score EC/AP/RTQ.
- Enforce leakage controls (timestamp checks, provenance hashing) and automated anomaly detection (missing evidence, fake pages).
- Provide audit reports + alerts that feed back into ingestion/predictor agents.
- Constraint: configuration is TOML-first (env vars only as fallbacks); new tools/agents must read settings from `config/agentbeats.toml` and document env override behavior.
- Deliverable: evaluator outputs quantitative scores plus qualitative evidence audits per event.

Phase 3 task breakdown:
- [ ] Evidence validation agent (LLM, LangChain, single-agent) to re-fetch/validate cited EDGAR facts and news snippets for EC/AP checks.
- [ ] Reusable LLM provider for purple agent (shared across tools/modules).
- [ ] Reasoning strategy pattern for purple agent (ReAct, Plan-and-Solve, ReWOO selectable).
- [ ] Reporting: per-event audit summaries (EC/AP/RTQ placeholders) in run artifacts.
- [ ] CLI/Docs: expose audit/evidence validation commands and document expected outputs.

Phase 3 milestones (planned):
- [ ] M3.1 Evidence validator baseline: single-agent LangChain pipeline that takes `PredictionRecord` evidence cites, re-fetches EDGAR/news snippets, and emits EC/AP judgements with provenance + timestamps stored under `data/generated/runs/<run_id>/audits/`.
  - Success: sample CLI run over fixtures produces JSONL with per-citation verdicts and a short RTQ note; leakage guard rejects evidence newer than `EventSpec.close_time`.
- [ ] M3.1b Live evidence validator: same pipeline running against real EDGAR/news data using `config/agentbeats.toml` credentials, with caching/rate-limit handling and provenance hashing.
  - Success: run over a live event sample completes without manual edits, logs tool calls, stores raw evidence + audit verdicts, and enforces leakage/timestamp checks.
- [ ] M3.2 LLM provider unification: shared provider module configurable via TOML (`llm.provider`, `llm.model`, rate limits) with env overrides only as fallbacks, reused by purple-agent tools/audits.
  - Success: predictor and evidence validator both call the shared provider; dry-run mode for offline tests documented.
- [ ] M3.3 Reasoning strategies: selectable strategy layer for the purple agent (ReAct, Plan-and-Solve, ReWOO) controlled by CLI flag/config.
  - Success: `agentbeats run predictor` accepts a `--strategy` flag; run logs capture chosen strategy and reasoning trace metadata.
- [ ] M3.4 Audit reporting: evaluator writes per-event audit summaries (EC/AP/RTQ + anomalies) alongside Accuracy/Brier outputs.
  - Success: `agentbeats run evaluator` (or `agentbeats run audit` if separated) drops human-readable summaries plus machine-readable JSONL under `data/generated/runs/<run_id>/`.
- [ ] M3.5 CLI/Docs: new audit command(s) and README table entries with examples/env vars; plan/architecture docs updated to reflect audit loop and leakage controls.
  - Success: `--help` for audit commands shows inputs/outputs; docs list expected artifacts and how to interpret audit scores.

### Phase 4 – Automation & Release

- Automate the full AAA loop: scheduled ingestion, predictor orchestration (A2A/MCP endpoints), resolution fetching, scoring, dashboards.
- Publish public leaderboards, documentation for new assessee agents, and ops runbooks.
- Deliverable: production-ready green agent that continuously curates tasks, manages tools, evaluates agents, and reports results without manual intervention.

Phase 4 task breakdown:
- [ ] Scheduling/orchestration: cron/runner for ingest → predict → resolve → evaluate.
- [ ] A2A/MCP endpoints: expose predictor/evaluator interfaces for external agents.
- [ ] Dashboards/leaderboards: surface metrics and run logs; publish public leaderboard.
- [ ] Ops/runbooks: document deployment, monitoring, and recovery procedures.
- [ ] Submission: baseline purple agent(s) A2A-compatible for competition demonstration.
- [ ] Submission: Docker image of green agent (end-to-end, no manual intervention).

## Cross-Agent & External Dependencies

- **Tool adapters:** news (critical), Alpha Vantage (high), EDGAR (medium), Polymarket (low) per [docs/green-agent/architecture.md](architecture.md).
- **Assessee agents:** purple-agent reference stays in repo for testing; external agents must speak the shared schema/A2A protocol.
- **Standards:** align with AgentBeats AAA (task/env/eval) requirements and MCP for tool access as they come online.

## Scoring & Metrics Roadmap

- **Phase 1 (done):** Accuracy + Brier computed from prediction/resolution JSONL via `agentbeats run-evaluator`.
- **Phase 2 (in progress):** Accuracy + Brier are the primary metrics. Optional metrics (ELS/Information Ratio, calibration, Kelly) are skipped unless a baseline probability is present.
- **Phase 3:** Evidence Coverage, Attribution Precision, Reasoning Trace Quality, leakage/contamination checks powered by audit agents.
- **Phase 4:** Automated dashboards/leaderboards summarizing all metrics and surfacing reliability/QA alerts.
