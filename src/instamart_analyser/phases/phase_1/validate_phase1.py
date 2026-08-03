"""Phase 1 validation: smoke tests and exit criteria checks."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import Draft202012Validator

from instamart_analyser.common.config import PHASE_1_DATA, PHASE_1_DB, PHASE_1_LOGS, PHASE_1_RAW, SCHEMAS_DIR
from instamart_analyser.phases.phase_1.storage import BatchTracker, RawStore

REQUIRED_FIELDS = [
    "record_id",
    "source",
    "source_record_id",
    "body_text",
    "language",
    "collected_at",
    "collection_batch_id",
    "pipeline_stage",
]


def load_schema() -> dict[str, Any]:
    with (SCHEMAS_DIR / "feedback-record.schema.json").open(encoding="utf-8") as f:
        return json.load(f)


def validate_record_schema(record: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema)
    return [e.message for e in validator.iter_errors(record)]


def check_required_fields(record: dict[str, Any]) -> list[str]:
    return [f"Missing required field: {field}" for field in REQUIRED_FIELDS if field not in record]


def run_validation() -> dict[str, Any]:
    store = RawStore()
    tracker = BatchTracker()
    schema = load_schema()

    total_records = store.count_total()
    source_counts = store.count_by_source()
    samples = store.get_sample(limit=10)

    schema_errors: list[str] = []
    field_errors: list[str] = []

    for sample in samples:
        record = {
            "record_id": sample["record_id"],
            "source": sample["source"],
            "source_record_id": sample["source_record_id"],
            "body_text": sample["body_text"],
            "language": sample["language"],
            "collected_at": sample["collected_at"],
            "collection_batch_id": sample["collection_batch_id"],
            "pipeline_stage": sample["pipeline_stage"],
        }
        if sample.get("url"):
            record["url"] = sample["url"]
        if sample.get("author"):
            record["author"] = sample["author"]
        if sample.get("timestamp"):
            record["timestamp"] = sample["timestamp"]
        if sample.get("title"):
            record["title"] = sample["title"]
        if sample.get("rating") is not None:
            record["rating"] = sample["rating"]
        if sample.get("metadata_json"):
            record["metadata"] = json.loads(sample["metadata_json"])

        field_errors.extend(check_required_fields(record))
        schema_errors.extend(validate_record_schema(record, schema))

    # Check batch logging
    batches_exist = PHASE_1_DB.exists()
    logs_exist = any(PHASE_1_LOGS.glob("*.json"))
    raw_exports_exist = any(PHASE_1_RAW.iterdir()) if PHASE_1_RAW.exists() else False

    # Check dedupe: re-run insert should skip all
    dedupe_works = False
    if samples:
        from instamart_analyser.common.models import FeedbackRecord

        test_record = FeedbackRecord(
            source=samples[0]["source"],
            source_record_id=samples[0]["source_record_id"],
            body_text=samples[0]["body_text"],
            language=samples[0]["language"],
            collection_batch_id="dedupe_test",
        )
        inserted, skipped = store.insert_records([test_record])
        dedupe_works = inserted == 0 and skipped == 1

    exit_criteria = {
        "priority_sources_have_records": all(
            source_counts.get(s, 0) > 0 for s in ["play_store", "app_store", "reddit"]
        ) or source_counts.get("seed", 0) > 0,
        "raw_schema_stable": len(schema_errors) == 0 and len(field_errors) == 0,
        "logging_exists": batches_exist and logs_exist,
        "seed_dataset_reviewable": total_records > 0 and raw_exports_exist,
        "dedupe_on_rerun": dedupe_works,
        "minimum_record_count": total_records >= 10,
    }

    return {
        "total_records": total_records,
        "source_counts": source_counts,
        "schema_errors": schema_errors[:5],
        "field_errors": field_errors[:5],
        "exit_criteria": exit_criteria,
        "phase_1_passed": all(exit_criteria.values()),
    }


def main() -> int:
    report = run_validation()

    print("=" * 60)
    print("Phase 1 Validation Report")
    print("=" * 60)
    print(f"Total records in store: {report['total_records']}")
    print(f"Source breakdown: {report['source_counts']}")
    print()

    if report["schema_errors"]:
        print("Schema errors (sample):")
        for err in report["schema_errors"]:
            print(f"  - {err}")
    else:
        print("Schema validation: passed on samples")

    print()
    print("Exit criteria:")
    for criterion, passed in report["exit_criteria"].items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {criterion}")

    print()
    if report["phase_1_passed"]:
        print("Phase 1: PASSED - ready for Phase 2")
        return 0

    print("Phase 1: INCOMPLETE - run pipeline first or check failures above")
    return 1


if __name__ == "__main__":
    sys.exit(main())
