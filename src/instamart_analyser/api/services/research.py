"""Compose Product Research Intelligence summary from Phase 1–5 artifacts."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from instamart_analyser.api.services.artifacts import ArtifactService, _load_json_optional
from instamart_analyser.common.config import PHASE_1_DATA, PHASE_3_DATA, PHASE_4_DATA, PHASE_5_DATA
from instamart_analyser.phases.phase_1.storage.normalized_store import NormalizedStore
from instamart_analyser.phases.phase_2.storage import EnrichedStore


TRUST_BARRIER_KEYS = {"trust_quality", "past_bad_experience", "lack_of_trust"}


class ResearchSummaryService:
    """Spotify-style research brief built from existing Instamart artifacts (no LLM required)."""

    def __init__(self, artifacts: ArtifactService | None = None) -> None:
        self.artifacts = artifacts or ArtifactService()
        self.enriched = EnrichedStore()
        self.normalized = NormalizedStore()

    def get_summary(self) -> dict[str, Any]:
        enrichment = self.artifacts.enrichment_status()
        theme_summary = _load_json_optional(PHASE_3_DATA / "theme-summary.json") or {}
        insights = _load_json_optional(PHASE_3_DATA / "insights.json") or {}
        opportunity_map = _load_json_optional(PHASE_4_DATA / "opportunity-map.json") or {}
        phase5 = _load_json_optional(PHASE_5_DATA / "phase-5-summary.json") or {}
        segment_payload = _load_json_optional(PHASE_3_DATA / "segment-analysis.json") or {}
        pre_llm = _load_json_optional(PHASE_1_DATA / "pre-llm-analysis.json") or {}
        discovery_barriers = _load_json_optional(PHASE_3_DATA / "discovery-barriers.json") or {}

        source_counts = self._source_counts()
        ingested_total = sum(source_counts.values())
        sentiment = self._sentiment_breakdown(pre_llm)
        avg_rating = self._avg_rating(pre_llm)
        segments = self._segment_priority(segment_payload.get("items") or [])
        top_opportunity = self._top_opportunity(opportunity_map.get("opportunities") or [])
        trust = self._discovery_trust_score(
            theme_summary=theme_summary,
            sentiment=sentiment,
            segments=segments,
        )
        key_findings = self._key_findings(theme_summary, insights, segments)
        executive_brief = self._executive_brief(
            enrichment=enrichment,
            theme_summary=theme_summary,
            sentiment=sentiment,
            trust=trust,
            segments=segments,
            top_opportunity=top_opportunity,
            insights=insights,
        )
        pipeline_status = self._pipeline_status(enrichment)

        return {
            "product": "Swiggy Instamart",
            "title": "Product Research Intelligence",
            "subtitle": "Category-discovery intelligence across ingested Instamart feedback",
            "executive_brief": executive_brief,
            "key_findings": key_findings,
            "portfolio": {
                "reviews_ingested": ingested_total,
                "source_counts": source_counts,
                "play_store": source_counts.get("play_store", 0),
                "app_store": source_counts.get("app_store", 0),
                "reddit": source_counts.get("reddit", 0)
                + source_counts.get("reddit_selenium", 0),
                "themes_discovered": theme_summary.get("cluster_count") or 0,
                "insights_count": insights.get("insight_count") or 0,
                "opportunities_count": (opportunity_map.get("input_summary") or {}).get(
                    "opportunity_count",
                    len(opportunity_map.get("opportunities") or []),
                ),
                "avg_rating": avg_rating,
                "analysis_sample": enrichment["enriched_count"],
                "analysis_pending": enrichment["remaining_to_enrich"],
                "cohort_size": enrichment["cohort_size"],
                "coverage_pct": enrichment["coverage_pct"],
            },
            "sentiment": sentiment,
            "discovery_trust": trust,
            "segment_priority": {
                "recommended_focus": segments[0] if segments else None,
                "segments": segments,
                "formula": (
                    "priority_score = review_count × (discovery_barrier_rate + trust_barrier_rate). "
                    "Higher scores = scale × discovery/trust pain."
                ),
            },
            "top_opportunity": top_opportunity,
            "top_challenge": self._top_challenge(theme_summary, discovery_barriers),
            "research_grounding": {
                "themes": theme_summary.get("cluster_count") or 0,
                "segments": len(segment_payload.get("items") or []),
                "insights": insights.get("insight_count") or 0,
                "opportunities": len(opportunity_map.get("opportunities") or []),
                "enriched_records": enrichment["enriched_count"],
            },
            "pipeline_status": pipeline_status,
            "pilot": {
                "pilot_ready": phase5.get("pilot_ready"),
                "alignment_verdict": phase5.get("alignment_verdict"),
                "open_defects": phase5.get("open_defects"),
            },
            "bias_notes": theme_summary.get("bias_notes")
            or (
                [segment_payload["play_store_bias_note"]]
                if segment_payload.get("play_store_bias_note")
                else []
            ),
            "score_formulas": {
                "discovery_trust": trust["formula"],
                "segment_priority": (
                    "priority_score = review_count × (discovery_barrier_rate + trust_barrier_rate)"
                ),
            },
        }

    def _source_counts(self) -> dict[str, int]:
        try:
            return dict(self.normalized.count_by_source())
        except Exception:  # noqa: BLE001
            pre = _load_json_optional(PHASE_1_DATA / "pre-llm-analysis.json") or {}
            return dict(pre.get("by_source") or {})

    def _sentiment_breakdown(self, pre_llm: dict[str, Any]) -> dict[str, Any]:
        counts = Counter()
        try:
            with self.enriched._connect() as conn:  # noqa: SLF001
                rows = conn.execute(
                    "SELECT enrichment_json FROM enriched_feedback WHERE review_status != 'error'"
                ).fetchall()
            for row in rows:
                try:
                    payload = json.loads(row["enrichment_json"])
                    sentiment = (payload.get("sentiment") or "neutral").lower()
                    if sentiment not in {"positive", "negative", "neutral", "mixed"}:
                        sentiment = "neutral"
                    counts[sentiment] += 1
                except Exception:  # noqa: BLE001
                    continue
        except Exception:  # noqa: BLE001
            counts = Counter()

        if not counts:
            hint = pre_llm.get("sentiment_hint") or {}
            counts = Counter(
                {
                    "positive": int(hint.get("positive") or 0),
                    "negative": int(hint.get("negative") or 0),
                    "neutral": int(hint.get("neutral") or 0),
                    "mixed": 0,
                }
            )
            source = "pre_llm_heuristic"
        else:
            source = "enriched_labels"

        total = sum(counts.values()) or 1
        pct = {k: round((counts.get(k, 0) / total) * 100, 1) for k in ("positive", "negative", "neutral", "mixed")}
        return {
            "source": source,
            "counts": {
                "positive": counts.get("positive", 0),
                "negative": counts.get("negative", 0),
                "neutral": counts.get("neutral", 0),
                "mixed": counts.get("mixed", 0),
            },
            "percentages": pct,
            "total": sum(counts.values()),
        }

    def _avg_rating(self, pre_llm: dict[str, Any]) -> float | None:
        dist = pre_llm.get("rating_distribution") or {}
        total = 0
        weight = 0
        for rating_str, count in dist.items():
            try:
                rating = int(rating_str)
                n = int(count)
            except (TypeError, ValueError):
                continue
            total += rating * n
            weight += n
        if weight <= 0:
            return None
        return round(total / weight, 2)

    def _segment_priority(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        sample_total = sum(int(i.get("review_count") or 0) for i in items) or 1
        ranked: list[dict[str, Any]] = []
        for item in items:
            review_count = int(item.get("review_count") or 0)
            if review_count <= 0:
                continue
            discovery = item.get("top_discovery_barriers") or []
            barriers = item.get("top_barriers") or []
            discovery_hits = sum(int(c) for _, c in discovery)
            trust_hits = sum(
                int(c)
                for name, c in barriers
                if str(name) in TRUST_BARRIER_KEYS
            )
            discovery_rate = min(discovery_hits / review_count, 1.5)
            trust_rate = min(trust_hits / review_count, 1.5)
            priority_score = round(review_count * (discovery_rate + trust_rate), 1)
            top_frustration = None
            if discovery:
                top_frustration = discovery[0][0]
            elif barriers:
                top_frustration = barriers[0][0]
            ranked.append(
                {
                    "segment": item.get("segment"),
                    "review_count": review_count,
                    "pct_sample": round((review_count / sample_total) * 100, 1),
                    "discovery_barrier_rate": round(discovery_rate, 3),
                    "trust_barrier_rate": round(trust_rate, 3),
                    "priority_score": priority_score,
                    "top_frustration": top_frustration,
                    "top_missions": (item.get("top_missions") or [])[:3],
                    "top_discovery_barriers": discovery[:5],
                }
            )
        ranked.sort(key=lambda row: row["priority_score"], reverse=True)
        for idx, row in enumerate(ranked, start=1):
            row["rank"] = idx
            row["recommended"] = idx == 1
        return ranked

    def _top_opportunity(self, opportunities: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not opportunities:
            return None
        ordered = sorted(
            opportunities,
            key=lambda o: (
                -((o.get("priority") or {}).get("score") or 0),
                o.get("rank") or 999,
            ),
        )
        top = ordered[0]
        return {
            "opportunity_id": top.get("opportunity_id"),
            "title": top.get("title"),
            "opportunity_statement": top.get("opportunity_statement"),
            "user_problem": top.get("user_problem"),
            "affected_segment": top.get("affected_segment"),
            "supporting_record_count": top.get("supporting_record_count"),
            "priority_score": (top.get("priority") or {}).get("score"),
            "priority_band": (top.get("priority") or {}).get("priority_band"),
            "opportunity_types": top.get("opportunity_types") or [],
            "recommended_moves": (top.get("recommended_moves") or [])[:3],
        }

    def _discovery_trust_score(
        self,
        *,
        theme_summary: dict[str, Any],
        sentiment: dict[str, Any],
        segments: list[dict[str, Any]],
    ) -> dict[str, Any]:
        enriched = int(theme_summary.get("enriched_record_count") or sentiment.get("total") or 1)
        barriers = theme_summary.get("top_barriers") or []
        trust_hits = sum(int(c) for name, c in barriers if str(name) in TRUST_BARRIER_KEYS)
        discovery_hits = sum(
            int(c)
            for name, c in barriers
            if str(name) in {"poor_discovery", "habit_lock_in", "cognitive_overload", "information_gap"}
        )
        neg_pct = float((sentiment.get("percentages") or {}).get("negative") or 0)
        focus = segments[0] if segments else None
        focus_penalty = 0.0
        if focus:
            focus_penalty = min(float(focus.get("discovery_barrier_rate") or 0) * 10, 15)

        # 100 baseline; subtract trust/discovery intensity and negativity.
        trust_penalty = min((trust_hits / enriched) * 35, 35)
        discovery_penalty = min((discovery_hits / enriched) * 25, 25)
        sentiment_penalty = min(neg_pct * 0.25, 25)
        score = max(0.0, round(100 - trust_penalty - discovery_penalty - sentiment_penalty - focus_penalty, 1))
        formula = (
            "100 − trust_barrier_share×35 − discovery_barrier_share×25 − negative%×0.25 "
            "− focus_segment_discovery_rate×10 (each term capped)."
        )
        return {
            "score": score,
            "label": (
                "strong" if score >= 70 else "moderate" if score >= 45 else "weak"
            ),
            "components": {
                "trust_penalty": round(trust_penalty, 1),
                "discovery_penalty": round(discovery_penalty, 1),
                "sentiment_penalty": round(sentiment_penalty, 1),
                "focus_segment_penalty": round(focus_penalty, 1),
            },
            "formula": formula,
        }

    def _top_challenge(
        self,
        theme_summary: dict[str, Any],
        discovery_barriers: dict[str, Any],
    ) -> dict[str, Any]:
        barriers = theme_summary.get("top_barriers") or []
        if barriers:
            name, count = barriers[0]
            return {
                "name": name,
                "count": count,
                "detail": f"{name} appears across {count} enriched reviews in top barrier tallies.",
            }
        items = discovery_barriers.get("items") or []
        if items:
            first = items[0]
            return {
                "name": first.get("theme") or first.get("barrier") or "discovery_friction",
                "count": first.get("supporting_review_count") or 0,
                "detail": first.get("product_opportunity")
                or first.get("summary")
                or "Top discovery barrier from Phase 3.",
            }
        return {"name": "not_available", "count": 0, "detail": "No challenge data yet."}

    def _key_findings(
        self,
        theme_summary: dict[str, Any],
        insights: dict[str, Any],
        segments: list[dict[str, Any]],
    ) -> list[str]:
        findings: list[str] = []
        barriers = theme_summary.get("top_barriers") or []
        for name, count in barriers[:3]:
            findings.append(f"{name.replace('_', ' ').title()} shows up in {count} enriched reviews.")
        if segments:
            focus = segments[0]
            findings.append(
                f"{str(focus['segment']).replace('_', ' ').title()} is the priority segment "
                f"({focus['review_count']} reviews, priority score {focus['priority_score']})."
            )
        insight_list = insights.get("insights") or []
        for insight in insight_list[:2]:
            statement = (insight.get("statement") or "").strip()
            if statement:
                findings.append(statement[:220] + ("…" if len(statement) > 220 else ""))
        return findings[:6]

    def _executive_brief(
        self,
        *,
        enrichment: dict[str, Any],
        theme_summary: dict[str, Any],
        sentiment: dict[str, Any],
        trust: dict[str, Any],
        segments: list[dict[str, Any]],
        top_opportunity: dict[str, Any] | None,
        insights: dict[str, Any],
    ) -> str:
        neg = (sentiment.get("percentages") or {}).get("negative", 0)
        focus = segments[0]["segment"].replace("_", " ") if segments else "priority shoppers"
        top_barrier = "trust and discovery friction"
        if theme_summary.get("top_barriers"):
            top_barrier = str(theme_summary["top_barriers"][0][0]).replace("_", " ")
        opp_line = ""
        if top_opportunity:
            opp_line = (
                f" Highest-impact opportunity: {top_opportunity.get('title')} "
                f"(priority {top_opportunity.get('priority_band')}, "
                f"score {top_opportunity.get('priority_score')})."
            )
        pending = enrichment.get("remaining_to_enrich") or 0
        sample = enrichment.get("enriched_count") or 0
        pending_note = (
            f" {sample} of {enrichment.get('cohort_size') or sample} cohort reviews analyzed"
            + (f"; {pending} still pending enrichment." if pending else ".")
        )
        return (
            f"Instamart category discovery is constrained by {top_barrier}. "
            f"Among analyzed feedback, {neg}% is negative and category-discovery trust sits at "
            f"{trust['score']}/100 ({trust['label']}). "
            f"The {focus} segment carries the largest scale × pain signal. "
            f"{insights.get('insight_count') or 0} insights and "
            f"{theme_summary.get('cluster_count') or 0} themes ground this view."
            f"{opp_line}{pending_note}"
        )

    def _pipeline_status(self, enrichment: dict[str, Any]) -> dict[str, Any]:
        jobs = self.artifacts.store.list_jobs(limit=20)
        last = jobs[0] if jobs else None
        active = next((j for j in jobs if j["status"] in {"queued", "running"}), None)
        return {
            "active_job": active,
            "last_job": last,
            "enrichment_pending": enrichment.get("remaining_to_enrich"),
            "quota_blocked": enrichment.get("quota_blocked"),
            "quota_message": enrichment.get("quota_message"),
        }
