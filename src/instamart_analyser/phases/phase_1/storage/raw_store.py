"""SQLite raw data storage for Phase 1."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from instamart_analyser.common.config import PHASE_1_DB, PHASE_1_RAW, is_instamart_review
from instamart_analyser.common.models import FeedbackRecord


class RawStore:
    """Persists raw feedback records with deduplication on (source, source_record_id)."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or (PHASE_1_DB / "instamart_raw.sqlite")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS raw_feedback (
                    record_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    body_text TEXT NOT NULL,
                    language TEXT NOT NULL,
                    collected_at TEXT NOT NULL,
                    collection_batch_id TEXT NOT NULL,
                    pipeline_stage TEXT NOT NULL DEFAULT 'raw',
                    url TEXT,
                    author TEXT,
                    timestamp TEXT,
                    title TEXT,
                    rating INTEGER,
                    content_hash TEXT NOT NULL,
                    metadata_json TEXT,
                    UNIQUE(source, source_record_id)
                );

                CREATE INDEX IF NOT EXISTS idx_raw_feedback_source
                    ON raw_feedback(source);
                CREATE INDEX IF NOT EXISTS idx_raw_feedback_batch
                    ON raw_feedback(collection_batch_id);
                CREATE INDEX IF NOT EXISTS idx_raw_feedback_hash
                    ON raw_feedback(content_hash);
                """
            )

    def insert_records(self, records: list[FeedbackRecord]) -> tuple[int, int]:
        """Insert records. Returns (inserted_count, skipped_duplicates)."""
        inserted = 0
        skipped = 0

        with self._connect() as conn:
            for record in records:
                content_hash = FeedbackRecord.content_hash(record.body_text)
                try:
                    conn.execute(
                        """
                        INSERT INTO raw_feedback (
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

    def count_by_source(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT source, COUNT(*) as cnt FROM raw_feedback GROUP BY source"
            ).fetchall()
        return {row["source"]: row["cnt"] for row in rows}

    def count_total(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM raw_feedback").fetchone()
        return row["cnt"] if row else 0

    def get_sample(self, limit: int = 5) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM raw_feedback ORDER BY collected_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_all_records(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM raw_feedback").fetchall()
        return [dict(row) for row in rows]

    def purge_non_instamart(self) -> int:
        """Delete records that do not explicitly mention Instamart."""
        with self._connect() as conn:
            rows = conn.execute("SELECT record_id, body_text, title FROM raw_feedback").fetchall()
            to_delete = []
            for row in rows:
                combined = f"{row['title'] or ''}\n{row['body_text']}"
                if not is_instamart_review(combined):
                    to_delete.append(row["record_id"])
            if to_delete:
                placeholders = ",".join("?" * len(to_delete))
                conn.execute(
                    f"DELETE FROM raw_feedback WHERE record_id IN ({placeholders})",
                    to_delete,
                )
                conn.commit()
        return len(to_delete)

    def export_batch_jsonl(self, batch_id: str, output_dir: Path | None = None) -> Path:
        """Export all records from a batch to JSONL."""
        out_dir = output_dir or (PHASE_1_RAW / batch_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "records.jsonl"

        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM raw_feedback WHERE collection_batch_id = ?",
                (batch_id,),
            ).fetchall()

        with out_path.open("w", encoding="utf-8") as f:
            for row in rows:
                record = dict(row)
                if record.get("metadata_json"):
                    record["metadata"] = json.loads(record["metadata_json"])
                    del record["metadata_json"]
                del record["content_hash"]
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return out_path
