"""Feedback service with Phase 5 summary refresh hook."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from instamart_analyser.api.store import ApiStore
from instamart_analyser.common.config import PHASE_5_DATA
from instamart_analyser.common.models import utc_now_iso
from instamart_analyser.phases.phase_5.feedback import (
    FEEDBACK_RESPONSES_PATH,
    ensure_feedback_template,
    summarize_stakeholder_feedback,
)


class FeedbackService:
    def __init__(self, store: ApiStore | None = None) -> None:
        self.store = store or ApiStore()

    def list_feedback(self) -> dict[str, Any]:
        items = self.store.list_feedback()
        return {"count": len(items), "responses": items}

    def submit_feedback(self, payload: dict[str, Any], created_by: str) -> dict[str, Any]:
        created = self.store.add_feedback(payload, created_by=created_by)
        refresh = self._sync_phase5_feedback()
        return {
            "status": "accepted",
            **created,
            "phase5_feedback_refresh": refresh,
        }

    def _sync_phase5_feedback(self) -> dict[str, Any]:
        """Merge API feedback into Phase 5 responses and regenerate the summary."""
        ensure_feedback_template()
        PHASE_5_DATA.mkdir(parents=True, exist_ok=True)

        existing: dict[str, Any]
        if FEEDBACK_RESPONSES_PATH.exists():
            with FEEDBACK_RESPONSES_PATH.open(encoding="utf-8") as f:
                existing = json.load(f)
        else:
            existing = {"created_at": utc_now_iso(), "responses": []}

        api_items = self.store.list_feedback(limit=500)
        # Keep seed responses, then append API-submitted payloads not already present.
        seed_responses = existing.get("responses", [])
        merged = list(seed_responses)
        seen = {
            (
                r.get("reviewer"),
                tuple(r.get("comments") or []),
                r.get("role"),
            )
            for r in seed_responses
        }
        added = 0
        for item in reversed(api_items):  # oldest first for stable append
            payload = item.get("payload", {})
            key = (
                payload.get("reviewer"),
                tuple(payload.get("comments") or []),
                payload.get("role"),
            )
            if key in seen:
                continue
            merged.append(payload)
            seen.add(key)
            added += 1

        payload_out = {
            "created_at": existing.get("created_at", utc_now_iso()),
            "updated_at": utc_now_iso(),
            "responses": merged,
            "source": "phase6c_feedback_sync",
        }
        with FEEDBACK_RESPONSES_PATH.open("w", encoding="utf-8") as f:
            json.dump(payload_out, f, indent=2, ensure_ascii=False)

        summary = summarize_stakeholder_feedback()
        return {
            "added_from_api": added,
            "response_count": summary.get("response_count"),
            "open_defects": summary.get("open_defect_count"),
            "summary_path": str(PHASE_5_DATA / "stakeholder-feedback-summary.md"),
        }

    def review_stats(self) -> dict[str, Any]:
        reviews = self.store.get_all_insight_reviews()
        counts = Counter(r.get("status", "draft") for r in reviews.values())
        return {
            "reviewed_count": len(reviews),
            "status_breakdown": dict(counts),
            "updated_at": utc_now_iso(),
        }
