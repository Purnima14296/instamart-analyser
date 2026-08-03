"""Apple App Store review connector via iTunes RSS feed."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import requests

from instamart_analyser.common.config import (
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_BACKOFF_SECONDS,
    SWIGGY_APP_STORE_COUNTRY,
    SWIGGY_APP_STORE_ID,
    USER_AGENT,
)
from instamart_analyser.common.dates import DEFAULT_LOOKBACK_DAYS, review_cutoff
from instamart_analyser.common.models import ConnectorResult, FeedbackRecord
from instamart_analyser.common.retry import with_retry
from instamart_analyser.phases.phase_1.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

MAX_RSS_PAGES = 200  # ~50 reviews/page → up to ~10k reviews scanned


class AppStoreConnector(BaseConnector):
    source = "app_store"

    def __init__(
        self,
        batch_id: str,
        max_records: int = 0,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    ) -> None:
        super().__init__(batch_id, max_records, lookback_days)

    def collect(self) -> ConnectorResult:
        retries = 0
        try:
            entries, retries = with_retry(
                lambda: self._fetch_entries_paginated(),
                max_attempts=DEFAULT_RETRY_ATTEMPTS,
                backoff_seconds=DEFAULT_RETRY_BACKOFF_SECONDS,
                description="App Store RSS fetch",
            )
        except RuntimeError as exc:
            logger.error("App Store fetch failed: %s", exc)
            return ConnectorResult(
                source=self.source,
                records=[],
                fetched_count=0,
                filtered_count=0,
                errors=[str(exc)],
                retries=retries,
            )

        records: list[FeedbackRecord] = []
        fetched_count = len(entries)
        cutoff = review_cutoff(self.lookback_days)

        for entry in entries:
            content = self._extract_text(entry)
            title = entry.get("title", {}).get("label") if isinstance(entry.get("title"), dict) else entry.get("title")
            combined = f"{title or ''}\n{content or ''}".strip()
            if not combined or not self.matches_instamart_keywords(combined):
                continue

            updated = entry.get("updated", {}).get("label") if isinstance(entry.get("updated"), dict) else entry.get("updated")
            timestamp = self._parse_timestamp(updated)
            if timestamp:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if dt < cutoff:
                    continue

            entry_id = entry.get("id", {}).get("label") or entry.get("id")
            author = entry.get("author", {}).get("name", {}).get("label") if isinstance(entry.get("author"), dict) else None
            rating = self._extract_rating(entry)
            link = entry.get("link", {})
            url = link.get("attributes", {}).get("href") if isinstance(link, dict) else None

            records.append(
                FeedbackRecord(
                    source=self.source,
                    source_record_id=str(entry_id),
                    body_text=content.strip() if content else combined,
                    language=self.detect_language(combined),
                    collection_batch_id=self.batch_id,
                    url=url,
                    author=author,
                    timestamp=timestamp,
                    title=title,
                    rating=rating,
                    metadata={
                        "app_store_id": SWIGGY_APP_STORE_ID,
                        "country": SWIGGY_APP_STORE_COUNTRY,
                    },
                )
            )

            if self.max_records > 0 and len(records) >= self.max_records:
                break

        logger.info(
            "App Store: scanned %d reviews (%d days), matched %d Instamart reviews",
            fetched_count,
            self.lookback_days,
            len(records),
        )

        return ConnectorResult(
            source=self.source,
            records=records,
            fetched_count=fetched_count,
            filtered_count=len(records),
            retries=retries,
        )

    def _fetch_entries_paginated(self) -> list[dict[str, Any]]:
        all_entries: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        cutoff = review_cutoff(self.lookback_days)

        for page in range(1, MAX_RSS_PAGES + 1):
            url = (
                f"https://itunes.apple.com/{SWIGGY_APP_STORE_COUNTRY}/rss/customerreviews"
                f"/page={page}/id={SWIGGY_APP_STORE_ID}/sortBy=mostRecent/json"
            )
            response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
            if response.status_code == 400:
                break
            response.raise_for_status()
            data = response.json()
            feed = data.get("feed", {})
            entries = feed.get("entry", [])
            if isinstance(entries, dict):
                entries = [entries]

            page_entries = [e for e in entries if self._extract_text(e) or e.get("title")]
            if not page_entries:
                break

            new_count = 0
            page_older_than_cutoff = True
            for entry in page_entries:
                entry_id = str(entry.get("id", {}).get("label") or entry.get("id", ""))
                if entry_id in seen_ids:
                    continue
                seen_ids.add(entry_id)

                updated = entry.get("updated", {}).get("label") if isinstance(entry.get("updated"), dict) else entry.get("updated")
                ts = self._parse_timestamp(updated)
                if ts:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if dt >= cutoff:
                        page_older_than_cutoff = False

                all_entries.append(entry)
                new_count += 1

            logger.info("App Store: page %d — %d new reviews (total %d)", page, new_count, len(all_entries))

            if new_count == 0:
                break
            if page_older_than_cutoff and page > 1:
                logger.info("App Store: reached %d-day cutoff at page %d", self.lookback_days, page)
                break

        return all_entries

    def _extract_text(self, entry: dict[str, Any]) -> str:
        content = entry.get("content", {})
        if isinstance(content, dict):
            return content.get("label", "") or ""
        return str(content) if content else ""

    def _extract_rating(self, entry: dict[str, Any]) -> int | None:
        rating = entry.get("im:rating", {})
        if isinstance(rating, dict):
            label = rating.get("label")
            return int(label) if label else None
        return None

    def _parse_timestamp(self, value: str | None) -> str | None:
        if not value:
            return None
        try:
            dt = parsedate_to_datetime(value)
            return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()
        except (TypeError, ValueError):
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()
            except ValueError:
                return None
