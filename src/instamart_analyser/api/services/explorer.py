"""Research explorer services: sources, reviews, challenges, causes, needs, journey."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from instamart_analyser.api.services.artifacts import ArtifactService, _load_json_optional
from instamart_analyser.api.services.research import ResearchSummaryService
from instamart_analyser.common.config import PHASE_1_DATA, PHASE_3_DATA, PHASE_4_DATA, PHASE_5_DATA
from instamart_analyser.phases.phase_1.storage.normalized_store import NormalizedStore
from instamart_analyser.phases.phase_2.storage import EnrichedStore

CONCERN_FIELDS = (
    "trust_concerns",
    "price_concerns",
    "assortment_concerns",
    "information_gaps",
    "friction_types",
)

NEED_FIELDS = ("information_gaps", "assortment_concerns")


def _top(counter: Counter, limit: int = 10) -> list[dict[str, Any]]:
    return [{"name": name, "count": count} for name, count in counter.most_common(limit)]


class ExplorerService:
    """Derives explorer views from Phase 1–5 artifacts and stores."""

    def __init__(self, artifacts: ArtifactService | None = None) -> None:
        self.artifacts = artifacts or ArtifactService()
        self.research = ResearchSummaryService(self.artifacts)
        self.normalized = NormalizedStore()
        self.enriched = EnrichedStore()

    # ---------- shared helpers ----------

    def _enriched_index(self) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        for row in self.enriched.get_all_enriched():
            index[row["record_id"]] = row
        return index

    def _bias_notes(self) -> list[str]:
        summary = _load_json_optional(PHASE_3_DATA / "theme-summary.json") or {}
        return summary.get("bias_notes", [])

    # ---------- source analysis ----------

    def sources(self) -> dict[str, Any]:
        records = self.normalized.get_all_records()
        enriched = self._enriched_index()

        by_source: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "rating_sum": 0,
                "rating_count": 0,
                "enriched_count": 0,
                "sentiment": Counter(),
                "barriers": Counter(),
            }
        )

        for record in records:
            source = record["source"]
            bucket = by_source[source]
            bucket["count"] += 1
            if record.get("rating"):
                bucket["rating_sum"] += int(record["rating"])
                bucket["rating_count"] += 1
            hit = enriched.get(record["record_id"])
            if hit:
                bucket["enriched_count"] += 1
                payload = hit["enrichment"]
                bucket["sentiment"][(payload.get("sentiment") or "neutral")] += 1
                for barrier in payload.get("barriers") or []:
                    bucket["barriers"][barrier] += 1

        total = len(records)
        items = []
        for source, bucket in by_source.items():
            avg_rating = (
                round(bucket["rating_sum"] / bucket["rating_count"], 2)
                if bucket["rating_count"]
                else None
            )
            sentiment_total = sum(bucket["sentiment"].values()) or 1
            items.append(
                {
                    "source": source,
                    "count": bucket["count"],
                    "share_pct": round((bucket["count"] / total) * 100, 1) if total else 0.0,
                    "avg_rating": avg_rating,
                    "rated_count": bucket["rating_count"],
                    "enriched_count": bucket["enriched_count"],
                    "enriched_pct": (
                        round((bucket["enriched_count"] / bucket["count"]) * 100, 1)
                        if bucket["count"]
                        else 0.0
                    ),
                    "sentiment_pct": {
                        key: round((bucket["sentiment"].get(key, 0) / sentiment_total) * 100, 1)
                        for key in ("positive", "negative", "neutral", "mixed")
                    },
                    "top_barriers": _top(bucket["barriers"], 5),
                }
            )

        items.sort(key=lambda row: row["count"], reverse=True)
        pre_llm = _load_json_optional(PHASE_1_DATA / "pre-llm-analysis.json") or {}
        return {
            "total_reviews": total,
            "source_count": len(items),
            "sources": items,
            "rating_distribution": pre_llm.get("rating_distribution", {}),
            "coverage_note": (
                "Source mix is uneven: Play Store dominates. Treat cross-source comparisons as directional."
            ),
            "bias_notes": self._bias_notes(),
        }

    # ---------- review discovery ----------

    def reviews(
        self,
        *,
        query: str | None = None,
        source: str | None = None,
        sentiment: str | None = None,
        segment: str | None = None,
        mission: str | None = None,
        barrier: str | None = None,
        enriched_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        records = self.normalized.get_all_records()
        enriched = self._enriched_index()
        needle = (query or "").strip().lower()

        matches: list[dict[str, Any]] = []
        for record in records:
            hit = enriched.get(record["record_id"])
            payload = hit["enrichment"] if hit else None

            if enriched_only and not payload:
                continue
            if source and record["source"] != source:
                continue
            if needle and needle not in (record.get("body_text") or "").lower():
                continue
            if sentiment and (not payload or payload.get("sentiment") != sentiment):
                continue
            if segment and (not payload or payload.get("user_segment_hypothesis") != segment):
                continue
            if mission and (not payload or payload.get("shopping_mission") != mission):
                continue
            if barrier and (not payload or barrier not in (payload.get("barriers") or [])):
                continue

            matches.append(
                {
                    "record_id": record["record_id"],
                    "source": record["source"],
                    "rating": record.get("rating"),
                    "title": record.get("title"),
                    "url": record.get("url"),
                    "timestamp": record.get("timestamp"),
                    "body_text": record.get("body_text"),
                    "enriched": bool(payload),
                    "sentiment": (payload or {}).get("sentiment"),
                    "shopping_mission": (payload or {}).get("shopping_mission"),
                    "user_segment": (payload or {}).get("user_segment_hypothesis"),
                    "barriers": (payload or {}).get("barriers") or [],
                    "categories_mentioned": (payload or {}).get("categories_mentioned") or [],
                    "habit_signal": (payload or {}).get("habit_signal"),
                    "experimentation_signal": (payload or {}).get("experimentation_signal"),
                }
            )

        page = matches[offset : offset + limit]
        return {
            "total_matched": len(matches),
            "returned": len(page),
            "offset": offset,
            "limit": limit,
            "facets": self._review_facets(records, enriched),
            "reviews": page,
        }

    def _review_facets(
        self,
        records: list[dict[str, Any]],
        enriched: dict[str, dict[str, Any]],
    ) -> dict[str, list[str]]:
        sources = sorted({r["source"] for r in records})
        segments: set[str] = set()
        missions: set[str] = set()
        barriers: set[str] = set()
        for row in enriched.values():
            payload = row["enrichment"]
            if payload.get("user_segment_hypothesis"):
                segments.add(payload["user_segment_hypothesis"])
            if payload.get("shopping_mission"):
                missions.add(payload["shopping_mission"])
            for barrier in payload.get("barriers") or []:
                barriers.add(barrier)
        return {
            "sources": sources,
            "segments": sorted(segments),
            "missions": sorted(missions),
            "barriers": sorted(barriers),
            "sentiments": ["positive", "negative", "neutral", "mixed"],
        }

    # ---------- discovery challenges ----------

    def discovery_challenges(self) -> dict[str, Any]:
        payload = _load_json_optional(PHASE_3_DATA / "discovery-barriers.json") or {}
        summary = _load_json_optional(PHASE_3_DATA / "theme-summary.json") or {}
        rows = self.enriched.get_all_enriched()

        barrier_counts = Counter()
        discovery_channel_counts = Counter()
        for row in rows:
            enrichment = row["enrichment"]
            for barrier in enrichment.get("barriers") or []:
                barrier_counts[barrier] += 1
            for channel in enrichment.get("discovery_channels") or []:
                discovery_channel_counts[channel] += 1

        items = payload.get("items") or []
        for item in items:
            item["evidence_count"] = len(item.get("evidence_examples") or [])

        items.sort(key=lambda i: i.get("supporting_review_count") or 0, reverse=True)
        return {
            "created_at": payload.get("created_at"),
            "challenge_count": len(items),
            "challenges": items,
            "barrier_totals": _top(barrier_counts, 12),
            "discovery_channels": _top(discovery_channel_counts, 10),
            "top_discovery_barriers": summary.get("top_discovery_barriers", []),
            "bias_notes": self._bias_notes(),
        }

    # ---------- segment explorer ----------

    def segments(self) -> dict[str, Any]:
        payload = _load_json_optional(PHASE_3_DATA / "segment-analysis.json") or {}
        research = self.research.get_summary()
        priority = {
            row["segment"]: row for row in research["segment_priority"]["segments"]
        }
        items = []
        for item in payload.get("items") or []:
            merged = dict(item)
            merged["priority"] = priority.get(item.get("segment"))
            items.append(merged)
        items.sort(
            key=lambda i: (i.get("priority") or {}).get("priority_score") or 0,
            reverse=True,
        )
        return {
            "created_at": payload.get("created_at"),
            "segment_count": len(items),
            "segments": items,
            "recommended_focus": research["segment_priority"]["recommended_focus"],
            "formula": research["segment_priority"]["formula"],
            "bias_notes": self._bias_notes(),
        }

    # ---------- root cause analysis ----------

    def root_causes(self) -> dict[str, Any]:
        rows = self.enriched.get_all_enriched()
        by_barrier: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "causes": Counter(),
                "segments": Counter(),
                "missions": Counter(),
                "sentiment": Counter(),
                "evidence": [],
            }
        )

        for row in rows:
            enrichment = row["enrichment"]
            barriers = enrichment.get("barriers") or ["other"]
            for barrier in barriers:
                bucket = by_barrier[barrier]
                bucket["count"] += 1
                for field in CONCERN_FIELDS:
                    for value in enrichment.get(field) or []:
                        bucket["causes"][f"{field.replace('_', ' ')}: {value}"] += 1
                if enrichment.get("user_segment_hypothesis"):
                    bucket["segments"][enrichment["user_segment_hypothesis"]] += 1
                if enrichment.get("shopping_mission"):
                    bucket["missions"][enrichment["shopping_mission"]] += 1
                bucket["sentiment"][enrichment.get("sentiment") or "neutral"] += 1
                if len(bucket["evidence"]) < 3:
                    bucket["evidence"].append(
                        {
                            "record_id": row["record_id"],
                            "source": row["source"],
                            "snippet": (row.get("body_text") or "")[:240],
                        }
                    )

        causes = []
        for barrier, bucket in by_barrier.items():
            causes.append(
                {
                    "barrier": barrier,
                    "affected_reviews": bucket["count"],
                    "root_causes": _top(bucket["causes"], 6),
                    "top_segments": _top(bucket["segments"], 3),
                    "top_missions": _top(bucket["missions"], 3),
                    "sentiment": dict(bucket["sentiment"]),
                    "evidence": bucket["evidence"],
                    "confidence": (
                        "high"
                        if bucket["count"] >= 25
                        else "medium"
                        if bucket["count"] >= 10
                        else "low"
                    ),
                }
            )
        causes.sort(key=lambda c: c["affected_reviews"], reverse=True)
        return {
            "analyzed_records": len(rows),
            "cause_group_count": len(causes),
            "causes": causes,
            "method": (
                "Group enriched reviews by barrier, then tally trust / price / assortment / "
                "information / friction concerns as candidate root causes."
            ),
            "bias_notes": self._bias_notes(),
        }

    # ---------- unmet needs ----------

    def unmet_needs(self) -> dict[str, Any]:
        rows = self.enriched.get_all_enriched()
        need_counts: Counter = Counter()
        need_segments: dict[str, Counter] = defaultdict(Counter)
        need_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for row in rows:
            enrichment = row["enrichment"]
            for field in NEED_FIELDS:
                for value in enrichment.get(field) or []:
                    key = f"{value}"
                    need_counts[key] += 1
                    if enrichment.get("user_segment_hypothesis"):
                        need_segments[key][enrichment["user_segment_hypothesis"]] += 1
                    if len(need_evidence[key]) < 3:
                        need_evidence[key].append(
                            {
                                "record_id": row["record_id"],
                                "source": row["source"],
                                "snippet": (row.get("body_text") or "")[:240],
                            }
                        )

        needs = []
        for name, count in need_counts.most_common(20):
            needs.append(
                {
                    "need": name,
                    "mentions": count,
                    "top_segments": _top(need_segments[name], 3),
                    "evidence": need_evidence[name],
                    "confidence": "high" if count >= 15 else "medium" if count >= 5 else "low",
                }
            )

        category = _load_json_optional(PHASE_3_DATA / "category-opportunities.json") or {}
        opportunity_map = _load_json_optional(PHASE_4_DATA / "opportunity-map.json") or {}
        return {
            "analyzed_records": len(rows),
            "need_count": len(needs),
            "needs": needs,
            "category_opportunities": category.get("items", []),
            "linked_opportunities": [
                {
                    "opportunity_id": o.get("opportunity_id"),
                    "title": o.get("title"),
                    "priority_band": (o.get("priority") or {}).get("priority_band"),
                }
                for o in (opportunity_map.get("opportunities") or [])[:5]
            ],
            "bias_notes": self._bias_notes(),
        }

    # ---------- discovery journey ----------

    def journey(self) -> dict[str, Any]:
        rows = self.enriched.get_all_enriched()
        missions = Counter()
        channels = Counter()
        triggers = Counter()
        barriers = Counter()
        categories = Counter()
        habit = 0
        experimentation = 0
        urgency = 0
        convenience = 0

        for row in rows:
            enrichment = row["enrichment"]
            if enrichment.get("shopping_mission"):
                missions[enrichment["shopping_mission"]] += 1
            for channel in enrichment.get("discovery_channels") or []:
                channels[channel] += 1
            for trigger in enrichment.get("triggers") or []:
                triggers[trigger] += 1
            for barrier in enrichment.get("barriers") or []:
                barriers[barrier] += 1
            for category in enrichment.get("categories_mentioned") or []:
                categories[category] += 1
            habit += 1 if enrichment.get("habit_signal") else 0
            experimentation += 1 if enrichment.get("experimentation_signal") else 0
            urgency += 1 if enrichment.get("urgency_context") else 0
            convenience += 1 if enrichment.get("convenience_signal") else 0

        total = len(rows) or 1
        stages = [
            {
                "stage": "Arrive with a mission",
                "description": "What brings the shopper into the app.",
                "items": _top(missions, 6),
            },
            {
                "stage": "Discover",
                "description": "How they find products today.",
                "items": _top(channels, 6),
            },
            {
                "stage": "Trigger to explore",
                "description": "What nudges a step outside the usual basket.",
                "items": _top(triggers, 6),
            },
            {
                "stage": "Blocked",
                "description": "Barriers that stop cross-category trial.",
                "items": _top(barriers, 6),
            },
            {
                "stage": "Categories reached",
                "description": "Categories actually mentioned in feedback.",
                "items": _top(categories, 6),
            },
        ]

        return {
            "analyzed_records": len(rows),
            "stages": stages,
            "behaviour_signals": {
                "habit_pct": round((habit / total) * 100, 1),
                "experimentation_pct": round((experimentation / total) * 100, 1),
                "urgency_pct": round((urgency / total) * 100, 1),
                "convenience_pct": round((convenience / total) * 100, 1),
                "habit_count": habit,
                "experimentation_count": experimentation,
            },
            "shopping_behaviour": (
                _load_json_optional(PHASE_3_DATA / "shopping-behaviour.json") or {}
            ).get("items", []),
            "bias_notes": self._bias_notes(),
        }

    # ---------- validation ----------

    def validation(self) -> dict[str, Any]:
        alignment = _load_json_optional(PHASE_5_DATA / "manual-alignment.json") or {}
        phase5 = _load_json_optional(PHASE_5_DATA / "phase-5-summary.json") or {}
        refinements = _load_json_optional(PHASE_5_DATA / "refinements-log.json") or {}
        pilot = _load_json_optional(PHASE_5_DATA / "pilot-status.json") or {}
        feedback = self.artifacts.store.list_feedback() if hasattr(self.artifacts.store, "list_feedback") else []

        return {
            "method": alignment.get("method"),
            "alignment_verdict": alignment.get("alignment_verdict"),
            "aligned_top5_count": alignment.get("aligned_top5_count"),
            "comparisons": alignment.get("comparisons", []),
            "pilot_ready": phase5.get("pilot_ready"),
            "open_defects": phase5.get("open_defects"),
            "feedback_responses": phase5.get("feedback_responses"),
            "refinements": {
                "prompt": refinements.get("prompt_refinements", []),
                "taxonomy": refinements.get("taxonomy_refinements", []),
                "threshold": refinements.get("threshold_refinements", []),
            },
            "pilot_scope": pilot.get("pilot_scope", {}),
            "stakeholder_feedback_count": len(feedback) if isinstance(feedback, list) else 0,
            "bias_notes": self._bias_notes(),
        }
