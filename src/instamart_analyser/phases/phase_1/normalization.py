"""Phase 1 review normalization: English-only, min word count, emoji removal."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from langdetect import LangDetectException, detect

from instamart_analyser.common.models import FeedbackRecord

MIN_WORD_COUNT = 5  # more than 4 words

RejectReason = Literal["too_short", "non_english", "empty_after_cleaning"]

# Unicode emoji and symbol ranges
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "]+",
    flags=re.UNICODE,
)

# Devanagari and other common non-Latin scripts in Indian reviews
_NON_LATIN_SCRIPT = re.compile(r"[\u0900-\u097F\u0B80-\u0BFF\u0C00-\u0C7F\u0980-\u09FF]")


@dataclass
class NormalizationOutcome:
    record: FeedbackRecord | None
    reason: RejectReason | None = None
    original_language: str | None = None


def remove_emojis(text: str) -> str:
    """Strip emoji characters from text."""
    return _EMOJI_PATTERN.sub("", text)


def clean_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def word_count(text: str) -> int:
    if not text.strip():
        return 0
    return len(text.split())


def detect_language(text: str) -> str | None:
    """Detect language code; returns None if detection fails."""
    sample = text.strip()
    if len(sample) < 10:
        return "en" if not _NON_LATIN_SCRIPT.search(sample) else None
    try:
        return detect(sample)
    except LangDetectException:
        return None


def is_english(text: str) -> bool:
    """Return True if review text is English."""
    if _NON_LATIN_SCRIPT.search(text):
        return False
    lang = detect_language(text)
    if lang is None:
        # Short ASCII-heavy Instamart reviews default to English
        ascii_ratio = sum(1 for c in text if ord(c) < 128) / max(len(text), 1)
        return ascii_ratio > 0.85
    return lang == "en"


def normalize_text(text: str) -> str:
    """Remove emojis and normalize whitespace."""
    return clean_whitespace(remove_emojis(text))


def normalize_record(record: FeedbackRecord) -> NormalizationOutcome:
    """
    Normalize a single review.

    Rules:
    - Remove emojis
    - Keep only English
    - Require more than 4 words (>4, i.e. at least 5)
    """
    raw_body = record.body_text or ""
    raw_title = record.title or ""
    combined_for_lang = f"{raw_title}\n{raw_body}".strip()

    cleaned_body = normalize_text(raw_body)
    if not cleaned_body:
        return NormalizationOutcome(record=None, reason="empty_after_cleaning")

    if word_count(cleaned_body) <= 4:
        return NormalizationOutcome(record=None, reason="too_short")

    if not is_english(combined_for_lang):
        return NormalizationOutcome(
            record=None,
            reason="non_english",
            original_language=detect_language(combined_for_lang),
        )

    cleaned_title = normalize_text(raw_title) if raw_title else None

    normalized = FeedbackRecord(
        record_id=record.record_id,
        source=record.source,
        source_record_id=record.source_record_id,
        body_text=cleaned_body,
        language="en",
        collection_batch_id=record.collection_batch_id,
        pipeline_stage="normalized",
        collected_at=record.collected_at,
        url=record.url,
        author=record.author,
        timestamp=record.timestamp,
        title=cleaned_title,
        rating=record.rating,
        metadata={
            **record.metadata,
            "normalization": {
                "original_language": record.language,
                "word_count": word_count(cleaned_body),
                "emoji_removed": raw_body != cleaned_body,
            },
        },
    )
    return NormalizationOutcome(record=normalized, original_language=record.language)


def normalize_records(
    records: list[FeedbackRecord],
) -> tuple[list[FeedbackRecord], dict[str, int]]:
    """Normalize a batch; return kept records and rejection counts."""
    kept: list[FeedbackRecord] = []
    rejections: dict[str, int] = {}

    for record in records:
        outcome = normalize_record(record)
        if outcome.record:
            kept.append(outcome.record)
        elif outcome.reason:
            rejections[outcome.reason] = rejections.get(outcome.reason, 0) + 1

    return kept, rejections
