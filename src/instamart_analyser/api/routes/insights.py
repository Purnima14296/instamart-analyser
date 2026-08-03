"""Insights and themes routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from instamart_analyser.api.deps import get_current_user, require_role
from instamart_analyser.api.schemas.models import InsightStatusUpdate, TokenUser
from instamart_analyser.api.services.artifacts import ArtifactService

router = APIRouter(tags=["insights"])
service = ArtifactService()


@router.get("/api/insights")
def list_insights(
    confidence: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    segment: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: TokenUser = Depends(get_current_user),
) -> dict:
    _ = user
    return service.list_insights(
        confidence=confidence,
        status_filter=status_filter,
        segment=segment,
        limit=limit,
    )


@router.get("/api/insights/{insight_id}")
def get_insight(insight_id: str, user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return service.get_insight(insight_id)


@router.patch("/api/insights/{insight_id}/status")
def update_insight_status(
    insight_id: str,
    body: InsightStatusUpdate,
    user: TokenUser = Depends(require_role("reviewer")),
) -> dict:
    return service.update_insight_status(
        insight_id,
        status_value=body.status,
        notes=body.notes,
        reviewed_by=user.token_name,
    )


@router.get("/api/themes")
def get_themes(user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return service.get_themes()
