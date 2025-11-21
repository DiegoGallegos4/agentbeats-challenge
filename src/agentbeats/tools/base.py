"""Common utilities for tool adapters."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


class ToolLogger:
    """Simple JSONL logger for tool requests/responses."""

    def __init__(self, tool_name: str, log_dir: Path | None = None):
        self.tool_name = tool_name
        self.log_dir = log_dir or Path("data/generated/tool_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / f"{tool_name}.jsonl"

    def log(self, payload: Dict[str, Any]) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = {"timestamp": timestamp, **payload}
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry))
            handle.write("\n")
