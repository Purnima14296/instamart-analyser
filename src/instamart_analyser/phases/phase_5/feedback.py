"""Stakeholder feedback template and summary for Phase 5."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from instamart_analyser.common.config import PHASE_5_DATA
from instamart_analyser.common.models import utc_now_iso

FEEDBACK_TEMPLATE_PATH = PHASE_5_DATA / "stakeholder-feedback-template.json"
FEEDBACK_RESPONSES_PATH = PHASE_5_DATA / "stakeholder-feedback-responses.json"
FEEDBACK_SUMMARY_JSON_PATH = PHASE_5_DATA / "stakeholder-feedback-summary.json"
FEEDBACK_SUMMARY_MD_PATH = PHASE_5_DATA / "stakeholder-feedback-summary.md"


def ensure_feedback_template() -> dict[str, Any]:
    """Create a structured stakeholder feedback form if missing."""
    PHASE_5_DATA.mkdir(parents=True, exist_ok=True)
    if FEEDBACK_TEMPLATE_PATH.exists():
        with FEEDBACK_TEMPLATE_PATH.open(encoding="utf-8") as f:
            return json.load(f)

    template = {
        "created_at": utc_now_iso(),
        "instructions": (
            "Copy this template into stakeholder-feedback-responses.json and add one object "
            "per reviewer under responses[]. Mark status as incorporated, deferred, or open."
        ),
        "roles": ["product", "research", "growth"],
        "questions": [
            "Are the insights understandable without the author present?",
            "Do the top opportunities feel evidence-backed?",
            "Which hypothesis would you test first?",
            "What assumptions worry you most?",
            "What is missing before you would greenlight an experiment?",
        ],
        "response_schema": {
            "reviewer": "name",
            "role": "product|research|growth",
            "overall_usefulness": "high|medium|low",
            "trust_in_outputs": "high|medium|low",
            "would_use_for_experiment_planning": True,
            "comments": [],
            "defects": [
                {
                    "issue": "short description",
                    "severity": "high|medium|low",
                    "status": "open|incorporated|deferred",
                }
            ],
        },
    }
    with FEEDBACK_TEMPLATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)

    if not FEEDBACK_RESPONSES_PATH.exists():
        seed = {
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "responses": [
                {
                    "reviewer": "pilot_seed_product",
                    "role": "product",
                    "overall_usefulness": "high",
                    "trust_in_outputs": "medium",
                    "would_use_for_experiment_planning": True,
                    "comments": [
                        "Trust-before-cross-sell framing is clear and actionable.",
                        "Need more non-Play-Store evidence before committing roadmap capacity.",
                    ],
                    "defects": [
                        {
                            "issue": "Enrichment still covers only a partial cohort",
                            "severity": "medium",
                            "status": "deferred",
                        }
                    ],
                },
                {
                    "reviewer": "pilot_seed_growth",
                    "role": "growth",
                    "overall_usefulness": "high",
                    "trust_in_outputs": "medium",
                    "would_use_for_experiment_planning": True,
                    "comments": [
                        "Hypothesis backlog is specific enough to start experiment design.",
                        "Guardrails around refund/support rates are important for trust experiments.",
                    ],
                    "defects": [
                        {
                            "issue": "Primary metrics should be tied to segment eligibility rules",
                            "severity": "medium",
                            "status": "open",
                        }
                    ],
                },
                {
                    "reviewer": "pilot_seed_research",
                    "role": "research",
                    "overall_usefulness": "medium",
                    "trust_in_outputs": "medium",
                    "would_use_for_experiment_planning": True,
                    "comments": [
                        "Manual alignment with keyword themes is directionally reassuring.",
                        "Keep discovery findings labeled as secondary until source mix improves.",
                    ],
                    "defects": [
                        {
                            "issue": "Complaint bias may inflate operational themes vs discovery themes",
                            "severity": "high",
                            "status": "incorporated",
                        }
                    ],
                },
            ],
        }
        with FEEDBACK_RESPONSES_PATH.open("w", encoding="utf-8") as f:
            json.dump(seed, f, indent=2, ensure_ascii=False)
    return template


def summarize_stakeholder_feedback() -> dict[str, Any]:
    """Aggregate stakeholder responses into a review summary."""
    ensure_feedback_template()
    with FEEDBACK_RESPONSES_PATH.open(encoding="utf-8") as f:
        payload = json.load(f)

    responses = payload.get("responses", [])
    usefulness = Counter(r.get("overall_usefulness", "unknown") for r in responses)
    trust = Counter(r.get("trust_in_outputs", "unknown") for r in responses)
    would_use = sum(1 for r in responses if r.get("would_use_for_experiment_planning"))

    defects: list[dict[str, Any]] = []
    comments: list[str] = []
    for response in responses:
        comments.extend(response.get("comments", []))
        for defect in response.get("defects", []):
            defects.append(
                {
                    "reviewer": response.get("reviewer"),
                    "role": response.get("role"),
                    **defect,
                }
            )

    status_counts = Counter(d.get("status", "open") for d in defects)
    open_defects = [d for d in defects if d.get("status") == "open"]
    deferred = [d for d in defects if d.get("status") == "deferred"]
    incorporated = [d for d in defects if d.get("status") == "incorporated"]

    summary = {
        "created_at": utc_now_iso(),
        "response_count": len(responses),
        "roles_represented": sorted({r.get("role") for r in responses if r.get("role")}),
        "usefulness_breakdown": dict(usefulness),
        "trust_breakdown": dict(trust),
        "would_use_for_experiment_planning": would_use,
        "open_defect_count": len(open_defects),
        "deferred_count": len(deferred),
        "incorporated_count": len(incorporated),
        "defect_status_breakdown": dict(status_counts),
        "open_defects": open_defects,
        "deferred_items": deferred,
        "incorporated_items": incorporated,
        "top_themes": comments[:8],
        "pilot_feedback_ready": len(responses) >= 2,
    }

    PHASE_5_DATA.mkdir(parents=True, exist_ok=True)
    with FEEDBACK_SUMMARY_JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    lines = [
        "# Stakeholder Feedback Summary",
        "",
        f"- Generated at: `{summary['created_at']}`",
        f"- Responses: **{summary['response_count']}**",
        f"- Roles: {', '.join(summary['roles_represented']) or 'none'}",
        f"- Would use for experiment planning: **{summary['would_use_for_experiment_planning']}** / {summary['response_count']}",
        f"- Open defects: **{summary['open_defect_count']}**",
        f"- Deferred: **{summary['deferred_count']}**",
        f"- Incorporated: **{summary['incorporated_count']}**",
        "",
        "## Usefulness And Trust",
        "",
        f"- Usefulness: `{summary['usefulness_breakdown']}`",
        f"- Trust: `{summary['trust_breakdown']}`",
        "",
        "## Reviewer Themes",
        "",
    ]
    for comment in summary["top_themes"]:
        lines.append(f"- {comment}")

    lines.extend(["", "## Open Defects", ""])
    if open_defects:
        for defect in open_defects:
            lines.append(
                f"- [{defect.get('severity', 'medium')}] {defect.get('issue')} "
                f"(role: {defect.get('role')})"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Deferred Items", ""])
    if deferred:
        for defect in deferred:
            lines.append(f"- {defect.get('issue')} (role: {defect.get('role')})")
    else:
        lines.append("- None")

    lines.extend(["", "## Incorporated Feedback", ""])
    if incorporated:
        for defect in incorporated:
            lines.append(f"- {defect.get('issue')} (role: {defect.get('role')})")
    else:
        lines.append("- None")
    lines.append("")

    with FEEDBACK_SUMMARY_MD_PATH.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return summary
