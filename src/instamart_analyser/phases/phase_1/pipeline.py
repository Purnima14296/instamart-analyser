"""Phase 1: Data ingestion and storage pipeline."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from pathlib import Path

from instamart_analyser.common.config import DEFAULT_MAX_PER_SOURCE, PHASE_1_SEED, is_instamart_review
from instamart_analyser.common.dates import DEFAULT_LOOKBACK_DAYS
from instamart_analyser.common.models import BatchSummary, FeedbackRecord, utc_now_iso
from functools import partial

from instamart_analyser.phases.phase_1.connectors import (
    AppStoreConnector,
    MouthShutConnector,
    PlayStoreConnector,
    RedditConnector,
    RedditSeleniumConnector,
    SeedCategoryConnector,
)
from instamart_analyser.phases.phase_1.storage import BatchTracker, NormalizedStore, RawStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def load_seed_records(
    batch_id: str,
    seed_path: Path | None = None,
    source_filter: str | None = None,
) -> list[FeedbackRecord]:
    """Load seed records from JSON file for offline/demo runs."""
    path = seed_path or (PHASE_1_SEED / "seed-records.json")
    if not path.exists():
        return []

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    records = []
    for item in data.get("records", []):
        if source_filter and item.get("source") != source_filter:
            continue
        body = item["body_text"]
        title = item.get("title", "") or ""
        if not is_instamart_review(f"{title}\n{body}"):
            continue
        records.append(
            FeedbackRecord(
                source=item["source"],
                source_record_id=item["source_record_id"],
                body_text=item["body_text"],
                language=item.get("language", "en"),
                collection_batch_id=batch_id,
                url=item.get("url"),
                author=item.get("author"),
                timestamp=item.get("timestamp"),
                title=item.get("title"),
                rating=item.get("rating"),
                metadata=item.get("metadata", {}),
            )
        )
    return records


def run_ingestion(
    *,
    max_per_source: int = DEFAULT_MAX_PER_SOURCE,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    seed_only: bool = False,
    include_seed: bool = True,
    sources: list[str] | None = None,
) -> BatchSummary:
    """Run the full Phase 1 ingestion pipeline."""
    batch_id = f"batch_{utc_now_iso().replace(':', '').replace('+00:00', 'Z')}_{uuid.uuid4().hex[:8]}"
    store = RawStore()
    tracker = BatchTracker()
    tracker.start_batch(batch_id)
    logger.info("Ingestion window: last %d days (~%.1f months)", lookback_days, lookback_days / 30)

    all_connectors = {
        "play_store": PlayStoreConnector,
        "app_store": AppStoreConnector,
        "reddit": RedditConnector,
        "reddit_selenium": RedditSeleniumConnector,
        "mouthshut": MouthShutConnector,
        "quora": partial(SeedCategoryConnector, source="quora"),
        "youtube": partial(SeedCategoryConnector, source="youtube"),
        "twitter": partial(SeedCategoryConnector, source="twitter"),
        "facebook": partial(SeedCategoryConnector, source="facebook"),
    }

    selected = sources or list(all_connectors.keys())
    source_counts: dict[str, int] = {}
    total_inserted = 0
    total_skipped = 0
    errors: list[str] = []

    if not seed_only:
        for source_name in selected:
            connector_cls = all_connectors.get(source_name)
            if not connector_cls:
                errors.append(f"Unknown source: {source_name}")
                continue

            connector = connector_cls(
                batch_id=batch_id,
                max_records=max_per_source,
                lookback_days=lookback_days,
            )
            logger.info("Collecting from %s...", source_name)
            result = connector.collect()
            tracker.log_connector_result(batch_id, result)

            if result.errors and not result.records:
                errors.extend(result.errors)

            inserted, skipped = store.insert_records(result.records)
            total_inserted += inserted
            total_skipped += skipped
            source_counts[source_name] = source_counts.get(source_name, 0) + inserted
            logger.info(
                "%s: %d inserted, %d duplicates skipped",
                source_name,
                inserted,
                skipped,
            )

            # Fallback to seed data when live connector returns no records
            if len(result.records) == 0:
                fallback = load_seed_records(batch_id, source_filter=source_name)
                if fallback:
                    fb_inserted, fb_skipped = store.insert_records(fallback)
                    total_inserted += fb_inserted
                    total_skipped += fb_skipped
                    source_counts[source_name] = source_counts.get(source_name, 0) + fb_inserted
                    logger.info(
                        "%s seed fallback: %d inserted, %d duplicates skipped",
                        source_name,
                        fb_inserted,
                        fb_skipped,
                    )

    if include_seed or seed_only:
        seed_records = load_seed_records(batch_id)
        if seed_records:
            inserted, skipped = store.insert_records(seed_records)
            total_inserted += inserted
            total_skipped += skipped
            source_counts["seed"] = source_counts.get("seed", 0) + inserted
            logger.info("Seed data: %d inserted, %d duplicates skipped", inserted, skipped)

    export_path = store.export_batch_jsonl(batch_id)
    logger.info("Exported batch to %s", export_path)

    store_total = store.count_total()
    status = "completed" if (total_inserted > 0 or store_total > 0) else "failed"
    summary = BatchSummary(
        batch_id=batch_id,
        started_at=tracker.get_batch(batch_id)["started_at"],
        completed_at=utc_now_iso(),
        status=status,
        source_counts=source_counts,
        total_inserted=total_inserted,
        total_skipped_duplicates=total_skipped,
        errors=errors,
    )
    tracker.complete_batch(summary)

    norm_stats = run_normalization()
    logger.info(
        "Normalization: %d kept, %d rejected from %d raw",
        norm_stats["normalized_kept"],
        norm_stats["rejected_total"],
        norm_stats["raw_total"],
    )
    summary.source_counts["normalized_kept"] = norm_stats["normalized_kept"]
    return summary


def run_normalization() -> dict:
    """Apply Phase 1 normalization rules to all raw reviews."""
    raw_store = RawStore()
    normalized_store = NormalizedStore()
    return normalized_store.rebuild_from_raw(raw_store)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1: Data Ingestion Pipeline")
    parser.add_argument(
        "command",
        choices=["run", "normalize"],
        help="Pipeline command",
    )
    parser.add_argument(
        "--max-per-source",
        type=int,
        default=DEFAULT_MAX_PER_SOURCE,
        help="Max Instamart reviews per source (0 = unlimited)",
    )
    parser.add_argument(
        "--months",
        type=float,
        default=6,
        help="How many months of reviews to fetch (default: 6)",
    )
    parser.add_argument(
        "--seed-only",
        action="store_true",
        help="Only load seed data (skip live connectors)",
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Skip seed data when running live connectors",
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=[
            "play_store",
            "app_store",
            "reddit",
            "reddit_selenium",
            "mouthshut",
            "quora",
            "youtube",
            "twitter",
            "facebook",
        ],
        help="Limit to specific sources",
    )
    args = parser.parse_args()

    if args.command == "run":
        lookback_days = int(args.months * 30)
        summary = run_ingestion(
            max_per_source=args.max_per_source,
            lookback_days=lookback_days,
            seed_only=args.seed_only,
            include_seed=not args.no_seed,
            sources=args.sources,
        )
        print(json.dumps(summary.to_dict(), indent=2))
        return 0 if summary.status == "completed" else 1

    if args.command == "normalize":
        stats = run_normalization()
        print(json.dumps(stats, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
