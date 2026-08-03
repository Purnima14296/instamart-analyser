"""Phase 6C validation: roles, quota guards, feedback sync, job recovery APIs."""

from __future__ import annotations

import json
import sys

from fastapi.testclient import TestClient

from instamart_analyser.api.main import app


def main() -> int:
    client = TestClient(app)
    errors: list[str] = []

    viewer = {"Authorization": "Bearer viewer-demo-token"}
    reviewer = {"Authorization": "Bearer reviewer-demo-token"}
    admin = {"Authorization": "Bearer admin-demo-token"}

    me = client.get("/api/me", headers=viewer)
    if me.status_code != 200 or me.json().get("permissions", {}).get("can_run_jobs"):
        errors.append("viewer /api/me permissions incorrect")

    limits = client.get("/api/system/limitations", headers=viewer)
    if limits.status_code != 200 or not limits.json().get("limitations"):
        errors.append("limitations endpoint missing data")

    overview = client.get("/api/overview", headers=viewer)
    if overview.status_code != 200 or "known_limitations" not in overview.json():
        errors.append("overview missing known_limitations")

    research = client.get("/api/research/summary", headers=viewer)
    if research.status_code != 200:
        errors.append(f"research summary failed: {research.status_code}")
    else:
        body = research.json()
        for key in (
            "executive_brief",
            "portfolio",
            "sentiment",
            "discovery_trust",
            "segment_priority",
            "pipeline_status",
            "score_formulas",
        ):
            if key not in body:
                errors.append(f"research summary missing {key}")
        trust = body.get("discovery_trust") or {}
        if "score" not in trust or "formula" not in trust:
            errors.append("discovery_trust missing score/formula")
        if not (body.get("portfolio") or {}).get("source_counts"):
            errors.append("research portfolio missing source_counts")

    explorer_expectations = {
        "/api/explore/sources": ("sources", "rating_distribution"),
        "/api/explore/reviews?limit=5": ("reviews", "facets", "total_matched"),
        "/api/explore/discovery-challenges": ("challenges", "barrier_totals"),
        "/api/explore/segments": ("segments", "recommended_focus"),
        "/api/explore/root-causes": ("causes", "method"),
        "/api/explore/unmet-needs": ("needs", "linked_opportunities"),
        "/api/explore/journey": ("stages", "behaviour_signals"),
        "/api/explore/validation": ("comparisons", "refinements"),
    }
    for path, keys in explorer_expectations.items():
        response = client.get(path, headers=viewer)
        if response.status_code != 200:
            errors.append(f"{path} failed: {response.status_code}")
            continue
        payload = response.json()
        for key in keys:
            if key not in payload:
                errors.append(f"{path} missing {key}")

    # viewer cannot review or run jobs
    insights = client.get("/api/insights", headers=viewer).json()
    if insights.get("count", 0) < 1:
        errors.append("expected insights for review tests")
    else:
        insight_id = insights["insights"][0]["insight_id"]
        denied = client.patch(
            f"/api/insights/{insight_id}/status",
            headers=viewer,
            json={"status": "approved"},
        )
        if denied.status_code != 403:
            errors.append(f"viewer patch should be 403, got {denied.status_code}")

        ok = client.patch(
            f"/api/insights/{insight_id}/status",
            headers=reviewer,
            json={"status": "approved", "notes": "phase6c validation"},
        )
        if ok.status_code != 200 or ok.json().get("status") != "approved":
            errors.append("reviewer could not approve insight")

    denied_job = client.post("/api/jobs/phase4", headers=viewer)
    if denied_job.status_code != 403:
        errors.append("viewer job start should be 403")

    denied_ingest = client.post("/api/jobs/ingest_play", headers=viewer)
    if denied_ingest.status_code != 403:
        errors.append("viewer ingest job start should be 403")

    jobs_catalog = client.get("/api/jobs", headers=admin)
    if jobs_catalog.status_code != 200:
        errors.append("jobs list failed")
    else:
        available = set(jobs_catalog.json().get("available_job_types") or [])
        for required in {
            "enrich",
            "phase3",
            "phase4",
            "phase5",
            "ingest_play",
            "ingest_appstore",
            "ingest_reddit_selenium",
            "ingest_all",
            "analysis_cascade",
        }:
            if required not in available:
                errors.append(f"missing job type in catalog: {required}")

    fb = client.post(
        "/api/feedback",
        headers=reviewer,
        json={
            "reviewer": "phase6c_validator",
            "role": "research",
            "overall_usefulness": "high",
            "trust_in_outputs": "medium",
            "would_use_for_experiment_planning": True,
            "comments": ["Phase 6C feedback sync check"],
            "defects": [{"issue": "Need clearer quota messaging", "severity": "low", "status": "open"}],
        },
    )
    if fb.status_code != 200:
        errors.append(f"feedback failed: {fb.status_code} {fb.text[:200]}")
    else:
        refresh = fb.json().get("phase5_feedback_refresh")
        if not refresh or refresh.get("response_count", 0) < 1:
            errors.append("feedback did not refresh Phase 5 summary")

    recover = client.post("/api/jobs/recover-stale", headers=admin)
    if recover.status_code != 200 or "recovered" not in recover.json():
        errors.append("recover-stale endpoint failed")

    # If quota is blocked, enrich should return 429 for admin
    enrichment = client.get("/api/enrichment/status", headers=admin).json()
    if enrichment.get("quota_blocked"):
        blocked = client.post("/api/jobs/enrich", headers=admin)
        if blocked.status_code != 429:
            errors.append(f"expected 429 when quota blocked, got {blocked.status_code}")

    # Start a short phase5 job if none active
    jobs = client.get("/api/jobs", headers=admin).json()
    if jobs.get("active_count", 0) == 0:
        started = client.post("/api/jobs/phase5", headers=admin)
        if started.status_code != 200:
            errors.append(f"admin phase5 start failed: {started.status_code} {started.text[:200]}")
        else:
            import time

            job_id = started.json()["job_id"]
            final = None
            for _ in range(40):
                time.sleep(0.4)
                final = client.get(f"/api/jobs/{job_id}", headers=admin).json()
                if final.get("status") in {"completed", "failed"}:
                    break
            if not final or final.get("status") not in {"completed", "failed"}:
                errors.append("phase5 job did not finish")
            elif final.get("status") == "failed":
                errors.append(f"phase5 job failed: {final.get('error')}")

    stats = client.get("/api/feedback/review-stats", headers=viewer)
    if stats.status_code != 200:
        errors.append("review-stats endpoint failed")

    result = {"status": "passed" if not errors else "failed", "errors": errors}
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
