"""Ingestion batch tracking and event logging."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from instamart_analyser.common.config import PHASE_1_DB, PHASE_1_LOGS
from instamart_analyser.common.models import BatchSummary, ConnectorResult, utc_now_iso


class BatchTracker:
    """Tracks ingestion batches and logs success, failure, and retry events."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or (PHASE_1_DB / "instamart_raw.sqlite")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        PHASE_1_LOGS.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS ingestion_batches (
                    batch_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    status TEXT NOT NULL,
                    source_counts_json TEXT,
                    total_inserted INTEGER DEFAULT 0,
                    total_skipped_duplicates INTEGER DEFAULT 0,
                    errors_json TEXT
                );

                CREATE TABLE IF NOT EXISTS ingestion_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    source TEXT,
                    message TEXT,
                    details_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (batch_id) REFERENCES ingestion_batches(batch_id)
                );

                CREATE INDEX IF NOT EXISTS idx_events_batch
                    ON ingestion_events(batch_id);
                """
            )

    def start_batch(self, batch_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO ingestion_batches (batch_id, started_at, status)
                VALUES (?, ?, 'running')
                """,
                (batch_id, utc_now_iso()),
            )
            conn.commit()
        self._log_event(batch_id, "batch_started", message="Ingestion batch started")

    def log_connector_result(self, batch_id: str, result: ConnectorResult) -> None:
        event_type = "connector_success" if result.success else "connector_failure"
        message = (
            f"{result.source}: fetched={result.fetched_count}, "
            f"filtered={result.filtered_count}, retries={result.retries}"
        )
        self._log_event(
            batch_id,
            event_type,
            source=result.source,
            message=message,
            details={
                "fetched_count": result.fetched_count,
                "filtered_count": result.filtered_count,
                "record_count": len(result.records),
                "retries": result.retries,
                "errors": result.errors,
            },
        )

        if result.retries > 0:
            self._log_event(
                batch_id,
                "connector_retry",
                source=result.source,
                message=f"Required {result.retries} retries",
            )

        for error in result.errors:
            self._log_event(
                batch_id,
                "connector_error",
                source=result.source,
                message=error,
            )

    def complete_batch(self, summary: BatchSummary) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE ingestion_batches
                SET completed_at = ?, status = ?, source_counts_json = ?,
                    total_inserted = ?, total_skipped_duplicates = ?, errors_json = ?
                WHERE batch_id = ?
                """,
                (
                    summary.completed_at,
                    summary.status,
                    json.dumps(summary.source_counts),
                    summary.total_inserted,
                    summary.total_skipped_duplicates,
                    json.dumps(summary.errors),
                    summary.batch_id,
                ),
            )
            conn.commit()

        self._log_event(
            summary.batch_id,
            "batch_completed",
            message=f"Status={summary.status}, inserted={summary.total_inserted}",
            details=summary.to_dict(),
        )

        log_file = PHASE_1_LOGS / f"{summary.batch_id}.json"
        log_file.write_text(json.dumps(summary.to_dict(), indent=2), encoding="utf-8")

    def _log_event(
        self,
        batch_id: str,
        event_type: str,
        *,
        source: str | None = None,
        message: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO ingestion_events
                    (batch_id, event_type, source, message, details_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    batch_id,
                    event_type,
                    source,
                    message,
                    json.dumps(details) if details else None,
                    utc_now_iso(),
                ),
            )
            conn.commit()

    def get_batch(self, batch_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM ingestion_batches WHERE batch_id = ?",
                (batch_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_events(self, batch_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM ingestion_events WHERE batch_id = ? ORDER BY id",
                (batch_id,),
            ).fetchall()
        return [dict(row) for row in rows]
