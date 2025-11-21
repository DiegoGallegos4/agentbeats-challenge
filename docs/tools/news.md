# News Evidence Tool

## Purpose

Provide timely articles and sentiment signals for financial events (earnings, macro, crypto). Critical priority per `docs/architecture.md`.

## Interface

- **Input:** event tags (`list[str]`), optional ticker/company keywords, time window.
- **Output:** list of evidence objects containing:
  - `title`, `url`, `published_at`
  - `summary/snippet`
  - sentiment score ([-1, 1])
- **Usage:** Purple agents call this tool to populate `EvidenceItem` entries; green agents can replay the call to validate provenance/timestamps.

## Implementation Notes

- The concrete fetcher hits Google News RSS (`https://news.google.com/rss/search?q=...`) and logs each request.
- If the RSS call fails or returns nothing, it falls back to optional fixtures (`data/fixtures/news/sample_news.json`).
- Add anti-leakage safeguards (timestamp filters, hashed content) as the pipeline matures.
