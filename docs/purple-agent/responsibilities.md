# Purple (Predictor) Agent Responsibilities

This note decomposes the purple agent’s duties below the level of `docs/research/research-spec.md`, using FutureX (<https://futurex-ai.github.io/>, <https://huggingface.co/futurex-ai>) and the “FutureX: An Advanced Live Benchmark for LLM Agents in Future Prediction” paper (arXiv:2508.11987) as the reference predictor style. It ensures the green evaluator can rely on well-formed submissions across all phases.

## Core Mission

Produce calibrated financial forecasts for FutureBench-Finance events by:

1. **Ingesting event specs** (Polymarket streams, SEC calendars) via the offline ingestion pipeline (`agentbeats ingest-events`).
2. **Collecting evidence** (EDGAR/XBRL facts, authoritative news, market snapshots).
3. **Reasoning over signals** using a FutureX-style agent loop (tool calls + reflections).
4. **Emitting predictions** that satisfy the benchmark schema (probability, rationale, citations, metadata).

## Functional Responsibilities

| Stage | Responsibility | Notes / References |
| --- | --- | --- |
| Task Intake | Normalize questions into the schema in `docs/research/research-spec.md:115-143`. | Align IDs, domains, timestamps, horizons. |
| Market Context | Pull Polymarket order book / price history to ground market comparison metrics. | Needed for ELS + Kelly sim later. |
| Evidence Retrieval | Use news fixtures/APIs (critical), EdgarAgent tools (`search_edgar_filings`, `xbrl_get`, etc.), plus `web_search`/`web_scraper`. | Must capture provenance (URL, factId). |
| Reasoning Loop | Follow FutureX predictor conventions (multi-step reasoning, reflection, error handling). | Output intermediate traces for RTQ scoring; enforce ≤30 min/question execution budgets per FutureX §3.2.3. |
| Forecast Generation | Quantitative probability (0–1), binary outcome definition, optional confidence intervals. | Store belief snapshots over time for rolling evaluation (§8). |
| Rationale Construction | Compose structured rationales referencing retrieved evidence objects. | Each citation maps to verifiable proof for EC/AP metrics and guards against fake-page failures noted in FutureX §1. |
| Submission Packaging | Serialize to JSONL/Parquet per task schema, include model identifiers, version, timestamp. | Compatible with evaluator ingestion Phase 1+. |
| Update Discipline | Decide when to refresh predictions (daily/weekly per §9). | Track deltas to support “Update Discipline” metric; mirror FutureX’s 70–100 event daily cadence (§3.2.3). |

## Interfaces & Contracts

- **Inputs**
  - Event descriptor (`id`, `question`, `resolution_date`, `ground_truth_source`).
  - Tool credentials/config (Polymarket API key, SEC/EdgarAgent endpoints).
  - Optional historical submissions for incremental updates.

- **Outputs**
  - `prediction.probability`: float probability before resolution.
  - `prediction.rationale`: ordered list of evidence objects with type, source, timestamp, snippet.
  - `prediction.analysis`: short reasoning summary derived from the gathered evidence.
  - `prediction.trace` (optional): reasoning steps for RTQ auditing.
  - `metadata`: model name, commit hash/config, tool versions, latency, cost metrics.

- **Validation Rules**
  - Evidence timestamps must precede `resolution_date`.
  - All external sources tagged with canonical IDs (CIKs, market IDs).
  - Probabilities remain within [0.01, 0.99] unless explicitly justified (prevents degenerate log loss).

## FutureX Alignment

- **Architecture Style:** Reuse FutureX’s agent scaffolding (task planner + solver + tool layer) inspired by frameworks such as SmolAgent and AgentOrchestra (§3.2.3), swapping in finance tools where needed.
- **Prompting:** Mirror FutureX’s structured prompting (problem statement → hypothesis → tool plan) while injecting finance-domain priors (earnings guidance, macro signals).
- **Daily Ops:** Schedule runs alongside the fully automated FutureX loop (event database → daily curation → agent prediction → answer acquisition, §3.2) and respect the shared Beijing-time timeline for timestamps. Offline ingestion (`agentbeats ingest-events`) produces the JSONL snapshot the purple agent consumes.
- **Data Artifacts:** Adopt FutureX’s JSONL logging format so predictions can later flow into Hugging Face datasets (e.g., `futurex-ai/futurebench-*`) for public benchmarking.
- **Failure Mode Mitigation:** Build defenses highlighted in the paper (fake web pages, temporal validity drift) by double-checking evidence timestamps, hashing retrieved HTML, and cross-verifying sources.

## Dependency Map

- **Evaluator (Green Agent):** Requires schema-compliant outputs, well-formed citations, and consistent model identifiers. Purple agent must version its configs to keep evaluator diffs meaningful.
- **Evidence Auditor:** Starting Phase 3, provide raw tool responses (or signed hashes) so leakage checks and EC/AP scoring can replay the evidence and evaluate planning/tool-use quality similar to SmolAgent analyses (§4.5).
- **Automation Loop:** Coordinate with scheduling/orchestration components when rolling evaluations go live (Phase 4), ensuring predictions arrive before each resolution window closes.

## Next Actions

1. Expand the purple-agent scaffold to pull high-priority news evidence (critical), adjusting probabilities + rationale fields accordingly.
2. Continue sharing ingestion snapshots + mock tool responses so both agents stay in sync.
3. Prototype safeguards for fake-page detection (e.g., multi-source verification, content hashing) ahead of Phase 3 evidence audits.
