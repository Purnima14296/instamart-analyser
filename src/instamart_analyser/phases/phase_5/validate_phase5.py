"""Validation checks for Phase 5 outputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from instamart_analyser.common.config import PHASE_5_DATA


REQUIRED_FILES = [
    "pilot-status.json",
    "pilot-report.md",
    "manual-alignment.json",
    "stakeholder-feedback-template.json",
    "stakeholder-feedback-summary.md",
    "stakeholder-feedback-summary.json",
    "refinements-log.json",
    "measurement-framework.json",
    "growth-handoff-package.md",
    "phase-5-summary.json",
]


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    errors: list[str] = []

    for name in REQUIRED_FILES:
        if not (PHASE_5_DATA / name).exists():
            errors.append(f"Missing required output: {name}")

    if errors:
        print(json.dumps({"status": "failed", "errors": errors}, indent=2))
        return 1

    status = _load_json(PHASE_5_DATA / "pilot-status.json")
    alignment = _load_json(PHASE_5_DATA / "manual-alignment.json")
    feedback = _load_json(PHASE_5_DATA / "stakeholder-feedback-summary.json")
    refinements = _load_json(PHASE_5_DATA / "refinements-log.json")
    measurement = _load_json(PHASE_5_DATA / "measurement-framework.json")
    summary = _load_json(PHASE_5_DATA / "phase-5-summary.json")
    handoff = (PHASE_5_DATA / "growth-handoff-package.md").read_text(encoding="utf-8")
    report = (PHASE_5_DATA / "pilot-report.md").read_text(encoding="utf-8")

    if not status.get("artifact_checks"):
        errors.append("pilot-status.json missing artifact_checks.")
    if not status.get("known_limitations"):
        errors.append("pilot-status.json missing known_limitations.")
    if alignment.get("aligned_top5_count", 0) < 1:
        errors.append("manual alignment found no overlapping themes.")
    if feedback.get("response_count", 0) < 1:
        errors.append("No stakeholder feedback responses recorded.")
    if not refinements.get("prompt_refinements"):
        errors.append("refinements-log.json missing prompt_refinements.")
    if not refinements.get("taxonomy_refinements"):
        errors.append("refinements-log.json missing taxonomy_refinements.")
    if not refinements.get("threshold_refinements"):
        errors.append("refinements-log.json missing threshold_refinements.")
    if measurement.get("metric_count", 0) < 1:
        errors.append("measurement-framework.json has no core metrics.")
    if measurement.get("hypotheses_with_metrics", 0) < 1:
        errors.append("No hypotheses mapped to metrics.")
    if "does not authorize product changes" not in handoff.lower() and "does not claim" not in handoff.lower():
        if "Non-Claims" not in handoff:
            errors.append("Handoff package should document non-claims / human review.")
    if "Known Limitations" not in report:
        errors.append("Pilot report missing Known Limitations section.")
    if summary.get("pilot_ready") is None:
        errors.append("phase-5-summary.json missing pilot_ready.")

    result = {
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "pilot_ready": status.get("pilot_ready"),
        "aligned_top5_count": alignment.get("aligned_top5_count"),
        "feedback_responses": feedback.get("response_count"),
        "metric_count": measurement.get("metric_count"),
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
