"""Phase 2 validation: cohort, enrichment store, and exit criteria."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from instamart_analyser.common.config import PHASE_2_DATA, SCHEMAS_DIR
from instamart_analyser.phases.phase_2.cohort import COHORT_PATH, load_cohort
from instamart_analyser.phases.phase_2.storage import EnrichedStore, UsageTracker


def run_validation() -> dict[str, Any]:
    cohort_exists = COHORT_PATH.exists()
    cohort_size = 0
    if cohort_exists:
        cohort = load_cohort()
        cohort_size = cohort.get("cohort_size", 0)

    store = EnrichedStore()
    enriched_count = store.count_enriched()
    error_count = store.count_errors()
    latest_run = store.get_latest_run()
    usage = UsageTracker().get_daily_usage()

    schema_path = SCHEMAS_DIR / "enriched-feedback.schema.json"
    schema_stable = schema_path.exists()

    samples = store.get_all_enriched()[:5]
    samples_have_prompt = all(s.get("prompt_version") for s in samples)
    samples_have_model = all(s.get("enrichment_model") for s in samples)

    exit_criteria = {
        "cohort_built": cohort_exists and cohort_size > 0,
        "enriched_schema_available": schema_stable,
        "enrichment_store_ready": store.db_path.exists(),
        "has_enriched_records": enriched_count > 0,
        "prompt_and_model_tracked": samples_have_prompt and samples_have_model if samples else True,
        "usage_tracking_ready": usage is not None,
    }

    return {
        "cohort_size": cohort_size,
        "enriched_count": enriched_count,
        "error_count": error_count,
        "latest_run": latest_run,
        "usage_today": usage,
        "exit_criteria": exit_criteria,
        "phase_2_passed": all(exit_criteria.values()),
    }


def main() -> int:
    report = run_validation()
    print("=" * 60)
    print("Phase 2 Validation Report")
    print("=" * 60)
    print(json.dumps(report, indent=2))
    print()
    print("Exit criteria:")
    for criterion, passed in report["exit_criteria"].items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {criterion}")

    if report["phase_2_passed"]:
        print("\nPhase 2: PASSED - ready for Phase 3")
        return 0

    print("\nPhase 2: INCOMPLETE - run build-cohort and enrich first")
    return 1


if __name__ == "__main__":
    sys.exit(main())
