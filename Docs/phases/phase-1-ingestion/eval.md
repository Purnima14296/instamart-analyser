## Phase 1 Evaluation

## Purpose

Validate that feedback data can be collected reliably and stored with enough metadata for later analysis and auditability.

## What To Test

- connectors successfully collect records from each priority source
- raw text and metadata are stored correctly
- ingestion retries and failures are logged
- duplicate source pulls do not silently corrupt the dataset
- batch IDs and timestamps allow reruns and comparisons

## Validation Methods

- run connector smoke tests for each source
- inspect sampled raw records for completeness
- simulate failure cases such as partial source outage or malformed records
- verify batch logging and row counts after repeated runs

## Exit Criteria

- priority sources ingest successfully
- raw schema is stable and documented
- logging exists for success, failure, and retry paths
- at least one seed dataset is collected and reviewable
- data can be rerun without manual patching

## Failure Signals

- missing metadata prevents traceability
- repeated runs create uncontrolled duplicates
- source-specific failures are hard to detect
- ingestion requires frequent manual intervention
