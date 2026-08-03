"""Validation checks for Phase 4 outputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from instamart_analyser.common.config import PHASE_4_DATA


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    errors: list[str] = []
    opportunity_path = PHASE_4_DATA / "opportunity-map.json"
    hypothesis_path = PHASE_4_DATA / "hypothesis-backlog.json"
    summary_path = PHASE_4_DATA / "phase-4-summary.json"
    memo_path = PHASE_4_DATA / "experiment-framing-memo.md"

    for path in [opportunity_path, hypothesis_path, summary_path]:
        if not path.exists():
            errors.append(f"Missing required output: {path.name}")

    if not memo_path.exists():
        errors.append("Missing required output: experiment-framing-memo.md")

    if errors:
        print(json.dumps({"status": "failed", "errors": errors}, indent=2))
        return 1

    opportunities = _load_json(opportunity_path).get("opportunities", [])
    hypotheses = _load_json(hypothesis_path).get("hypotheses", [])
    summary = _load_json(summary_path)

    if not opportunities:
        errors.append("No opportunities were generated.")
    if not hypotheses:
        errors.append("No hypotheses were generated.")

    for idx, opportunity in enumerate(opportunities, start=1):
        if not opportunity.get("linked_insight_ids"):
            errors.append(f"Opportunity {idx} is missing linked_insight_ids.")
        if not opportunity.get("linked_theme_ids"):
            errors.append(f"Opportunity {idx} is missing linked_theme_ids.")
        if not opportunity.get("evidence_examples"):
            errors.append(f"Opportunity {idx} is missing evidence_examples.")
        if "causality" in " ".join(opportunity.get("assumptions_and_unknowns", [])).lower():
            pass
        if opportunity.get("priority", {}).get("priority_band") not in {"high", "medium", "low"}:
            errors.append(f"Opportunity {idx} has an invalid priority band.")

    for idx, hypothesis in enumerate(hypotheses, start=1):
        if not hypothesis.get("traceability", {}).get("opportunity_id"):
            errors.append(f"Hypothesis {idx} is missing opportunity traceability.")
        if not hypothesis.get("traceability", {}).get("insight_ids"):
            errors.append(f"Hypothesis {idx} is missing insight traceability.")
        if not hypothesis.get("primary_metric"):
            errors.append(f"Hypothesis {idx} is missing a primary_metric.")

    if summary.get("opportunity_count") != len(opportunities):
        errors.append("Opportunity count in summary does not match output.")
    if summary.get("hypothesis_count") != len(hypotheses):
        errors.append("Hypothesis count in summary does not match output.")

    memo_text = memo_path.read_text(encoding="utf-8")
    if "does not claim causality" not in memo_text.lower():
        errors.append("Memo should explicitly state that recommendations do not claim causality.")

    result = {"status": "passed" if not errors else "failed", "errors": errors}
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
