"""Core data models for the ingestion pipeline."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class FeedbackRecord:
    """Raw feedback record aligned with feedback-record.schema.json."""

    source: str
    source_record_id: str
    body_text: str
    language: str
    collection_batch_id: str
    pipeline_stage: str = "raw"
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    collected_at: str = field(default_factory=utc_now_iso)
    url: str | None = None
    author: str | None = None
    timestamp: str | None = None
    title: str | None = None
    rating: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @staticmethod
    def content_hash(text: str) -> str:
        normalized = " ".join(text.lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass
class ConnectorResult:
    """Result from a single connector run."""

    source: str
    records: list[FeedbackRecord]
    fetched_count: int
    filtered_count: int
    errors: list[str] = field(default_factory=list)
    retries: int = 0

    @property
    def success(self) -> bool:
        return len(self.errors) == 0 or len(self.records) > 0


@dataclass
class BatchSummary:
    """Summary of an ingestion batch run."""

    batch_id: str
    started_at: str
    completed_at: str | None
    status: str
    source_counts: dict[str, int]
    total_inserted: int
    total_skipped_duplicates: int
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
