"""Overview, research summary, and enrichment status routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from instamart_analyser.api.deps import get_current_user
from instamart_analyser.api.schemas.models import TokenUser
from instamart_analyser.api.services.artifacts import ArtifactService
from instamart_analyser.api.services.research import ResearchSummaryService

router = APIRouter(tags=["overview"])
service = ArtifactService()
research = ResearchSummaryService(service)


@router.get("/api/overview")
def overview(user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return service.get_overview()


@router.get("/api/research/summary")
def research_summary(user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return research.get_summary()


@router.get("/api/enrichment/status")
def enrichment_status(user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return service.enrichment_status()


@router.get("/api/system/limitations")
def limitations(user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return service.known_limitations()
