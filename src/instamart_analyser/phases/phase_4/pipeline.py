"""Phase 4 pipeline: recommendation framing and hypothesis backlog."""

from __future__ import annotations

import argparse
import json
import sys

from instamart_analyser.common.config import PHASE_4_DATA
from instamart_analyser.phases.phase_4.recommender import build_recommendation_frame, write_experiment_memo


def cmd_frame(_args: argparse.Namespace) -> int:
    payload = build_recommendation_frame()
    memo_path = write_experiment_memo(payload)
    print(
        json.dumps(
            {
                "opportunity_count": payload["summary"]["opportunity_count"],
                "hypothesis_count": payload["summary"]["hypothesis_count"],
                "opportunity_map_path": str(PHASE_4_DATA / "opportunity-map.json"),
                "hypothesis_backlog_path": str(PHASE_4_DATA / "hypothesis-backlog.json"),
                "memo_path": str(memo_path),
            },
            indent=2,
        )
    )
    return 0 if payload["summary"]["opportunity_count"] > 0 else 1


def cmd_status(_args: argparse.Namespace) -> int:
    status = {
        "summary_exists": (PHASE_4_DATA / "phase-4-summary.json").exists(),
        "opportunity_map_exists": (PHASE_4_DATA / "opportunity-map.json").exists(),
        "hypothesis_backlog_exists": (PHASE_4_DATA / "hypothesis-backlog.json").exists(),
        "experiment_memo_exists": (PHASE_4_DATA / "experiment-framing-memo.md").exists(),
    }
    print(json.dumps(status, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 4: Recommendation Framing")
    sub = parser.add_subparsers(dest="command", required=True)

    p_frame = sub.add_parser("frame", help="Build Phase 4 opportunity map and hypotheses")
    p_frame.set_defaults(func=cmd_frame)

    p_run = sub.add_parser("run", help="Alias for frame")
    p_run.set_defaults(func=cmd_frame)

    p_status = sub.add_parser("status", help="Show Phase 4 output status")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
