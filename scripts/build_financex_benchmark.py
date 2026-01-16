#!/usr/bin/env python
"""Build a FinanceX benchmark dataset from FutureX rows and portfolio tickers."""

from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

LEVEL_MAP = {
    1: "Basic",
    2: "Wide Search",
    3: "Deep Search",
    4: "Super Agent",
}

PORTFOLIO_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def parse_date_dir(path: Path) -> date | None:
    try:
        return datetime.strptime(path.name, "%Y-%m-%d").date()
    except ValueError:
        return None


def pick_latest_market_files(data_root: Path, tickers: Iterable[str]) -> dict[str, Path]:
    latest = {}
    for ticker in tickers:
        candidates = []
        for path in data_root.glob(f"*/market/{ticker}.csv"):
            dir_date = parse_date_dir(path.parent.parent)
            if dir_date is not None:
                candidates.append((dir_date, path))
        if candidates:
            candidates.sort(key=lambda item: item[0], reverse=True)
            latest[ticker] = candidates[0][1]
    return latest


def load_market_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")
    return df.reset_index(drop=True)


def build_level1(records: list[dict], count: int) -> list[dict]:
    rows = []
    for record in records[:count]:
        threshold = round(record["prev_close"], 2)
        rows.append(
            {
                "prompt": (
                    f'Will {record["ticker"]} close above ${threshold:.2f} on '
                    f'{record["date"].date()}? Options: A) Yes B) No.'
                ),
                "ticker": record["ticker"],
                "end_time": record["date"].isoformat(),
            }
        )
    return rows


def build_level3(records: list[dict], count: int) -> list[dict]:
    rows = []
    for record in records[:count]:
        rows.append(
            {
                "prompt": (
                    f'What was the closing price of {record["ticker"]} on '
                    f'{record["date"].date()}? Provide USD to 2 decimals.'
                ),
                "ticker": record["ticker"],
                "end_time": record["date"].isoformat(),
            }
        )
    return rows


def build_level4(records: list[dict], count: int) -> list[dict]:
    rows = []
    for record in records[:count]:
        rows.append(
            {
                "prompt": (
                    f'What was the intraday range (high-low) for {record["ticker"]} on '
                    f'{record["date"].date()}? Provide USD to 2 decimals.'
                ),
                "ticker": record["ticker"],
                "end_time": record["date"].isoformat(),
            }
        )
    return rows


def build_level2(common_dates: list[pd.Timestamp], count: int) -> list[dict]:
    rows = []
    for day in common_dates[:count]:
        prompt = (
            f"Which of these tickers closed above their previous close on {day.date()}? "
            f"Select all that apply: {', '.join(PORTFOLIO_TICKERS)}."
        )
        rows.append(
            {
                "prompt": prompt,
                "ticker": "MULTI",
                "tickers": PORTFOLIO_TICKERS,
                "end_time": day.isoformat(),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build FinanceX benchmark dataset.")
    parser.add_argument(
        "--input",
        default="data/futurex/data/train-00000-of-00001.parquet",
        help="FutureX parquet path",
    )
    parser.add_argument(
        "--max-per-level",
        type=int,
        default=5,
        help="Max questions to keep per level (default: 5). Use 20 for full cap.",
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
    levels_present = sorted({int(level) for level in df["level"].dropna().unique()})
    expected_levels = sorted(LEVEL_MAP.keys())
    if not set(expected_levels).issubset(levels_present):
        print(
            "Warning: FutureX levels missing from parquet. "
            f"Expected {expected_levels}, saw {levels_present}."
        )

    max_per_level = args.max_per_level if args.max_per_level is not None else 5

    data_root = Path("data")
    market_files = pick_latest_market_files(data_root, PORTFOLIO_TICKERS)
    if set(market_files.keys()) != set(PORTFOLIO_TICKERS):
        missing = sorted(set(PORTFOLIO_TICKERS) - set(market_files.keys()))
        raise FileNotFoundError(
            "Missing market data for tickers: "
            + ", ".join(missing)
            + ". Run scripts/setup.sh to download market data."
        )

    price_map = {ticker: load_market_data(path) for ticker, path in market_files.items()}

    records = []
    for ticker, df_prices in price_map.items():
        for idx in range(1, len(df_prices)):
            prev_row = df_prices.iloc[idx - 1]
            row = df_prices.iloc[idx]
            records.append(
                {
                    "ticker": ticker,
                    "date": row["date"],
                    "prev_close": float(prev_row["close"]),
                    "close": float(row["close"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                }
            )

    records = sorted(records, key=lambda item: item["date"], reverse=True)

    common_dates = None
    for ticker, df_prices in price_map.items():
        ticker_dates = set(df_prices["date"].iloc[1:])
        common_dates = ticker_dates if common_dates is None else common_dates & ticker_dates
    common_dates = sorted(common_dates, reverse=True) if common_dates else []

    rows = []
    level_builders = {
        1: build_level1(records, max_per_level),
        2: build_level2(common_dates, max_per_level),
        3: build_level3(records, max_per_level),
        4: build_level4(records, max_per_level),
    }

    for level, prompts in level_builders.items():
        level_name = LEVEL_MAP.get(level, "Unknown")
        for idx, prompt_row in enumerate(prompts, start=1):
            rows.append(
                {
                    "id": f"financex-{level}-{idx}",
                    "source_id": f"financex-{level}",
                    "ticker": prompt_row["ticker"],
                    "tickers": prompt_row.get("tickers"),
                    "end_time": prompt_row.get("end_time"),
                    "level": level,
                    "level_name": level_name,
                    "prompt": prompt_row["prompt"],
                }
            )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_json(output_path, orient="records", lines=True)

    print(f"Wrote {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
