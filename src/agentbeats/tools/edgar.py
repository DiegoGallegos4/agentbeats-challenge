"""EDGAR evidence fetcher for filings metadata and simple XBRL snippets."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import requests

from ..models import EventSpec, EvidenceItem
from .base import ToolLogger


class EdgarEvidenceFetcher:
    """
    Lightweight client that pulls filings metadata and XBRL facts from SEC endpoints.

    Examples
    --------
    >>> fetcher = EdgarEvidenceFetcher(user_agent="example/1.0 (contact: you@example.com)")
    >>> event = EventSpec(id="demo_tsla", question="Will TSLA beat EPS?", tags=["TSLA"])
    >>> filings = fetcher.fetch_latest(event, forms=("8-K",), limit=1)
    >>> filings[0].type
    'edgar_filing'
    >>> facts = fetcher.fetch_facts(event, tags=["us-gaap:EarningsPerShareDiluted"], limit=1)
    >>> facts[0]["tag"]
    'us-gaap:EarningsPerShareDiluted'
    """

    COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
    COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

    def __init__(
        self,
        user_agent: Optional[str] = None,
        ticker_map: Optional[Dict[str, str]] = None,
        cache_dir: Optional[Path] = None,
        logger: Optional[ToolLogger] = None,
    ) -> None:
        # SEC requires a descriptive User-Agent with contact info.
        self.user_agent = user_agent or os.getenv("SEC_USER_AGENT") or "agentbeats/0.1 (contact: your-email@example.com)"
        self.ticker_map = {k.upper(): v for k, v in (ticker_map or {}).items()}
        self.cache_dir = cache_dir or Path("data/generated/tool_cache/edgar")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger or ToolLogger("edgar", Path("data/generated/tool_logs"))
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self.user_agent})

    def _cache_path(self, name: str) -> Path:
        return self.cache_dir / name

    def _load_cached_json(self, name: str) -> Optional[Dict[str, Any]]:
        path = self._cache_path(name)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return None

    def _save_cached_json(self, name: str, data: Dict[str, Any]) -> None:
        path = self._cache_path(name)
        try:
            with path.open("w", encoding="utf-8") as handle:
                json.dump(data, handle)
        except Exception:
            return None

    def _load_company_tickers(self) -> Dict[str, str]:
        cached = self._load_cached_json("company_tickers.json")
        if cached and "data" in cached:
            return cached["data"]
        try:
            response = self._session.get(self.COMPANY_TICKERS_URL, timeout=30)
            response.raise_for_status()
            payload = response.json()
            ticker_map: Dict[str, str] = {}
            # The SEC file uses an object keyed by index with fields ticker and cik_str.
            for item in payload.values():
                ticker_map[item["ticker"].upper()] = str(item["cik_str"]).zfill(10)
            self._save_cached_json(
                "company_tickers.json",
                {"fetched_at": datetime.utcnow().isoformat(), "data": ticker_map},
            )
            return ticker_map
        except Exception as exc:  # noqa: BLE001
            self.logger.log({"tool": "edgar", "mode": "ticker_lookup_failed", "error": str(exc)})
            return {}

    def _lookup_cik(self, ticker: str) -> Optional[str]:
        if not ticker:
            return None
        ticker = ticker.upper()
        if ticker in self.ticker_map:
            return self.ticker_map[ticker]
        tickers = self._load_company_tickers()
        return tickers.get(ticker)

    def _fetch_submissions(self, cik: str) -> Optional[Dict[str, Any]]:
        cache_name = f"submissions_{cik}.json"
        cached = self._load_cached_json(cache_name)
        if cached and "data" in cached:
            return cached["data"]
        try:
            url = self.SUBMISSIONS_URL.format(cik=cik)
            response = self._session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            self.logger.log({"tool": "edgar", "mode": "submissions", "cik": cik, "status": response.status_code})
            self._save_cached_json(
                cache_name,
                {"fetched_at": datetime.utcnow().isoformat(), "data": data},
            )
            return data
        except Exception as exc:  # noqa: BLE001
            self.logger.log({"tool": "edgar", "mode": "submissions_error", "cik": cik, "error": str(exc)})
            return None

    def _latest_filings(self, submissions: Dict[str, Any], forms: Sequence[str]) -> List[Dict[str, Any]]:
        filings = submissions.get("filings", {}).get("recent", {})
        form_list = filings.get("form", [])
        accession_list = filings.get("accessionNumber", [])
        filed_list = filings.get("filingDate", [])
        primary_docs = filings.get("primaryDocument", [])
        results: List[Dict[str, Any]] = []
        for form, accession, filed_at, primary_doc in zip(form_list, accession_list, filed_list, primary_docs):
            if form not in forms:
                continue
            url = self._build_filing_url(submissions.get("cik"), accession, primary_doc)
            results.append(
                {
                    "form": form,
                    "accession": accession,
                    "filed_at": filed_at,
                    "url": url,
                    "primary_doc": primary_doc,
                }
            )
        return results

    @staticmethod
    def _build_filing_url(cik: Optional[str], accession: str, primary_doc: str | None) -> str:
        if not cik or not accession:
            return ""
        normalized_cik = str(cik).lstrip("0")
        accession_nodash = accession.replace("-", "")
        base = f"https://www.sec.gov/Archives/edgar/data/{normalized_cik}/{accession_nodash}"
        if primary_doc:
            return f"{base}/{primary_doc}"
        return base

    def fetch_latest(self, event: EventSpec, forms: Sequence[str] = ("8-K", "10-Q"), limit: int = 1) -> List[EvidenceItem]:
        """
        Return filing-level evidence items for the latest matching forms.

        Example return:
        `EvidenceItem(type="edgar_filing", source="https://www.sec.gov/Archives/.../tm2530590d1_8k.htm", snippet="TSLA 8-K filed 2025-11-07", timestamp=datetime(...))`
        """
        ticker = (event.tags[0] if event.tags else None) or (event.source.market_id if event.source else None)
        cik = self._lookup_cik(ticker) if ticker else None
        if not cik:
            self.logger.log({"tool": "edgar", "mode": "skip", "reason": "no_cik", "event_id": event.id})
            return []
        submissions = self._fetch_submissions(cik)
        if not submissions:
            return []
        filings = self._latest_filings(submissions, forms)[:limit]
        evidence_items: List[EvidenceItem] = []
        for filing in filings:
            filed_at = filing.get("filed_at")
            timestamp = None
            if filed_at:
                try:
                    timestamp = datetime.fromisoformat(filed_at)
                except ValueError:
                    timestamp = None
            evidence_items.append(
                EvidenceItem(
                    type="edgar_filing",
                    source=filing.get("url") or "https://www.sec.gov",
                    snippet=f"{ticker or 'company'} {filing.get('form')} filed {filed_at}",
                    timestamp=timestamp,
                )
            )
        return evidence_items

    # ---- XBRL facts (companyfacts API) ----
    def _fetch_company_facts(self, cik: str) -> Optional[Dict[str, Any]]:
        cache_name = f"companyfacts_{cik}.json"
        cached = self._load_cached_json(cache_name)
        if cached and "data" in cached:
            return cached["data"]
        try:
            url = self.COMPANY_FACTS_URL.format(cik=cik)
            response = self._session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            self.logger.log({"tool": "edgar", "mode": "companyfacts", "cik": cik, "status": response.status_code})
            self._save_cached_json(
                cache_name,
                {"fetched_at": datetime.utcnow().isoformat(), "data": data},
            )
            return data
        except Exception as exc:  # noqa: BLE001
            self.logger.log({"tool": "edgar", "mode": "companyfacts_error", "cik": cik, "error": str(exc)})
            return None

    @staticmethod
    def _split_tag(tag: str) -> tuple[str, str]:
        if ":" in tag:
            prefix, name = tag.split(":", 1)
            return prefix, name
        return "us-gaap", tag

    @staticmethod
    def _select_unit(units: Dict[str, Any]) -> Optional[str]:
        if not units:
            return None
        preferred = ("USD", "USD/shares", "shares", "pure")
        for candidate in preferred:
            if candidate in units:
                return candidate
        return next(iter(units.keys()), None)

    @staticmethod
    def _latest_fact_entry(entries: List[Dict[str, Any]], cutoff: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not entries:
            return None
        # Filter by cutoff on filed date if provided (YYYY-MM-DD)
        filtered = []
        for entry in entries:
            filed = entry.get("filed")
            if cutoff and filed and filed > cutoff:
                continue
            filtered.append(entry)
        use_entries = filtered or entries
        return max(
            use_entries,
            key=lambda e: (e.get("filed") or "", e.get("end") or "", e.get("start") or ""),
        )

    def fetch_facts(
        self,
        event: EventSpec,
        tags: Sequence[str],
        forms: Sequence[str] = ("10-Q", "10-K", "8-K"),
        limit: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Fetch latest XBRL facts for given tags using the SEC companyfacts endpoint.

        Returns a list of dicts shaped like:

        ```
        {
            "tag": "us-gaap:EarningsPerShareDiluted",
            "value": 2.27,
            "unit": "USD/shares",
            "period_start": "2025-07-01",
            "period_end": "2025-09-30",
            "filed_at": "2025-11-07",
            "source_url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0001318605.json",
            "accession": "0001104659-25-108507",
            "context_ref": "D2025Q3",
            "form": "8-K",
        }
        ```
        """
        ticker = (event.tags[0] if event.tags else None) or (event.source.market_id if event.source else None)
        cik = self._lookup_cik(ticker) if ticker else None
        if not cik:
            self.logger.log({"tool": "edgar", "mode": "facts_skip", "reason": "no_cik", "event_id": event.id})
            return []
        facts_doc = self._fetch_company_facts(cik)
        if not facts_doc:
            return []
        facts_root = facts_doc.get("facts", {})
        results: List[Dict[str, Any]] = []
        cutoff = event.resolution_date.isoformat()[:10] if event.resolution_date else None

        for raw_tag in tags:
            prefix, name = self._split_tag(raw_tag)
            namespace = facts_root.get(prefix, {})
            tag_data = namespace.get(name)
            if not tag_data:
                continue
            units = tag_data.get("units", {})
            unit_key = self._select_unit(units)
            if not unit_key:
                continue
            entries = units.get(unit_key, [])
            entry = self._latest_fact_entry(entries, cutoff=cutoff)
            if not entry:
                continue
            if forms and entry.get("form") not in forms:
                continue
            results.append(
                {
                    "tag": f"{prefix}:{name}",
                    "value": entry.get("val"),
                    "unit": unit_key,
                    "period_start": entry.get("start"),
                    "period_end": entry.get("end"),
                    "filed_at": entry.get("filed"),
                    "source_url": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                    "accession": entry.get("accn"),
                    "context_ref": entry.get("contextRef"),
                    "form": entry.get("form"),
                }
            )
            if len(results) >= limit:
                break
        return results
