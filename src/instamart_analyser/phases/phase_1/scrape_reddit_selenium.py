"""CLI: full Selenium scrape for r/swiggyinstamart (posts + comments)."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid

from instamart_analyser.common.models import BatchSummary, utc_now_iso
from instamart_analyser.phases.phase_1.connectors.reddit_selenium import RedditSeleniumConnector
from instamart_analyser.phases.phase_1.pipeline import run_normalization
from instamart_analyser.phases.phase_1.storage import BatchTracker, RawStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Selenium scrape for r/swiggyinstamart")
    parser.add_argument("--subreddit", default="swiggyinstamart")
    parser.add_argument("--max-records", type=int, default=500)
    parser.add_argument("--max-scrolls", type=int, default=40)
    parser.add_argument("--max-pages", type=int, default=50, help="Max JSON pages per sort")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Scrape all sorts + expand every thread (posts and comments)",
    )
    parser.add_argument(
        "--posts-only",
        action="store_true",
        help="Skip comment expansion",
    )
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    parser.add_argument("--ingest", action="store_true", help="Save into Phase 1 raw+normalized stores")
    args = parser.parse_args()

    include_comments = not args.posts_only
    if args.full:
        include_comments = True
        if args.max_records < 500:
            args.max_records = 500
        if args.max_pages < 50:
            args.max_pages = 50

    batch_id = f"batch_{utc_now_iso().replace(':', '').replace('+00:00', 'Z')}_{uuid.uuid4().hex[:8]}"
    connector = RedditSeleniumConnector(
        batch_id=batch_id,
        max_records=args.max_records,
        subreddits=[args.subreddit],
        max_scrolls=args.max_scrolls,
        headless=not args.headed,
        include_comments=include_comments,
        max_pages_per_sort=args.max_pages,
        comment_limit=500,
    )
    result = connector.collect()

    def _safe_print(obj: object) -> None:
        text = json.dumps(obj, indent=2, ensure_ascii=True, default=str)
        try:
            print(text)
        except UnicodeEncodeError:
            sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))

    kinds = {}
    for r in result.records:
        kind = (r.metadata or {}).get("kind", "post")
        kinds[kind] = kinds.get(kind, 0) + 1

    payload = {
        "batch_id": batch_id,
        "fetched_count": result.fetched_count,
        "matched_count": result.filtered_count,
        "kinds": kinds,
        "errors": result.errors,
        "records": [
            {
                "source_record_id": r.source_record_id,
                "title": r.title,
                "url": r.url,
                "author": r.author,
                "timestamp": r.timestamp,
                "body_text": r.body_text[:300],
                "metadata": r.metadata,
            }
            for r in result.records[:30]
        ],
    }
    _safe_print(payload)

    if not args.ingest:
        return 0 if result.records else 1

    store = RawStore()
    tracker = BatchTracker()
    tracker.start_batch(batch_id)
    tracker.log_connector_result(batch_id, result)
    inserted, skipped = store.insert_records(result.records)
    export_path = store.export_batch_jsonl(batch_id)
    summary = BatchSummary(
        batch_id=batch_id,
        started_at=tracker.get_batch(batch_id)["started_at"],
        completed_at=utc_now_iso(),
        status="completed" if inserted else "failed",
        source_counts={"reddit": inserted},
        total_inserted=inserted,
        total_skipped_duplicates=skipped,
        errors=result.errors,
    )
    tracker.complete_batch(summary)
    norm_stats = run_normalization()
    logger.info(
        "Ingested reddit selenium batch %s: inserted=%d skipped=%d normalized_kept=%d export=%s",
        batch_id,
        inserted,
        skipped,
        norm_stats.get("normalized_kept"),
        export_path,
    )
    _safe_print(
        {
            "ingested": True,
            "batch_id": batch_id,
            "inserted": inserted,
            "skipped": skipped,
            "kinds": kinds,
            "normalization": norm_stats,
            "export_path": str(export_path),
        }
    )
    return 0 if inserted or result.records else 1


if __name__ == "__main__":
    sys.exit(main())
