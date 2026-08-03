"""SQLite storage for enriched feedback records."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from instamart_analyser.common.config import PHASE_2_DB
from instamart_analyser.common.models import utc_now_iso


class EnrichedStore:
    """Persists Groq-enriched feedback and enrichment run checkpoints."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or (PHASE_2_DB / "enriched.sqlite")
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
                CREATE TABLE IF NOT EXISTS enriched_feedback (
                    record_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    body_text TEXT NOT NULL,
                    taxonomy_version TEXT NOT NULL,
                    enriched_at TEXT NOT NULL,
                    enrichment_model TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    enrichment_json TEXT NOT NULL,
                    review_status TEXT NOT NULL DEFAULT 'pending',
                    error_message TEXT
                );

                CREATE TABLE IF NOT EXISTS enrichment_runs (
                    run_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    status TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    model TEXT NOT NULL,
                    cohort_size INTEGER NOT NULL,
                    processed_count INTEGER NOT NULL DEFAULT 0,
                    success_count INTEGER NOT NULL DEFAULT 0,
                    error_count INTEGER NOT NULL DEFAULT 0,
                    last_record_id TEXT,
                    notes TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_enriched_status
                    ON enriched_feedback(review_status);
                """
            )

    def upsert_enriched(
        self,
        record_id: str,
        source: str,
        body_text: str,
        enrichment: dict[str, Any],
        *,
        taxonomy_version: str,
        enrichment_model: str,
        prompt_version: str,
        review_status: str = "pending",
        error_message: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO enriched_feedback (
                    record_id, source, body_text, taxonomy_version, enriched_at,
                    enrichment_model, prompt_version, enrichment_json, review_status, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(record_id) DO UPDATE SET
                    source = excluded.source,
                    body_text = excluded.body_text,
                    taxonomy_version = excluded.taxonomy_version,
                    enriched_at = excluded.enriched_at,
                    enrichment_model = excluded.enrichment_model,
                    prompt_version = excluded.prompt_version,
                    enrichment_json = excluded.enrichment_json,
                    review_status = excluded.review_status,
                    error_message = excluded.error_message
                """,
                (
                    record_id,
                    source,
                    body_text,
                    taxonomy_version,
                    enrichment.get("enriched_at", utc_now_iso()),
                    enrichment_model,
                    prompt_version,
                    json.dumps(enrichment, ensure_ascii=False),
                    review_status,
                    error_message,
                ),
            )
            conn.commit()

    def is_enriched(self, record_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM enriched_feedback WHERE record_id = ? AND error_message IS NULL",
                (record_id,),
            ).fetchone()
        return row is not None

    def count_enriched(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM enriched_feedback WHERE error_message IS NULL"
            ).fetchone()
        return row["cnt"] if row else 0

    def count_errors(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM enriched_feedback WHERE error_message IS NOT NULL"
            ).fetchone()
        return row["cnt"] if row else 0

    def get_enriched_record(self, record_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM enriched_feedback WHERE record_id = ?",
                (record_id,),
            ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["enrichment"] = json.loads(data.pop("enrichment_json"))
        return data

    def get_all_enriched(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM enriched_feedback WHERE error_message IS NULL ORDER BY enriched_at"
            ).fetchall()
        results = []
        for row in rows:
            data = dict(row)
            data["enrichment"] = json.loads(data.pop("enrichment_json"))
            results.append(data)
        return results

    def start_run(
        self,
        run_id: str,
        *,
        prompt_version: str,
        model: str,
        cohort_size: int,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO enrichment_runs (
                    run_id, started_at, status, prompt_version, model, cohort_size
                ) VALUES (?, ?, 'running', ?, ?, ?)
                """,
                (run_id, utc_now_iso(), prompt_version, model, cohort_size),
            )
            conn.commit()

    def update_run(
        self,
        run_id: str,
        *,
        processed_count: int,
        success_count: int,
        error_count: int,
        last_record_id: str | None,
        status: str = "running",
        notes: str | None = None,
    ) -> None:
        completed_at = utc_now_iso() if status in ("completed", "stopped", "failed") else None
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE enrichment_runs SET
                    processed_count = ?,
                    success_count = ?,
                    error_count = ?,
                    last_record_id = ?,
                    status = ?,
                    completed_at = COALESCE(?, completed_at),
                    notes = COALESCE(?, notes)
                WHERE run_id = ?
                """,
                (
                    processed_count,
                    success_count,
                    error_count,
                    last_record_id,
                    status,
                    completed_at,
                    notes,
                    run_id,
                ),
            )
            conn.commit()

    def get_latest_run(self) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM enrichment_runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
        return dict(row) if row else None

    def export_jsonl(self, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        records = self.get_all_enriched()
        with output_path.open("w", encoding="utf-8") as f:
            for row in records:
                payload = {
                    "record_id": row["record_id"],
                    "source": row["source"],
                    "body_text": row["body_text"],
                    "taxonomy_version": row["taxonomy_version"],
                    "enriched_at": row["enriched_at"],
                    "enrichment_model": row["enrichment_model"],
                    "prompt_version": row["prompt_version"],
                    "review_status": row["review_status"],
                    **row["enrichment"],
                }
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return output_path
