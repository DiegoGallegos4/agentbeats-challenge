"""Utilities for working with purple-agent fixtures."""

from pathlib import Path
from typing import List, Dict
import json


def load_fixture_predictions(path: Path) -> List[Dict]:
    """Return all JSONL entries from the given fixture path."""

    entries: List[Dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries
