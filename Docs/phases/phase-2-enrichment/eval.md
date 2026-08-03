## Phase 2 Evaluation

## Purpose

Validate that raw feedback is cleaned, normalized, deduplicated, and enriched with labels that are accurate enough for pattern detection.

## What To Test

- cleaning removes noise without losing meaning
- normalization produces a consistent schema across sources
- duplicate and near-duplicate detection is effective
- language detection and translation maintain usable meaning
- AI labels are accurate for sentiment, mission, barriers, triggers, and segment hypotheses
- confidence scores are stored and interpretable

## Validation Methods

- manually label a gold set of sample records and compare model outputs
- review false positives and false negatives by label type
- sample translated content for nuance loss
- compare dedupe output against hand-reviewed duplicate groups
- rerun the same data batch to confirm deterministic storage behavior

## Exit Criteria

- normalized schema is stable
- dedupe performance is acceptable on review samples
- core label quality reaches team-approved thresholds
- prompt versions and confidence fields are tracked
- reviewers agree the enriched data is usable for aggregation

## Suggested Acceptance Thresholds

- critical labels such as barrier type and mission should show strong reviewer agreement
- low-confidence classifications should be clearly separable for human review
- duplicate suppression should reduce repeated records without hiding distinct opinions

## Failure Signals

- labels drift significantly across similar records
- sentiment or barrier tags are frequently misread
- translated items lose important context
- confidence scores do not correlate with actual quality
