"""Pydantic models for the Phase 6A API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


RoleName = Literal["viewer", "reviewer", "admin"]
InsightStatus = Literal["draft", "approved", "rejected", "hypothesis"]
JobType = Literal["enrich", "phase3", "phase4", "phase5"]
JobStatus = Literal["queued", "running", "completed", "failed"]


class InsightStatusUpdate(BaseModel):
    status: InsightStatus
    notes: str | None = None


class FeedbackCreate(BaseModel):
    reviewer: str = Field(min_length=1)
    role: Literal["product", "research", "growth", "other"] = "other"
    overall_usefulness: Literal["high", "medium", "low"] = "medium"
    trust_in_outputs: Literal["high", "medium", "low"] = "medium"
    would_use_for_experiment_planning: bool = True
    comments: list[str] = Field(default_factory=list)
    defects: list[dict[str, Any]] = Field(default_factory=list)


class JobCreateResponse(BaseModel):
    job_id: str
    job_type: JobType
    status: JobStatus
    message: str


class TokenUser(BaseModel):
    role: RoleName
    token_name: str
