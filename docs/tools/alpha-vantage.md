# Alpha Vantage Tool (Planned)

## Purpose

Fetch real-time and historical financial data (prices, indicators) for equities, FX, crypto, and macro series. High priority for quantitative evidence and Kelly PnL simulations.

## Interface (proposed)

- **Input:** symbol/ticker, function (TIME_SERIES_DAILY, FX_DAILY, etc.), optional range.
- **Output:** JSON structure with timestamps, open/high/low/close/volume, or indicator values.
- **Usage:** Purple agents derive signals (momentum, volatility) for predictions; green agents may compare predictions against market baselines for ELS/Kelly metrics.

## Considerations

- Requires API key + rate-limit handling.
- Store raw responses + derived features for audit replay.
- Align timestamps (UTC) and guard against post-event leakage.
