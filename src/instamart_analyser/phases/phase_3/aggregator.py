"""Deterministic theme aggregation for Phase 3."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from instamart_analyser.common.config import PHASE_3_DATA
from instamart_analyser.common.models import utc_now_iso
from instamart_analyser.phases.phase_2.storage import EnrichedStore

SUMMARY_PATH = PHASE_3_DATA / "theme-summary.json"
CLUSTERS_PATH = PHASE_3_DATA / "theme-clusters.json"
DISCOVERY_BARRIERS_PATH = PHASE_3_DATA / "discovery-barriers.json"
SHOPPING_BEHAVIOUR_PATH = PHASE_3_DATA / "shopping-behaviour.json"
CATEGORY_OPPORTUNITIES_PATH = PHASE_3_DATA / "category-opportunities.json"
SEGMENT_ANALYSIS_PATH = PHASE_3_DATA / "segment-analysis.json"


def make_snippet(text: str, limit: int = 220) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."


def _cluster_id(barrier: str, mission: str, category: str) -> str:
    return f"{barrier}__{mission}__{category}"


def classify_bucket(enrichment: dict[str, Any]) -> str:
    category_barriers = enrichment.get("category_exploration_barrier", [])
    mission = enrichment.get("shopping_mission", "other")
    adjacent = enrichment.get("adjacent_category_opportunity", [])
    if category_barriers:
        return "discovery_barriers"
    if adjacent or enrichment.get("experimentation_likelihood") == "high":
        return "category_expansion_opportunities"
    if mission in {"planned_purchase", "impulse_purchase", "emergency_purchase", "exploration", "browse_discover"}:
        return "shopping_behaviour_patterns"
    return "operational_pain_points"


def derive_analysis_fields(enrichment: dict[str, Any]) -> dict[str, Any]:
    """Backfill discovery fields from older enrichment records."""
    discovery_trigger = list(enrichment.get("discovery_trigger", []))
    if not discovery_trigger:
        channel_map = {
            "search": "search",
            "reorder_previous": "previous_orders",
            "homepage_browse": "homepage_category_browsing",
            "recommendation_engine": "recommendation",
            "promotional_banner": "offers",
            "external_referral": "external_influence",
        }
        discovery_trigger = list(
            dict.fromkeys(
                channel_map[ch]
                for ch in enrichment.get("discovery_channels", [])
                if ch in channel_map
            )
        )

    exploration_barriers = list(enrichment.get("category_exploration_barrier", []))
    if not exploration_barriers:
        barrier_map = {
            "trust_quality": "lack_of_trust",
            "information_gap": "lack_of_information",
            "price_sensitivity": "price_uncertainty",
            "habit_lock_in": "habit_lock_in",
            "assortment_gap": "unavailable_products",
            "poor_discovery": "poor_discovery",
        }
        exploration_barriers = list(
            dict.fromkeys(
                barrier_map[barrier]
                for barrier in enrichment.get("barriers", [])
                if barrier in barrier_map
            )
        )

    experimentation_likelihood = enrichment.get("experimentation_likelihood")
    if experimentation_likelihood not in {"high", "medium", "low"}:
        if enrichment.get("experimentation_signal") or enrichment.get("shopping_mission") in {"browse_discover", "exploration"}:
            experimentation_likelihood = "high"
        elif exploration_barriers or enrichment.get("habit_signal"):
            experimentation_likelihood = "low"
        else:
            experimentation_likelihood = "medium"

    required_trust_signal = list(enrichment.get("required_trust_signal", []))
    if not required_trust_signal:
        inferred: list[str] = []
        if enrichment.get("trust_concerns") or "lack_of_trust" in exploration_barriers:
            inferred.extend(["reviews", "ratings", "guarantees"])
        if "lack_of_information" in exploration_barriers:
            inferred.append("comparisons")
        if enrichment.get("price_concerns"):
            inferred.append("recommendations")
        required_trust_signal = list(dict.fromkeys(inferred))

    adjacent_category_opportunity = list(enrichment.get("adjacent_category_opportunity", []))
    if not adjacent_category_opportunity and experimentation_likelihood == "high":
        adjacent_category_opportunity = [
            category
            for category in enrichment.get("categories_mentioned", [])
            if category != "grocery"
        ]

    return {
        "discovery_trigger": discovery_trigger,
        "category_exploration_barrier": exploration_barriers,
        "experimentation_likelihood": experimentation_likelihood,
        "required_trust_signal": required_trust_signal,
        "adjacent_category_opportunity": adjacent_category_opportunity,
    }


def product_opportunity(cluster: dict[str, Any]) -> str:
    barrier = cluster["primary_barrier"]
    discovery_barriers = set(cluster.get("category_exploration_barrier", []))
    if "poor_discovery" in discovery_barriers or barrier == "poor_discovery":
        return "Improve homepage/category discovery, search relevance, and cross-category recommendations."
    if "habit_lock_in" in discovery_barriers or barrier == "habit_lock_in":
        return "Create habit-breaking nudges such as adjacent-category prompts on reorder journeys."
    if "lack_of_information" in discovery_barriers or barrier == "information_gap":
        return "Add richer PDP information, reviews, comparisons, and trust cues before trial."
    if "price_uncertainty" in discovery_barriers or barrier in {"price_sensitivity", "delivery_fee_threshold"}:
        return "Use clearer pricing, entry offers, and low-risk bundles to reduce trial friction."
    if "unavailable_products" in discovery_barriers or barrier == "assortment_gap":
        return "Highlight assortment breadth and substitute availability in under-explored categories."
    if "lack_of_trust" in discovery_barriers or barrier in {"trust_quality", "past_bad_experience"}:
        return "Fix quality/refund/service failures and surface guarantees before pushing new categories."
    return "Review this theme manually and map it to a targeted growth or product experiment."


def aggregate_themes(
    *,
    min_cluster_size: int = 3,
    max_evidence: int = 8,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Group enriched records into repeatable theme clusters."""
    store = EnrichedStore()
    rows = store.get_all_enriched()

    by_cluster: dict[str, dict[str, Any]] = {}
    barrier_counts: Counter[str] = Counter()
    mission_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    segment_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    cooccurrence_counts: Counter[str] = Counter()
    exploration_barrier_counts: Counter[str] = Counter()
    discovery_trigger_counts: Counter[str] = Counter()
    trust_signal_counts: Counter[str] = Counter()
    experimentation_counts: Counter[str] = Counter()
    bucket_counts: Counter[str] = Counter()
    segment_profiles: dict[str, dict[str, Counter[str]]] = {}

    for row in rows:
        enrichment = row["enrichment"]
        derived = derive_analysis_fields(enrichment)
        source = row["source"]
        body_text = row["body_text"]
        barriers = enrichment.get("barriers", []) or ["other"]
        mission = enrichment.get("shopping_mission", "other")
        categories = enrichment.get("categories_mentioned", []) or ["other"]
        segment = enrichment.get("user_segment_hypothesis", "other")
        analysis_enrichment = {**enrichment, **derived}
        bucket = classify_bucket(analysis_enrichment)
        bucket_counts[bucket] += 1
        category_exploration_barriers = derived["category_exploration_barrier"]
        discovery_triggers = derived["discovery_trigger"]
        trust_signals = derived["required_trust_signal"]
        experimentation = derived["experimentation_likelihood"]

        mission_counts[mission] += 1
        segment_counts[segment] += 1
        source_counts[source] += 1
        experimentation_counts[experimentation] += 1
        for barrier in category_exploration_barriers:
            exploration_barrier_counts[barrier] += 1
        for trigger in discovery_triggers:
            discovery_trigger_counts[trigger] += 1
        for signal in trust_signals:
            trust_signal_counts[signal] += 1
        for barrier in barriers:
            barrier_counts[barrier] += 1
        for category in categories:
            category_counts[category] += 1

        profile = segment_profiles.setdefault(
            segment,
            {
                "missions": Counter(),
                "barriers": Counter(),
                "exploration_barriers": Counter(),
                "experimentation_likelihood": Counter(),
            },
        )
        profile["missions"][mission] += 1
        for barrier in barriers:
            profile["barriers"][barrier] += 1
        for barrier in category_exploration_barriers:
            profile["exploration_barriers"][barrier] += 1
        profile["experimentation_likelihood"][experimentation] += 1

        unique_barriers = sorted(set(barriers))
        for i, left in enumerate(unique_barriers):
            for right in unique_barriers[i + 1 :]:
                cooccurrence_counts[f"{left}|{right}"] += 1

        primary_barrier = barriers[0] if barriers else "other"
        primary_category = categories[0] if categories else "other"
        theme_id = _cluster_id(primary_barrier, mission, primary_category)
        cluster = by_cluster.setdefault(
            theme_id,
            {
                "theme_id": theme_id,
                "primary_barrier": primary_barrier,
                "shopping_mission": mission,
                "primary_category": primary_category,
                "source_breakdown": Counter(),
                "segment_breakdown": Counter(),
                "record_ids": [],
                "supporting_evidence": [],
                "cooccurring_barriers": Counter(),
                "bucket": bucket,
                "category_exploration_barrier": Counter(),
                "discovery_trigger": Counter(),
                "required_trust_signal": Counter(),
                "experimentation_likelihood": Counter(),
            },
        )
        cluster["source_breakdown"][source] += 1
        cluster["segment_breakdown"][segment] += 1
        cluster["record_ids"].append(row["record_id"])
        cluster["supporting_evidence"].append(
            {
                "record_id": row["record_id"],
                "source": source,
                "snippet": make_snippet(body_text),
            }
        )
        for barrier in barriers[1:]:
            cluster["cooccurring_barriers"][barrier] += 1
        for barrier in category_exploration_barriers:
            cluster["category_exploration_barrier"][barrier] += 1
        for trigger in discovery_triggers:
            cluster["discovery_trigger"][trigger] += 1
        for signal in trust_signals:
            cluster["required_trust_signal"][signal] += 1
        cluster["experimentation_likelihood"][experimentation] += 1

    clusters: list[dict[str, Any]] = []
    for cluster in by_cluster.values():
        total = len(cluster["record_ids"])
        if total < min_cluster_size:
            continue
        segment_breakdown = Counter(cluster["segment_breakdown"])
        source_breakdown = Counter(cluster["source_breakdown"])
        clusters.append(
            {
                "theme_id": cluster["theme_id"],
                "primary_barrier": cluster["primary_barrier"],
                "shopping_mission": cluster["shopping_mission"],
                "primary_category": cluster["primary_category"],
                "analysis_bucket": cluster["bucket"],
                "total_supporting_records": total,
                "source_breakdown": dict(source_breakdown),
                "affected_segment": segment_breakdown.most_common(1)[0][0] if segment_breakdown else "general",
                "segment_breakdown": dict(segment_breakdown),
                "cooccurring_barriers": dict(cluster["cooccurring_barriers"].most_common(5)),
                "category_exploration_barrier": list(cluster["category_exploration_barrier"].keys()),
                "discovery_trigger": list(cluster["discovery_trigger"].keys()),
                "required_trust_signal": list(cluster["required_trust_signal"].keys()),
                "experimentation_likelihood": cluster["experimentation_likelihood"].most_common(1)[0][0]
                if cluster["experimentation_likelihood"]
                else "medium",
                "supporting_evidence": cluster["supporting_evidence"][:max_evidence],
                "record_ids": cluster["record_ids"],
                "confidence": "high" if total >= 10 and len(source_breakdown) >= 2 else "medium" if total >= 5 else "low",
                "product_opportunity": product_opportunity(
                    {
                        "primary_barrier": cluster["primary_barrier"],
                        "category_exploration_barrier": list(cluster["category_exploration_barrier"].keys()),
                    }
                ),
            }
        )

    clusters.sort(
        key=lambda c: (
            -c["total_supporting_records"],
            -len(c["source_breakdown"]),
            c["theme_id"],
        )
    )

    summary = {
        "created_at": utc_now_iso(),
        "enriched_record_count": len(rows),
        "cluster_count": len(clusters),
        "analysis_bucket_counts": dict(bucket_counts),
        "top_barriers": barrier_counts.most_common(10),
        "top_missions": mission_counts.most_common(10),
        "top_categories": category_counts.most_common(10),
        "top_segments": segment_counts.most_common(10),
        "top_discovery_barriers": exploration_barrier_counts.most_common(10),
        "top_discovery_triggers": discovery_trigger_counts.most_common(10),
        "top_required_trust_signals": trust_signal_counts.most_common(10),
        "experimentation_likelihood_breakdown": experimentation_counts.most_common(),
        "source_breakdown": dict(source_counts),
        "top_barrier_cooccurrences": cooccurrence_counts.most_common(10),
        "bias_notes": [
            "Current enriched sample is complaint-heavy and dominated by Play Store reviews.",
            "Discovery-specific themes should be interpreted alongside this source bias.",
        ],
    }

    payload = {"summary": summary, "clusters": clusters}
    target_dir = output_dir or PHASE_3_DATA
    target_dir.mkdir(parents=True, exist_ok=True)
    with SUMMARY_PATH.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    with CLUSTERS_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    discovery_barriers = [
        {
            "theme": cluster["theme_id"],
            "category_exploration_barrier": cluster["category_exploration_barrier"],
            "supporting_review_count": cluster["total_supporting_records"],
            "affected_segment": cluster["affected_segment"],
            "confidence": cluster["confidence"],
            "evidence_examples": cluster["supporting_evidence"][:3],
            "product_opportunity": cluster["product_opportunity"],
        }
        for cluster in clusters
        if cluster["analysis_bucket"] == "discovery_barriers"
    ]
    shopping_behaviour = [
        {
            "theme": cluster["theme_id"],
            "shopping_mission": cluster["shopping_mission"],
            "experimentation_likelihood": cluster["experimentation_likelihood"],
            "supporting_review_count": cluster["total_supporting_records"],
            "affected_segment": cluster["affected_segment"],
            "confidence": cluster["confidence"],
            "evidence_examples": cluster["supporting_evidence"][:3],
            "product_opportunity": cluster["product_opportunity"],
        }
        for cluster in clusters
        if cluster["analysis_bucket"] == "shopping_behaviour_patterns"
    ]
    category_opportunities = [
        {
            "theme": cluster["theme_id"],
            "adjacent_category": cluster["primary_category"],
            "discovery_trigger": cluster["discovery_trigger"],
            "supporting_review_count": cluster["total_supporting_records"],
            "affected_segment": cluster["affected_segment"],
            "confidence": cluster["confidence"],
            "evidence_examples": cluster["supporting_evidence"][:3],
            "product_opportunity": cluster["product_opportunity"],
        }
        for cluster in clusters
        if cluster["analysis_bucket"] == "category_expansion_opportunities"
    ]
    segment_analysis = [
        {
            "segment": segment,
            "review_count": segment_counts[segment],
            "top_missions": profile["missions"].most_common(5),
            "top_barriers": profile["barriers"].most_common(5),
            "top_discovery_barriers": profile["exploration_barriers"].most_common(5),
            "experimentation_likelihood": profile["experimentation_likelihood"].most_common(),
        }
        for segment, profile in sorted(segment_profiles.items(), key=lambda item: -segment_counts[item[0]])
    ]

    with DISCOVERY_BARRIERS_PATH.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "created_at": summary["created_at"],
                "play_store_bias_note": summary["bias_notes"][0],
                "items": discovery_barriers,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    with SHOPPING_BEHAVIOUR_PATH.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "created_at": summary["created_at"],
                "play_store_bias_note": summary["bias_notes"][0],
                "items": shopping_behaviour,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    with CATEGORY_OPPORTUNITIES_PATH.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "created_at": summary["created_at"],
                "play_store_bias_note": summary["bias_notes"][0],
                "items": category_opportunities,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    with SEGMENT_ANALYSIS_PATH.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "created_at": summary["created_at"],
                "play_store_bias_note": summary["bias_notes"][0],
                "items": segment_analysis,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    return payload


def load_clusters(path: Path | None = None) -> dict[str, Any]:
    clusters_path = path or CLUSTERS_PATH
    with clusters_path.open(encoding="utf-8") as f:
        return json.load(f)
