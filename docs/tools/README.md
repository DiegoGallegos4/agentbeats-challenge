# Tools Overview

Tools are shared capabilities accessed by both assessor (green) and predictor (purple) agents. Each tool adapter must provide:
- **Inputs:** required parameters (e.g., ticker, form type, date range).
- **Outputs:** structured data with timestamps, provenance URLs, and any confidence scores.
- **Usage:** how the purple agent calls it during reasoning, and how the green agent may replay/validate the call.

## Current & Planned Tools

| Tool | Priority | Status | Notes |
| --- | --- | --- | --- |
| News evidence fetcher | Critical | Implemented via fixtures (`src/agentbeats/predictor/news.py`) | Upgrade to live API later. |
| Alpha Vantage | High | Planned | Market/macro time series. |
| EDGAR / EdgarAgent | Medium | Planned | Filings, XBRL facts, compliance checks. |
| Polymarket API | Low | Planned | Markets for event ingestion + odds baselines. |

Each tool will get its own spec (see individual Markdown files in this directory) detailing API schemas, rate limits, and provenance requirements.
