"""Read Phase 2–5 artifacts for API responses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from instamart_analyser.api.store import ApiStore
from instamart_analyser.common.config import (
    GROQ_API_KEY,
    GROQ_DAILY_TOKEN_BUDGET,
    GROQ_ENRICHMENT_DAILY_CAP,
    PHASE_2_DATA,
    PHASE_3_DATA,
    PHASE_4_DATA,
    PHASE_5_DATA,
)
from instamart_analyser.phases.phase_2.storage import EnrichedStore
from instamart_analyser.phases.phase_2.storage.usage_tracker import UsageTracker


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact not found: {path.name}",
        )
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _load_json_optional(path: Path) -> Any | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _read_text(path: Path) -> str:
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {path.name}",
        )
    return path.read_text(encoding="utf-8")


REPORT_FILES: dict[str, Path] = {
    "stakeholder-summary": PHASE_3_DATA / "stakeholder-summary.md",
    "insight-report": PHASE_3_DATA / "insight-report.md",
    "experiment-framing-memo": PHASE_4_DATA / "experiment-framing-memo.md",
    "pilot-report": PHASE_5_DATA / "pilot-report.md",
    "growth-handoff-package": PHASE_5_DATA / "growth-handoff-package.md",
    "stakeholder-feedback-summary": PHASE_5_DATA / "stakeholder-feedback-summary.md",
    "theme-summary": PHASE_3_DATA / "theme-summary.json",
    "insights": PHASE_3_DATA / "insights.json",
    "opportunity-map": PHASE_4_DATA / "opportunity-map.json",
    "hypothesis-backlog": PHASE_4_DATA / "hypothesis-backlog.json",
    "measurement-framework": PHASE_5_DATA / "measurement-framework.json",
    "phase-5-summary": PHASE_5_DATA / "phase-5-summary.json",
}


class ArtifactService:
    def __init__(self, store: ApiStore | None = None) -> None:
        self.store = store or ApiStore()
        self.enriched = EnrichedStore()
        self.usage = UsageTracker()

    def enrichment_status(self) -> dict[str, Any]:
        cohort = _load_json_optional(PHASE_2_DATA / "enrichment-cohort.json") or {}
        cohort_size = len(cohort.get("record_ids", []))
        enriched_count = self.enriched.count_enriched()
        error_count = self.enriched.count_errors()
        usage = self.usage.get_daily_usage()
        coverage = round((enriched_count / cohort_size) * 100, 1) if cohort_size else 0.0
        remaining = max(GROQ_ENRICHMENT_DAILY_CAP - usage["enrichment_count"], 0)
        token_remaining = max(GROQ_DAILY_TOKEN_BUDGET - usage["token_count"], 0)
        quota_blocked = remaining <= 0 or token_remaining < 500
        return {
            "cohort_size": cohort_size,
            "enriched_count": enriched_count,
            "error_count": error_count,
            "coverage_pct": coverage,
            "remaining_to_enrich": max(cohort_size - enriched_count, 0),
            "usage_today": {
                "date": self.usage.today(),
                "requests": usage["request_count"],
                "tokens": usage["token_count"],
                "enrichment_calls": usage["enrichment_count"],
                "limits": {
                    "enrichment_daily_cap": GROQ_ENRICHMENT_DAILY_CAP,
                    "daily_token_budget": GROQ_DAILY_TOKEN_BUDGET,
                },
                "remaining_enrichment_estimate": remaining,
                "remaining_token_estimate": token_remaining,
            },
            "quota_blocked": quota_blocked,
            "quota_message": (
                "Daily Groq enrichment quota is exhausted. Wait for reset (usually next calendar day) "
                "or raise limits / use another key."
                if quota_blocked
                else "Quota available for more enrichment."
            ),
            "groq_key_configured": bool(GROQ_API_KEY),
            "can_start_enrichment": bool(GROQ_API_KEY) and not quota_blocked and enriched_count < cohort_size,
        }

    def known_limitations(self) -> dict[str, Any]:
        enrichment = self.enrichment_status()
        return {
            "limitations": [
                "Public feedback overrepresents extreme negative opinions.",
                "Play Store reviews dominate the current sample.",
                "Partial enrichment means rankings are directional, not final.",
                "Recommendations are not causal proof and need experiments.",
                "Groq free-tier quotas can stop enrichment mid-day (HTTP 429 / daily cap).",
            ],
            "operational_notes": [
                enrichment["quota_message"],
                f"Enrichment coverage is {enrichment['coverage_pct']}% "
                f"({enrichment['enriched_count']}/{enrichment['cohort_size']}).",
                "Only one pipeline job can run at a time.",
                "GROQ_API_KEY stays server-side and is never sent to the browser.",
            ],
            "enrichment": enrichment,
        }

    def get_overview(self) -> dict[str, Any]:
        theme_summary = _load_json_optional(PHASE_3_DATA / "theme-summary.json") or {}
        insights = _load_json_optional(PHASE_3_DATA / "insights.json") or {}
        phase4 = _load_json_optional(PHASE_4_DATA / "phase-4-summary.json") or {}
        phase5 = _load_json_optional(PHASE_5_DATA / "phase-5-summary.json") or {}
        enrichment = self.enrichment_status()
        return {
            "enrichment": enrichment,
            "theme_summary": {
                "created_at": theme_summary.get("created_at"),
                "cluster_count": theme_summary.get("cluster_count"),
                "enriched_record_count": theme_summary.get("enriched_record_count"),
                "top_barriers": theme_summary.get("top_barriers", [])[:8],
                "top_missions": theme_summary.get("top_missions", [])[:5],
                "top_segments": theme_summary.get("top_segments", [])[:5],
                "bias_notes": theme_summary.get("bias_notes", []),
            },
            "insights": {
                "insight_count": insights.get("insight_count", 0),
                "dry_run": insights.get("dry_run"),
                "created_at": insights.get("created_at"),
            },
            "opportunities": {
                "opportunity_count": phase4.get("opportunity_count", 0),
                "hypothesis_count": phase4.get("hypothesis_count", 0),
                "priority_band_breakdown": phase4.get("priority_band_breakdown", {}),
            },
            "pilot": {
                "pilot_ready": phase5.get("pilot_ready"),
                "alignment_verdict": phase5.get("alignment_verdict"),
                "open_defects": phase5.get("open_defects"),
                "metric_count": phase5.get("metric_count"),
            },
            "sample_size": enrichment["enriched_count"],
            "bias_notes": theme_summary.get("bias_notes", []),
            "known_limitations": self.known_limitations()["limitations"],
            "operational_notes": self.known_limitations()["operational_notes"],
        }

    def list_insights(
        self,
        *,
        confidence: str | None = None,
        status_filter: str | None = None,
        segment: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        payload = _load_json(PHASE_3_DATA / "insights.json")
        reviews = self.store.get_all_insight_reviews()
        items = []
        for insight in payload.get("insights", []):
            insight_id = insight["insight_id"]
            review = reviews.get(insight_id)
            effective_status = review["status"] if review else insight.get("status", "draft")
            if confidence and insight.get("confidence") != confidence:
                continue
            if status_filter and effective_status != status_filter:
                continue
            if segment and insight.get("affected_segment") != segment:
                continue
            items.append(
                {
                    **insight,
                    "status": effective_status,
                    "review": review,
                    "supporting_record_count": insight.get("total_supporting_records"),
                    "evidence_count": len(insight.get("supporting_evidence", [])),
                }
            )
            if len(items) >= limit:
                break
        return {
            "created_at": payload.get("created_at"),
            "dry_run": payload.get("dry_run"),
            "count": len(items),
            "bias_notes": (_load_json_optional(PHASE_3_DATA / "theme-summary.json") or {}).get(
                "bias_notes", []
            ),
            "insights": items,
        }

    def get_insight(self, insight_id: str) -> dict[str, Any]:
        payload = _load_json(PHASE_3_DATA / "insights.json")
        for insight in payload.get("insights", []):
            if insight.get("insight_id") == insight_id:
                review = self.store.get_insight_review(insight_id)
                effective_status = review["status"] if review else insight.get("status", "draft")
                return {
                    **insight,
                    "status": effective_status,
                    "review": review,
                    "bias_notes": (_load_json_optional(PHASE_3_DATA / "theme-summary.json") or {}).get(
                        "bias_notes", []
                    ),
                }
        raise HTTPException(status_code=404, detail=f"Insight not found: {insight_id}")

    def update_insight_status(
        self,
        insight_id: str,
        *,
        status_value: str,
        notes: str | None,
        reviewed_by: str,
    ) -> dict[str, Any]:
        # Ensure insight exists first
        self.get_insight(insight_id)
        self.store.upsert_insight_review(
            insight_id=insight_id,
            status=status_value,
            notes=notes,
            reviewed_by=reviewed_by,
        )
        return self.get_insight(insight_id)

    def get_themes(self) -> dict[str, Any]:
        clusters_payload = _load_json(PHASE_3_DATA / "theme-clusters.json")
        summary = clusters_payload.get("summary", {})
        return {
            "created_at": summary.get("created_at"),
            "enriched_record_count": summary.get("enriched_record_count"),
            "cluster_count": summary.get("cluster_count"),
            "top_barriers": summary.get("top_barriers", []),
            "top_missions": summary.get("top_missions", []),
            "top_segments": summary.get("top_segments", []),
            "top_discovery_barriers": summary.get("top_discovery_barriers", []),
            "bias_notes": summary.get("bias_notes", []),
            "clusters": clusters_payload.get("clusters", []),
        }

    def get_opportunities(self) -> dict[str, Any]:
        return _load_json(PHASE_4_DATA / "opportunity-map.json")

    def get_hypotheses(self) -> dict[str, Any]:
        return _load_json(PHASE_4_DATA / "hypothesis-backlog.json")

    def get_measurement(self) -> dict[str, Any]:
        return _load_json(PHASE_5_DATA / "measurement-framework.json")

    def get_report(self, name: str) -> dict[str, Any]:
        path = REPORT_FILES.get(name)
        if not path:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown report '{name}'. Available: {sorted(REPORT_FILES)}",
            )
        if path.suffix.lower() == ".json":
            return {
                "name": name,
                "format": "json",
                "content": _load_json(path),
            }
        return {
            "name": name,
            "format": "markdown",
            "content": _read_text(path),
        }

    def list_report_names(self) -> list[str]:
        return sorted(REPORT_FILES)
