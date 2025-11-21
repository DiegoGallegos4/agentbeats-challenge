# Polymarket Tool (Planned)

## Purpose

Supply market questions, odds snapshots, and resolution data for both ingestion and evaluation.

## Interface (proposed)

- **Inputs:** market ID or query filters (topic, resolution date).
- **Outputs:** market metadata (question, outcomes, prices, liquidity) and resolution status.
- **Usage:**
  - Ingestion agent crawls markets to populate `EventSpec` entries.
  - Purple agents use odds as priors/evidence; evaluator uses price series for ELS/Kelly comparisons.

## Considerations

- REST/WebSocket endpoints with rate limits; need caching and provenance tracking.
- Ensure snapshots match pre-resolution timestamps to avoid leakage.
- Store price histories for evaluator metrics (Time-Weighted Brier, ELS).
