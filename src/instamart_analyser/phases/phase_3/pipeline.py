"""Phase 3 pipeline: aggregate themes and draft insights."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from instamart_analyser.common.config import PHASE_3_DATA
from instamart_analyser.phases.phase_3.aggregator import aggregate_themes, load_clusters
from instamart_analyser.phases.phase_3.insight_generator import generate_insights, write_markdown_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def cmd_aggregate(args: argparse.Namespace) -> int:
    payload = aggregate_themes(min_cluster_size=args.min_cluster_size)
    print(
        json.dumps(
            {
                "enriched_record_count": payload["summary"]["enriched_record_count"],
                "cluster_count": payload["summary"]["cluster_count"],
                "summary_path": str(PHASE_3_DATA / "theme-summary.json"),
                "clusters_path": str(PHASE_3_DATA / "theme-clusters.json"),
            },
            indent=2,
        )
    )
    return 0


def cmd_draft_insights(args: argparse.Namespace) -> int:
    payload = load_clusters()
    insights = generate_insights(
        clusters=payload["clusters"],
        limit=args.limit,
        dry_run=args.dry_run,
    )
    report_path = write_markdown_report(payload["summary"], insights)
    print(
        json.dumps(
            {
                "insight_count": insights["insight_count"],
                "error_count": insights["error_count"],
                "dry_run": insights["dry_run"],
                "insights_path": str(PHASE_3_DATA / "insights.json"),
                "report_path": str(report_path),
            },
            indent=2,
        )
    )
    return 0 if insights["insight_count"] > 0 else 1


def cmd_run(args: argparse.Namespace) -> int:
    aggregate = aggregate_themes(min_cluster_size=args.min_cluster_size)
    insights = generate_insights(
        clusters=aggregate["clusters"],
        limit=args.limit,
        dry_run=args.dry_run,
    )
    report_path = write_markdown_report(aggregate["summary"], insights)
    print(
        json.dumps(
            {
                "cluster_count": aggregate["summary"]["cluster_count"],
                "insight_count": insights["insight_count"],
                "error_count": insights["error_count"],
                "dry_run": insights["dry_run"],
                "report_path": str(report_path),
            },
            indent=2,
        )
    )
    return 0 if insights["insight_count"] > 0 else 1


def cmd_status(_args: argparse.Namespace) -> int:
    status = {
        "theme_summary_exists": (PHASE_3_DATA / "theme-summary.json").exists(),
        "theme_clusters_exists": (PHASE_3_DATA / "theme-clusters.json").exists(),
        "insights_exists": (PHASE_3_DATA / "insights.json").exists(),
        "report_exists": (PHASE_3_DATA / "insight-report.md").exists(),
    }
    print(json.dumps(status, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 3: Theme Detection And Insight Generation")
    sub = parser.add_subparsers(dest="command", required=True)

    p_aggregate = sub.add_parser("aggregate", help="Build deterministic theme clusters")
    p_aggregate.add_argument("--min-cluster-size", type=int, default=3, help="Minimum records per cluster")
    p_aggregate.set_defaults(func=cmd_aggregate)

    p_draft = sub.add_parser("draft-insights", help="Draft insights from existing clusters")
    p_draft.add_argument("--limit", type=int, default=10, help="Max clusters to draft")
    p_draft.add_argument("--dry-run", action="store_true", help="Use heuristic drafts instead of Groq")
    p_draft.set_defaults(func=cmd_draft_insights)

    p_run = sub.add_parser("run", help="Aggregate and draft insights")
    p_run.add_argument("--min-cluster-size", type=int, default=3, help="Minimum records per cluster")
    p_run.add_argument("--limit", type=int, default=10, help="Max clusters to draft")
    p_run.add_argument("--dry-run", action="store_true", help="Use heuristic drafts instead of Groq")
    p_run.set_defaults(func=cmd_run)

    p_status = sub.add_parser("status", help="Show Phase 3 output status")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
