"""Build deterministic enrichment cohort from Phase 1 normalized reviews."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from instamart_analyser.common.config import ENRICHMENT_COHORT_CAP, PHASE_2_DATA
from instamart_analyser.common.models import FeedbackRecord, utc_now_iso
from instamart_analyser.phases.phase_1.storage import NormalizedStore

COHORT_PATH = PHASE_2_DATA / "enrichment-cohort.json"

DISCOVERY_SIGNAL_KEYWORDS: dict[str, list[str]] = {
    "category_exploration": [
        "personal care",
        "pet",
        "baby",
        "grocery",
        "snacks",
        "household",
        "never tried",
        "didn't know",
        "discover",
        "new category",
    ],
    "habit_reorder": [
        "reorder",
        "same",
        "repeat",
        "regular",
        "every week",
        "usual",
        "habit",
    ],
    "app_ux_discovery": [
        "app",
        "search",
        "browse",
        "ui",
        "interface",
        "find",
        "category",
        "navigate",
        "clutter",
    ],
}


def has_discovery_signal(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for keywords in DISCOVERY_SIGNAL_KEYWORDS.values() for kw in keywords)


def dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_hashes: set[str] = set()
    unique: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda r: r["record_id"]):
        body_hash = record.get("content_hash") or FeedbackRecord.content_hash(record["body_text"])
        if body_hash in seen_hashes:
            continue
        seen_hashes.add(body_hash)
        unique.append(record)
    return unique


def build_cohort(
    *,
    cap: int = ENRICHMENT_COHORT_CAP,
    output_path: Path | None = None,
    store: NormalizedStore | None = None,
) -> dict[str, Any]:
    """Sample up to `cap` reviews using architecture sampling rules."""
    normalized = store or NormalizedStore()
    all_records = normalized.get_all_records()
    unique = dedupe_records(all_records)

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()

    def try_add(record: dict[str, Any]) -> bool:
        if record["record_id"] in selected_ids or len(selected_ids) >= cap:
            return False
        selected_ids.add(record["record_id"])
        selected.append(record)
        return True

    for record in unique:
        text = f"{record.get('title') or ''} {record['body_text']}"
        if has_discovery_signal(text):
            try_add(record)

    for record in unique:
        if record["source"] != "play_store":
            try_add(record)

    remaining = [r for r in unique if r["record_id"] not in selected_ids]
    by_rating: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for record in remaining:
        rating = record.get("rating")
        key = int(rating) if rating is not None else 0
        by_rating[key].append(record)

    slots = cap - len(selected_ids)
    rating_keys = sorted(by_rating.keys())
    while slots > 0 and rating_keys:
        progressed = False
        for rating in rating_keys:
            bucket = by_rating[rating]
            if bucket and slots > 0:
                try_add(bucket.pop(0))
                slots -= 1
                progressed = True
        if not progressed:
            break

    cohort = {
        "created_at": utc_now_iso(),
        "cap": cap,
        "normalized_total": len(all_records),
        "deduped_total": len(unique),
        "cohort_size": len(selected),
        "record_ids": [r["record_id"] for r in selected],
        "records": [
            {
                "record_id": r["record_id"],
                "source": r["source"],
                "rating": r.get("rating"),
                "body_text": r["body_text"],
                "title": r.get("title"),
            }
            for r in selected
        ],
        "sampling_notes": {
            "priority": "discovery_signals + non_play_store + stratified_by_rating",
            "deduped_removed": len(all_records) - len(unique),
        },
    }

    path = output_path or COHORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(cohort, f, indent=2, ensure_ascii=False)

    return cohort


def load_cohort(path: Path | None = None) -> dict[str, Any]:
    cohort_path = path or COHORT_PATH
    if not cohort_path.exists():
        raise FileNotFoundError(
            f"Enrichment cohort not found at {cohort_path}. Run: pipeline build-cohort"
        )
    with cohort_path.open(encoding="utf-8") as f:
        return json.load(f)
