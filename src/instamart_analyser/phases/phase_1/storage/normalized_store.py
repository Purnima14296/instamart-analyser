"""Normalized review storage (Phase 1 cleaning rules applied)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from instamart_analyser.common.config import PHASE_1_DB
from instamart_analyser.common.models import FeedbackRecord
from instamart_analyser.phases.phase_1.normalization import normalize_record


class NormalizedStore:
    """Stores reviews that pass Phase 1 normalization rules."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or (PHASE_1_DB / "instamart_raw.sqlite")
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS normalized_feedback (
                    record_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    body_text TEXT NOT NULL,
                    language TEXT NOT NULL DEFAULT 'en',
                    collected_at TEXT NOT NULL,
                    collection_batch_id TEXT NOT NULL,
                    pipeline_stage TEXT NOT NULL DEFAULT 'normalized',
                    url TEXT,
                    author TEXT,
                    timestamp TEXT,
                    title TEXT,
                    rating INTEGER,
                    content_hash TEXT NOT NULL,
                    metadata_json TEXT,
                    UNIQUE(source, source_record_id)
                );

                CREATE TABLE IF NOT EXISTS normalization_rejects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id TEXT NOT NULL,
                    source TEXT,
                    reason TEXT NOT NULL,
                    body_text TEXT,
                    rejected_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_normalized_source
                    ON normalized_feedback(source);
                """
            )

    def insert_records(self, records: list[FeedbackRecord]) -> tuple[int, int]:
        inserted = 0
        skipped = 0
        with self._connect() as conn:
            for record in records:
                content_hash = FeedbackRecord.content_hash(record.body_text)
                try:
                    conn.execute(
                        """
                        INSERT INTO normalized_feedback (
                            record_id, source, source_record_id, body_text, language,
                            collected_at, collection_batch_id, pipeline_stage,
                            url, author, timestamp, title, rating, content_hash, metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            record.record_id,
                            record.source,
                            record.source_record_id,
                            record.body_text,
                            record.language,
                            record.collected_at,
                            record.collection_batch_id,
                            record.pipeline_stage,
                            record.url,
                            record.author,
                            record.timestamp,
                            record.title,
                            record.rating,
                            content_hash,
                            json.dumps(record.metadata) if record.metadata else None,
                        ),
                    )
                    inserted += 1
                except sqlite3.IntegrityError:
                    skipped += 1
            conn.commit()
        return inserted, skipped

    def rebuild_from_raw(self, raw_store: Any) -> dict[str, Any]:
        """Re-normalize all raw records; replaces normalized table contents."""
        with self._connect() as conn:
            conn.execute("DELETE FROM normalized_feedback")
            conn.execute("DELETE FROM normalization_rejects")
            conn.commit()

        rows = raw_store.get_all_records()
        kept: list[FeedbackRecord] = []
        rejections: dict[str, int] = {}

        for row in rows:
            record = FeedbackRecord(
                record_id=row["record_id"],
                source=row["source"],
                source_record_id=row["source_record_id"],
                body_text=row["body_text"],
                language=row["language"],
                collection_batch_id=row["collection_batch_id"],
                pipeline_stage=row["pipeline_stage"],
                collected_at=row["collected_at"],
                url=row.get("url"),
                author=row.get("author"),
                timestamp=row.get("timestamp"),
                title=row.get("title"),
                rating=row.get("rating"),
                metadata=json.loads(row["metadata_json"]) if row.get("metadata_json") else {},
            )
            outcome = normalize_record(record)
            if outcome.record:
                kept.append(outcome.record)
            elif outcome.reason:
                rejections[outcome.reason] = rejections.get(outcome.reason, 0) + 1
                self._log_reject(row["record_id"], row["source"], outcome.reason, row["body_text"])

        inserted, skipped = self.insert_records(kept)
        return {
            "raw_total": len(rows),
            "normalized_kept": inserted,
            "duplicates_skipped": skipped,
            "rejections": rejections,
            "rejected_total": sum(rejections.values()),
        }

    def _log_reject(self, record_id: str, source: str, reason: str, body: str) -> None:
        from instamart_analyser.common.models import utc_now_iso

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO normalization_rejects (record_id, source, reason, body_text, rejected_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (record_id, source, reason, body[:500], utc_now_iso()),
            )
            conn.commit()

    def count_total(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM normalized_feedback").fetchone()
        return row["cnt"] if row else 0

    def count_by_source(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT source, COUNT(*) as cnt FROM normalized_feedback GROUP BY source"
            ).fetchall()
        return {row["source"]: row["cnt"] for row in rows}

    def get_all_records(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT record_id, source, source_record_id, body_text, language,
                       collected_at, collection_batch_id, pipeline_stage,
                       url, author, timestamp, title, rating, content_hash, metadata_json
                FROM normalized_feedback
                ORDER BY record_id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_record(self, record_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM normalized_feedback WHERE record_id = ?",
                (record_id,),
            ).fetchone()
        return dict(row) if row else None
