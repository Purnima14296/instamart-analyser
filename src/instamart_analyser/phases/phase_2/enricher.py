"""Enrich normalized reviews with Groq taxonomy labels."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import Draft202012Validator

from instamart_analyser.common.config import (
    ENRICHMENT_CHECKPOINT_INTERVAL,
    PHASE_2_DATA,
    SCHEMAS_DIR,
)
from instamart_analyser.common.models import utc_now_iso
from instamart_analyser.phases.phase_1.storage import NormalizedStore
from instamart_analyser.phases.phase_2.cohort import load_cohort
from instamart_analyser.phases.phase_2.groq_client import GroqClient, GroqRateLimitError
from instamart_analyser.phases.phase_2.prompts import PROMPT_VERSION
from instamart_analyser.phases.phase_2.storage import EnrichedStore, UsageTracker
from instamart_analyser.taxonomy import load_taxonomy

logger = logging.getLogger(__name__)


def load_enriched_schema() -> dict[str, Any]:
    with (SCHEMAS_DIR / "enriched-feedback.schema.json").open(encoding="utf-8") as f:
        return json.load(f)


class Enricher:
    """Runs rate-limited Groq enrichment with per-record persistence."""

    def __init__(
        self,
        *,
        groq_client: GroqClient | None = None,
        enriched_store: EnrichedStore | None = None,
        normalized_store: NormalizedStore | None = None,
        dry_run: bool = False,
    ) -> None:
        self.groq = groq_client or GroqClient(dry_run=dry_run)
        self.store = enriched_store or EnrichedStore()
        self.normalized = normalized_store or NormalizedStore()
        self.taxonomy = load_taxonomy()
        self.schema = load_enriched_schema()
        self.validator = Draft202012Validator(self.schema)
        self.dry_run = dry_run

    def _sanitize_labels(self, parsed: dict[str, Any]) -> dict[str, Any]:
        """Coerce LLM output into taxonomy-safe fields before schema validation."""
        single_fields = {
            "shopping_mission": "shopping_missions",
            "sentiment": "sentiments",
            "user_segment_hypothesis": "user_segments",
            "experimentation_likelihood": "experimentation_likelihood",
        }
        list_fields = {
            "categories_mentioned": "categories",
            "adjacent_category_opportunity": "categories",
            "barriers": "barriers",
            "triggers": "triggers",
            "discovery_channels": "discovery_channels",
            "discovery_trigger": "discovery_triggers",
            "friction_types": "friction_types",
            "trust_concerns": "trust_concerns",
            "price_concerns": "price_concerns",
            "assortment_concerns": "assortment_concerns",
            "information_gaps": "information_gaps",
            "category_exploration_barrier": "category_exploration_barriers",
            "required_trust_signal": "required_trust_signals",
        }
        allowed_keys = {
            *single_fields,
            *list_fields,
            *self.taxonomy.signal_flags,
            "occasion_context",
            "confidence_scores",
        }
        cleaned: dict[str, Any] = {k: v for k, v in parsed.items() if k in allowed_keys and v is not None}

        for field, dimension in single_fields.items():
            value = cleaned.get(field)
            if value is None:
                continue
            if not self.taxonomy.is_valid_label(dimension, value):
                cleaned[field] = "other" if self.taxonomy.is_valid_label(dimension, "other") else None

        for field, dimension in list_fields.items():
            value = cleaned.get(field, [])
            if isinstance(value, str):
                value = [value] if value else []
            if not isinstance(value, list):
                value = []
            allowed = set(self.taxonomy.dimensions.get(dimension, []))
            sanitized: list[str] = []
            for item in value:
                if not isinstance(item, str):
                    continue
                if item in allowed:
                    sanitized.append(item)
                elif "other" in allowed and "other" not in sanitized:
                    sanitized.append("other")
            cleaned[field] = sanitized

        if not cleaned.get("discovery_trigger"):
            fallback_channels = cleaned.get("discovery_channels", [])
            trigger_map = {
                "search": "search",
                "reorder_previous": "previous_orders",
                "homepage_browse": "homepage_category_browsing",
                "recommendation_engine": "recommendation",
                "promotional_banner": "offers",
                "external_referral": "external_influence",
            }
            inferred = [trigger_map[ch] for ch in fallback_channels if ch in trigger_map]
            if inferred:
                cleaned["discovery_trigger"] = list(dict.fromkeys(inferred))

        if not cleaned.get("category_exploration_barrier"):
            inferred_barriers: list[str] = []
            for barrier in cleaned.get("barriers", []):
                inferred_map = {
                    "trust_quality": "lack_of_trust",
                    "information_gap": "lack_of_information",
                    "price_sensitivity": "price_uncertainty",
                    "habit_lock_in": "habit_lock_in",
                    "assortment_gap": "unavailable_products",
                    "poor_discovery": "poor_discovery",
                }
                mapped = inferred_map.get(barrier)
                if mapped and mapped not in inferred_barriers:
                    inferred_barriers.append(mapped)
            if inferred_barriers:
                cleaned["category_exploration_barrier"] = inferred_barriers

        if "experimentation_likelihood" not in cleaned:
            if cleaned.get("experimentation_signal") or cleaned.get("shopping_mission") in {"exploration", "browse_discover"}:
                cleaned["experimentation_likelihood"] = "high"
            elif cleaned.get("category_exploration_barrier") or cleaned.get("habit_signal"):
                cleaned["experimentation_likelihood"] = "low"
            else:
                cleaned["experimentation_likelihood"] = "medium"

        if not cleaned.get("required_trust_signal"):
            inferred_signals: list[str] = []
            if cleaned.get("trust_concerns") or "lack_of_trust" in cleaned.get("category_exploration_barrier", []):
                inferred_signals.extend(["reviews", "ratings", "guarantees"])
            if "lack_of_information" in cleaned.get("category_exploration_barrier", []):
                inferred_signals.append("comparisons")
            if cleaned.get("price_concerns"):
                inferred_signals.append("recommendations")
            if inferred_signals:
                cleaned["required_trust_signal"] = list(dict.fromkeys(inferred_signals))

        for flag in self.taxonomy.signal_flags:
            if flag in cleaned:
                cleaned[flag] = bool(cleaned[flag])

        if isinstance(cleaned.get("occasion_context"), str) and not cleaned["occasion_context"].strip():
            cleaned.pop("occasion_context", None)

        scores = cleaned.get("confidence_scores")
        if not isinstance(scores, dict):
            cleaned["confidence_scores"] = {
                "overall": 0.5,
                "barriers": 0.5,
                "shopping_mission": 0.5,
                "sentiment": 0.5,
                "user_segment": 0.5,
            }
        else:
            cleaned["confidence_scores"] = {
                key: max(0.0, min(1.0, float(scores.get(key, 0.5))))
                for key in ("overall", "barriers", "shopping_mission", "sentiment", "user_segment")
            }

        return cleaned

    def parse_and_validate(
        self,
        record: dict[str, Any],
        parsed: dict[str, Any],
        *,
        model: str,
    ) -> tuple[dict[str, Any] | None, list[str]]:
        errors: list[str] = []
        sanitized = self._sanitize_labels(parsed)
        enrichment = {
            "record_id": record["record_id"],
            "source": record["source"],
            "body_text": record["body_text"],
            "taxonomy_version": self.taxonomy.version,
            "enriched_at": utc_now_iso(),
            "enrichment_model": model,
            **sanitized,
        }

        if enrichment.get("occasion_context") is None:
            enrichment.pop("occasion_context", None)

        if "confidence_scores" not in enrichment:
            enrichment["confidence_scores"] = {
                "overall": 0.5,
                "barriers": 0.5,
                "shopping_mission": 0.5,
                "sentiment": 0.5,
                "user_segment": 0.5,
            }

        schema_errors = [e.message for e in self.validator.iter_errors(enrichment)]
        taxonomy_errors = self.taxonomy.validate_enrichment(enrichment)
        errors.extend(schema_errors)
        errors.extend(taxonomy_errors)

        if errors:
            return None, errors
        return enrichment, []

    def _parse_batch_response(
        self,
        records: list[dict[str, Any]],
        raw_json: str,
        *,
        model: str,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            return {}, {record["record_id"]: f"Invalid JSON: {exc}" for record in records}

        if len(records) == 1 and "reviews" not in parsed:
            enrichment, errors = self.parse_and_validate(records[0], parsed, model=model)
            if errors:
                return {}, {records[0]["record_id"]: "; ".join(errors[:5])}
            return {records[0]["record_id"]: enrichment}, {}

        review_items = parsed.get("reviews")
        if not isinstance(review_items, list):
            return {}, {record["record_id"]: "Missing `reviews` array in batch response" for record in records}

        raw_by_id: dict[str, dict[str, Any]] = {}
        for item in review_items:
            if not isinstance(item, dict):
                continue
            record_id = item.get("record_id")
            labels = item.get("labels")
            if isinstance(record_id, str) and isinstance(labels, dict):
                raw_by_id[record_id] = labels

        enrichments: dict[str, dict[str, Any]] = {}
        errors_by_id: dict[str, str] = {}
        for record in records:
            labels = raw_by_id.get(record["record_id"])
            if labels is None:
                errors_by_id[record["record_id"]] = "Batch response missing record_id"
                continue
            enrichment, errors = self.parse_and_validate(record, labels, model=model)
            if errors:
                errors_by_id[record["record_id"]] = "; ".join(errors[:5])
            else:
                enrichments[record["record_id"]] = enrichment
        return enrichments, errors_by_id

    def enrich_record(self, record: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
        if self.store.is_enriched(record["record_id"]):
            existing = self.store.get_enriched_record(record["record_id"])
            return (existing["enrichment"] if existing else None), None

        try:
            result = self.groq.classify_review(record)
        except GroqRateLimitError as exc:
            raise
        except Exception as exc:
            self.store.upsert_enriched(
                record["record_id"],
                record["source"],
                record["body_text"],
                {},
                taxonomy_version=self.taxonomy.version,
                enrichment_model=self.groq.model,
                prompt_version=PROMPT_VERSION,
                review_status="needs_review",
                error_message=str(exc),
            )
            return None, str(exc)

        enrichments, errors_by_id = self._parse_batch_response([record], result.content, model=result.model)
        error_message = errors_by_id.get(record["record_id"])
        if error_message:
            self.store.upsert_enriched(
                record["record_id"],
                record["source"],
                record["body_text"],
                {},
                taxonomy_version=self.taxonomy.version,
                enrichment_model=result.model,
                prompt_version=PROMPT_VERSION,
                review_status="needs_review",
                error_message=error_message,
            )
            return None, error_message

        enrichment = enrichments[record["record_id"]]
        self.store.upsert_enriched(
            record["record_id"],
            record["source"],
            record["body_text"],
            enrichment,
            taxonomy_version=self.taxonomy.version,
            enrichment_model=result.model,
            prompt_version=PROMPT_VERSION,
            review_status="pending",
        )
        return enrichment, None

    def enrich_batch(self, records: list[dict[str, Any]]) -> tuple[int, int]:
        if not records:
            return 0, 0
        try:
            result = self.groq.classify_reviews(records)
        except GroqRateLimitError:
            raise
        except Exception as exc:
            for record in records:
                self.store.upsert_enriched(
                    record["record_id"],
                    record["source"],
                    record["body_text"],
                    {},
                    taxonomy_version=self.taxonomy.version,
                    enrichment_model=self.groq.model,
                    prompt_version=PROMPT_VERSION,
                    review_status="needs_review",
                    error_message=str(exc),
                )
            return 0, len(records)

        enrichments, errors_by_id = self._parse_batch_response(records, result.content, model=result.model)
        success = 0
        errors = 0
        for record in records:
            enrichment = enrichments.get(record["record_id"])
            if enrichment:
                self.store.upsert_enriched(
                    record["record_id"],
                    record["source"],
                    record["body_text"],
                    enrichment,
                    taxonomy_version=self.taxonomy.version,
                    enrichment_model=result.model,
                    prompt_version=PROMPT_VERSION,
                    review_status="pending",
                )
                success += 1
                continue
            self.store.upsert_enriched(
                record["record_id"],
                record["source"],
                record["body_text"],
                {},
                taxonomy_version=self.taxonomy.version,
                enrichment_model=result.model,
                prompt_version=PROMPT_VERSION,
                review_status="needs_review",
                error_message=errors_by_id.get(record["record_id"], "Unknown batch parsing error"),
            )
            errors += 1
        return success, errors

    def run_cohort(
        self,
        *,
        cohort_path: Path | None = None,
        limit: int | None = None,
        skip_enriched: bool = True,
        record_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        cohort = load_cohort(cohort_path)
        ids = record_ids or cohort["record_ids"]
        if limit is not None:
            ids = ids[:limit]

        run_id = f"run_{utc_now_iso().replace(':', '').replace('+00:00', 'Z')}_{uuid.uuid4().hex[:8]}"
        self.store.start_run(
            run_id,
            prompt_version=PROMPT_VERSION,
            model=self.groq.model if not self.dry_run else "dry-run",
            cohort_size=len(ids),
        )

        processed = 0
        success = 0
        errors = 0
        stopped_reason: str | None = None
        last_record_id: str | None = None

        pending_records: list[dict[str, Any]] = []
        for record_id in ids:
            if skip_enriched and self.store.is_enriched(record_id):
                continue
            row = self.normalized.get_record(record_id)
            if not row:
                logger.warning("Record %s not in normalized store, skipping", record_id)
                continue
            pending_records.append(
                {
                    "record_id": row["record_id"],
                    "source": row["source"],
                    "body_text": row["body_text"],
                    "rating": row.get("rating"),
                    "title": row.get("title"),
                }
            )

        batch_size = max(1, self.groq.batch_size)
        for start in range(0, len(pending_records), batch_size):
            batch = pending_records[start : start + batch_size]
            try:
                batch_success, batch_errors = self.enrich_batch(batch)
            except GroqRateLimitError as exc:
                stopped_reason = str(exc)
                logger.info("Stopping enrichment: %s", stopped_reason)
                break

            processed += len(batch)
            success += batch_success
            errors += batch_errors
            last_record_id = batch[-1]["record_id"]

            if processed % ENRICHMENT_CHECKPOINT_INTERVAL == 0 or processed == len(pending_records):
                self.store.update_run(
                    run_id,
                    processed_count=processed,
                    success_count=success,
                    error_count=errors,
                    last_record_id=last_record_id,
                )
                logger.info(
                    "Checkpoint: %d processed, %d success, %d errors",
                    processed,
                    success,
                    errors,
                )

        status = "stopped" if stopped_reason else "completed"
        self.store.update_run(
            run_id,
            processed_count=processed,
            success_count=success,
            error_count=errors,
            last_record_id=last_record_id,
            status=status,
            notes=stopped_reason,
        )

        return {
            "run_id": run_id,
            "status": status,
            "processed": processed,
            "success": success,
            "errors": errors,
            "stopped_reason": stopped_reason,
            "usage": self.groq.usage_summary(),
            "total_enriched": self.store.count_enriched(),
        }
