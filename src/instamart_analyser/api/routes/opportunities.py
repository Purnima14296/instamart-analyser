"""Opportunities, hypotheses, measurement, and reports."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from instamart_analyser.api.deps import get_current_user
from instamart_analyser.api.schemas.models import TokenUser
from instamart_analyser.api.services.artifacts import ArtifactService

router = APIRouter(tags=["opportunities"])
service = ArtifactService()


@router.get("/api/opportunities")
def opportunities(user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return service.get_opportunities()


@router.get("/api/hypotheses")
def hypotheses(user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return service.get_hypotheses()


@router.get("/api/measurement")
def measurement(user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return service.get_measurement()


@router.get("/api/reports")
def list_reports(user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return {"reports": service.list_report_names()}


@router.get("/api/reports/{name}")
def get_report(name: str, user: TokenUser = Depends(get_current_user)) -> dict:
    _ = user
    return service.get_report(name)
