"""Generate insight drafts from aggregated theme clusters."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from groq import Groq
from jsonschema import Draft202012Validator

from instamart_analyser.common.config import GROQ_API_KEY, GROQ_MODEL, PHASE_3_DATA, SCHEMAS_DIR
from instamart_analyser.common.models import utc_now_iso
from instamart_analyser.taxonomy import load_taxonomy

INSIGHTS_PATH = PHASE_3_DATA / "insights.json"
REPORT_PATH = PHASE_3_DATA / "insight-report.md"


def load_insight_schema() -> dict[str, Any]:
    with (SCHEMAS_DIR / "insight.schema.json").open(encoding="utf-8") as f:
        return json.load(f)


def select_clusters_for_insights(clusters: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Balance insight drafting across analysis buckets."""
    bucket_order = [
        "discovery_barriers",
        "shopping_behaviour_patterns",
        "category_expansion_opportunities",
        "operational_pain_points",
    ]
    grouped: dict[str, list[dict[str, Any]]] = {bucket: [] for bucket in bucket_order}
    for cluster in clusters:
        grouped.setdefault(cluster.get("analysis_bucket", "operational_pain_points"), []).append(cluster)

    selected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    while len(selected) < limit:
        progressed = False
        for bucket in bucket_order:
            bucket_clusters = grouped.get(bucket, [])
            while bucket_clusters and bucket_clusters[0]["theme_id"] in seen_ids:
                bucket_clusters.pop(0)
            if not bucket_clusters:
                continue
            cluster = bucket_clusters.pop(0)
            selected.append(cluster)
            seen_ids.add(cluster["theme_id"])
            progressed = True
            if len(selected) >= limit:
                break
        if not progressed:
            break
    return selected


def question_ids_for_cluster(cluster: dict[str, Any]) -> list[str]:
    barrier = cluster["primary_barrier"]
    mapping = {
        "habit_lock_in": ["Q1", "Q4", "Q9"],
        "poor_discovery": ["Q2", "Q3", "Q9"],
        "low_awareness": ["Q2", "Q3"],
        "trust_quality": ["Q4", "Q10"],
        "price_sensitivity": ["Q10"],
        "assortment_gap": ["Q10", "Q12"],
        "information_gap": ["Q5", "Q10"],
        "mission_narrowness": ["Q1", "Q12"],
        "past_bad_experience": ["Q4", "Q6"],
        "delivery_fee_threshold": ["Q10"],
        "other": ["Q11"],
    }
    return mapping.get(barrier, ["Q11"])


def confidence_from_cluster(cluster: dict[str, Any]) -> str:
    total = cluster["total_supporting_records"]
    source_diversity = len(cluster["source_breakdown"])
    if total >= 10 and source_diversity >= 2:
        return "high"
    if total >= 5:
        return "medium"
    return "low"


def quality_score(cluster: dict[str, Any], confidence: str) -> dict[str, int]:
    evidence_strength = 5 if cluster["total_supporting_records"] >= 10 else 4 if cluster["total_supporting_records"] >= 5 else 3
    traceability = 5
    relevance = 4 if cluster["primary_barrier"] in {"poor_discovery", "habit_lock_in", "trust_quality", "price_sensitivity"} else 3
    actionability = 4 if cluster["primary_barrier"] != "other" else 3
    clarity = 4 if confidence != "low" else 3
    total = evidence_strength + traceability + relevance + actionability + clarity
    return {
        "evidence_strength": evidence_strength,
        "traceability": traceability,
        "relevance": relevance,
        "actionability": actionability,
        "clarity": clarity,
        "total": total,
    }


def _dry_run_insight(cluster: dict[str, Any], taxonomy_version: str) -> dict[str, Any]:
    barrier = cluster["primary_barrier"].replace("_", " ")
    mission = cluster["shopping_mission"].replace("_", " ")
    category = cluster["primary_category"].replace("_", " ")
    segment = cluster["affected_segment"].replace("_", " ")
    confidence = confidence_from_cluster(cluster)
    total = cluster["total_supporting_records"]
    evidence = cluster["supporting_evidence"][:5]
    statement = (
        f"Users in {mission} missions repeatedly hit {barrier} barriers around {category}, "
        f"which limits broader category exploration."
    )
    implication = (
        f"Instamart should address {barrier} for {segment} users during {mission} journeys "
        f"before expecting stronger cross-category expansion."
    )
    return {
        "insight_id": f"insight_{uuid.uuid4().hex[:8]}",
        "status": "draft",
        "statement": statement,
        "confidence": confidence,
        "analysis_question_ids": question_ids_for_cluster(cluster),
        "theme_ids": [cluster["theme_id"]],
        "primary_barriers": [cluster["primary_barrier"]],
        "primary_triggers": [],
        "supporting_evidence": evidence,
        "source_breakdown": cluster["source_breakdown"],
        "total_supporting_records": total,
        "affected_segment": cluster["affected_segment"],
        "business_implication": implication,
        "open_questions": [
            "Would this pattern hold across a larger and more source-diverse sample?",
            "Which product surface should be changed first to reduce this barrier?",
        ],
        "quality_score": quality_score(cluster, confidence),
        "taxonomy_version": taxonomy_version,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
    }


def _prompt_for_cluster(cluster: dict[str, Any], taxonomy_version: str) -> list[dict[str, str]]:
    prompt = {
        "taxonomy_version": taxonomy_version,
        "theme_id": cluster["theme_id"],
        "primary_barrier": cluster["primary_barrier"],
        "shopping_mission": cluster["shopping_mission"],
        "primary_category": cluster["primary_category"],
        "affected_segment": cluster["affected_segment"],
        "total_supporting_records": cluster["total_supporting_records"],
        "source_breakdown": cluster["source_breakdown"],
        "cooccurring_barriers": cluster["cooccurring_barriers"],
        "supporting_evidence": cluster["supporting_evidence"][:8],
        "analysis_question_ids": question_ids_for_cluster(cluster),
        "analysis_bucket": cluster.get("analysis_bucket"),
        "product_opportunity": cluster.get("product_opportunity"),
    }
    system = (
        "You draft one evidence-backed Instamart category-discovery insight from an aggregated theme cluster. "
        "Return only JSON. Do not invent evidence. Keep the statement to one clear sentence. "
        "Set status=draft. Confidence must be high, medium, or low."
    )
    user = (
        "Create one JSON object matching the insight schema fields: "
        "status, statement, confidence, analysis_question_ids, theme_ids, primary_barriers, "
        "primary_triggers, supporting_evidence, source_breakdown, total_supporting_records, "
        "affected_segment, business_implication, open_questions, quality_score. "
        "Use the provided product_opportunity to keep the output actionable. "
        f"Cluster context: {json.dumps(prompt, ensure_ascii=False)}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _sanitize_insight(insight: dict[str, Any], cluster: dict[str, Any], taxonomy_version: str) -> dict[str, Any]:
    confidence = insight.get("confidence")
    if confidence not in {"high", "medium", "low"}:
        confidence = confidence_from_cluster(cluster)
    if confidence == "high" and cluster["total_supporting_records"] < 10:
        confidence = "medium"
    evidence = insight.get("supporting_evidence") or cluster["supporting_evidence"][:5]
    if not isinstance(evidence, list):
        evidence = cluster["supporting_evidence"][:5]
    clean_evidence = []
    for item in evidence[:8]:
        if not isinstance(item, dict):
            continue
        record_id = item.get("record_id")
        snippet = item.get("snippet")
        if not isinstance(record_id, str) or not isinstance(snippet, str):
            continue
        clean = {"record_id": record_id, "snippet": snippet}
        if isinstance(item.get("source"), str):
            clean["source"] = item["source"]
        clean_evidence.append(clean)
    if not clean_evidence:
        clean_evidence = cluster["supporting_evidence"][:5]

    questions = insight.get("analysis_question_ids")
    if not isinstance(questions, list) or not questions:
        questions = question_ids_for_cluster(cluster)

    return {
        "insight_id": insight.get("insight_id") or f"insight_{uuid.uuid4().hex[:8]}",
        "status": insight.get("status") if insight.get("status") in {"draft", "published", "hypothesis", "rejected"} else "draft",
        "statement": insight.get("statement") or _dry_run_insight(cluster, taxonomy_version)["statement"],
        "confidence": confidence,
        "analysis_question_ids": questions,
        "theme_ids": insight.get("theme_ids") if isinstance(insight.get("theme_ids"), list) else [cluster["theme_id"]],
        "primary_barriers": insight.get("primary_barriers") if isinstance(insight.get("primary_barriers"), list) else [cluster["primary_barrier"]],
        "primary_triggers": insight.get("primary_triggers") if isinstance(insight.get("primary_triggers"), list) else [],
        "supporting_evidence": clean_evidence,
        "source_breakdown": insight.get("source_breakdown") if isinstance(insight.get("source_breakdown"), dict) else cluster["source_breakdown"],
        "total_supporting_records": int(insight.get("total_supporting_records") or cluster["total_supporting_records"]),
        "affected_segment": insight.get("affected_segment") or cluster["affected_segment"],
        "business_implication": insight.get("business_implication") or _dry_run_insight(cluster, taxonomy_version)["business_implication"],
        "open_questions": insight.get("open_questions") if isinstance(insight.get("open_questions"), list) else _dry_run_insight(cluster, taxonomy_version)["open_questions"],
        "quality_score": insight.get("quality_score") if isinstance(insight.get("quality_score"), dict) else quality_score(cluster, confidence),
        "taxonomy_version": taxonomy_version,
        "created_at": insight.get("created_at") or utc_now_iso(),
        "updated_at": utc_now_iso(),
    }


def generate_insights(
    *,
    clusters: list[dict[str, Any]],
    limit: int = 10,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Draft insights from top theme clusters."""
    tax = load_taxonomy()
    schema = load_insight_schema()
    validator = Draft202012Validator(schema)
    selected = select_clusters_for_insights(clusters, limit)

    client = None if dry_run else Groq(api_key=GROQ_API_KEY)
    insights: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for cluster in selected:
        try:
            if dry_run or not GROQ_API_KEY:
                insight = _dry_run_insight(cluster, tax.version)
            else:
                response = client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=_prompt_for_cluster(cluster, tax.version),
                    max_tokens=1024,
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )
                raw = response.choices[0].message.content or "{}"
                parsed = json.loads(raw)
                insight = _sanitize_insight(parsed, cluster, tax.version)

            schema_errors = [e.message for e in validator.iter_errors(insight)]
            if schema_errors:
                raise ValueError("; ".join(schema_errors[:5]))
            insights.append(insight)
        except Exception as exc:
            errors.append({"theme_id": cluster["theme_id"], "error": str(exc)})

    payload = {
        "created_at": utc_now_iso(),
        "dry_run": dry_run or not GROQ_API_KEY,
        "insight_count": len(insights),
        "error_count": len(errors),
        "insights": insights,
        "errors": errors,
    }
    PHASE_3_DATA.mkdir(parents=True, exist_ok=True)
    with INSIGHTS_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return payload


def write_markdown_report(summary: dict[str, Any], insights_payload: dict[str, Any]) -> Path:
    lines = [
        "# Phase 3 Insight Report",
        "",
        f"- Generated at: `{summary['created_at']}`",
        f"- Enriched records analyzed: **{summary['enriched_record_count']}**",
        f"- Theme clusters (>=3 records): **{summary['cluster_count']}**",
        f"- Insight drafts: **{insights_payload['insight_count']}**",
        "",
        "## Top Themes",
        "",
    ]
    for barrier, count in summary["top_barriers"][:5]:
        lines.append(f"- `{barrier}`: {count}")
    lines.extend(["", "## Draft Insights", ""])
    for idx, insight in enumerate(insights_payload["insights"], start=1):
        lines.extend(
            [
                f"### {idx}. {insight['statement']}",
                f"- Confidence: `{insight['confidence']}`",
                f"- Affected segment: `{insight['affected_segment']}`",
                f"- Supporting records: {insight['total_supporting_records']}",
                f"- Business implication: {insight['business_implication']}",
                f"- Product opportunity: {insight['business_implication']}",
                "- Evidence:",
            ]
        )
        for evidence in insight["supporting_evidence"][:3]:
            lines.append(f"  - `{evidence['record_id']}` ({evidence.get('source', 'unknown')}): {evidence['snippet']}")
        if insight.get("open_questions"):
            lines.append("- Open questions:")
            for question in insight["open_questions"]:
                lines.append(f"  - {question}")
        lines.append("")

    with REPORT_PATH.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    return REPORT_PATH
