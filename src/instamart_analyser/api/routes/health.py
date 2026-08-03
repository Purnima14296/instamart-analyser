"""Health and identity endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from instamart_analyser.api.deps import get_current_user
from instamart_analyser.api.schemas.models import TokenUser
from instamart_analyser.common.models import utc_now_iso

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict:
    """Unauthenticated probe for Railway / load balancers."""
    return {"status": "ok"}


@router.get("/api/health")
def health(user: TokenUser = Depends(get_current_user)) -> dict:
    return {
        "status": "ok",
        "service": "instamart-analyser-api",
        "phase": "6C",
        "time": utc_now_iso(),
        "role": user.role,
    }


@router.get("/api/me")
def me(user: TokenUser = Depends(get_current_user)) -> dict:
    return {
        "role": user.role,
        "token_name": user.token_name,
        "permissions": {
            "can_view": True,
            "can_review": user.role in {"reviewer", "admin"},
            "can_run_jobs": user.role == "admin",
        },
    }
