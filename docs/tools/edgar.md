# EDGAR / EdgarAgent Tool

Lightweight evidence fetcher that pulls recent filings from the SEC submissions feed for use in rationales and audits.

## Purpose

Retrieve SEC filings (8-K, 10-Q, 10-K) and expose them as `EvidenceItem` entries so predictors can cite filings and evaluators can validate provenance/timestamps.

## Interface (implemented)

- **Inputs:** event with ticker tag (or `source.market_id`), optional ticker→CIK map, target form types (default: 8-K, 10-Q).
- **Outputs:** list of `EvidenceItem` with `type="edgar_filing"`, `source` = SEC URL, `snippet` = form + filed date, `timestamp` = filing date.
- **Usage:**
  - `EdgarEvidenceFetcher.fetch_latest(event, forms=("8-K","10-Q"), limit=1)`
  - Returns `[]` if no ticker/CIK, network failure, or no recent filings of the requested forms.

## Behavior

- **User-Agent:** Uses `SEC_USER_AGENT` env var or a default string. SEC expects contact info in User-Agent.
- **Ticker→CIK lookup:** Accepts a provided map; otherwise downloads/caches `company_tickers.json` from SEC and keeps it in `data/generated/tool_cache/edgar/`.
- **Submissions feed:** Fetches `https://data.sec.gov/submissions/CIK{cik}.json`, caches responses under `data/generated/tool_cache/edgar/`, and logs requests to `data/generated/tool_logs/edgar.jsonl`.
- **Evidence construction:** Builds SEC filing URLs from CIK + accession + primary document and attaches filing dates as `timestamp`.
- **Failure mode:** Soft-fails (returns `[]`, logs error) on network or parsing errors to avoid breaking predictor runs.

## Next extensions

- Add XBRL fact extraction (e.g., EPS tags) for numeric ground truth.
- Add leakage guardrails (drop filings after event resolution timestamp).
- Integrate with a richer EdgarAgent toolchain (`search_edgar_filings`, `xbrl_get`, `diff_sections`) when available.

## Proposed module interface (agent-ready)

- **Fetcher (tool adapter)**
  - `EdgarEvidenceFetcher.fetch_latest(event, forms=("8-K","10-Q","10-K"), limit=1) -> list[EvidenceItem]`
    - Returns filing-level evidence (`type="edgar_filing"`, SEC URL, filed date in `timestamp`).
  - `EdgarEvidenceFetcher.fetch_facts(event, tags, forms=("10-Q","10-K","8-K"), limit=1) -> list[dict]`
    - Structured companyfacts entries from SEC: `{tag, value, unit, period_start, period_end, filed_at, source_url, accession, context_ref, form}`.
  - Config: `user_agent`, `ticker_map`, `cache_dir` (`data/generated/tool_cache/edgar/`), `logger` (`data/generated/tool_logs/edgar.jsonl`), optional leakage cutoff.

- **Evidence module (predictor/evaluator)**
  - `EdgarEvidenceModule.gather(event) -> EvidencePayload`
    - Steps: resolve ticker→CIK; fetch latest filings; optionally parse key XBRL tags (EPS diluted/basic, revenue, net income, cash from ops); emit `EvidenceItem` entries for filings and facts; `signal` is optional numeric heuristic; `messages` hold diagnostics. Soft-fails to `[]` on errors.

- **Resolution helper (earnings-style)**
  - `to_resolution(event, facts, tag) -> ResolutionRecord?` *(planned)*
    - Picks a target tag (e.g., EPS), sets `verified_value`, `verified_source` (SEC URL), `resolved_at` (filing date), and derives `outcome` from the question predicate.
