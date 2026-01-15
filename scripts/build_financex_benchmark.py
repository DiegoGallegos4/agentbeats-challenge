#!/usr/bin/env python
"""Build a FinanceX benchmark dataset from FutureX rows and portfolio tickers."""

from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

import pandas as pd

LEVEL_MAP = {
    1: "Basic",
    2: "Wide Search",
    3: "Deep Search",
    4: "Super Agent",
}

PORTFOLIO_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def last_month_window(today: date) -> tuple[datetime, datetime]:
    first_of_month = today.replace(day=1)
    last_month_end = first_of_month - pd.Timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    return (
        datetime.combine(last_month_start, datetime.min.time()),
        datetime.combine(last_month_end, datetime.max.time()),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build FinanceX benchmark dataset.")
    parser.add_argument(
        "--input",
        default="data/futurex/data/train-00000-of-00001.parquet",
        help="FutureX parquet path",
    )
    parser.add_argument(
        "--output",
        default="data/financeX_benchmark.jsonl",
        help="Output JSONL path",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Missing input file: {input_path}")

    df = pd.read_parquet(input_path)
    df["end_time"] = pd.to_datetime(df["end_time"], errors="coerce", utc=True)

    start_dt, end_dt = last_month_window(date.today())
    start_dt = start_dt.replace(tzinfo=None)
    end_dt = end_dt.replace(tzinfo=None)

    df_filtered = df[
        (df["end_time"].dt.tz_convert(None) >= start_dt)
        & (df["end_time"].dt.tz_convert(None) <= end_dt)
    ]

    if df_filtered.empty and df["end_time"].notna().any():
        latest_period = df["end_time"].dt.to_period("M").max()
        df_filtered = df[df["end_time"].dt.to_period("M") == latest_period]
    df = df_filtered

    rows = []
    for _, row in df.iterrows():
        level = int(row["level"]) if pd.notna(row["level"]) else None
        level_name = LEVEL_MAP.get(level, "Unknown")
        for ticker in PORTFOLIO_TICKERS:
            rows.append(
                {
                    "id": f"{row['id']}-{ticker}",
                    "source_id": row["id"],
                    "ticker": ticker,
                    "end_time": row["end_time"].isoformat() if pd.notna(row["end_time"]) else None,
                    "level": level,
                    "level_name": level_name,
                    "prompt": row["prompt"],
                }
            )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_json(output_path, orient="records", lines=True)

    print(f"Wrote {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
