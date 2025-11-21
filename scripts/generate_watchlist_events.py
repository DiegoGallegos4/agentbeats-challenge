"""Generate synthetic EventSpec entries for a watchlist of tickers."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from pydantic import BaseModel

WATCHLIST = {
    "TSLA": {
        "question_templates": [
            "Will TSLA close above ${target} on {date}?",
            "Will Tesla beat EPS guidance for {quarter}?",
            "Will Tesla deliver more than {units}k vehicles in {quarter}?",
            "Will Tesla announce a new Gigafactory by {date}?",
        ],
        "baseline_probability": 0.5,
    },
    "NVDA": {
        "question_templates": [
            "Will NVIDIA exceed ${target} market cap by {date}?",
            "Will NVIDIA beat revenue guidance in {quarter}?",
            "Will NVIDIA launch a new data center GPU before {date}?",
            "Will NVDA close above ${target} on {date}?",
        ],
        "baseline_probability": 0.5,
    },
    "AAPL": {
        "question_templates": [
            "Will Apple report iPhone sales above {units}M units in {quarter}?",
            "Will AAPL close above ${target} on {date}?",
            "Will Apple announce new Mac hardware by {date}?",
            "Will Apple services revenue exceed ${target}B in {quarter}?",
        ],
        "baseline_probability": 0.5,
    },
    "AMZN": {
        "question_templates": [
            "Will Amazon AWS revenue exceed ${target}B in {quarter}?",
            "Will AMZN close above ${target} on {date}?",
            "Will Amazon announce a stock split by {date}?",
            "Will Amazon Prime subscribers exceed {units}M by {date}?",
        ],
        "baseline_probability": 0.5,
    },
    "MSFT": {
        "question_templates": [
            "Will Microsoft Cloud revenue exceed ${target}B in {quarter}?",
            "Will MSFT close above ${target} on {date}?",
            "Will Microsoft acquire a major AI startup by {date}?",
            "Will Microsoft release a new Surface device by {date}?",
        ],
        "baseline_probability": 0.5,
    },
}

OUTPUT_PATH = Path("data/generated/events/watchlist_latest.jsonl")
EVENTS_PER_TICKER = 4


def future_date(days: int) -> str:
    return (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d")


def future_quarter(offset: int) -> str:
    base = datetime.utcnow()
    quarter_index = ((base.month - 1) // 3 + offset) % 4
    year = base.year + ((base.month - 1) // 3 + offset) // 4
    return f"Q{quarter_index + 1} {year}"


class EventSpec(BaseModel):
    id: str
    question: str
    domain: str = "finance"
    resolution_date: str
    source: dict
    ground_truth_source: str
    forecast_horizon_days: int | None = None
    tags: list[str] = []
    baseline_probability: float | None = None


def generate_event(ticker: str, template: str, idx: int) -> EventSpec:
    date = future_date(30 + idx * 30)
    quarter = future_quarter(idx % 4)
    question = template.format(
        target=round(100 + idx * 25, 2),
        date=date,
        quarter=quarter,
        units=100 + idx * 20,
    )
    return EventSpec(
        id=f"watch_{ticker.lower()}_{idx}",
        question=question,
        resolution_date=f"{date}T16:00:00Z",
        source={"type": "watchlist", "market_id": ticker},
        ground_truth_source="manual",
        tags=[ticker.lower()],
        baseline_probability=WATCHLIST[ticker]["baseline_probability"],
    )


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        for ticker, config in WATCHLIST.items():
            templates = config["question_templates"]
            for idx in range(EVENTS_PER_TICKER):
                template = templates[idx % len(templates)]
                event = generate_event(ticker, template, idx)
                handle.write(event.model_dump_json())
                handle.write("\n")
    print(f"Generated {len(WATCHLIST) * EVENTS_PER_TICKER} events at {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
