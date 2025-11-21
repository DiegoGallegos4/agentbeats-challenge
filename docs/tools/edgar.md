# EDGAR / EdgarAgent Tool (Planned)

## Purpose

Retrieve SEC filings and XBRL facts for evidence-based reasoning and ground-truth verification.

## Interface (proposed)

- **Inputs:** company identifier (CIK/ticker), form type (8-K/10-Q), fiscal period, specific XBRL tags.
- **Outputs:** structured filings metadata (URL, filing date) + extracted numerical/textual facts (value, context, units).
- **Usage:**
  - Purple agents cite EDGAR facts in rationales (`EvidenceItem` with type `xbrl_fact`).
  - Green agents validate citations by requerying and confirming timestamps (leakage checks).

## Considerations

- Integrate with EdgarAgent toolset (search, `xbrl_get`, `diff_sections`) when available.
- Cache responses + hashed sections to detect content drift.
- Enforce pre-resolution timestamps to satisfy leakage-control metrics.
