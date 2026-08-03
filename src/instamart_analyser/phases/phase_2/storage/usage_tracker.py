"""Track Groq API usage against daily quotas."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from instamart_analyser.common.config import PHASE_2_DB


class UsageTracker:
    """Persists per-day request and token counts for Groq rate-limit enforcement."""

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
                CREATE TABLE IF NOT EXISTS groq_usage_daily (
                    usage_date TEXT PRIMARY KEY,
                    request_count INTEGER NOT NULL DEFAULT 0,
                    token_count INTEGER NOT NULL DEFAULT 0,
                    enrichment_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def today() -> str:
        return date.today().isoformat()

    def get_daily_usage(self, usage_date: str | None = None) -> dict[str, int]:
        day = usage_date or self.today()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT request_count, token_count, enrichment_count FROM groq_usage_daily WHERE usage_date = ?",
                (day,),
            ).fetchone()
        if not row:
            return {"request_count": 0, "token_count": 0, "enrichment_count": 0}
        return {
            "request_count": row["request_count"],
            "token_count": row["token_count"],
            "enrichment_count": row["enrichment_count"],
        }

    def record_call(
        self,
        *,
        prompt_tokens: int,
        completion_tokens: int,
        enrichment_count: int = 1,
        is_enrichment: bool = True,
        usage_date: str | None = None,
    ) -> dict[str, int]:
        from instamart_analyser.common.models import utc_now_iso

        day = usage_date or self.today()
        total_tokens = prompt_tokens + completion_tokens
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO groq_usage_daily (usage_date, request_count, token_count, enrichment_count, updated_at)
                VALUES (?, 1, ?, ?, ?)
                ON CONFLICT(usage_date) DO UPDATE SET
                    request_count = request_count + 1,
                    token_count = token_count + excluded.token_count,
                    enrichment_count = enrichment_count + excluded.enrichment_count,
                    updated_at = excluded.updated_at
                """,
                (
                    day,
                    total_tokens,
                    enrichment_count if is_enrichment else 0,
                    utc_now_iso(),
                ),
            )
            conn.commit()
        return self.get_daily_usage(day)

    def can_enrich(
        self,
        *,
        daily_request_cap: int,
        daily_token_budget: int,
        daily_enrichment_cap: int,
        requested_enrichment_count: int = 1,
    ) -> tuple[bool, str]:
        usage = self.get_daily_usage()
        if usage["enrichment_count"] + requested_enrichment_count > daily_enrichment_cap:
            return False, f"Daily enrichment cap reached ({daily_enrichment_cap})"
        if usage["request_count"] >= daily_request_cap:
            return False, f"Daily request cap reached ({daily_request_cap})"
        if usage["token_count"] >= daily_token_budget:
            return False, f"Daily token budget reached ({daily_token_budget})"
        return True, ""
