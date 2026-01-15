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

## Output
The agent emits a single artifact named `Result` containing:
- Text summary (total PnL, avg return, hit rate, exposures, Sharpe, missing prices).
- JSON payload with per-ticker PnL rows and portfolio metrics.
