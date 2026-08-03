"""Community forums, social media, and extended source seed data."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from instamart_analyser.common.config import PHASE_1_SEED, is_instamart_review
from instamart_analyser.common.models import ConnectorResult, FeedbackRecord
from instamart_analyser.phases.phase_1.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

SEED_FILES = {
    "quora": PHASE_1_SEED / "seed-forums.json",
    "youtube": PHASE_1_SEED / "seed-social.json",
    "twitter": PHASE_1_SEED / "seed-social.json",
    "facebook": PHASE_1_SEED / "seed-forums.json",
}


class SeedCategoryConnector(BaseConnector):
    """Loads curated records for sources that need API credentials or are blocked."""

    def __init__(self, batch_id: str, source: str, max_records: int = 200) -> None:
        super().__init__(batch_id, max_records)
        self.source = source

    def collect(self) -> ConnectorResult:
        seed_path = SEED_FILES.get(self.source)
        if not seed_path or not seed_path.exists():
            return ConnectorResult(
                source=self.source,
                records=[],
                fetched_count=0,
                filtered_count=0,
                errors=[f"No seed file for {self.source}"],
            )

        with seed_path.open(encoding="utf-8") as f:
            data = json.load(f)

        records: list[FeedbackRecord] = []
        for item in data.get("records", []):
            if item.get("source") != self.source:
                continue
            title = item.get("title", "") or ""
            body = item["body_text"]
            if not is_instamart_review(f"{title}\n{body}"):
                continue
            records.append(
                FeedbackRecord(
                    source=self.source,
                    source_record_id=item["source_record_id"],
                    body_text=item["body_text"],
                    language=item.get("language", "en"),
                    collection_batch_id=self.batch_id,
                    url=item.get("url"),
                    author=item.get("author"),
                    timestamp=item.get("timestamp"),
                    title=item.get("title"),
                    rating=item.get("rating"),
                    metadata=item.get("metadata", {}),
                )
            )
            if len(records) >= self.max_records:
                break

        logger.info("%s seed: loaded %d records", self.source, len(records))
        return ConnectorResult(
            source=self.source,
            records=records,
            fetched_count=len(records),
            filtered_count=len(records),
        )
