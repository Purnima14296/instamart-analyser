"""Google Play Store review connector."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from google_play_scraper import Sort, reviews

from instamart_analyser.common.config import (
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_BACKOFF_SECONDS,
    SWIGGY_PLAY_STORE_APP_ID,
)
from instamart_analyser.common.dates import DEFAULT_LOOKBACK_DAYS, review_cutoff
from instamart_analyser.common.models import ConnectorResult, FeedbackRecord
from instamart_analyser.common.retry import with_retry
from instamart_analyser.phases.phase_1.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

PAGE_SIZE = 200
MAX_SCAN_SAFETY_LIMIT = 100_000
PLAY_STORE_LANGUAGES = ["en", "hi"]


class PlayStoreConnector(BaseConnector):
    source = "play_store"

    def __init__(
        self,
        batch_id: str,
        max_records: int = 0,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    ) -> None:
        super().__init__(batch_id, max_records, lookback_days)

    def collect(self) -> ConnectorResult:
        errors: list[str] = []
        retries = 0
        records: list[FeedbackRecord] = []

        try:
            raw_reviews, retries = with_retry(
                lambda: self._fetch_reviews_paginated(),
                max_attempts=DEFAULT_RETRY_ATTEMPTS,
                backoff_seconds=DEFAULT_RETRY_BACKOFF_SECONDS,
                description="Play Store review fetch",
            )
        except RuntimeError as exc:
            logger.error("Play Store fetch failed: %s", exc)
            return ConnectorResult(
                source=self.source,
                records=[],
                fetched_count=0,
                filtered_count=0,
                errors=[str(exc)],
                retries=retries,
            )

        fetched_count = len(raw_reviews)
        cutoff = review_cutoff(self.lookback_days)

        for review in raw_reviews:
            content = review.get("content") or ""
            if not content.strip():
                continue
            if not self.matches_instamart_keywords(content):
                continue

            at = review.get("at")
            if isinstance(at, datetime) and at.tzinfo is None:
                at = at.replace(tzinfo=timezone.utc)
            if isinstance(at, datetime) and at < cutoff:
                continue

            review_id = review.get("reviewId") or f"play_{review.get('userName', '')}_{review.get('at', '')}"
            timestamp = None
            if isinstance(at, datetime):
                timestamp = at.astimezone(timezone.utc).replace(microsecond=0).isoformat()

            records.append(
                FeedbackRecord(
                    source=self.source,
                    source_record_id=str(review_id),
                    body_text=content.strip(),
                    language=self.detect_language(content),
                    collection_batch_id=self.batch_id,
                    url=f"https://play.google.com/store/apps/details?id={SWIGGY_PLAY_STORE_APP_ID}&reviewId={review_id}",
                    author=review.get("userName"),
                    timestamp=timestamp,
                    rating=review.get("score"),
                    metadata={
                        "app_id": SWIGGY_PLAY_STORE_APP_ID,
                        "thumbs_up": review.get("thumbsUpCount"),
                        "app_version": review.get("reviewCreatedVersion"),
                        "reply_content": review.get("replyContent"),
                        "lang_fetched": review.get("_lang"),
                    },
                )
            )

            if self.max_records > 0 and len(records) >= self.max_records:
                break

        logger.info(
            "Play Store: scanned %d reviews (%d days), matched %d Instamart reviews",
            fetched_count,
            self.lookback_days,
            len(records),
        )

        return ConnectorResult(
            source=self.source,
            records=records,
            fetched_count=fetched_count,
            filtered_count=len(records),
            errors=errors,
            retries=retries,
        )

    def _fetch_reviews_paginated(self) -> list[dict]:
        all_reviews: list[dict] = []
        cutoff = review_cutoff(self.lookback_days)

        for lang in PLAY_STORE_LANGUAGES:
            continuation_token = None
            lang_scanned = 0

            while lang_scanned < MAX_SCAN_SAFETY_LIMIT:
                kwargs: dict = {
                    "app_id": SWIGGY_PLAY_STORE_APP_ID,
                    "lang": lang,
                    "country": "in",
                    "sort": Sort.NEWEST,
                    "count": PAGE_SIZE,
                }
                if continuation_token:
                    kwargs["continuation_token"] = continuation_token

                result, continuation_token = reviews(**kwargs)
                if not result:
                    break

                oldest_in_batch: datetime | None = None
                for item in result:
                    item["_lang"] = lang
                    at = item.get("at")
                    if isinstance(at, datetime):
                        if at.tzinfo is None:
                            at = at.replace(tzinfo=timezone.utc)
                        oldest_in_batch = at if oldest_in_batch is None else min(oldest_in_batch, at)
                        if at < cutoff:
                            continue
                    all_reviews.append(item)

                lang_scanned += len(result)
                logger.info(
                    "Play Store [%s]: scanned %d reviews this lang (total %d)",
                    lang,
                    lang_scanned,
                    len(all_reviews),
                )

                if oldest_in_batch and oldest_in_batch < cutoff:
                    logger.info("Play Store [%s]: reached %d-day cutoff", lang, self.lookback_days)
                    break
                if not continuation_token:
                    break

        return all_reviews
