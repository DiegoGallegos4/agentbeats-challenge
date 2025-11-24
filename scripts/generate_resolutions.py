"""Generate placeholder ResolutionRecord entries from an EventSpec JSONL."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


INPUT_EVENTS = Path("data/generated/events/watchlist_latest.jsonl")
OUTPUT_RESOLUTIONS = Path("data/generated/resolutions/watchlist_latest.jsonl")


def main(events_path: Optional[Path] = None, output_path: Optional[Path] = None) -> None:
    events_path = events_path or INPUT_EVENTS
    output_path = output_path or OUTPUT_RESOLUTIONS
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with events_path.open("r", encoding="utf-8") as ev_handle, output_path.open(
        "w", encoding="utf-8"
    ) as out_handle:
        for line in ev_handle:
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            resolution = {
                "id": event["id"],
                "outcome": 0,
                "verified_value": None,
                "verified_source": "manual",
                "resolved_at": None,
            }
            out_handle.write(json.dumps(resolution))
            out_handle.write("\n")
    print(f"Wrote placeholder resolutions to {output_path}")


if __name__ == "__main__":
    main()
