"""Smoke validation for Phase 6A API (in-process TestClient)."""

from __future__ import annotations

import json
import sys

from fastapi.testclient import TestClient

from instamart_analyser.api.main import app


def main() -> int:
    client = TestClient(app)
    errors: list[str] = []

    # Unauthenticated should fail
    r = client.get("/api/health")
    if r.status_code != 401:
        errors.append(f"Expected 401 without token, got {r.status_code}")

    headers = {"Authorization": "Bearer viewer-demo-token"}
    admin = {"Authorization": "Bearer admin-demo-token"}
    reviewer = {"Authorization": "Bearer reviewer-demo-token"}

    checks = [
        ("GET", "/api/health", headers, 200),
        ("GET", "/api/overview", headers, 200),
        ("GET", "/api/insights", headers, 200),
        ("GET", "/api/themes", headers, 200),
        ("GET", "/api/opportunities", headers, 200),
        ("GET", "/api/hypotheses", headers, 200),
        ("GET", "/api/measurement", headers, 200),
        ("GET", "/api/reports", headers, 200),
        ("GET", "/api/jobs", headers, 200),
        ("GET", "/api/feedback", headers, 200),
    ]
    for method, path, hdrs, expected in checks:
        resp = client.request(method, path, headers=hdrs)
        if resp.status_code != expected:
            errors.append(f"{method} {path} expected {expected}, got {resp.status_code}: {resp.text[:200]}")

    overview = client.get("/api/overview", headers=headers).json()
    if "enrichment" not in overview or "bias_notes" not in overview:
        errors.append("overview missing enrichment or bias_notes")
    if "sample_size" not in overview:
        errors.append("overview missing sample_size")

    insights = client.get("/api/insights", headers=headers).json()
    if insights.get("count", 0) < 1:
        errors.append("expected at least one insight")
    else:
        insight_id = insights["insights"][0]["insight_id"]
        detail = client.get(f"/api/insights/{insight_id}", headers=headers)
        if detail.status_code != 200:
            errors.append(f"insight detail failed: {detail.status_code}")
        # viewer cannot patch
        denied = client.patch(
            f"/api/insights/{insight_id}/status",
            headers=headers,
            json={"status": "approved", "notes": "viewer attempt"},
        )
        if denied.status_code != 403:
            errors.append(f"viewer patch should be 403, got {denied.status_code}")
        ok = client.patch(
            f"/api/insights/{insight_id}/status",
            headers=reviewer,
            json={"status": "approved", "notes": "phase6a smoke"},
        )
        if ok.status_code != 200:
            errors.append(f"reviewer patch failed: {ok.status_code} {ok.text[:200]}")
        elif ok.json().get("status") != "approved":
            errors.append("insight status not updated to approved")

    # viewer cannot start jobs
    denied_job = client.post("/api/jobs/phase5", headers=headers)
    if denied_job.status_code != 403:
        errors.append(f"viewer job start should be 403, got {denied_job.status_code}")

    # admin can enqueue a short phase5 job
    job = client.post("/api/jobs/phase5", headers=admin)
    if job.status_code != 200:
        errors.append(f"admin phase5 job failed: {job.status_code} {job.text[:200]}")
    else:
        job_id = job.json()["job_id"]
        # poll a few times
        import time

        final = None
        for _ in range(30):
            time.sleep(0.5)
            final = client.get(f"/api/jobs/{job_id}", headers=headers).json()
            if final.get("status") in {"completed", "failed"}:
                break
        if not final or final.get("status") not in {"completed", "failed"}:
            errors.append("phase5 job did not finish in smoke window")
        elif final.get("status") == "failed":
            errors.append(f"phase5 job failed: {final.get('error')}")

    fb = client.post(
        "/api/feedback",
        headers=reviewer,
        json={
            "reviewer": "smoke_tester",
            "role": "growth",
            "overall_usefulness": "high",
            "trust_in_outputs": "medium",
            "would_use_for_experiment_planning": True,
            "comments": ["Phase 6A API smoke test"],
            "defects": [],
        },
    )
    if fb.status_code != 200:
        errors.append(f"feedback post failed: {fb.status_code} {fb.text[:200]}")

    result = {"status": "passed" if not errors else "failed", "errors": errors}
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
