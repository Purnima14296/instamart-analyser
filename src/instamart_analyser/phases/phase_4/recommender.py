"""Phase 4 recommendation framing from Phase 3 insights."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from instamart_analyser.common.config import PHASE_3_DATA, PHASE_4_DATA
from instamart_analyser.common.models import utc_now_iso

OPPORTUNITY_MAP_PATH = PHASE_4_DATA / "opportunity-map.json"
HYPOTHESIS_BACKLOG_PATH = PHASE_4_DATA / "hypothesis-backlog.json"
EXPERIMENT_MEMO_PATH = PHASE_4_DATA / "experiment-framing-memo.md"
SUMMARY_PATH = PHASE_4_DATA / "phase-4-summary.json"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _pretty_label(value: str) -> str:
    return value.replace("_", " ").strip().title()


def _category_label(value: str) -> str:
    if value == "other":
        return "Cross-category"
    return _pretty_label(value)


def _bucket_weight(cluster: dict[str, Any]) -> int:
    bucket = cluster.get("analysis_bucket")
    if bucket == "discovery_barriers":
        return 3
    if bucket == "category_expansion_opportunities":
        return 3
    if bucket == "shopping_behaviour_patterns":
        return 2
    return 1


def _confidence_weight(confidence: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(confidence, 1)


def _segment_size(segment: str, segment_counts: dict[str, int]) -> dict[str, Any]:
    count = int(segment_counts.get(segment, 0))
    if count >= 30:
        band = "large"
    elif count >= 10:
        band = "medium"
    else:
        band = "small"
    return {"segment": segment, "review_count": count, "size_band": band}


def _opportunity_types(cluster: dict[str, Any]) -> list[str]:
    barrier = cluster.get("primary_barrier", "")
    discovery_barriers = set(cluster.get("category_exploration_barrier", []))
    types: list[str] = []
    if barrier in {"poor_discovery", "habit_lock_in", "information_gap"} or discovery_barriers & {
        "poor_discovery",
        "lack_of_information",
        "habit_lock_in",
    }:
        types.append("discovery")
    if barrier in {"trust_quality", "past_bad_experience"} or "lack_of_trust" in discovery_barriers:
        types.append("trust")
    if barrier in {"price_sensitivity", "delivery_fee_threshold"} or "price_uncertainty" in discovery_barriers:
        types.append("pricing")
    if barrier == "assortment_gap" or "unavailable_products" in discovery_barriers:
        types.append("assortment")
    if not types:
        types.append("service")
    return list(dict.fromkeys(types))


def _recommendation_playbook(cluster: dict[str, Any]) -> dict[str, Any]:
    barrier = cluster.get("primary_barrier", "")
    discovery_barriers = set(cluster.get("category_exploration_barrier", []))
    category = _category_label(cluster.get("primary_category", "other"))
    segment = _pretty_label(cluster.get("affected_segment", "general"))
    mission = _pretty_label(cluster.get("shopping_mission", "other"))

    if barrier in {"trust_quality", "past_bad_experience"} or "lack_of_trust" in discovery_barriers:
        return {
            "title": "Rebuild trust before cross-sell",
            "user_problem": f"{segment} users do not want to try more categories when core grocery or delivery experiences feel unreliable.",
            "intervention_area": "trust",
            "opportunity_statement": "Improve quality, refund, and service confidence before pushing category expansion.",
            "recommended_moves": [
                "Surface freshness or replacement guarantees near adjacent-category modules.",
                "Show delivery reliability and issue-resolution reassurance before trial prompts.",
                "Target category expansion prompts only after a clean recent order history.",
            ],
            "expected_business_effect": "Higher trust should reduce drop-off from expansion prompts and increase willingness to try adjacent categories.",
            "assumptions": [
                "Reliability concerns are suppressing exploration, not just driving churn.",
                "Trust cues placed near expansion surfaces will change willingness to browse or add items.",
            ],
        }
    if barrier == "poor_discovery" or "poor_discovery" in discovery_barriers:
        return {
            "title": "Make adjacent categories easier to notice",
            "user_problem": f"{segment} users stay in narrow {mission.lower()} missions because the app does not make new categories easy to find.",
            "intervention_area": "discovery",
            "opportunity_statement": f"Improve search, category browsing, and recommendation surfaces to reveal {category.lower()} and nearby categories.",
            "recommended_moves": [
                "Add adjacent-category prompts during reorder and search journeys.",
                "Improve homepage and category landing-page navigation for common missions.",
                "Use contextual recommendations tied to basket contents instead of generic banners.",
            ],
            "expected_business_effect": "Better discovery should increase browse depth and new-category consideration without needing deep discounts.",
            "assumptions": [
                "Users are willing to explore if relevant options are made visible at the right moment.",
                "Discovery friction is a bigger constraint than supply for these themes.",
            ],
        }
    if barrier in {"price_sensitivity", "delivery_fee_threshold"} or "price_uncertainty" in discovery_barriers:
        return {
            "title": "Lower the first-try price risk",
            "user_problem": f"{segment} users hesitate to add new-category items because total cost feels uncertain or not worth the risk.",
            "intervention_area": "pricing",
            "opportunity_statement": "Reduce trial friction with clearer value communication and low-risk entry offers.",
            "recommended_moves": [
                "Bundle adjacent-category trials with staple reorder journeys.",
                "Use entry-price callouts and fee transparency before checkout.",
                "Test limited-scope offers on categories with high hesitation and medium interest.",
            ],
            "expected_business_effect": "Lower perceived risk should improve trial conversion in categories users already consider but do not purchase.",
            "assumptions": [
                "Users already have some intent but stop because economics are unclear.",
                "Targeted offers will drive exploration without fully training users to wait for discounts.",
            ],
        }
    if barrier == "assortment_gap" or "unavailable_products" in discovery_barriers:
        return {
            "title": "Strengthen assortment credibility",
            "user_problem": f"{segment} users will not shift more shopping missions into the app when expected {category.lower()} products feel unavailable or incomplete.",
            "intervention_area": "assortment",
            "opportunity_statement": "Increase confidence that the category is worth exploring by improving perceived breadth and fallback options.",
            "recommended_moves": [
                "Highlight availability breadth and substitutes for underexplored categories.",
                "Expose category-specific assortment callouts before the user enters the list.",
                "Avoid promoting categories in cities or timeslots with weak availability.",
            ],
            "expected_business_effect": "Stronger assortment confidence should raise browse-to-add conversion for categories beyond staples.",
            "assumptions": [
                "The barrier is perceived lack of depth, not only isolated stock-outs.",
                "Merchandising can partially offset supply constraints by setting expectations better.",
            ],
        }
    if barrier == "information_gap" or "lack_of_information" in discovery_barriers:
        return {
            "title": "Explain new-category choices better",
            "user_problem": f"{segment} users do not have enough information to confidently try unfamiliar {category.lower()} items.",
            "intervention_area": "discovery",
            "opportunity_statement": "Use richer reviews, comparisons, and product context to make trial decisions easier.",
            "recommended_moves": [
                "Add review density, comparison aids, and use-case explanations to trial-focused surfaces.",
                "Show trust signals prominently on unfamiliar brands and categories.",
                "Prioritize education modules where experimentation likelihood is medium, not very low.",
            ],
            "expected_business_effect": "Better information should improve confidence for categories with curiosity but low conviction.",
            "assumptions": [
                "Missing information is blocking action more than price or trust in these themes.",
                "Users will engage with concise guidance if placed close to purchase decisions.",
            ],
        }
    if barrier == "habit_lock_in" or "habit_lock_in" in discovery_barriers:
        return {
            "title": "Interrupt repeat-order autopilot",
            "user_problem": f"{segment} users default to the same replenishment habits and rarely branch into adjacent categories.",
            "intervention_area": "discovery",
            "opportunity_statement": "Use context-aware nudges in repeat journeys to break narrow shopping habits.",
            "recommended_moves": [
                "Inject adjacent-category prompts into reorder flows.",
                "Trigger curated discovery modules when basket composition signals routine replenishment.",
                "Test reminders around use occasions, not only broad catalog promotions.",
            ],
            "expected_business_effect": "Breaking habit loops should create incremental category trials from already-engaged users.",
            "assumptions": [
                "These users are retained enough to respond to nudges instead of needing service fixes first.",
                "Contextual prompts will feel useful rather than distracting during repeat missions.",
            ],
        }
    return {
        "title": "Investigate and frame a targeted intervention",
        "user_problem": f"{segment} users show a repeat pattern in {mission.lower()} journeys, but the root cause is not specific enough for a single intervention yet.",
        "intervention_area": "service",
        "opportunity_statement": "Treat this as a secondary opportunity area pending more evidence or manual review.",
        "recommended_moves": [
            "Review the underlying evidence manually and refine the barrier definition.",
            "Pair this theme with a clearer adjacent-category or mission signal before experimentation.",
        ],
        "expected_business_effect": "Clarifying the theme can prevent low-signal experiments and sharpen the backlog.",
        "assumptions": [
            "Current evidence is directionally useful but not precise enough for a strong product bet.",
        ],
    }


def _priority_score(cluster: dict[str, Any], insight: dict[str, Any], segment_counts: dict[str, int]) -> dict[str, Any]:
    total_support = int(cluster.get("total_supporting_records", 0))
    segment = cluster.get("affected_segment", "general")
    segment_review_count = int(segment_counts.get(segment, 0))
    strategic_importance = 3 if cluster.get("shopping_mission") == "replenishment" else 2
    evidence = 3 if total_support >= 10 else 2 if total_support >= 5 else 1
    segment_scale = 3 if segment_review_count >= 30 else 2 if segment_review_count >= 10 else 1
    actionability = _bucket_weight(cluster)
    confidence = _confidence_weight(insight.get("confidence", cluster.get("confidence", "low")))
    total = evidence + segment_scale + strategic_importance + actionability + confidence
    if total >= 13:
        band = "high"
    elif total >= 10:
        band = "medium"
    else:
        band = "low"
    return {
        "score": total,
        "priority_band": band,
        "components": {
            "evidence_strength": evidence,
            "segment_size": segment_scale,
            "strategic_importance": strategic_importance,
            "actionability": actionability,
            "confidence": confidence,
        },
    }


def _top_items(counter_like: dict[str, int], limit: int = 3) -> list[str]:
    items = sorted(counter_like.items(), key=lambda item: (-item[1], item[0]))
    return [name for name, _count in items[:limit]]


def build_recommendation_frame(
    *,
    phase_3_dir: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    source_dir = phase_3_dir or PHASE_3_DATA
    target_dir = output_dir or PHASE_4_DATA
    target_dir.mkdir(parents=True, exist_ok=True)

    insights_payload = _load_json(source_dir / "insights.json")
    clusters_payload = _load_json(source_dir / "theme-clusters.json")
    summary = clusters_payload["summary"]
    clusters = {cluster["theme_id"]: cluster for cluster in clusters_payload["clusters"]}
    segment_counts = {name: count for name, count in summary.get("top_segments", [])}

    opportunities: list[dict[str, Any]] = []
    grouped_ids: dict[str, list[str]] = defaultdict(list)

    for insight in insights_payload.get("insights", []):
        theme_ids = insight.get("theme_ids") or []
        if not theme_ids:
            continue
        cluster = clusters.get(theme_ids[0])
        if not cluster:
            continue

        playbook = _recommendation_playbook(cluster)
        priority = _priority_score(cluster, insight, segment_counts)
        types = _opportunity_types(cluster)
        evidence = cluster.get("supporting_evidence", [])[:3]
        triggers = cluster.get("discovery_trigger", [])
        trust_signals = cluster.get("required_trust_signal", [])
        group_key = f"{playbook['title']}::{cluster.get('affected_segment', 'general')}::{cluster.get('shopping_mission', 'other')}"

        opportunity = {
            "opportunity_id": f"opp_{len(opportunities) + 1:03d}",
            "title": playbook["title"],
            "linked_insight_ids": [insight["insight_id"]],
            "linked_theme_ids": theme_ids,
            "opportunity_types": types,
            "intervention_area": playbook["intervention_area"],
            "user_problem": playbook["user_problem"],
            "opportunity_statement": playbook["opportunity_statement"],
            "recommended_moves": playbook["recommended_moves"],
            "expected_business_effect": playbook["expected_business_effect"],
            "affected_segment": cluster.get("affected_segment", "general"),
            "segment_size_estimate": _segment_size(cluster.get("affected_segment", "general"), segment_counts),
            "shopping_mission": cluster.get("shopping_mission", "other"),
            "primary_category": cluster.get("primary_category", "other"),
            "top_discovery_triggers": triggers[:3],
            "required_trust_signals": trust_signals[:3],
            "supporting_record_count": cluster.get("total_supporting_records", 0),
            "source_breakdown": cluster.get("source_breakdown", {}),
            "confidence": insight.get("confidence", cluster.get("confidence", "low")),
            "priority": priority,
            "assumptions_and_unknowns": playbook["assumptions"]
            + [
                "The current sample is still dominated by Play Store complaints and should be treated as directional.",
                "No recommendation here should be treated as proof of causality without an experiment.",
            ],
            "evidence_examples": evidence,
            "derived_from_bucket": cluster.get("analysis_bucket", "operational_pain_points"),
        }
        opportunities.append(opportunity)
        grouped_ids[group_key].append(opportunity["opportunity_id"])

    opportunities.sort(
        key=lambda item: (
            -item["priority"]["score"],
            -item["supporting_record_count"],
            item["title"],
        )
    )

    for idx, opportunity in enumerate(opportunities, start=1):
        opportunity["rank"] = idx

    hypotheses: list[dict[str, Any]] = []
    for opportunity in opportunities:
        category = _category_label(opportunity["primary_category"])
        segment = _pretty_label(opportunity["affected_segment"])
        mission = _pretty_label(opportunity["shopping_mission"]).lower()
        area = opportunity["intervention_area"]
        if area == "trust":
            test = "surface guarantees and post-order reassurance in adjacent-category prompts"
            metric = "new-category add-to-order rate among eligible users"
        elif area == "pricing":
            test = "show low-risk entry offers or bundles for adjacent categories"
            metric = "trial conversion for promoted adjacent-category items"
        elif area == "assortment":
            test = "prominently show assortment breadth and substitutes before category entry"
            metric = "browse-to-add conversion for the targeted category"
        else:
            test = "improve discovery prompts and category navigation in high-intent journeys"
            metric = "share of users who open or add from a new category"

        hypotheses.append(
            {
                "hypothesis_id": f"hyp_{len(hypotheses) + 1:03d}",
                "priority_rank": opportunity["rank"],
                "linked_opportunity_id": opportunity["opportunity_id"],
                "hypothesis": (
                    f"If Instamart uses {test} for {segment} users during {mission} missions, "
                    f"then {metric} should improve for {category.lower()} opportunities."
                ),
                "user_problem": opportunity["user_problem"],
                "proposed_intervention": opportunity["recommended_moves"][0],
                "expected_effect": opportunity["expected_business_effect"],
                "primary_metric": metric,
                "guardrail_metrics": [
                    "overall order conversion",
                    "customer support contacts per order",
                    "refund or cancellation rate",
                ],
                "priority": opportunity["priority"],
                "confidence": opportunity["confidence"],
                "assumptions": opportunity["assumptions_and_unknowns"][:3],
                "traceability": {
                    "opportunity_id": opportunity["opportunity_id"],
                    "insight_ids": opportunity["linked_insight_ids"],
                    "theme_ids": opportunity["linked_theme_ids"],
                },
            }
        )

    hypotheses.sort(key=lambda item: item["priority_rank"])

    type_counts: Counter[str] = Counter()
    band_counts: Counter[str] = Counter()
    for opportunity in opportunities:
        for item in opportunity["opportunity_types"]:
            type_counts[item] += 1
        band_counts[opportunity["priority"]["priority_band"]] += 1

    summary_payload = {
        "created_at": utc_now_iso(),
        "phase_3_created_at": insights_payload.get("created_at"),
        "input_insight_count": insights_payload.get("insight_count", 0),
        "input_cluster_count": summary.get("cluster_count", 0),
        "enriched_record_count": summary.get("enriched_record_count", 0),
        "opportunity_count": len(opportunities),
        "hypothesis_count": len(hypotheses),
        "opportunity_type_breakdown": dict(type_counts),
        "priority_band_breakdown": dict(band_counts),
        "top_segments": summary.get("top_segments", [])[:5],
        "bias_notes": summary.get("bias_notes", []),
    }

    opportunity_payload = {
        "created_at": summary_payload["created_at"],
        "input_summary": summary_payload,
        "opportunities": opportunities,
    }
    hypothesis_payload = {
        "created_at": summary_payload["created_at"],
        "input_summary": summary_payload,
        "hypotheses": hypotheses,
    }

    with OPPORTUNITY_MAP_PATH.open("w", encoding="utf-8") as f:
        json.dump(opportunity_payload, f, indent=2, ensure_ascii=False)
    with HYPOTHESIS_BACKLOG_PATH.open("w", encoding="utf-8") as f:
        json.dump(hypothesis_payload, f, indent=2, ensure_ascii=False)
    with SUMMARY_PATH.open("w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2, ensure_ascii=False)

    return {
        "summary": summary_payload,
        "opportunities": opportunities,
        "hypotheses": hypotheses,
    }


def write_experiment_memo(payload: dict[str, Any], output_dir: Path | None = None) -> Path:
    target_dir = output_dir or PHASE_4_DATA
    target_dir.mkdir(parents=True, exist_ok=True)

    summary = payload["summary"]
    opportunities = payload["opportunities"]
    hypotheses = payload["hypotheses"]

    lines = [
        "# Phase 4 Experiment Framing Memo",
        "",
        f"- Generated at: `{summary['created_at']}`",
        f"- Enriched reviews represented: **{summary['enriched_record_count']}**",
        f"- Phase 3 insight inputs: **{summary['input_insight_count']}**",
        f"- Opportunity areas: **{summary['opportunity_count']}**",
        f"- Hypotheses in backlog: **{summary['hypothesis_count']}**",
        "",
        "## What This Output Is",
        "",
        "This phase converts evidence-backed insights into product opportunity areas and experiment hypotheses.",
        "It does not claim causality. These recommendations are directional and should be validated through testing.",
        "",
        "## Priority Opportunity Areas",
        "",
    ]

    for opportunity in opportunities[:5]:
        lines.extend(
            [
                f"### {opportunity['rank']}. {opportunity['title']}",
                f"- Priority: `{opportunity['priority']['priority_band']}` ({opportunity['priority']['score']})",
                f"- Type: `{', '.join(opportunity['opportunity_types'])}`",
                f"- Segment: `{opportunity['affected_segment']}`",
                f"- Mission: `{opportunity['shopping_mission']}`",
                f"- User problem: {opportunity['user_problem']}",
                f"- Opportunity framing: {opportunity['opportunity_statement']}",
                f"- Expected effect: {opportunity['expected_business_effect']}",
                "- Suggested moves:",
            ]
        )
        for move in opportunity["recommended_moves"][:3]:
            lines.append(f"  - {move}")
        lines.append("- Evidence:")
        for evidence in opportunity["evidence_examples"][:2]:
            lines.append(
                f"  - `{evidence['record_id']}` ({evidence.get('source', 'unknown')}): {evidence['snippet']}"
            )
        lines.append("")

    lines.extend(["## Initial Hypothesis Backlog", ""])
    for hypothesis in hypotheses[:5]:
        lines.extend(
            [
                f"### {hypothesis['hypothesis_id']}: rank {hypothesis['priority_rank']}",
                f"- Hypothesis: {hypothesis['hypothesis']}",
                f"- Proposed intervention: {hypothesis['proposed_intervention']}",
                f"- Primary metric: {hypothesis['primary_metric']}",
                f"- Guardrails: {', '.join(hypothesis['guardrail_metrics'])}",
                "",
            ]
        )

    lines.extend(["## Assumptions And Risks", ""])
    for note in summary.get("bias_notes", []):
        lines.append(f"- {note}")
    lines.extend(
        [
            "- Recommendations are evidence-backed but still reflect a partial and complaint-heavy sample.",
            "- Themes with low confidence or weak source diversity should be tested after trust or service basics are stabilized.",
            "- Category-expansion experiments should avoid over-triggering users whose recent experiences were unresolved.",
            "",
        ]
    )

    with EXPERIMENT_MEMO_PATH.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    return EXPERIMENT_MEMO_PATH

