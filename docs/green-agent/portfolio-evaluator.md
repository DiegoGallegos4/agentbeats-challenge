# Portfolio Evaluator (Green Agent)

This green agent evaluates portfolio weights returned by a purple agent and computes simple PnL metrics using local market data.

## Request Format
The green agent expects a JSON payload in the A2A message:

```json
{
  "participants": {
    "agent": "http://localhost:9010"
  },
  "config": {
    "date": "2025-12-22",
    "pnl_date": "2025-12-23",
    "tickers": "subset",
    "download": false,
    "data_root": "/Volumes/ExtremePro/AV_data"
  }
}
```

Required fields:
- `participants.agent`: URL of the purple agent being evaluated.
- `config.date`: date for portfolio weights (YYYY-MM-DD).
- `config.pnl_date`: date used to compute PnL (YYYY-MM-DD).

Optional fields:
- `config.tickers`: forwarded to the purple agent (`subset`, `all`, comma-separated string, or list).
- `config.download`: if true, downloads market data for the evaluation date and `pnl_date`.
- `config.data_root`: overrides the local data root used by the evaluator.

## FinanceX Task Scoring Mode
To score FinanceX benchmark tasks, set `config.benchmark_path`. If you also provide `predictions_path`, the green agent scores those predictions without calling the purple agent.

```json
{
  "participants": {},
  "config": {
    "benchmark_path": "data/financeX_benchmark.jsonl",
    "predictions_path": "data/financeX_predictions.jsonl"
  }
}
```
If `predictions_path` is omitted, the green agent will call the purple agent with the benchmark tasks and score the returned predictions.

Current purple task mode uses a simple momentum baseline:
- Level 1: predicts "Yes" if prior close > close two days before.
- Level 2: selects tickers with prior close > close two days before.
- Level 3: predicts previous close.
- Level 4: predicts previous day's high-low range.

Prediction format (`predictions_path` JSONL):
```json
{"id": "financex-1-1", "answer": "Yes"}
{"id": "financex-2-1", "answer": ["AAPL", "MSFT"]}
{"id": "financex-3-1", "answer": 272.36}
{"id": "financex-4-1", "answer": 3.27}
```
The evaluator also accepts `prediction` as the value key if `answer` is not present.

Scoring notes:
- Level 1: 0/1 for correct Yes/No.
- Level 2: F1 score (F1) over the set of tickers that closed above their previous close.
- Level 3: numeric score using the FutureX formula with 7-day volatility.
- Level 4: numeric score on intraday range using the same formula.

## Output
The agent emits a single artifact named `Result` containing:
- Text summary (total PnL, avg return, hit rate, exposures, Sharpe, missing prices).
- JSON payload with per-ticker PnL rows and portfolio metrics.
- In FinanceX mode, the JSON payload includes per-level averages and per-task scores.
