"""Phase 0 validation: schemas, taxonomy walkthrough, and exit criteria checks."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import Draft202012Validator

from instamart_analyser.taxonomy import PROJECT_ROOT, Taxonomy, load_taxonomy

SCHEMAS_DIR = PROJECT_ROOT / "schemas"
SAMPLES_PATH = PROJECT_ROOT / "data" / "phase-0" / "samples" / "phase-0-feedback-samples.json"


def load_schema(name: str) -> dict[str, Any]:
    with (SCHEMAS_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


def validate_schema_documents() -> list[str]:
    """Validate that schema files are valid JSON Schema."""
    errors: list[str] = []
    for schema_file in SCHEMAS_DIR.glob("*.schema.json"):
        try:
            schema = load_schema(schema_file.name)
            Draft202012Validator.check_schema(schema)
        except jsonschema.SchemaError as e:
            errors.append(f"{schema_file.name}: {e.message}")
    return errors


def validate_sample_classifications(taxonomy: Taxonomy) -> tuple[int, list[str]]:
    """Validate all gold-standard sample labels against taxonomy v1."""
    with SAMPLES_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    errors: list[str] = []
    count = 0
    for sample in data["samples"]:
        count += 1
        sample_errors = taxonomy.validate_enrichment(sample["expected"])
        for err in sample_errors:
            errors.append(f"{sample['id']}: {err}")

    return count, errors


def run_walkthrough_report() -> dict[str, Any]:
    """Generate a Phase 0 walkthrough summary."""
    taxonomy = load_taxonomy()
    schema_errors = validate_schema_documents()
    sample_count, sample_errors = validate_sample_classifications(taxonomy)

    with SAMPLES_PATH.open(encoding="utf-8") as f:
        samples = json.load(f)["samples"]

    barrier_counts: dict[str, int] = {}
    mission_counts: dict[str, int] = {}
    segment_counts: dict[str, int] = {}

    for sample in samples:
        expected = sample["expected"]
        for barrier in expected.get("barriers", []):
            barrier_counts[barrier] = barrier_counts.get(barrier, 0) + 1
        mission = expected.get("shopping_mission")
        if mission:
            mission_counts[mission] = mission_counts.get(mission, 0) + 1
        segment = expected.get("user_segment_hypothesis")
        if segment:
            segment_counts[segment] = segment_counts.get(segment, 0) + 1

    exit_criteria = {
        "business_objective_documented": (PROJECT_ROOT / "Docs" / "phases" / "phase-0-problem-framing" / "business-objectives.md").exists(),
        "taxonomy_v1_documented": (PROJECT_ROOT / "Docs" / "phases" / "phase-0-problem-framing" / "taxonomy-v1.md").exists(),
        "output_schema_finalized": all(
            (SCHEMAS_DIR / f).exists()
            for f in [
                "feedback-record.schema.json",
                "enriched-feedback.schema.json",
                "insight.schema.json",
            ]
        ),
        "priority_source_list_agreed": (PROJECT_ROOT / "Docs" / "phases" / "phase-0-problem-framing" / "source-inventory.md").exists(),
        "insight_rubric_written": (PROJECT_ROOT / "Docs" / "phases" / "phase-0-problem-framing" / "insight-quality-rubric.md").exists(),
        "sample_walkthrough_complete": sample_count >= 20 and len(sample_errors) == 0,
        "schemas_valid": len(schema_errors) == 0,
    }

    return {
        "taxonomy_version": taxonomy.version,
        "sample_count": sample_count,
        "sample_errors": sample_errors,
        "schema_errors": schema_errors,
        "barrier_distribution": barrier_counts,
        "mission_distribution": mission_counts,
        "segment_distribution": segment_counts,
        "exit_criteria": exit_criteria,
        "phase_0_passed": all(exit_criteria.values()),
    }


def main() -> int:
    report = run_walkthrough_report()

    print("=" * 60)
    print("Phase 0 Validation Report")
    print("=" * 60)
    print(f"Taxonomy version: {report['taxonomy_version']}")
    print(f"Sample feedback items: {report['sample_count']}")
    print()

    if report["schema_errors"]:
        print("Schema errors:")
        for err in report["schema_errors"]:
            print(f"  - {err}")
    else:
        print("Schemas: all valid")

    if report["sample_errors"]:
        print("Sample classification errors:")
        for err in report["sample_errors"]:
            print(f"  - {err}")
    else:
        print("Sample walkthrough: all labels valid")

    print()
    print("Barrier distribution in samples:")
    for barrier, count in sorted(report["barrier_distribution"].items(), key=lambda x: -x[1]):
        print(f"  {barrier}: {count}")

    print()
    print("Exit criteria:")
    for criterion, passed in report["exit_criteria"].items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {criterion}")

    print()
    if report["phase_0_passed"]:
        print("Phase 0: PASSED - ready for Phase 1")
        return 0

    print("Phase 0: INCOMPLETE - see failures above")
    return 1


if __name__ == "__main__":
    sys.exit(main())
