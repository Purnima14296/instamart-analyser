"""MouthShut product review connector."""

from __future__ import annotations

import logging
import re
from typing import Any

import requests
from bs4 import BeautifulSoup

from instamart_analyser.common.config import (
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_BACKOFF_SECONDS,
    MOUTHSHUT_REVIEW_URLS,
    USER_AGENT,
)
from instamart_analyser.common.models import ConnectorResult, FeedbackRecord
from instamart_analyser.common.retry import with_retry
from instamart_analyser.phases.phase_1.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class MouthShutConnector(BaseConnector):
    """Collects Instamart-related product reviews from MouthShut.com."""

    source = "mouthshut"

    def collect(self) -> ConnectorResult:
        records: list[FeedbackRecord] = []
        errors: list[str] = []
        fetched_count = 0

        urls = self._discover_review_urls()
        fetched_count = len(urls)

        for url in urls:
            if len(records) >= self.max_records:
                break
            try:
                review, retries = with_retry(
                    lambda u=url: self._fetch_review(u),
                    max_attempts=DEFAULT_RETRY_ATTEMPTS,
                    backoff_seconds=DEFAULT_RETRY_BACKOFF_SECONDS,
                    description=f"MouthShut review {url}",
                )
            except RuntimeError as exc:
                errors.append(str(exc))
                continue

            if not review:
                continue
            body = review.get("body", "")
            title = review.get("title", "") or ""
            combined = f"{title}\n{body}".strip()
            if not combined or not self.matches_instamart_keywords(combined):
                continue

            review_id = review["review_id"]
            records.append(
                FeedbackRecord(
                    source=self.source,
                    source_record_id=review_id,
                    body_text=body,
                    language=self.detect_language(body),
                    collection_batch_id=self.batch_id,
                    url=url,
                    author=review.get("author"),
                    timestamp=review.get("timestamp"),
                    title=review.get("title"),
                    rating=review.get("rating"),
                    metadata={
                        "platform": "mouthshut",
                        "category": "product_reviews",
                    },
                )
            )

        logger.info("MouthShut: fetched %d pages, matched %d", fetched_count, len(records))
        return ConnectorResult(
            source=self.source,
            records=records,
            fetched_count=fetched_count,
            filtered_count=len(records),
            errors=errors,
        )

    def _discover_review_urls(self) -> list[str]:
        """Return known + search-discovered MouthShut review URLs."""
        urls = list(dict.fromkeys(MOUTHSHUT_REVIEW_URLS))
        try:
            response = requests.get(
                "https://www.mouthshut.com/search/prodsrch.htm",
                params={"txt": "swiggy instamart"},
                headers={"User-Agent": USER_AGENT},
                timeout=20,
            )
            if response.status_code == 200:
                for match in re.findall(r'href="(/review/swiggy-review-[a-z]+)"', response.text):
                    full = f"https://www.mouthshut.com{match}"
                    if full not in urls:
                        urls.append(full)
        except requests.RequestException as exc:
            logger.warning("MouthShut search discovery failed: %s", exc)
        return urls[: self.max_records * 2]

    def _fetch_review(self, url: str) -> dict[str, Any] | None:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        review_id = url.rstrip("/").split("-")[-1]
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True).split(" - ")[0] if title_tag else None

        body = ""
        og = soup.find("meta", property="og:description")
        if og and og.get("content"):
            body = og["content"]
        if not body:
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                body = meta_desc["content"]

        if not body:
            for p in soup.find_all("p"):
                text = p.get_text(" ", strip=True)
                if len(text) > 80 and ("instamart" in text.lower() or "swiggy" in text.lower()):
                    body = text
                    break

        rating = None
        rating_match = re.search(r"Rating:\s*(\d)", response.text)
        if rating_match:
            rating = int(rating_match.group(1))

        return {
            "review_id": review_id,
            "title": title,
            "body": body,
            "rating": rating,
            "author": None,
            "timestamp": None,
        }
