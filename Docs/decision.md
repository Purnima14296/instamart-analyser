## Decision Log

This file records important technical and business decisions for the Swiggy Instamart category-discovery AI agent.

## D-001: Focus The First Version On Discovery, Not Personalization

Status: accepted

Decision:
The first version of the system will focus on analyzing user feedback and generating insights. It will not directly power user-facing recommendations in the consumer app.

Reason:
The current business need is to understand the causes of low category exploration before shipping interventions.

Implication:
The system is optimized for research quality, traceability, and hypothesis generation rather than low-latency inference.

## D-002: Use A Multi-Stage Pipeline Instead Of A Single End-To-End Prompt

Status: accepted

Decision:
Implement collection, normalization, enrichment, aggregation, and insight generation as separate stages.

Reason:
This improves observability, rerun capability, error isolation, and human review.

Implication:
The architecture is more maintainable and easier to validate, though slightly slower to build than a one-shot prototype.

## D-003: Preserve Raw Data For Auditability

Status: accepted

Decision:
Store source records in raw form before any transformation.

Reason:
Prompt logic, taxonomies, and schemas will change. Preserving raw data allows backfills and retrospective validation.

Implication:
Storage needs increase, but reproducibility and trust improve significantly.

## D-004: Favor Traceable Insights Over Pure Summaries

Status: accepted

Decision:
Every insight must link back to supporting records, snippets, source types, and confidence.

Reason:
Growth and product decisions need evidence, not just polished summaries.

Implication:
The output format will be more structured and reviewer-friendly.

## D-005: Start With A Human-In-The-Loop Review Process

Status: accepted

Decision:
High-impact insights will require human review before being treated as final.

Reason:
LLM interpretation can be directionally correct but still misleading in edge cases, especially with sarcasm, duplicates, or thin evidence.

Implication:
The pipeline remains slower than a fully automated system, but output quality is safer for decision-making.

## D-006: Use A Taxonomy-Driven Labeling Strategy

Status: accepted

Decision:
The system will use a defined taxonomy for barriers, triggers, missions, segments, and opportunity areas.

Reason:
Taxonomy-based tagging makes the output easier to compare across runs and easier to aggregate quantitatively.

Implication:
The taxonomy must be versioned and periodically revised as new patterns emerge.

## D-007: Treat Public Feedback As Directional, Not Fully Representative

Status: accepted

Decision:
Insights from public sources will be treated as directional evidence rather than a complete representation of all Instamart customers.

Reason:
Public feedback often over-indexes on extreme experiences and vocal user segments.

Implication:
Business conclusions should be combined with internal product analytics or future experiments where possible.

## D-008: Optimize For Weekly Or Batch Refreshes In V1

Status: accepted

Decision:
The initial implementation will support scheduled batch refreshes rather than real-time processing.

Reason:
The primary use case is strategic product discovery, not real-time decisioning.

Implication:
This reduces operational complexity while keeping the system useful for planning and prioritization.

## D-009: Approve Taxonomy v1.0.0 For Phase 1

Status: accepted

Decision:
Adopt taxonomy version 1.0.0 with 9 category labels, 7 shopping missions, 12 barriers, 9 triggers, 8 discovery channels, 11 user segments, and supporting concern sub-taxonomies.

Reason:
Phase 0 walkthrough of 25 sample feedback items classified cleanly with no label overlap issues. All labels validated programmatically against `schemas/taxonomy-v1.json`.

Implication:
Phase 1 ingestion and Phase 2 enrichment must tag records using this taxonomy version. Changes require a version bump.

## D-010: Use SQLite For Phase 1 Raw Storage

Status: accepted

Decision:
Store raw feedback in SQLite (`data/phase-1/db/instamart_raw.sqlite`) with JSONL batch exports, rather than Postgres for V1.

Reason:
Simplifies local development, meets auditability requirements (D-003), and supports deduplication via unique constraints without external infrastructure.

Implication:
Phase 2 can read from the same SQLite database or exported JSONL. Migration to Postgres is possible later without schema changes.
