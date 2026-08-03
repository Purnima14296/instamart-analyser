"""Growth handoff package and measurement framework for Phase 5."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from instamart_analyser.common.config import PHASE_3_DATA, PHASE_4_DATA, PHASE_5_DATA
from instamart_analyser.common.models import utc_now_iso

MEASUREMENT_PATH = PHASE_5_DATA / "measurement-framework.json"
HANDOFF_PATH = PHASE_5_DATA / "growth-handoff-package.md"
SUMMARY_PATH = PHASE_5_DATA / "phase-5-summary.json"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def build_measurement_framework() -> dict[str, Any]:
    """Define experiment metrics needed for downstream product experiments."""
    hypotheses = _load_json(PHASE_4_DATA / "hypothesis-backlog.json").get("hypotheses", [])
    opportunities = _load_json(PHASE_4_DATA / "opportunity-map.json").get("opportunities", [])

    core_metrics = [
        {
            "metric_id": "m_new_category_add",
            "name": "new-category add-to-order rate",
            "definition": "Share of eligible sessions/orders that add an item from a category not purchased in the prior 30–90 days.",
            "owner": "growth",
            "applies_to": ["trust", "discovery", "pricing", "assortment"],
        },
        {
            "metric_id": "m_new_category_trial",
            "name": "adjacent-category trial conversion",
            "definition": "Share of users exposed to a category-expansion intervention who purchase from the promoted adjacent category.",
            "owner": "growth",
            "applies_to": ["pricing", "discovery", "assortment"],
        },
        {
            "metric_id": "m_browse_depth",
            "name": "new-category browse depth",
            "definition": "Average number of distinct non-staple categories opened per session among exposed users.",
            "owner": "product",
            "applies_to": ["discovery"],
        },
        {
            "metric_id": "m_repeat_expansion",
            "name": "30-day category expansion retention",
            "definition": "Share of first-time category triers who purchase from that category again within 30 days.",
            "owner": "growth",
            "applies_to": ["trust", "pricing", "assortment"],
        },
    ]
    guardrails = [
        {
            "metric_id": "g_order_conversion",
            "name": "overall order conversion",
            "definition": "Orders / sessions for exposed cohort vs control.",
        },
        {
            "metric_id": "g_support_contacts",
            "name": "customer support contacts per order",
            "definition": "Support tickets or in-app help starts per completed order.",
        },
        {
            "metric_id": "g_refund_cancel",
            "name": "refund or cancellation rate",
            "definition": "Share of orders with refund, replacement, or cancellation.",
        },
        {
            "metric_id": "g_nudge_dismiss",
            "name": "expansion-prompt dismiss rate",
            "definition": "Share of users who dismiss or ignore category-expansion prompts.",
        },
    ]

    hypothesis_metrics = []
    for hyp in hypotheses:
        hypothesis_metrics.append(
            {
                "hypothesis_id": hyp.get("hypothesis_id"),
                "linked_opportunity_id": hyp.get("linked_opportunity_id"),
                "primary_metric": hyp.get("primary_metric"),
                "guardrail_metrics": hyp.get("guardrail_metrics", []),
                "eligibility_suggestion": (
                    "Exclude users with unresolved refund/support issues in the last 14 days "
                    "when testing category-expansion prompts."
                    if "trust" in str(hyp.get("hypothesis", "")).lower()
                    or "guarantee" in str(hyp.get("proposed_intervention", "")).lower()
                    else "Define mission and segment eligibility from Phase 4 opportunity fields."
                ),
            }
        )

    payload = {
        "created_at": utc_now_iso(),
        "north_star": "Increase monthly new-category adoption among existing Instamart shoppers without harming core replenishment trust.",
        "metric_count": len(core_metrics),
        "guardrail_count": len(guardrails),
        "hypotheses_with_metrics": sum(1 for h in hypothesis_metrics if h.get("primary_metric")),
        "core_metrics": core_metrics,
        "guardrail_metrics": guardrails,
        "hypothesis_metric_map": hypothesis_metrics,
        "opportunity_count_represented": len(opportunities),
        "measurement_notes": [
            "Do not claim causality from observational feedback alone.",
            "Prefer holdout or A/B tests for all priority hypotheses.",
            "Segment results by family_household and habitual_replenisher first.",
            "Report Play Store complaint bias as a research caveat in every pilot readout.",
        ],
    }

    PHASE_5_DATA.mkdir(parents=True, exist_ok=True)
    with MEASUREMENT_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return payload


def write_growth_handoff(
    *,
    status: dict[str, Any],
    alignment: dict[str, Any],
    feedback: dict[str, Any],
    refinements: dict[str, Any],
    measurement: dict[str, Any],
) -> Path:
    """Create the growth experimentation handoff package."""
    phase4 = _load_json(PHASE_4_DATA / "phase-4-summary.json")
    opportunities = _load_json(PHASE_4_DATA / "opportunity-map.json").get("opportunities", [])
    hypotheses = _load_json(PHASE_4_DATA / "hypothesis-backlog.json").get("hypotheses", [])
    insights = _load_json(PHASE_3_DATA / "insights.json").get("insights", [])

    lines = [
        "# Growth Experimentation Handoff Package",
        "",
        f"- Generated at: `{utc_now_iso()}`",
        f"- Pilot ready: **{'yes' if status.get('pilot_ready') else 'no'}**",
        f"- Enriched reviews in pilot: **{status['pilot_scope']['enriched_count']}**",
        f"- Opportunities: **{phase4.get('opportunity_count', 0)}**",
        f"- Hypotheses: **{phase4.get('hypothesis_count', 0)}**",
        "",
        "## What This Package Is For",
        "",
        "Use this package to move from evidence-backed insights to experiment design.",
        "It separates evidence, interpretation, and recommendation. It does not authorize product changes without human review.",
        "",
        "## Recommended First Bets",
        "",
    ]
    for opportunity in opportunities[:3]:
        lines.extend(
            [
                f"### {opportunity.get('rank')}. {opportunity.get('title')}",
                f"- Priority: `{opportunity.get('priority', {}).get('priority_band')}`",
                f"- Segment: `{opportunity.get('affected_segment')}`",
                f"- User problem: {opportunity.get('user_problem')}",
                f"- First move: {opportunity.get('recommended_moves', ['n/a'])[0]}",
                f"- Linked insights: {', '.join(opportunity.get('linked_insight_ids', []))}",
                "",
            ]
        )

    lines.extend(["## Hypothesis Backlog (Top 5)", ""])
    for hyp in hypotheses[:5]:
        lines.extend(
            [
                f"### {hyp.get('hypothesis_id')}",
                f"- {hyp.get('hypothesis')}",
                f"- Primary metric: {hyp.get('primary_metric')}",
                f"- Guardrails: {', '.join(hyp.get('guardrail_metrics', []))}",
                "",
            ]
        )

    lines.extend(
        [
            "## Measurement Framework",
            "",
            f"- North star: {measurement.get('north_star')}",
            f"- Core metrics: **{measurement.get('metric_count')}**",
            f"- Guardrails: **{measurement.get('guardrail_count')}**",
            "",
        ]
    )
    for metric in measurement.get("core_metrics", []):
        lines.append(f"- `{metric['metric_id']}` **{metric['name']}**: {metric['definition']}")

    lines.extend(
        [
            "",
            "## Evidence Traceability",
            "",
            f"- Insights available: {len(insights)}",
            f"- Manual alignment verdict: {alignment.get('alignment_verdict')}",
            "- Key source files:",
            "  - `data/phase-3/insights.json`",
            "  - `data/phase-3/stakeholder-summary.md`",
            "  - `data/phase-4/opportunity-map.json`",
            "  - `data/phase-4/hypothesis-backlog.json`",
            "  - `data/phase-4/experiment-framing-memo.md`",
            "",
            "## Stakeholder Review Status",
            "",
            f"- Feedback responses: {feedback.get('response_count', 0)}",
            f"- Open defects: {feedback.get('open_defect_count', 0)}",
            f"- Deferred items: {feedback.get('deferred_count', 0)}",
            f"- Incorporated items: {feedback.get('incorporated_count', 0)}",
            "",
            "## Refinements Already Applied",
            "",
            f"- Prompt: {len(refinements.get('prompt_refinements', []))}",
            f"- Taxonomy: {len(refinements.get('taxonomy_refinements', []))}",
            f"- Thresholds: {len(refinements.get('threshold_refinements', []))}",
            "",
            "## Explicit Non-Claims",
            "",
            "- Feedback themes are not causal proof.",
            "- Public reviews are complaint-biased.",
            "- Partial enrichment means rankings may shift as more reviews are labeled.",
            "",
            "## Suggested Next Actions",
            "",
            "1. Review top 3 opportunities with product + growth.",
            "2. Choose one trust and one discovery hypothesis for experiment design.",
            "3. Define eligibility rules and success thresholds using the measurement framework.",
            "4. Continue Phase 2 enrichment when Groq quota resets to strengthen evidence.",
            "",
        ]
    )

    PHASE_5_DATA.mkdir(parents=True, exist_ok=True)
    with HANDOFF_PATH.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return HANDOFF_PATH


def write_phase5_summary(
    *,
    status: dict[str, Any],
    alignment: dict[str, Any],
    feedback: dict[str, Any],
    refinements: dict[str, Any],
    measurement: dict[str, Any],
) -> dict[str, Any]:
    summary = {
        "created_at": utc_now_iso(),
        "pilot_ready": status.get("pilot_ready"),
        "enriched_count": status.get("pilot_scope", {}).get("enriched_count"),
        "alignment_verdict": alignment.get("alignment_verdict"),
        "aligned_top5_count": alignment.get("aligned_top5_count"),
        "feedback_responses": feedback.get("response_count"),
        "open_defects": feedback.get("open_defect_count"),
        "prompt_refinements": len(refinements.get("prompt_refinements", [])),
        "taxonomy_refinements": len(refinements.get("taxonomy_refinements", [])),
        "threshold_refinements": len(refinements.get("threshold_refinements", [])),
        "metric_count": measurement.get("metric_count"),
        "hypothesis_metrics_mapped": measurement.get("hypotheses_with_metrics"),
        "deliverables": {
            "pilot_report": str(PHASE_5_DATA / "pilot-report.md"),
            "stakeholder_feedback_summary": str(PHASE_5_DATA / "stakeholder-feedback-summary.md"),
            "refinements_log": str(PHASE_5_DATA / "refinements-log.json"),
            "measurement_framework": str(PHASE_5_DATA / "measurement-framework.json"),
            "growth_handoff_package": str(PHASE_5_DATA / "growth-handoff-package.md"),
        },
    }
    with SUMMARY_PATH.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return summary
