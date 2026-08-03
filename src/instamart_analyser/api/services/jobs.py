"""Background job runner that reuses Phase 1–5 pipeline modules."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from instamart_analyser.api.services.artifacts import ArtifactService
from instamart_analyser.api.store import ApiStore
from instamart_analyser.common.config import PROJECT_ROOT
from instamart_analyser.common.models import utc_now_iso

logger = logging.getLogger(__name__)

PY = sys.executable

# Each job type maps to one or more sequential CLI commands.
JOB_COMMANDS: dict[str, list[list[str]]] = {
    "enrich": [[PY, "-m", "instamart_analyser.phases.phase_2.pipeline", "enrich"]],
    "phase3": [
        [
            PY,
            "-m",
            "instamart_analyser.phases.phase_3.pipeline",
            "run",
            "--dry-run",
            "--limit",
            "8",
        ]
    ],
    "phase4": [[PY, "-m", "instamart_analyser.phases.phase_4.pipeline", "run"]],
    "phase5": [[PY, "-m", "instamart_analyser.phases.phase_5.pipeline", "run"]],
    "ingest_play": [
        [
            PY,
            "-m",
            "instamart_analyser.phases.phase_1.pipeline",
            "run",
            "--sources",
            "play_store",
            "--no-seed",
            "--max-per-source",
            "300",
        ]
    ],
    "ingest_appstore": [
        [
            PY,
            "-m",
            "instamart_analyser.phases.phase_1.pipeline",
            "run",
            "--sources",
            "app_store",
            "--no-seed",
            "--max-per-source",
            "200",
        ]
    ],
    "ingest_reddit_selenium": [
        [
            PY,
            "-m",
            "instamart_analyser.phases.phase_1.scrape_reddit_selenium",
            "--full",
            "--ingest",
        ]
    ],
    "ingest_all": [
        [
            PY,
            "-m",
            "instamart_analyser.phases.phase_1.pipeline",
            "run",
            "--sources",
            "play_store",
            "app_store",
            "--no-seed",
            "--max-per-source",
            "300",
        ],
        [
            PY,
            "-m",
            "instamart_analyser.phases.phase_1.scrape_reddit_selenium",
            "--full",
            "--ingest",
        ],
    ],
    "analysis_cascade": [
        [PY, "-m", "instamart_analyser.phases.phase_2.pipeline", "enrich"],
        [
            PY,
            "-m",
            "instamart_analyser.phases.phase_3.pipeline",
            "run",
            "--dry-run",
            "--limit",
            "10",
        ],
        [PY, "-m", "instamart_analyser.phases.phase_4.pipeline", "run"],
        [PY, "-m", "instamart_analyser.phases.phase_5.pipeline", "run"],
    ],
}

STALE_JOB_MINUTES = 90
ENRICH_JOB_TYPES = {"enrich", "analysis_cascade"}


def classify_failure(text: str) -> str:
    lowered = (text or "").lower()
    if "429" in lowered or "too many requests" in lowered:
        return "rate_limit"
    if "daily" in lowered and ("cap" in lowered or "quota" in lowered or "budget" in lowered):
        return "quota_exhausted"
    if "groq_api_key" in lowered or "api key" in lowered:
        return "missing_api_key"
    if "timeout" in lowered:
        return "timeout"
    return "pipeline_error"


class JobService:
    def __init__(self, store: ApiStore | None = None) -> None:
        self.store = store or ApiStore()
        self.artifacts = ArtifactService(self.store)
        self._lock = threading.Lock()

    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        self.recover_stale_jobs()
        jobs = self.store.list_jobs(limit=limit)
        for job in jobs:
            job["failure_class"] = None
            if job.get("status") == "failed":
                job["failure_class"] = classify_failure(
                    f"{job.get('error') or ''} {job.get('message') or ''}"
                )
                job["recovery_hint"] = self._recovery_hint(job["failure_class"])
        return jobs

    def get_job(self, job_id: str) -> dict[str, Any]:
        self.recover_stale_jobs()
        job = self.store.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        if job.get("status") == "failed":
            job["failure_class"] = classify_failure(
                f"{job.get('error') or ''} {job.get('message') or ''}"
            )
            job["recovery_hint"] = self._recovery_hint(job["failure_class"])
        return job

    def start_job(self, job_type: str, created_by: str) -> dict[str, Any]:
        if job_type not in JOB_COMMANDS:
            raise HTTPException(status_code=400, detail=f"Unknown job type: {job_type}")

        self.recover_stale_jobs()

        if job_type in ENRICH_JOB_TYPES:
            enrichment = self.artifacts.enrichment_status()
            if not enrichment["groq_key_configured"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="GROQ_API_KEY is not configured on the server.",
                )
            # Cascade may still refresh Phase 3–5 even if enrich is blocked;
            # only hard-block pure enrich when quota is exhausted.
            if job_type == "enrich" and enrichment["quota_blocked"]:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=enrichment["quota_message"],
                )
            if job_type == "enrich" and enrichment["remaining_to_enrich"] <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="All cohort reviews are already enriched.",
                )

        with self._lock:
            if self.store.has_active_job():
                active = [
                    j for j in self.store.list_jobs(20) if j["status"] in {"queued", "running"}
                ]
                if active:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Another job is already active: "
                            f"{active[0]['job_id']} ({active[0]['job_type']}). "
                            "Wait for it to finish or recover stale jobs."
                        ),
                    )

            job = self.store.create_job(
                job_type=job_type,
                created_by=created_by,
                message=f"{job_type} queued",
            )

        thread = threading.Thread(
            target=self._run_job,
            args=(job["job_id"], job_type),
            daemon=True,
        )
        thread.start()
        return {
            "job_id": job["job_id"],
            "job_type": job_type,
            "status": "queued",
            "message": f"Started {job_type} job",
        }

    def recover_stale_jobs(self) -> int:
        """Mark long-running jobs as failed so the queue can recover."""
        recovered = 0
        now = datetime.now(timezone.utc)
        for job in self.store.list_jobs(50):
            if job["status"] not in {"queued", "running"}:
                continue
            started = job.get("started_at") or job.get("created_at")
            if not started:
                continue
            try:
                started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
            except ValueError:
                continue
            age_min = (now - started_dt).total_seconds() / 60
            if age_min < STALE_JOB_MINUTES:
                continue
            self.store.update_job(
                job["job_id"],
                status="failed",
                message=f"{job['job_type']} marked stale after {STALE_JOB_MINUTES} minutes",
                error="Stale job recovered by Phase 6C hardening",
                progress={"stage": "stale_recovered", "recovered_at": utc_now_iso()},
                completed=True,
            )
            recovered += 1
        return recovered

    def _run_job(self, job_id: str, job_type: str) -> None:
        self.store.update_job(
            job_id,
            status="running",
            message=f"{job_type} running",
            started=True,
            progress={"stage": "started", "step": 0},
        )
        commands = JOB_COMMANDS[job_type]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []

        try:
            for step_idx, cmd in enumerate(commands, start=1):
                step_name = " ".join(cmd[-4:])
                self.store.update_job(
                    job_id,
                    status="running",
                    message=f"{job_type} step {step_idx}/{len(commands)}",
                    progress={
                        "stage": "running",
                        "step": step_idx,
                        "steps": len(commands),
                        "command_tail": step_name,
                    },
                )
                # Soft-skip enrich step inside cascade when quota is blocked.
                if (
                    job_type == "analysis_cascade"
                    and step_idx == 1
                    and self.artifacts.enrichment_status().get("quota_blocked")
                ):
                    stdout_parts.append("[skipped enrich: quota blocked]")
                    continue

                completed = subprocess.run(
                    cmd,
                    cwd=str(PROJECT_ROOT),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=60 * 90,
                    check=False,
                )
                stdout_tail = (completed.stdout or "")[-3000:]
                stderr_tail = (completed.stderr or "")[-3000:]
                stdout_parts.append(stdout_tail)
                stderr_parts.append(stderr_tail)
                combined = f"{stdout_tail}\n{stderr_tail}"
                failure_class = classify_failure(combined)

                # Enrichment often exits 0 after hitting daily cap; continue cascade.
                if (
                    "enrich" in cmd
                    and completed.returncode == 0
                    and (
                        "daily" in combined.lower()
                        and ("cap" in combined.lower() or "quota" in combined.lower())
                    )
                ):
                    if job_type == "enrich":
                        self.store.update_job(
                            job_id,
                            status="completed",
                            message="enrichment stopped at daily quota (partial progress saved)",
                            progress={
                                "stage": "quota_stop",
                                "returncode": 0,
                                "failure_class": "quota_exhausted",
                            },
                            result={
                                "stdout_tail": "\n".join(stdout_parts)[-4000:],
                                "stderr_tail": "\n".join(stderr_parts)[-4000:],
                                "failure_class": "quota_exhausted",
                                "recovery_hint": self._recovery_hint("quota_exhausted"),
                            },
                            completed=True,
                        )
                        return
                    continue

                if completed.returncode != 0:
                    # For cascade enrich failures due to quota/rate limit, continue.
                    if (
                        job_type == "analysis_cascade"
                        and step_idx == 1
                        and failure_class in {"rate_limit", "quota_exhausted"}
                    ):
                        continue
                    self.store.update_job(
                        job_id,
                        status="failed",
                        message=f"{job_type} failed at step {step_idx} ({failure_class})",
                        error=stderr_tail or stdout_tail or "Unknown error",
                        progress={
                            "stage": "failed",
                            "step": step_idx,
                            "returncode": completed.returncode,
                            "failure_class": failure_class,
                        },
                        result={
                            "stdout_tail": "\n".join(stdout_parts)[-4000:],
                            "stderr_tail": "\n".join(stderr_parts)[-4000:],
                            "failure_class": failure_class,
                            "recovery_hint": self._recovery_hint(failure_class),
                        },
                        completed=True,
                    )
                    return

            self.store.update_job(
                job_id,
                status="completed",
                message=f"{job_type} completed",
                progress={"stage": "completed", "steps": len(commands), "returncode": 0},
                result={
                    "stdout_tail": "\n".join(stdout_parts)[-4000:],
                    "stderr_tail": "\n".join(stderr_parts)[-4000:],
                },
                completed=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Job %s failed", job_id)
            failure_class = classify_failure(str(exc))
            self.store.update_job(
                job_id,
                status="failed",
                message=f"{job_type} crashed ({failure_class})",
                error=str(exc),
                progress={"stage": "crashed", "failure_class": failure_class},
                result={
                    "failure_class": failure_class,
                    "recovery_hint": self._recovery_hint(failure_class),
                },
                completed=True,
            )

    @staticmethod
    def _recovery_hint(failure_class: str) -> str:
        hints = {
            "rate_limit": "Wait a few minutes and retry. Groq returned HTTP 429.",
            "quota_exhausted": "Wait for daily quota reset, then resume enrichment.",
            "missing_api_key": "Set GROQ_API_KEY in the server .env and restart the API.",
            "timeout": "Retry the job. If it keeps timing out, reduce batch size.",
            "pipeline_error": "Inspect job error details, fix the cause, then retry.",
        }
        return hints.get(failure_class, "Inspect the job error and retry when ready.")
