"""Validation for Phase 3 theme and insight outputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from instamart_analyser.common.config import PHASE_3_DATA, SCHEMAS_DIR


def run_validation() -> dict[str, Any]:
    summary_path = PHASE_3_DATA / "theme-summary.json"
    clusters_path = PHASE_3_DATA / "theme-clusters.json"
    insights_path = PHASE_3_DATA / "insights.json"
    report_path = PHASE_3_DATA / "insight-report.md"
    discovery_barriers_path = PHASE_3_DATA / "discovery-barriers.json"
    shopping_behaviour_path = PHASE_3_DATA / "shopping-behaviour.json"
    category_opportunities_path = PHASE_3_DATA / "category-opportunities.json"
    segment_analysis_path = PHASE_3_DATA / "segment-analysis.json"

    summary_exists = summary_path.exists()
    clusters_exists = clusters_path.exists()
    insights_exists = insights_path.exists()
    report_exists = report_path.exists()
    discovery_barriers_exists = discovery_barriers_path.exists()
    shopping_behaviour_exists = shopping_behaviour_path.exists()
    category_opportunities_exists = category_opportunities_path.exists()
    segment_analysis_exists = segment_analysis_path.exists()

    cluster_count = 0
    insight_count = 0
    insight_errors: list[str] = []
    low_volume_uncertain = True
    bias_reported = False

    if clusters_exists:
        with clusters_path.open(encoding="utf-8") as f:
            clusters = json.load(f)
        cluster_count = len(clusters.get("clusters", []))
        for cluster in clusters.get("clusters", []):
            total = cluster.get("total_supporting_records", 0)
            confidence = cluster.get("confidence")
            if total < 5 and confidence not in {"low", "medium"}:
                low_volume_uncertain = False

    if insights_exists:
        with insights_path.open(encoding="utf-8") as f:
            insights_payload = json.load(f)
        insight_count = len(insights_payload.get("insights", []))
        with (SCHEMAS_DIR / "insight.schema.json").open(encoding="utf-8") as f:
            schema = json.load(f)
        validator = Draft202012Validator(schema)
        for insight in insights_payload.get("insights", [])[:10]:
            for error in validator.iter_errors(insight):
                insight_errors.append(error.message)
            if not insight.get("supporting_evidence"):
                insight_errors.append("Missing supporting evidence")
            if not insight.get("confidence"):
                insight_errors.append("Missing confidence")

    if summary_exists:
        with summary_path.open(encoding="utf-8") as f:
            summary = json.load(f)
        bias_notes = summary.get("bias_notes", [])
        bias_reported = any("Play Store" in note or "play store" in note.lower() for note in bias_notes)

    exit_criteria = {
        "theme_summary_exists": summary_exists,
        "theme_clusters_exist": clusters_exists,
        "has_clusters": cluster_count > 0,
        "insights_exist": insights_exists,
        "has_insights": insight_count > 0,
        "insights_match_schema": len(insight_errors) == 0,
        "discovery_barriers_report_exists": discovery_barriers_exists,
        "shopping_behaviour_report_exists": shopping_behaviour_exists,
        "category_opportunities_report_exists": category_opportunities_exists,
        "segment_analysis_report_exists": segment_analysis_exists,
        "low_volume_themes_marked_uncertain": low_volume_uncertain,
        "play_store_bias_reported": bias_reported,
        "report_exists": report_exists,
    }

    return {
        "cluster_count": cluster_count,
        "insight_count": insight_count,
        "insight_schema_errors": insight_errors[:5],
        "exit_criteria": exit_criteria,
        "phase_3_passed": all(exit_criteria.values()),
    }


def main() -> int:
    report = run_validation()
    print("=" * 60)
    print("Phase 3 Validation Report")
    print("=" * 60)
    print(json.dumps(report, indent=2))
    print()
    print("Exit criteria:")
    for criterion, passed in report["exit_criteria"].items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {criterion}")

    if report["phase_3_passed"]:
        print("\nPhase 3: PASSED - ready for Phase 4")
        return 0

    print("\nPhase 3: INCOMPLETE - run pipeline aggregate/draft-insights first")
    return 1


if __name__ == "__main__":
    sys.exit(main())
