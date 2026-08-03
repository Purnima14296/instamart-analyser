"""Taxonomy loading and label validation for Phase 0."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TAXONOMY_PATH = PROJECT_ROOT / "schemas" / "taxonomy-v1.json"


class Taxonomy:
    """Loads taxonomy v1 and validates label assignments."""

    def __init__(self, taxonomy_path: Path | None = None) -> None:
        path = taxonomy_path or TAXONOMY_PATH
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        self.version: str = data["version"]
        self.dimensions: dict[str, list[str]] = data["dimensions"]
        self.signal_flags: list[str] = data["signal_flags"]
        self.analysis_questions: list[dict[str, str]] = data["analysis_questions"]

    def is_valid_label(self, dimension: str, label: str) -> bool:
        allowed = self.dimensions.get(dimension, [])
        return label in allowed

    def validate_labels(self, dimension: str, labels: list[str]) -> list[str]:
        """Return list of invalid labels for a dimension."""
        allowed = set(self.dimensions.get(dimension, []))
        return [label for label in labels if label not in allowed]

    def validate_enrichment(self, enrichment: dict[str, Any]) -> list[str]:
        """Validate an enrichment dict against taxonomy. Returns error messages."""
        errors: list[str] = []

        single_fields = {
            "shopping_mission": "shopping_missions",
            "sentiment": "sentiments",
            "user_segment_hypothesis": "user_segments",
        }
        for field, dimension in single_fields.items():
            if field in enrichment and enrichment[field] is not None:
                if not self.is_valid_label(dimension, enrichment[field]):
                    errors.append(f"Invalid {field}: {enrichment[field]}")

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
        for field, dimension in list_fields.items():
            if field in enrichment:
                invalid = self.validate_labels(dimension, enrichment.get(field, []))
                for label in invalid:
                    errors.append(f"Invalid {field} label: {label}")

        if "experimentation_likelihood" in enrichment and enrichment["experimentation_likelihood"] is not None:
            if not self.is_valid_label("experimentation_likelihood", enrichment["experimentation_likelihood"]):
                errors.append(
                    f"Invalid experimentation_likelihood: {enrichment['experimentation_likelihood']}"
                )

        for flag in self.signal_flags:
            if flag in enrichment and not isinstance(enrichment[flag], bool):
                errors.append(f"{flag} must be a boolean, got {type(enrichment[flag])}")

        return errors


def load_taxonomy(taxonomy_path: Path | None = None) -> Taxonomy:
    return Taxonomy(taxonomy_path)
