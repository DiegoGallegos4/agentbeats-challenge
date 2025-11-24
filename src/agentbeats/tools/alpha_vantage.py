"""Alpha Vantage client for financial time-series with simple caching."""

from __future__ import annotations

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from .base import ToolLogger


class AlphaVantageClient:
    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: Optional[str] = None, logger: Optional[ToolLogger] = None, cache_dir: Optional[Path] = None):
        self.api_key = api_key or os.getenv("ALPHAVANTAGE_API_KEY")
        self.logger = logger or ToolLogger("alpha_vantage", Path("data/generated/tool_logs"))
        self.cache_dir = cache_dir or Path("data/generated/tool_cache/alpha_vantage")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: Dict[tuple[str, str], Dict[str, Any]] = {}
        self.last_from_cache: bool = False

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _cache_path(self, symbol: str, function: str) -> Path:
        safe_symbol = symbol.replace("/", "-")
        return self.cache_dir / f"{safe_symbol}_{function}.json"

    def _load_cache(self, symbol: str, function: str) -> Optional[Dict[str, Any]]:
        key = (function, symbol)
        if key in self._memory_cache:
            self.last_from_cache = True
            return self._memory_cache[key]
        path = self._cache_path(symbol, function)
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    self._memory_cache[key] = data
                    self.last_from_cache = True
                    return data
            except Exception:
                return None
        return None

    def _save_cache(self, symbol: str, function: str, data: Dict[str, Any]) -> None:
        key = (function, symbol)
        self._memory_cache[key] = data
        path = self._cache_path(symbol, function)
        try:
            with path.open("w", encoding="utf-8") as handle:
                json.dump({"fetched_at": datetime.now(timezone.utc).isoformat(), "data": data}, handle)
        except Exception:
            pass

    def fetch_time_series(self, symbol: str, function: str = "TIME_SERIES_DAILY") -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("Alpha Vantage API key not configured (set ALPHAVANTAGE_API_KEY).")

        cached = self._load_cache(symbol, function)
        if cached:
            return cached.get("data", cached)

        params = {
            "function": function,
            "symbol": symbol,
            "apikey": self.api_key,
        }
        response = requests.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        self.last_from_cache = False
        self.logger.log({
            "tool": "alpha_vantage",
            "function": function,
            "symbol": symbol,
            "status": response.status_code,
        })
        self._save_cache(symbol, function, data)
        return data
