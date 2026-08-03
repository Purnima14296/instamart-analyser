"""FastAPI application entrypoint for Phase 6A."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from instamart_analyser.api.routes import (
    explore,
    feedback,
    health,
    insights,
    jobs,
    opportunities,
    overview,
)
from instamart_analyser.common.config import API_CORS_ORIGIN_REGEX, API_CORS_ORIGINS

app = FastAPI(
    title="Instamart Analyser API",
    description=(
        "Phase 6 backend for the Instamart category-discovery agent. "
        "Serves Phase 2–5 artifacts, review actions, feedback, and pipeline jobs."
    ),
    version="0.6.6",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=API_CORS_ORIGINS,
    allow_origin_regex=API_CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(overview.router)
app.include_router(explore.router)
app.include_router(insights.router)
app.include_router(opportunities.router)
app.include_router(jobs.router)
app.include_router(feedback.router)


@app.get("/")
def root() -> dict:
    return {
        "service": "instamart-analyser-api",
        "phase": "6C",
        "docs": "/docs",
        "health": "/api/health",
    }
