"""Versioned Groq prompts for Phase 2 enrichment."""

from __future__ import annotations

import json
from typing import Any

from instamart_analyser.common.config import ENRICHMENT_BODY_WORD_CAP
from instamart_analyser.taxonomy import load_taxonomy

PROMPT_VERSION = "enrichment-v1.0.0"


def _compact_taxonomy_enums() -> dict[str, list[str]]:
    tax = load_taxonomy()
    return {
        "categories": tax.dimensions["categories"],
        "shopping_missions": tax.dimensions["shopping_missions"],
        "barriers": tax.dimensions["barriers"],
        "triggers": tax.dimensions["triggers"],
        "discovery_channels": tax.dimensions["discovery_channels"],
        "friction_types": tax.dimensions["friction_types"],
        "sentiments": tax.dimensions["sentiments"],
        "trust_concerns": tax.dimensions["trust_concerns"],
        "price_concerns": tax.dimensions["price_concerns"],
        "assortment_concerns": tax.dimensions["assortment_concerns"],
        "information_gaps": tax.dimensions["information_gaps"],
        "discovery_triggers": tax.dimensions["discovery_triggers"],
        "category_exploration_barriers": tax.dimensions["category_exploration_barriers"],
        "experimentation_likelihood": tax.dimensions["experimentation_likelihood"],
        "required_trust_signals": tax.dimensions["required_trust_signals"],
        "user_segments": tax.dimensions["user_segments"],
        "signal_flags": tax.signal_flags,
    }


def cap_review_body(text: str, max_words: int = ENRICHMENT_BODY_WORD_CAP) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + " …"


def build_system_prompt() -> str:
    enums = _compact_taxonomy_enums()
    return (
        "You classify Swiggy Instamart user feedback for category-expansion research. "
        "Return ONLY valid JSON. Use enum values exactly as listed. "
        "Use empty arrays [] when not applicable. "
        "Focus on discovery barriers and shopping missions, not only delivery complaints. "
        "Each review must be classified independently with no cross-review reasoning. "
        "Never put barrier labels into trust_concerns/assortment_concerns/price_concerns. "
        "Use only the enums for each field.\n"
        f"ENUMS: {json.dumps(enums, separators=(',', ':'))}"
    )


def build_user_message(record: dict[str, Any]) -> str:
    body = cap_review_body(record["body_text"])
    parts = [
        f"record_id: {record['record_id']}",
        f"source: {record.get('source', 'unknown')}",
        f"rating: {record.get('rating', 'null')}",
        f"review: {body}",
    ]
    return "\n".join(parts)


def _response_shape_instruction() -> str:
    return (
        "For each review return these JSON fields: shopping_mission, sentiment, barriers, "
        "triggers, discovery_channels, discovery_trigger, friction_types, categories_mentioned, "
        "adjacent_category_opportunity, trust_concerns, price_concerns, "
        "assortment_concerns, information_gaps, category_exploration_barrier, "
        "experimentation_likelihood, required_trust_signal, user_segment_hypothesis, "
        "habit_signal, experimentation_signal, urgency_context, convenience_signal, "
        "occasion_context (string or null), confidence_scores "
        "(object with overall, barriers, shopping_mission, sentiment, user_segment as 0-1)."
    )


def build_messages(record: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": build_system_prompt()},
        {
            "role": "user",
            "content": (
                build_user_message(record)
                + "\n\n"
                + _response_shape_instruction()
            ),
        },
    ]


def build_batch_messages(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    review_blocks = [build_user_message(record) for record in records]
    joined = "\n\n---\n\n".join(review_blocks)
    user_content = (
        "Classify each review independently and return ONE JSON object with this shape:\n"
        '{"reviews":[{"record_id":"<record_id>","labels":{...}}]}\n\n'
        "Requirements:\n"
        "- include every input `record_id` exactly once\n"
        "- preserve input/output alignment using `record_id`\n"
        "- do not omit records\n"
        "- do not include extra top-level keys\n\n"
        f"{_response_shape_instruction()}\n\n"
        f"REVIEWS:\n{joined}"
    )
    return [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": user_content},
    ]
