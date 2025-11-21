"""Polymarket API client for markets and prices."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from .base import ToolLogger


class PolymarketClient:
    BASE_URL = "https://gamma-api.polymarket.com"

    def __init__(self, logger: Optional[ToolLogger] = None):
        self.logger = logger or ToolLogger("polymarket", Path("data/generated/tool_logs"))

    def _request(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.BASE_URL}{path}"
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        self.logger.log({
            "tool": "polymarket",
            "path": path,
            "params": params or {},
            "status": response.status_code,
        })
        return payload

    def fetch_markets(self, limit: int = 20, active_only: bool = True) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": limit}
        if active_only:
            params["active"] = "true"
            params["closed"] = "false"
        return self._request("/markets", params=params)

    def fetch_market(self, market_id: str) -> Dict[str, Any]:
        return self._request(f"/markets/{market_id}")
