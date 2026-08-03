"""Local SQLite persistence for API jobs, insight reviews, and feedback."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from instamart_analyser.common.config import PHASE_6_DATA
from instamart_analyser.common.models import utc_now_iso

DB_PATH = PHASE_6_DATA / "api.sqlite"


class ApiStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DB_PATH
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
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    created_by TEXT,
                    message TEXT,
                    error TEXT,
                    progress_json TEXT,
                    result_json TEXT
                );

                CREATE TABLE IF NOT EXISTS insight_reviews (
                    insight_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    notes TEXT,
                    reviewed_by TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS stakeholder_feedback (
                    feedback_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT
                );
                """
            )

    def create_job(
        self,
        *,
        job_type: str,
        created_by: str,
        message: str = "queued",
    ) -> dict[str, Any]:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    job_id, job_type, status, created_at, created_by, message, progress_json
                ) VALUES (?, ?, 'queued', ?, ?, ?, ?)
                """,
                (job_id, job_type, now, created_by, message, json.dumps({})),
            )
        return self.get_job(job_id)  # type: ignore[return-value]

    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_job(row) for row in rows]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def has_active_job(self, job_type: str | None = None) -> bool:
        query = "SELECT 1 FROM jobs WHERE status IN ('queued', 'running')"
        params: tuple[Any, ...] = ()
        if job_type:
            query += " AND job_type = ?"
            params = (job_type,)
        with self._connect() as conn:
            row = conn.execute(query, params).fetchone()
        return row is not None

    def update_job(
        self,
        job_id: str,
        *,
        status: str | None = None,
        message: str | None = None,
        error: str | None = None,
        progress: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        started: bool = False,
        completed: bool = False,
    ) -> dict[str, Any] | None:
        job = self.get_job(job_id)
        if not job:
            return None
        fields: list[str] = []
        values: list[Any] = []
        if status is not None:
            fields.append("status = ?")
            values.append(status)
        if message is not None:
            fields.append("message = ?")
            values.append(message)
        if error is not None:
            fields.append("error = ?")
            values.append(error)
        if progress is not None:
            fields.append("progress_json = ?")
            values.append(json.dumps(progress))
        if result is not None:
            fields.append("result_json = ?")
            values.append(json.dumps(result))
        if started:
            fields.append("started_at = ?")
            values.append(utc_now_iso())
        if completed:
            fields.append("completed_at = ?")
            values.append(utc_now_iso())
        if not fields:
            return job
        values.append(job_id)
        with self._connect() as conn:
            conn.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE job_id = ?", values)
        return self.get_job(job_id)

    def upsert_insight_review(
        self,
        *,
        insight_id: str,
        status: str,
        notes: str | None,
        reviewed_by: str,
    ) -> dict[str, Any]:
        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO insight_reviews (insight_id, status, notes, reviewed_by, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(insight_id) DO UPDATE SET
                    status = excluded.status,
                    notes = excluded.notes,
                    reviewed_by = excluded.reviewed_by,
                    updated_at = excluded.updated_at
                """,
                (insight_id, status, notes, reviewed_by, now),
            )
        return self.get_insight_review(insight_id)  # type: ignore[return-value]

    def get_insight_review(self, insight_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM insight_reviews WHERE insight_id = ?",
                (insight_id,),
            ).fetchone()
        if not row:
            return None
        return dict(row)

    def get_all_insight_reviews(self) -> dict[str, dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM insight_reviews").fetchall()
        return {row["insight_id"]: dict(row) for row in rows}

    def add_feedback(self, payload: dict[str, Any], created_by: str) -> dict[str, Any]:
        feedback_id = f"fb_{uuid.uuid4().hex[:10]}"
        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO stakeholder_feedback (feedback_id, payload_json, created_at, created_by)
                VALUES (?, ?, ?, ?)
                """,
                (feedback_id, json.dumps(payload), now, created_by),
            )
        return {
            "feedback_id": feedback_id,
            "created_at": now,
            "created_by": created_by,
            "payload": payload,
        }

    def list_feedback(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM stakeholder_feedback ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "feedback_id": row["feedback_id"],
                "created_at": row["created_at"],
                "created_by": row["created_by"],
                "payload": json.loads(row["payload_json"]),
            }
            for row in rows
        ]

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "job_id": row["job_id"],
            "job_type": row["job_type"],
            "status": row["status"],
            "created_at": row["created_at"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "created_by": row["created_by"],
            "message": row["message"],
            "error": row["error"],
            "progress": json.loads(row["progress_json"] or "{}"),
            "result": json.loads(row["result_json"] or "null"),
        }
