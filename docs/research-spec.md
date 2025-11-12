# 🧾 FutureBench-Finance Track Specification

**Extending FutureBench with Polymarket and EdgarAgent for Financial Forecasting**

---

## 1. Overview

**Goal:**
Expand the existing **FutureBench** benchmark beyond general event prediction to include **financial, regulatory, and market-driven forecasts**, leveraging:

* **Polymarket** (real-time prediction market data) as *live signal source*
* **EdgarAgent** (SEC/XBRL tool-using LLM agent) as *finance evidence retriever & reasoning layer*

This track evaluates how well LLMs and LLM-agents can:

1. Predict **future financial outcomes** (earnings beats/misses, guidance changes, macro events).
2. Provide **verifiable evidence** (EDGAR filings, XBRL facts, authoritative news).
3. Demonstrate **calibrated, consistent reasoning** over time.

---

## 2. Motivation

| Problem                                 | Limitation in existing benchmarks                          | This track adds                                       |
| --------------------------------------- | ---------------------------------------------------------- | ----------------------------------------------------- |
| Financial forecasting under uncertainty | Current FutureBench sources are general (sports, politics) | High-impact, evidence-rich finance tasks              |
| Lack of verifiable data                 | FutureX/ProphetArena rely on crowd resolutions             | EDGAR filings & XBRL → objective numeric ground truth |
| Weak interpretability                   | Forecast rationales unverified                             | Evidence trace & compliance grounding                 |
| Missing economic calibration            | Accuracy ≠ financial intelligence                          | Return simulation & market-calibrated Brier scores    |

---

## 3. Architecture (Pipeline)

```
[Polymarket + SEC Calendar]
          │
          ▼
 ┌───────────────────────────┐
 │ Question Generator        │
 │  - Extracts finance events│
 │  - Normalizes schema      │
 └────────────┬──────────────┘
              │
              ▼
 ┌───────────────────────────┐
 │ Predictor Agents          │
 │  - Base LLMs (GPT-4, Claude) │
 │  - EdgarAgent (XBRL tools)│
 └────────────┬──────────────┘
              │
              ▼
 ┌───────────────────────────┐
 │ Evidence Collector        │
 │  - EdgarAgent (search_edgar_filings, xbrl_get) │
 │  - web_search, web_scraper │
 └────────────┬──────────────┘
              │
              ▼
 ┌───────────────────────────┐
 │ Prediction Logger         │
 │  - Records P(model), rationale, citations │
 └────────────┬──────────────┘
              │
              ▼
 ┌───────────────────────────┐
 │ Event Resolution Engine   │
 │  - Fetches Polymarket result │
 │  - Or uses EDGAR truth post-filing │
 └────────────┬──────────────┘
              │
              ▼
 ┌───────────────────────────┐
 │ Evaluator (Scoring)       │
 │  - Accuracy, Brier, ELS, EC, RTQ │
 └───────────────────────────┘
```

---

## 4. Data Sources

| Type                       | Source                                     | Examples                          | Access             |
| -------------------------- | ------------------------------------------ | --------------------------------- | ------------------ |
| **Prediction markets**     | Polymarket API                             | “Will BTC > $100K by Dec 2025?”   | REST/WebSocket     |
| **Earnings events**        | SEC Edgar / Nasdaq Calendar                | “Will TSLA beat Q3 EPS guidance?” | EdgarAgent tools   |
| **Macroeconomic releases** | BEA, FRED                                  | “Will CPI YoY < 3%?”              | RSS / API          |
| **News evidence**          | Web search, Google Finance, Reuters        | context for rationale             | `web_search`       |
| **Ground truth**           | Polymarket resolutions, SEC 8-K/XBRL facts | numeric verification              | automated scraping |

---

## 5. Tool Interfaces

**Inherited from FutureBench:**

* `web_search(query[])`
* `web_scraper(url, goal?)`
* `code_interpreter(code)`
* `file_parser(file, format)`

**Finance extensions (via EdgarAgent):**

* `search_edgar_filings(company, form, year)`
* `xbrl_get(instance_url, tag, context_hint)`
* `diff_sections(url_y1, url_y2, section)`
* `classify_compliance_item(text)`
* `compute_ratio(expr, bindings)`

All tools return structured JSON with provenance (URL or factId).

---

## 6. Task Schema

```json
{
  "id": "poly_fin_2025_001",
  "domain": "finance",
  "question": "Will Tesla beat EPS guidance for Q3 2025?",
  "source": {
    "type": "Polymarket",
    "market_id": "xyz123",
    "resolution_date": "2025-11-05"
  },
  "ground_truth_source": "EDGAR 8-K",
  "predictor": "edgar_agent_v1",
  "timestamp": "2025-10-29T00:00:00Z",
  "prediction": {
    "probability": 0.68,
    "rationale": [
      {"type":"xbrl_fact","tag":"us-gaap:EarningsPerShareDiluted","value":2.11,"context":"Q3FY2024"},
      {"type":"news","url":"https://reuters.com/tesla-guidance-oct-25"}
    ]
  },
  "resolution": {
    "outcome": 1,
    "verified_value": 2.27,
    "verified_source": "https://www.sec.gov/.../8-k.htm"
  }
}
```

---

## 7. Evaluation Metrics

| Category                 | Metric                        | Description                                           |
| ------------------------ | ----------------------------- | ----------------------------------------------------- |
| **Prediction Quality**   | Accuracy                      | 1 if correct binary prediction; else 0                |
|                          | Brier Score                   | Mean squared error between predicted prob and outcome |
|                          | Log Loss                      | Penalizes overconfident errors                        |
| **Market Comparison**    | **Excess Log Score (ELS)**    | log p(model)(y_true) − log p(market)(y_true)          |
|                          | Information Ratio             | Mean(ELS)/Std(ELS)                                    |
| **Calibration**          | ECE / Reliability             | Confidence vs actual accuracy bins                    |
|                          | Sharpness                     | Entropy of belief distribution                        |
| **Temporal Dynamics**    | Time-Weighted Brier           | Reward early correct forecasts                        |
|                          | Update Discipline             | Penalize unjustified large belief swings              |
| **Evidence & Reasoning** | Evidence Coverage (EC)        | Fraction of key facts properly cited                  |
|                          | Attribution Precision (AP)    | Citation validity (anchors, XBRL tags)                |
|                          | Reasoning Trace Quality (RTQ) | Coherence of chain-of-thought                         |
| **Economic Return**      | Kelly PnL / Sharpe            | Simulated trading profitability                       |
| **Robustness**           | Leakage-Control Pass          | All evidence predates event date                      |

---

## 8. Evaluation Procedure

1. **At time t₀ (before event)**
   Model/agent produces `p(event)`, rationale, citations.
   → Logged into benchmark store.

2. **After event resolves (t_resolve)**
   Fetch ground truth from Polymarket or EDGAR.
   → Compute Accuracy, Brier, ELS, etc.

3. **Evidence audit**
   DeepResearch sub-agent validates citations (e.g., EDGAR anchors resolve).
   → Compute EC, AP, RTQ.

4. **Economic evaluation**
   Simulate market trades using Polymarket price series.
   → Compute Kelly-PnL metrics.

5. **Composite score (optional)**
   Weighted sum of standardized sub-scores.
   Example weighting:

   ```
   0.25 Accuracy
   0.25 Brier/ELS
   0.20 Evidence (EC+AP)
   0.15 RTQ
   0.10 Temporal Dynamics
   0.05 Efficiency
   ```

---

## 9. Experimental Design

| Aspect                | Setting                                                          |
| --------------------- | ---------------------------------------------------------------- |
| **Frequency**         | Daily or weekly prediction refresh                               |
| **Forecast horizon**  | 7d – 30d                                                         |
| **Models**            | LLMs (GPT-4o/Claude), EdgarAgent, ensemble variants              |
| **Domains**           | Finance (EDGAR), Macroeconomy (CPI, FOMC), Markets (BTC, S&P500) |
| **Evaluation window** | Rolling, auto-recompute upon resolution                          |
| **Storage**           | JSONL or Parquet, one entry per (model × event × time)           |

---

## 10. Analysis Outputs

* **Leaderboard**

  * Accuracy, Brier, ELS, Sharpe, EC, RTQ
  * Split by domain & prediction horizon.

* **Rationale audit dashboards**

  * Show cited sources, EDGAR anchors, tag validity.
  * Identify hallucinated or post-event evidence.

* **Temporal calibration plots**

  * Forecast evolution vs market odds.

* **Error taxonomy**

  * Miscalibration, wrong evidence, wrong causal model, delayed updates.

---

## 11. Implementation Plan (Milestones)

| Phase                          | Deliverables                                    | Target |
| ------------------------------ | ----------------------------------------------- | ------ |
| **v0.1 Prototype**             | Integrate Polymarket API + static EDGAR queries | Week 2 |
| **v0.2 Data Schema + Scorer**  | JSONL logging + Brier/ELS computation           | Week 4 |
| **v0.3 Evidence Validation**   | DeepResearch citation checker                   | Week 6 |
| **v1.0 Finance Track Release** | Full evaluation harness + dashboard             | Week 8 |

---

## 12. Research Impact

| Dimension            | Contribution                                                                     |
| -------------------- | -------------------------------------------------------------------------------- |
| **Benchmarking**     | First *live* benchmark combining prediction markets and regulatory filings.      |
| **Interpretability** | Introduces evidence & reasoning metrics for forecasting.                         |
| **Finance AI**       | Tests LLMs on tasks directly relevant to earnings analysis and market sentiment. |
| **Agent Evaluation** | Merges ReAct reasoning trace evaluation with market-based scoring.               |
| **Open Science**     | Provides reproducible daily snapshot + automated scoring pipeline.               |

---

## 13. Example Evaluation Output

| Model | Domain | Accuracy | Brier ↓ | ELS ↑ | EC ↑ | RTQ ↑ | Sharpe ↑ |
|--------|---------|-----------|-----------|----------|---------|-----------|
| GPT-4o | General | 0.61 | 0.19 | +0.03 | 0.42 | 0.37 | 0.11 |
| EdgarAgent | Finance | 0.74 | 0.14 | +0.09 | 0.83 | 0.72 | 0.48 |
| Ensemble | All | 0.69 | 0.16 | +0.06 | 0.59 | 0.55 | 0.27 |

---

## 14. Future Work

* **Multi-modal forecasts:** combine numeric + textual evidence (charts, filings, news).
* **Rationale quality models:** train verifier to judge evidence relevance.
* **Cross-market aggregation:** unify Polymarket + Kalshi + synthetic “expert consensus.”
* **Causal validation:** test if cited variables truly predict outcome historically.

---

### TL;DR

> **FutureBench-Finance** turns prediction-market benchmarking into *evidence-grounded financial reasoning*.
> It uses **Polymarket** for live event streams and **EdgarAgent** for verifiable, SEC-based rationale — scored on **accuracy, calibration, profitability, and reasoning quality**.
