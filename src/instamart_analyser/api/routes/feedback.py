"""Stakeholder feedback routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from instamart_analyser.api.deps import get_current_user, require_role
from instamart_analyser.api.schemas.models import FeedbackCreate, TokenUser
from instamart_analyser.api.services.feedback import FeedbackService

router = APIRouter(tags=["feedback"])
service = FeedbackService()


@router.get("/api/feedback")
def list_feedback(user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return service.list_feedback()


@router.get("/api/feedback/review-stats")
def review_stats(user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return service.review_stats()


@router.post("/api/feedback")
def create_feedback(
    body: FeedbackCreate,
    user: TokenUser = Depends(require_role("reviewer")),
) -> dict:
    payload = body.model_dump()
    return service.submit_feedback(payload, created_by=user.token_name)
