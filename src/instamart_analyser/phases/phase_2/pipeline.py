"""Phase 2: Groq enrichment pipeline CLI."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from instamart_analyser.common.config import ENRICHMENT_BATCH_SIZE, PHASE_2_DATA
from instamart_analyser.phases.phase_2.cohort import build_cohort
from instamart_analyser.phases.phase_2.enricher import Enricher
from instamart_analyser.phases.phase_2.gold_set import evaluate_gold_set, export_gold_candidates
from instamart_analyser.phases.phase_2.groq_client import GroqClient
from instamart_analyser.phases.phase_2.storage import EnrichedStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def cmd_build_cohort(args: argparse.Namespace) -> int:
    cohort = build_cohort(cap=args.cap)
    print(json.dumps(
        {
            "cohort_size": cohort["cohort_size"],
            "normalized_total": cohort["normalized_total"],
            "deduped_total": cohort["deduped_total"],
            "path": str(PHASE_2_DATA / "enrichment-cohort.json"),
        },
        indent=2,
    ))
    return 0


def cmd_enrich(args: argparse.Namespace) -> int:
    enricher = Enricher(dry_run=args.dry_run)
    enricher.groq.batch_size = args.batch_size
    result = enricher.run_cohort(limit=args.limit, skip_enriched=not args.force)
    print(json.dumps(result, indent=2))
    if result.get("stopped_reason"):
        return 2
    return 0 if result["errors"] == 0 or result["success"] > 0 else 1


def cmd_status(_args: argparse.Namespace) -> int:
    store = EnrichedStore()
    usage = GroqClient(dry_run=True).usage_summary()
    latest = store.get_latest_run()
    print(json.dumps(
        {
            "enriched_count": store.count_enriched(),
            "error_count": store.count_errors(),
            "usage_today": usage,
            "latest_run": latest,
        },
        indent=2,
    ))
    return 0


def cmd_export(_args: argparse.Namespace) -> int:
    store = EnrichedStore()
    jsonl_path = PHASE_2_DATA / "enriched-feedback.jsonl"
    store.export_jsonl(jsonl_path)
    print(json.dumps({"exported": str(jsonl_path), "count": store.count_enriched()}, indent=2))
    return 0


def cmd_gold_export(_args: argparse.Namespace) -> int:
    payload = export_gold_candidates()
    print(json.dumps(
        {
            "exported": len(payload["records"]),
            "candidates_path": str(PHASE_2_DATA / "gold-set-candidates.json"),
            "gold_set_path": str(PHASE_2_DATA / "gold-set.json"),
        },
        indent=2,
    ))
    return 0


def cmd_gold_eval(args: argparse.Namespace) -> int:
    report = evaluate_gold_set(dry_run=args.dry_run)
    print(json.dumps(report, indent=2))
    if report.get("status") == "incomplete":
        return 1
    return 0 if report.get("gate_passed") else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 2: Groq Enrichment Pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    p_cohort = sub.add_parser("build-cohort", help="Build enrichment cohort from Phase 1 data")
    p_cohort.add_argument("--cap", type=int, default=1000, help="Max reviews in cohort")
    p_cohort.set_defaults(func=cmd_build_cohort)

    p_enrich = sub.add_parser("enrich", help="Run rate-limited Groq enrichment")
    p_enrich.add_argument("--limit", type=int, default=None, help="Max records this run")
    p_enrich.add_argument("--dry-run", action="store_true", help="Rule-based stub (no API)")
    p_enrich.add_argument("--force", action="store_true", help="Re-enrich already enriched records")
    p_enrich.add_argument(
        "--batch-size",
        type=int,
        default=ENRICHMENT_BATCH_SIZE,
        help="Groq micro-batch size (recommended 5-8)",
    )
    p_enrich.set_defaults(func=cmd_enrich)

    p_status = sub.add_parser("status", help="Show enrichment and usage status")
    p_status.set_defaults(func=cmd_status)

    p_export = sub.add_parser("export", help="Export enriched records to JSONL")
    p_export.set_defaults(func=cmd_export)

    p_gold_export = sub.add_parser("gold-export", help="Export 30 gold-set candidates")
    p_gold_export.set_defaults(func=cmd_gold_export)

    p_gold_eval = sub.add_parser("gold-eval", help="Evaluate gold-set labels vs Groq")
    p_gold_eval.add_argument("--dry-run", action="store_true", help="Use dry-run classifier")
    p_gold_eval.set_defaults(func=cmd_gold_eval)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
