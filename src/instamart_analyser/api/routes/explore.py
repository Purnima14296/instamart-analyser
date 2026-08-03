"""Research explorer routes: sources, reviews, challenges, causes, needs, journey."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from instamart_analyser.api.deps import get_current_user
from instamart_analyser.api.schemas.models import TokenUser
from instamart_analyser.api.services.explorer import ExplorerService

router = APIRouter(tags=["explore"])
service = ExplorerService()


@router.get("/api/explore/sources")
def sources(user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return service.sources()


@router.get("/api/explore/reviews")
def reviews(
    q: str | None = None,
    source: str | None = None,
    sentiment: str | None = None,
    segment: str | None = None,
    mission: str | None = None,
    barrier: str | None = None,
    enriched_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: TokenUser = Depends(get_current_user),
) -> dict:
    _ = user
    return service.reviews(
        query=q,
        source=source,
        sentiment=sentiment,
        segment=segment,
        mission=mission,
        barrier=barrier,
        enriched_only=enriched_only,
        limit=limit,
        offset=offset,
    )


@router.get("/api/explore/discovery-challenges")
def discovery_challenges(user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return service.discovery_challenges()


@router.get("/api/explore/segments")
def segments(user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return service.segments()


@router.get("/api/explore/root-causes")
def root_causes(user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return service.root_causes()


@router.get("/api/explore/unmet-needs")
def unmet_needs(user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return service.unmet_needs()


@router.get("/api/explore/journey")
def journey(user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return service.journey()


@router.get("/api/explore/validation")
def validation(user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return service.validation()
