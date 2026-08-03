"""Phase 5 pilot readiness, manual alignment, and pilot report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from instamart_analyser.common.config import (
    PHASE_1_DATA,
    PHASE_2_DATA,
    PHASE_2_DB,
    PHASE_3_DATA,
    PHASE_4_DATA,
    PHASE_5_DATA,
)
from instamart_analyser.common.models import utc_now_iso
from instamart_analyser.phases.phase_2.storage import EnrichedStore

PILOT_STATUS_PATH = PHASE_5_DATA / "pilot-status.json"
MANUAL_ALIGNMENT_PATH = PHASE_5_DATA / "manual-alignment.json"
PILOT_REPORT_PATH = PHASE_5_DATA / "pilot-report.md"

# Map pre-LLM keyword themes to Phase 3 taxonomy barriers for alignment checks.
THEME_TO_BARRIER = {
    "product_quality": "trust_quality",
    "customer_support": "past_bad_experience",
    "delivery_quality": "past_bad_experience",
    "delivery_speed": "past_bad_experience",
    "app_ux_discovery": "poor_discovery",
    "habit_reorder": "habit_lock_in",
    "pricing_offers": "price_sensitivity",
    "category_exploration": "poor_discovery",
}


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _exists(path: Path) -> bool:
    return path.exists()


def collect_pilot_status() -> dict[str, Any]:
    """Inspect Phases 1–4 artifacts and enrichment coverage for the pilot."""
    store = EnrichedStore()
    enriched_count = store.count_enriched()
    error_count = store.count_errors()

    cohort = _load_json(PHASE_2_DATA / "enrichment-cohort.json") or {}
    cohort_size = len(cohort.get("record_ids", [])) if cohort else 0
    theme_summary = _load_json(PHASE_3_DATA / "theme-summary.json") or {}
    insights = _load_json(PHASE_3_DATA / "insights.json") or {}
    phase4 = _load_json(PHASE_4_DATA / "phase-4-summary.json") or {}
    pre_llm = _load_json(PHASE_1_DATA / "pre-llm-analysis.json") or {}

    coverage_pct = round((enriched_count / cohort_size) * 100, 1) if cohort_size else 0.0
    artifact_checks = {
        "phase1_normalized_db": _exists(PHASE_1_DATA / "db" / "instamart_raw.sqlite"),
        "phase1_pre_llm_analysis": _exists(PHASE_1_DATA / "pre-llm-analysis.json"),
        "phase2_cohort": _exists(PHASE_2_DATA / "enrichment-cohort.json"),
        "phase2_enriched_db": _exists(PHASE_2_DB / "enriched.sqlite"),
        "phase3_theme_summary": _exists(PHASE_3_DATA / "theme-summary.json"),
        "phase3_insights": _exists(PHASE_3_DATA / "insights.json"),
        "phase3_stakeholder_summary": _exists(PHASE_3_DATA / "stakeholder-summary.md"),
        "phase4_opportunity_map": _exists(PHASE_4_DATA / "opportunity-map.json"),
        "phase4_hypothesis_backlog": _exists(PHASE_4_DATA / "hypothesis-backlog.json"),
        "phase4_experiment_memo": _exists(PHASE_4_DATA / "experiment-framing-memo.md"),
    }

    readiness = {
        "artifacts_complete": all(artifact_checks.values()),
        "has_enriched_sample": enriched_count >= 100,
        "has_insights": int(insights.get("insight_count", 0)) > 0,
        "has_hypotheses": int(phase4.get("hypothesis_count", 0)) > 0,
        "bias_documented": bool(theme_summary.get("bias_notes")),
        "enrichment_coverage_note": (
            "Partial enrichment is acceptable for pilot if bias and confidence are documented."
            if coverage_pct < 80
            else "Enrichment coverage is strong for pilot scope."
        ),
    }

    status = {
        "created_at": utc_now_iso(),
        "pilot_scope": {
            "cohort_size": cohort_size,
            "enriched_count": enriched_count,
            "enrichment_error_count": error_count,
            "enrichment_coverage_pct": coverage_pct,
            "normalized_review_count": pre_llm.get("total_reviews"),
            "theme_cluster_count": theme_summary.get("cluster_count"),
            "insight_count": insights.get("insight_count"),
            "opportunity_count": phase4.get("opportunity_count"),
            "hypothesis_count": phase4.get("hypothesis_count"),
        },
        "artifact_checks": artifact_checks,
        "readiness": readiness,
        "pilot_ready": all(
            [
                readiness["artifacts_complete"],
                readiness["has_enriched_sample"],
                readiness["has_insights"],
                readiness["has_hypotheses"],
                readiness["bias_documented"],
            ]
        ),
        "known_limitations": [
            "Public feedback overrepresents extreme negative opinions.",
            "Play Store reviews dominate the sample.",
            "Partial enrichment means Phase 3–4 conclusions are directional, not final.",
            "Recommendations must not be treated as causal proof without experiments.",
        ],
    }

    PHASE_5_DATA.mkdir(parents=True, exist_ok=True)
    with PILOT_STATUS_PATH.open("w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
    return status


def compare_manual_alignment() -> dict[str, Any]:
    """Compare Phase 3 AI barriers against Phase 1 pre-LLM keyword themes."""
    pre_llm = _load_json(PHASE_1_DATA / "pre-llm-analysis.json") or {}
    theme_summary = _load_json(PHASE_3_DATA / "theme-summary.json") or {}

    keyword_themes = pre_llm.get("theme_signal_counts", {})
    ai_barriers = {
        name: count for name, count in theme_summary.get("top_barriers", [])
    }

    mapped_keyword_strength: dict[str, int] = {}
    for theme, count in keyword_themes.items():
        barrier = THEME_TO_BARRIER.get(theme)
        if not barrier:
            continue
        mapped_keyword_strength[barrier] = mapped_keyword_strength.get(barrier, 0) + int(count)

    comparisons: list[dict[str, Any]] = []
    all_barriers = sorted(set(mapped_keyword_strength) | set(ai_barriers))
    aligned = 0
    for barrier in all_barriers:
        keyword_rank = (
            sorted(mapped_keyword_strength, key=mapped_keyword_strength.get, reverse=True).index(barrier) + 1
            if barrier in mapped_keyword_strength
            else None
        )
        ai_rank = (
            sorted(ai_barriers, key=ai_barriers.get, reverse=True).index(barrier) + 1
            if barrier in ai_barriers
            else None
        )
        both_present = keyword_rank is not None and ai_rank is not None
        top_both = both_present and keyword_rank <= 5 and ai_rank <= 5
        if top_both:
            aligned += 1
        comparisons.append(
            {
                "barrier": barrier,
                "pre_llm_mapped_count": mapped_keyword_strength.get(barrier, 0),
                "ai_enriched_count": ai_barriers.get(barrier, 0),
                "pre_llm_rank": keyword_rank,
                "ai_rank": ai_rank,
                "aligned_in_top5": top_both,
            }
        )

    comparisons.sort(
        key=lambda item: (-item["ai_enriched_count"], -item["pre_llm_mapped_count"], item["barrier"])
    )

    alignment = {
        "created_at": utc_now_iso(),
        "method": (
            "Compare Phase 1 keyword theme counts (mapped to taxonomy barriers) "
            "against Phase 3 AI-enriched barrier counts."
        ),
        "aligned_top5_count": aligned,
        "alignment_verdict": (
            "Major themes align between keyword pre-analysis and AI enrichment."
            if aligned >= 3
            else "Partial alignment — review disagreements before stakeholder publish."
        ),
        "comparisons": comparisons,
        "notes": [
            "Keyword analysis covers the full normalized corpus; AI barriers cover the enriched subset only.",
            "Trust/quality and past-bad-experience often absorb delivery and support keyword themes.",
            "Gold-set human labels remain the preferred precision check when filled.",
        ],
    }

    PHASE_5_DATA.mkdir(parents=True, exist_ok=True)
    with MANUAL_ALIGNMENT_PATH.open("w", encoding="utf-8") as f:
        json.dump(alignment, f, indent=2, ensure_ascii=False)
    return alignment


def write_pilot_report(
    status: dict[str, Any],
    alignment: dict[str, Any],
    feedback_summary: dict[str, Any] | None = None,
    refinements: dict[str, Any] | None = None,
    measurement: dict[str, Any] | None = None,
) -> Path:
    """Write the Phase 5 pilot report markdown."""
    scope = status["pilot_scope"]
    lines = [
        "# Phase 5 Pilot Report",
        "",
        f"- Generated at: `{status['created_at']}`",
        f"- Pilot ready: **{'yes' if status['pilot_ready'] else 'no'}**",
        f"- Enriched sample: **{scope['enriched_count']}** / {scope['cohort_size']} cohort "
        f"({scope['enrichment_coverage_pct']}%)",
        f"- Insights: **{scope['insight_count']}**",
        f"- Opportunities / hypotheses: **{scope['opportunity_count']}** / **{scope['hypothesis_count']}**",
        "",
        "## Pilot Objective",
        "",
        "Confirm the end-to-end Instamart category-discovery agent is stable enough for stakeholder review "
        "and ready to support growth experiment planning.",
        "",
        "## End-To-End Readiness",
        "",
    ]
    for name, ok in status["artifact_checks"].items():
        lines.append(f"- `{'PASS' if ok else 'FAIL'}` {name}")

    lines.extend(
        [
            "",
            "## Manual Alignment Check",
            "",
            f"- Verdict: {alignment['alignment_verdict']}",
            f"- Barriers aligned in both top-5 views: **{alignment['aligned_top5_count']}**",
            "",
            "| Barrier | Pre-LLM mapped | AI enriched | Pre-LLM rank | AI rank | Top-5 align |",
            "|---|---:|---:|---:|---:|:---:|",
        ]
    )
    for row in alignment["comparisons"][:8]:
        lines.append(
            f"| `{row['barrier']}` | {row['pre_llm_mapped_count']} | {row['ai_enriched_count']} | "
            f"{row['pre_llm_rank'] or '-'} | {row['ai_rank'] or '-'} | "
            f"{'yes' if row['aligned_in_top5'] else 'no'} |"
        )

    if feedback_summary:
        lines.extend(
            [
                "",
                "## Stakeholder Feedback Snapshot",
                "",
                f"- Responses recorded: **{feedback_summary.get('response_count', 0)}**",
                f"- Open defects: **{feedback_summary.get('open_defect_count', 0)}**",
                f"- Deferred items: **{feedback_summary.get('deferred_count', 0)}**",
            ]
        )
        for item in feedback_summary.get("top_themes", [])[:5]:
            lines.append(f"- {item}")

    if refinements:
        lines.extend(
            [
                "",
                "## Captured Refinements",
                "",
                f"- Prompt refinements: **{len(refinements.get('prompt_refinements', []))}**",
                f"- Taxonomy refinements: **{len(refinements.get('taxonomy_refinements', []))}**",
                f"- Threshold refinements: **{len(refinements.get('threshold_refinements', []))}**",
            ]
        )

    if measurement:
        lines.extend(
            [
                "",
                "## Measurement Readiness",
                "",
                f"- Experiment metrics defined: **{measurement.get('metric_count', 0)}**",
                f"- Guardrail metrics defined: **{measurement.get('guardrail_count', 0)}**",
                f"- Hypotheses with primary metrics: **{measurement.get('hypotheses_with_metrics', 0)}**",
            ]
        )

    lines.extend(
        [
            "",
            "## Known Limitations",
            "",
        ]
    )
    for note in status.get("known_limitations", []):
        lines.append(f"- {note}")

    lines.extend(
        [
            "",
            "## Exit Criteria Assessment",
            "",
            f"- End-to-end artifacts present: `{'PASS' if status['readiness']['artifacts_complete'] else 'FAIL'}`",
            f"- Meaningful enriched sample (>=100): `{'PASS' if status['readiness']['has_enriched_sample'] else 'FAIL'}`",
            f"- Insights available: `{'PASS' if status['readiness']['has_insights'] else 'FAIL'}`",
            f"- Hypotheses available: `{'PASS' if status['readiness']['has_hypotheses'] else 'FAIL'}`",
            f"- Bias documented: `{'PASS' if status['readiness']['bias_documented'] else 'FAIL'}`",
            f"- Manual theme alignment: `{'PASS' if alignment['aligned_top5_count'] >= 3 else 'WARN'}`",
            "",
            "## Recommendation",
            "",
        ]
    )
    if status["pilot_ready"]:
        lines.append(
            "The pilot package is ready for growth / product / research review. "
            "Use the handoff package for experiment planning, and treat conclusions as directional until enrichment coverage grows."
        )
    else:
        lines.append(
            "The pilot is not yet ready. Fix missing artifacts or enlarge the enriched sample before stakeholder publish."
        )
    lines.append("")

    PHASE_5_DATA.mkdir(parents=True, exist_ok=True)
    with PILOT_REPORT_PATH.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return PILOT_REPORT_PATH
