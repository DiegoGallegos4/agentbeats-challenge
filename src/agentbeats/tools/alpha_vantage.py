"""Alpha Vantage client for financial time-series."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from .base import ToolLogger


class AlphaVantageClient:
    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: Optional[str] = None, logger: Optional[ToolLogger] = None):
        self.api_key = api_key or os.getenv("ALPHAVANTAGE_API_KEY")
        self.logger = logger or ToolLogger("alpha_vantage", Path("data/generated/tool_logs"))

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def fetch_time_series(self, symbol: str, function: str = "TIME_SERIES_DAILY") -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("Alpha Vantage API key not configured (set ALPHAVANTAGE_API_KEY).")
        params = {
            "function": function,
            "symbol": symbol,
            "apikey": self.api_key,
        }
        response = requests.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        self.logger.log({
            "tool": "alpha_vantage",
            "function": function,
            "symbol": symbol,
            "status": response.status_code,
        })
        return data
