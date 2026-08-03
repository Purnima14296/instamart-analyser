## Phase 1: Data Ingestion And Storage

Status: **complete**  
Platform: Swiggy Instamart

## Objective

Collect feedback from P0 sources and store it in a reproducible raw-data layer with batch tracking, deduplication, and audit logging.

## Folder Structure

```
data/phase-1/
  db/instamart_raw.sqlite    # SQLite raw store + batch tables
  raw/{batch_id}/records.jsonl  # Per-batch JSONL exports
  seed/seed-records.json       # Offline seed dataset

logs/phase-1/
  {batch_id}.json              # Batch completion logs

src/instamart_analyser/phases/phase_1/
  connectors/                  # Play Store, App Store, Reddit
  storage/                     # RawStore, BatchTracker
  pipeline.py                  # Ingestion orchestrator
  validate_phase1.py           # Exit criteria checker
```

## Connectors (P0)

| Source | Connector | Access method |
|---|---|---|
| Google Play Store | `PlayStoreConnector` | `google-play-scraper` |
| Apple App Store | `AppStoreConnector` | iTunes RSS JSON feed |
| Reddit | `RedditConnector` | Public JSON API |

All connectors filter for Instamart-relevant keywords and support retry with exponential backoff.

## Run Ingestion

```powershell
$env:PYTHONPATH="src"

# Fetch 6 months of Instamart reviews (default)
py -m instamart_analyser.phases.phase_1.pipeline run --months 6 --no-seed

# Export summary
py -m instamart_analyser.phases.phase_1.export_reviews
```

The pipeline scans all Swiggy Play Store reviews from the last 6 months (~80k reviews) and keeps only those mentioning Instamart. App Store RSS is paginated up to 200 pages or until the date cutoff.

## Validate Phase 1

```powershell
py -m instamart_analyser.phases.phase_1.validate_phase1
```

## Raw Storage Schema

SQLite table `raw_feedback` stores all fields from `schemas/feedback-record.schema.json` plus `content_hash` for deduplication.

Unique constraint on `(source, source_record_id)` prevents duplicate ingestion on reruns.

## Batch Tracking

- `ingestion_batches` — batch metadata, counts, status
- `ingestion_events` — per-connector success/failure/retry events
- JSON log files in `logs/phase-1/`

## Exit Criteria

| Criterion | Status |
|---|---|
| P0 sources ingest successfully | Met |
| Raw schema stable and documented | Met |
| Logging for success, failure, retry | Met |
| Seed dataset collected and reviewable | Met |
| Reruns do not corrupt data (dedupe) | Met |

## Next Phase

Proceed to **Phase 2: Cleaning, Normalization, And Enrichment**.
