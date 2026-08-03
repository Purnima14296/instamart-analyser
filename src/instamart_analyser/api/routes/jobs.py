"""Job management routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from instamart_analyser.api.deps import get_current_user, require_role
from instamart_analyser.api.schemas.models import TokenUser
from instamart_analyser.api.services.jobs import JOB_COMMANDS, JobService

router = APIRouter(tags=["jobs"])
service = JobService()


@router.get("/api/jobs")
def list_jobs(user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    jobs = service.list_jobs()
    active = [j for j in jobs if j["status"] in {"queued", "running"}]
    return {
        "count": len(jobs),
        "active_count": len(active),
        "active_job": active[0] if active else None,
        "jobs": jobs,
        "available_job_types": sorted(JOB_COMMANDS.keys()),
    }


@router.get("/api/jobs/{job_id}")
def get_job(job_id: str, user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return service.get_job(job_id)


@router.post("/api/jobs/recover-stale")
def recover_stale(user: TokenUser = Depends(require_role("admin"))) -> dict:
    recovered = service.recover_stale_jobs()
    return {"recovered": recovered, "triggered_by": user.token_name}


def _start(job_type: str, user: TokenUser) -> dict:
    return service.start_job(job_type, created_by=user.token_name)


@router.post("/api/jobs/enrich")
def start_enrich(user: TokenUser = Depends(require_role("admin"))) -> dict:
    return _start("enrich", user)


@router.post("/api/jobs/phase3")
def start_phase3(user: TokenUser = Depends(require_role("admin"))) -> dict:
    return _start("phase3", user)


@router.post("/api/jobs/phase4")
def start_phase4(user: TokenUser = Depends(require_role("admin"))) -> dict:
    return _start("phase4", user)


@router.post("/api/jobs/phase5")
def start_phase5(user: TokenUser = Depends(require_role("admin"))) -> dict:
    return _start("phase5", user)


@router.post("/api/jobs/ingest_play")
def start_ingest_play(user: TokenUser = Depends(require_role("admin"))) -> dict:
    return _start("ingest_play", user)


@router.post("/api/jobs/ingest_appstore")
def start_ingest_appstore(user: TokenUser = Depends(require_role("admin"))) -> dict:
    return _start("ingest_appstore", user)


@router.post("/api/jobs/ingest_reddit_selenium")
def start_ingest_reddit(user: TokenUser = Depends(require_role("admin"))) -> dict:
    return _start("ingest_reddit_selenium", user)


@router.post("/api/jobs/ingest_all")
def start_ingest_all(user: TokenUser = Depends(require_role("admin"))) -> dict:
    return _start("ingest_all", user)


@router.post("/api/jobs/analysis_cascade")
def start_analysis_cascade(user: TokenUser = Depends(require_role("admin"))) -> dict:
    return _start("analysis_cascade", user)
