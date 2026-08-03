"""Gold-set export and evaluation for Phase 2 quality gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from instamart_analyser.common.config import PHASE_2_DATA
from instamart_analyser.common.models import utc_now_iso
from instamart_analyser.phases.phase_1.storage import NormalizedStore
from instamart_analyser.phases.phase_2.enricher import Enricher

GOLD_CANDIDATES_PATH = PHASE_2_DATA / "gold-set-candidates.json"
GOLD_SET_PATH = PHASE_2_DATA / "gold-set.json"
GOLD_EVAL_PATH = PHASE_2_DATA / "gold-set-eval.json"


def word_count(text: str) -> int:
    return len(text.split())


def export_gold_candidates(
    *,
    short: int = 10,
    medium: int = 10,
    long_count: int = 10,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Export 30 stratified reviews for manual gold labeling."""
    store = NormalizedStore()
    records = store.get_all_records()

    short_bucket: list[dict[str, Any]] = []
    medium_bucket: list[dict[str, Any]] = []
    long_bucket: list[dict[str, Any]] = []

    for record in sorted(records, key=lambda r: r["record_id"]):
        wc = word_count(record["body_text"])
        if wc <= 15:
            short_bucket.append(record)
        elif wc <= 50:
            medium_bucket.append(record)
        else:
            long_bucket.append(record)

    selected = (
        short_bucket[:short]
        + medium_bucket[:medium]
        + long_bucket[:long_count]
    )

    payload = {
        "created_at": utc_now_iso(),
        "instructions": (
            "Fill expected_labels for each record before running gold-eval. "
            "Required: shopping_mission, barriers (list). "
            "Target: >=80% agreement on barriers and shopping_mission."
        ),
        "records": [
            {
                "record_id": r["record_id"],
                "source": r["source"],
                "rating": r.get("rating"),
                "word_count": word_count(r["body_text"]),
                "body_text": r["body_text"],
                "expected_labels": {
                    "shopping_mission": None,
                    "barriers": [],
                },
            }
            for r in selected
        ],
    }

    path = output_path or GOLD_CANDIDATES_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    gold_path = GOLD_SET_PATH
    if not gold_path.exists():
        with gold_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    return payload


def load_gold_set(path: Path | None = None) -> dict[str, Any]:
    gold_path = path or GOLD_SET_PATH
    if not gold_path.exists():
        raise FileNotFoundError(
            f"Gold set not found at {gold_path}. Run: pipeline gold-export"
        )
    with gold_path.open(encoding="utf-8") as f:
        return json.load(f)


def _barrier_agreement(expected: list[str], predicted: list[str]) -> float:
    if not expected and not predicted:
        return 1.0
    exp = set(expected)
    pred = set(predicted)
    if not exp:
        return 0.0
    return len(exp & pred) / len(exp)


def evaluate_gold_set(
    *,
    gold_path: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run Groq on labeled gold records and compare to expected labels."""
    gold = load_gold_set(gold_path)
    enricher = Enricher(dry_run=dry_run)
    store = NormalizedStore()

    labeled = [
        r for r in gold["records"]
        if r.get("expected_labels", {}).get("shopping_mission")
        and r.get("expected_labels", {}).get("barriers") is not None
    ]

    if not labeled:
        return {
            "status": "incomplete",
            "message": "No labeled records in gold-set.json. Fill expected_labels first.",
            "labeled_count": 0,
        }

    mission_matches = 0
    barrier_scores: list[float] = []
    details: list[dict[str, Any]] = []

    for item in labeled:
        row = store.get_record(item["record_id"])
        if not row:
            continue
        record = {
            "record_id": row["record_id"],
            "source": row["source"],
            "body_text": row["body_text"],
            "rating": row.get("rating"),
        }
        enrichment, error = enricher.enrich_record(record)
        expected = item["expected_labels"]
        if not enrichment:
            details.append(
                {
                    "record_id": item["record_id"],
                    "error": error,
                }
            )
            continue

        mission_ok = enrichment.get("shopping_mission") == expected["shopping_mission"]
        if mission_ok:
            mission_matches += 1
        barrier_score = _barrier_agreement(
            expected.get("barriers", []),
            enrichment.get("barriers", []),
        )
        barrier_scores.append(barrier_score)
        details.append(
            {
                "record_id": item["record_id"],
                "expected_mission": expected["shopping_mission"],
                "predicted_mission": enrichment.get("shopping_mission"),
                "mission_match": mission_ok,
                "expected_barriers": expected.get("barriers", []),
                "predicted_barriers": enrichment.get("barriers", []),
                "barrier_agreement": round(barrier_score, 3),
            }
        )

    n = len(details)
    mission_pct = (mission_matches / n * 100) if n else 0.0
    barrier_pct = (sum(barrier_scores) / len(barrier_scores) * 100) if barrier_scores else 0.0
    passed = mission_pct >= 80 and barrier_pct >= 80

    report = {
        "evaluated_at": utc_now_iso(),
        "labeled_count": len(labeled),
        "evaluated_count": n,
        "shopping_mission_agreement_pct": round(mission_pct, 1),
        "barriers_agreement_pct": round(barrier_pct, 1),
        "gate_passed": passed,
        "threshold_pct": 80,
        "dry_run": dry_run,
        "details": details,
    }

    GOLD_EVAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with GOLD_EVAL_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report
