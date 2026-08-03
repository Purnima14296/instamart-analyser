"""Phase 5 pipeline: pilot, review, and measurement readiness."""

from __future__ import annotations

import argparse
import json
import sys

from instamart_analyser.common.config import PHASE_5_DATA
from instamart_analyser.phases.phase_5.feedback import ensure_feedback_template, summarize_stakeholder_feedback
from instamart_analyser.phases.phase_5.handoff import (
    build_measurement_framework,
    write_growth_handoff,
    write_phase5_summary,
)
from instamart_analyser.phases.phase_5.pilot import collect_pilot_status, compare_manual_alignment, write_pilot_report
from instamart_analyser.phases.phase_5.refinements import build_refinements_log


def _run_pilot() -> dict:
    status = collect_pilot_status()
    alignment = compare_manual_alignment()
    ensure_feedback_template()
    feedback = summarize_stakeholder_feedback()
    refinements = build_refinements_log()
    measurement = build_measurement_framework()
    report_path = write_pilot_report(status, alignment, feedback, refinements, measurement)
    handoff_path = write_growth_handoff(
        status=status,
        alignment=alignment,
        feedback=feedback,
        refinements=refinements,
        measurement=measurement,
    )
    summary = write_phase5_summary(
        status=status,
        alignment=alignment,
        feedback=feedback,
        refinements=refinements,
        measurement=measurement,
    )
    return {
        "pilot_ready": status["pilot_ready"],
        "enriched_count": status["pilot_scope"]["enriched_count"],
        "aligned_top5_count": alignment["aligned_top5_count"],
        "feedback_responses": feedback["response_count"],
        "open_defects": feedback["open_defect_count"],
        "metric_count": measurement["metric_count"],
        "pilot_report": str(report_path),
        "handoff_package": str(handoff_path),
        "summary_path": str(PHASE_5_DATA / "phase-5-summary.json"),
        "summary": summary,
    }


def cmd_run(_args: argparse.Namespace) -> int:
    result = _run_pilot()
    print(json.dumps({k: v for k, v in result.items() if k != "summary"}, indent=2))
    return 0 if result["pilot_ready"] else 1


def cmd_status(_args: argparse.Namespace) -> int:
    status = {
        "pilot_status_exists": (PHASE_5_DATA / "pilot-status.json").exists(),
        "pilot_report_exists": (PHASE_5_DATA / "pilot-report.md").exists(),
        "manual_alignment_exists": (PHASE_5_DATA / "manual-alignment.json").exists(),
        "feedback_summary_exists": (PHASE_5_DATA / "stakeholder-feedback-summary.md").exists(),
        "refinements_log_exists": (PHASE_5_DATA / "refinements-log.json").exists(),
        "measurement_framework_exists": (PHASE_5_DATA / "measurement-framework.json").exists(),
        "handoff_package_exists": (PHASE_5_DATA / "growth-handoff-package.md").exists(),
        "phase5_summary_exists": (PHASE_5_DATA / "phase-5-summary.json").exists(),
    }
    print(json.dumps(status, indent=2))
    return 0


def cmd_feedback(_args: argparse.Namespace) -> int:
    ensure_feedback_template()
    summary = summarize_stakeholder_feedback()
    print(
        json.dumps(
            {
                "response_count": summary["response_count"],
                "open_defects": summary["open_defect_count"],
                "summary_path": str(PHASE_5_DATA / "stakeholder-feedback-summary.md"),
            },
            indent=2,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 5: Pilot, Review, And Measurement Readiness")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Build the full Phase 5 pilot package")
    p_run.set_defaults(func=cmd_run)

    p_pilot = sub.add_parser("pilot", help="Alias for run")
    p_pilot.set_defaults(func=cmd_run)

    p_feedback = sub.add_parser("feedback", help="Refresh stakeholder feedback summary")
    p_feedback.set_defaults(func=cmd_feedback)

    p_status = sub.add_parser("status", help="Show Phase 5 output status")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
