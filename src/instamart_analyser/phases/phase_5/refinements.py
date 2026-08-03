"""Capture prompt, taxonomy, and threshold refinements for Phase 5."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from instamart_analyser.common.config import PHASE_5_DATA
from instamart_analyser.common.models import utc_now_iso

REFINEMENTS_PATH = PHASE_5_DATA / "refinements-log.json"


def build_refinements_log() -> dict[str, Any]:
    """Persist known refinements made during Phases 2–4 plus a backlog template."""
    payload = {
        "created_at": utc_now_iso(),
        "purpose": (
            "Track prompt, taxonomy, and threshold changes systematically so pilot "
            "improvements are auditable and rerunnable."
        ),
        "prompt_refinements": [
            {
                "id": "prompt_001",
                "phase": "phase_2",
                "change": "Switched from 1-review-per-call to micro-batches of 5–8 reviews.",
                "reason": "Reduce Groq request overhead under free-tier RPM/TPD limits.",
                "status": "incorporated",
            },
            {
                "id": "prompt_002",
                "phase": "phase_2",
                "change": "Added label sanitization when LLM puts barrier values in wrong fields.",
                "reason": "Schema validation failures were discarding otherwise usable enrichments.",
                "status": "incorporated",
            },
            {
                "id": "prompt_003",
                "phase": "phase_3",
                "change": "Balanced insight drafting across discovery, behaviour, opportunity, and operational buckets.",
                "reason": "Complaint volume alone overweighted operational pain and underweighted discovery.",
                "status": "incorporated",
            },
        ],
        "taxonomy_refinements": [
            {
                "id": "tax_001",
                "phase": "phase_3",
                "change": "Extended taxonomy to v1.1.0 with discovery_trigger, category_exploration_barrier, experimentation_likelihood, required_trust_signal.",
                "reason": "Category-discovery analysis needed fields beyond generic complaint barriers.",
                "status": "incorporated",
            },
            {
                "id": "tax_002",
                "phase": "phase_3",
                "change": "Added backward-compatible inference from older enrichment labels.",
                "reason": "Avoid re-burning Groq quota to re-label already enriched reviews.",
                "status": "incorporated",
            },
        ],
        "threshold_refinements": [
            {
                "id": "thr_001",
                "phase": "phase_2",
                "change": "Daily enrichment cap default 130 reviews; RPM throttle 10.",
                "reason": "Stay under Groq free-tier token and request budgets.",
                "status": "incorporated",
            },
            {
                "id": "thr_002",
                "phase": "phase_3",
                "change": "Minimum cluster size 3; low-volume themes marked lower confidence.",
                "reason": "Prevent overclaiming from thin evidence.",
                "status": "incorporated",
            },
            {
                "id": "thr_003",
                "phase": "phase_4",
                "change": "Priority score combines evidence, segment size, strategic importance, actionability, confidence.",
                "reason": "Make recommendation ranking explicit and reviewable.",
                "status": "incorporated",
            },
        ],
        "proposed_next_refinements": [
            {
                "id": "next_001",
                "change": "Fill and evaluate the Phase 2 gold set against Groq labels.",
                "reason": "Strengthen precision claims before operationalizing the agent.",
                "status": "proposed",
            },
            {
                "id": "next_002",
                "change": "Raise enrichment coverage above 50% of the cohort before publishing final discovery rankings.",
                "reason": "Current pilot is directional on a partial enriched sample.",
                "status": "proposed",
            },
            {
                "id": "next_003",
                "change": "Add eligibility rules for trust-based expansion experiments (e.g. recent clean order).",
                "reason": "Stakeholder feedback asked for clearer segment eligibility on primary metrics.",
                "status": "proposed",
            },
        ],
    }

    PHASE_5_DATA.mkdir(parents=True, exist_ok=True)
    with REFINEMENTS_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return payload
