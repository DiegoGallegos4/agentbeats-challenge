"""News evidence fetcher with live RSS support."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

import requests

from ..models import EventSpec, EvidenceItem
from .base import ToolLogger


class NewsEvidenceFetcher:
    """Fetch articles for a given event using Google News RSS (fallback to fixtures)."""

    GOOGLE_NEWS_URL = "https://news.google.com/rss/search"

    def __init__(self, fixtures_path: Optional[Path] = None, logger: Optional[ToolLogger] = None):
        self.fixtures_path = fixtures_path
        self.logger = logger or ToolLogger("news")
        self._fixture_articles = self._load_fixture() if fixtures_path and fixtures_path.exists() else []

    def _load_fixture(self) -> List[Dict[str, Any]]:
        with self.fixtures_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _build_query(self, event: EventSpec) -> str:
        if event.tags:
            return " ".join(event.tags)
        return event.question.split("?")[0]

    def _fetch_rss(self, query: str, limit: int) -> List[Dict[str, Any]]:
        params = {
            "q": quote_plus(query),
            "hl": "en-US",
            "gl": "US",
            "ceid": "US:en",
        }
        response = requests.get(self.GOOGLE_NEWS_URL, params=params, timeout=30)
        response.raise_for_status()
        self.logger.log({"tool": "news", "mode": "rss", "query": query, "status": response.status_code})
        root = ET.fromstring(response.content)
        items = root.findall("./channel/item")
        articles: List[Dict[str, Any]] = []
        for item in items[:limit]:
            published = item.findtext("pubDate")
            timestamp = None
            if published:
                try:
                    timestamp = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %Z").isoformat()
                except ValueError:
                    timestamp = None
            articles.append(
                {
                    "id": item.findtext("guid") or item.findtext("link"),
                    "title": item.findtext("title"),
                    "url": item.findtext("link"),
                    "published_at": timestamp,
                    "summary": item.findtext("description"),
                    "sentiment": 0.0,
                    "tags": [],
                }
            )
        return articles

    def fetch_articles(self, event: EventSpec, limit: int = 3) -> List[Dict[str, Any]]:
        query = self._build_query(event)
        try:
            articles = self._fetch_rss(query, limit)
            if articles:
                return articles
        except Exception as exc:  # noqa: BLE001
            self.logger.log({"tool": "news", "mode": "rss_error", "error": str(exc), "query": query})
        return self._fixture_articles[:limit]

    def to_evidence(self, article: Dict[str, Any]) -> EvidenceItem:
        timestamp_raw = article.get("published_at")
        timestamp = None
        if timestamp_raw:
            try:
                timestamp = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
            except ValueError:
                timestamp = None
        snippet = article.get("summary") or article.get("title", "")
        return EvidenceItem(
            type="news",
            source=article.get("url", "unknown"),
            snippet=snippet,
            timestamp=timestamp,
        )

    def aggregate_sentiment(self, articles: List[Dict[str, Any]]) -> float:
        if not articles:
            return 0.0
        sentiments = [float(article.get("sentiment", 0.0)) for article in articles]
        return sum(sentiments) / len(sentiments)
