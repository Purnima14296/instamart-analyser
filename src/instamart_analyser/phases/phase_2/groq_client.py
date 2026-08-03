"""Rate-limited Groq API client for Phase 2 enrichment."""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

from instamart_analyser.common.config import (
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_BACKOFF_SECONDS,
    ENRICHMENT_BATCH_SIZE,
    GROQ_API_KEY,
    GROQ_DAILY_REQUEST_RESERVE,
    GROQ_DAILY_TOKEN_BUDGET,
    GROQ_ENRICHMENT_DAILY_CAP,
    GROQ_MAX_REQUESTS_PER_MINUTE,
    GROQ_MAX_TOKENS,
    GROQ_MODEL,
    GROQ_TEMPERATURE,
)
from instamart_analyser.phases.phase_2.prompts import build_batch_messages, build_messages
from instamart_analyser.phases.phase_2.storage.usage_tracker import UsageTracker

logger = logging.getLogger(__name__)


@dataclass
class GroqCallResult:
    content: str
    prompt_tokens: int
    completion_tokens: int
    model: str


class GroqRateLimitError(RuntimeError):
    """Raised when daily Groq quotas are exhausted."""


class GroqClient:
    """Groq chat client with RPM throttle and daily usage tracking."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        batch_size: int | None = None,
        max_requests_per_minute: int | None = None,
        enrichment_daily_cap: int | None = None,
        daily_token_budget: int | None = None,
        daily_request_reserve: int | None = None,
        usage_tracker: UsageTracker | None = None,
        dry_run: bool = False,
    ) -> None:
        self.api_key = api_key if api_key is not None else GROQ_API_KEY
        self.model = model or GROQ_MODEL
        self.batch_size = batch_size or ENRICHMENT_BATCH_SIZE
        self.max_rpm = max_requests_per_minute or GROQ_MAX_REQUESTS_PER_MINUTE
        self.enrichment_daily_cap = enrichment_daily_cap or GROQ_ENRICHMENT_DAILY_CAP
        self.daily_token_budget = daily_token_budget or GROQ_DAILY_TOKEN_BUDGET
        self.daily_request_cap = 1000 - (daily_request_reserve or GROQ_DAILY_REQUEST_RESERVE)
        self.usage = usage_tracker or UsageTracker()
        self.dry_run = dry_run
        self._request_times: deque[float] = deque()

        if not self.dry_run and not self.api_key:
            raise ValueError("GROQ_API_KEY is required (set in environment or pass api_key=)")

    def _throttle(self) -> None:
        now = time.monotonic()
        while self._request_times and now - self._request_times[0] >= 60:
            self._request_times.popleft()
        if len(self._request_times) >= self.max_rpm:
            sleep_for = 60 - (now - self._request_times[0]) + 0.05
            logger.info("RPM throttle: sleeping %.1fs", sleep_for)
            time.sleep(max(sleep_for, 0))
        self._request_times.append(time.monotonic())

    def _check_daily_limits(self, requested_enrichment_count: int = 1) -> None:
        ok, reason = self.usage.can_enrich(
            daily_request_cap=self.daily_request_cap,
            daily_token_budget=self.daily_token_budget,
            daily_enrichment_cap=self.enrichment_daily_cap,
            requested_enrichment_count=requested_enrichment_count,
        )
        if not ok:
            raise GroqRateLimitError(reason)

    def classify_review(self, record: dict[str, Any]) -> GroqCallResult:
        return self.classify_reviews([record])

    def classify_reviews(self, records: list[dict[str, Any]]) -> GroqCallResult:
        if not records:
            raise ValueError("At least one record is required")
        if not self.dry_run:
            self._check_daily_limits(requested_enrichment_count=len(records))
            self._throttle()

        if self.dry_run:
            content = self._dry_run_json(records)
            result = GroqCallResult(
                content=content,
                prompt_tokens=250 + (125 * len(records)),
                completion_tokens=120 * len(records),
                model="dry-run",
            )
            self.usage.record_call(
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                enrichment_count=len(records),
            )
            return result

        messages = build_batch_messages(records) if len(records) > 1 else build_messages(records[0])
        last_error: Exception | None = None

        for attempt in range(1, DEFAULT_RETRY_ATTEMPTS + 1):
            try:
                result = self._call_api(messages)
                self.usage.record_call(
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                    enrichment_count=len(records),
                )
                return result
            except Exception as exc:
                last_error = exc
                status = getattr(exc, "status_code", None)
                if status == 429 and attempt < DEFAULT_RETRY_ATTEMPTS:
                    sleep_for = DEFAULT_RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
                    logger.warning("Groq 429: retrying in %.1fs", sleep_for)
                    time.sleep(sleep_for)
                    continue
                raise

        raise RuntimeError("Groq call failed") from last_error

    def _call_api(self, messages: list[dict[str, str]]) -> GroqCallResult:
        from groq import Groq

        client = Groq(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=GROQ_MAX_TOKENS,
            temperature=GROQ_TEMPERATURE,
            response_format={"type": "json_object"},
        )
        choice = response.choices[0].message.content or "{}"
        usage = response.usage
        return GroqCallResult(
            content=choice,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            model=response.model or self.model,
        )

    @staticmethod
    def _dry_run_json(records: list[dict[str, Any]]) -> str:
        import json

        review_payloads = []
        for record in records:
            text = record.get("body_text", "").lower()
            barriers = []
            if any(w in text for w in ("delivery", "late", "delay")):
                barriers.append("past_bad_experience")
            if any(w in text for w in ("search", "find", "category", "browse")):
                barriers.append("poor_discovery")
            if not barriers:
                barriers = ["other"]
            labels = {
                "shopping_mission": "replenishment",
                "sentiment": "negative" if record.get("rating") == 1 else "neutral",
                "barriers": barriers,
                "triggers": [],
                "discovery_channels": [],
                "friction_types": ["delivery_experience"] if "delivery" in text else [],
                "categories_mentioned": [],
                "adjacent_category_opportunity": [],
                "trust_concerns": [],
                "price_concerns": [],
                "assortment_concerns": [],
                "information_gaps": [],
                "user_segment_hypothesis": "other",
                "habit_signal": "reorder" in text or "same" in text,
                "experimentation_signal": "discover" in text or "new category" in text,
                "urgency_context": "urgent" in text,
                "convenience_signal": False,
                "confidence_scores": {
                    "overall": 0.5,
                    "barriers": 0.5,
                    "shopping_mission": 0.5,
                    "sentiment": 0.5,
                    "user_segment": 0.5,
                },
            }
            if len(records) == 1:
                return json.dumps(labels)
            review_payloads.append({"record_id": record["record_id"], "labels": labels})
        return json.dumps({"reviews": review_payloads})

    def usage_summary(self) -> dict[str, Any]:
        usage = self.usage.get_daily_usage()
        return {
            "date": self.usage.today(),
            "requests": usage["request_count"],
            "tokens": usage["token_count"],
            "enrichment_calls": usage["enrichment_count"],
            "limits": {
                "max_rpm": self.max_rpm,
                "batch_size": self.batch_size,
                "enrichment_daily_cap": self.enrichment_daily_cap,
                "daily_token_budget": self.daily_token_budget,
                "daily_request_cap": self.daily_request_cap,
            },
        }
