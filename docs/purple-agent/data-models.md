# Data Models & Lifecycle

This note documents the JSONL schema that flows through the FutureBench-Finance pipeline (ingestion → purple agent → evaluator), aligning with the FutureX-style datasets. All fields mirror the Pydantic models in `src/agentbeats/models.py`.

## EventSpec (ingestion output)

| Field | Type | Description |
| --- | --- | --- |
| `id` | `str` | Canonical event identifier (e.g., `poly_fin_2025_001`). |
| `question` | `str` | Human-readable forecast question. |
| `domain` | `str?` | Domain tag (`finance`, `markets`, etc.). |
| `resolution_date` | `datetime?` | ISO timestamp when the event resolves. |
| `source` | `EventSource?` | Origin metadata (prediction market, calendar). |
| `ground_truth_source` | `str?` | Where the final truth comes from (EDGAR 8-K, Polymarket). |
| `forecast_horizon_days` | `int?` | Days between prediction timestamp and resolution. |
| `tags` | `list[str]` | Topical labels (earnings, crypto). |
| `baseline_probability` | `float?` | Reference probability from the source market (used for ELS/Kelly). |

### EventSource

| Field | Type | Description |
| --- | --- | --- |
| `type` | `str` | Source type (e.g., `Polymarket`, `SEC`). |
| `market_id` | `str?` | Native identifier on the source platform. |
| `url` | `str?` | Source URL. |
| `resolution_date` | `datetime?` | Resolution timestamp recorded by the source. |

## PredictionRecord (purple agent output)

| Field | Type | Description |
| --- | --- | --- |
| `id` | `str` | Matches `EventSpec.id`. |
| `prediction` | `PredictionPayload` | Probability + rationale bundle. |
| `metadata` | `PredictionMetadata?` | Agent/runtime metadata. |

### PredictionPayload

| Field | Type | Description |
| --- | --- | --- |
| `probability` | `float [0,1]` | Forecasted probability of outcome=1. |
| `rationale` | `list[EvidenceItem]?` | Evidence objects cited for this forecast. |
| `analysis` | `str?` | Short reasoning summary derived from the evidence. |

### EvidenceItem

| Field | Type | Description |
| --- | --- | --- |
| `type` | `str` | Evidence modality (`market_snapshot`, `xbrl_fact`). |
| `source` | `str` | URL or identifier for the evidence. |
| `snippet` | `str?` | Human-readable summary. |
| `timestamp` | `datetime?` | When the evidence was observed. |

### PredictionMetadata

| Field | Type | Description |
| --- | --- | --- |
| `model` | `str` | Base LLM/agent name (`purple_stub`). |
| `timestamp` | `datetime` | When the prediction was generated. |
| `version` | `str?` | Code/config version. |
| `predictor_id` | `str?` | Unique identifier for the agent instance. |

## ResolutionRecord (evaluator input)

| Field | Type | Description |
| --- | --- | --- |
| `id` | `str` | Matches `EventSpec.id`. |
| `outcome` | `int (0/1)` | Binary result for the event. |
| `verified_value` | `float?` | Numeric truth (e.g., EPS). |
| `verified_source` | `str?` | URL/source of the resolved fact. |
| `resolved_at` | `datetime?` | Timestamp when the outcome was verified. |

## Lifecycle Summary

1. **Ingestion pipeline** produces `EventSpec` JSONL (daily FutureX-style crawl + curation).
2. **Purple agent** ingests those events, runs reasoning/tooling, emits `PredictionRecord` JSONL.
3. **Evaluator** reads the predictions + `ResolutionRecord` JSONL to compute metrics (Accuracy, Brier, etc.), eventually layering on evidence audits.
