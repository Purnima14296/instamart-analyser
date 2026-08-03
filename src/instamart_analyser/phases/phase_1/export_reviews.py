"""Export Phase 1 reviews to a readable summary file."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from instamart_analyser.common.config import PHASE_1_DATA
from instamart_analyser.phases.phase_1.storage import NormalizedStore, RawStore


def export_summary(
    output_path: Path | None = None,
    *,
    normalized: bool = True,
) -> Path:
    if normalized:
        store = NormalizedStore()
        table = "normalized_feedback"
        out = output_path or (PHASE_1_DATA / "reviews-summary.json")
    else:
        store = RawStore()
        table = "raw_feedback"
        out = output_path or (PHASE_1_DATA / "reviews-summary-raw.json")

    with store._connect() as conn:
        rows = conn.execute(
            f"""
            SELECT source, source_record_id, body_text, rating, author,
                   timestamp, url, language, collection_batch_id, title
            FROM {table}
            ORDER BY source, timestamp DESC
            """
        ).fetchall()

    records = [dict(row) for row in rows]
    rating_dist = Counter(r["rating"] for r in records if r.get("rating"))

    summary = {
        "pipeline_stage": "normalized" if normalized else "raw",
        "total_reviews": len(records),
        "by_source": dict(Counter(r["source"] for r in records)),
        "rating_distribution": dict(sorted(rating_dist.items())),
        "normalization_rules": {
            "min_words": 5,
            "english_only": True,
            "emoji_removed": True,
        },
        "reviews": records,
    }

    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def main() -> int:
    path = export_summary(normalized=True)
    norm = NormalizedStore()
    raw = RawStore()
    print(f"Exported {norm.count_total()} normalized reviews to {path}")
    print(f"Normalized by source: {norm.count_by_source()}")
    print(f"Raw total (unfiltered): {raw.count_total()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
