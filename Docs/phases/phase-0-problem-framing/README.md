## Phase 0: Problem Framing And Taxonomy

Status: **complete**  
Platform: Swiggy Instamart  
Taxonomy version: `1.0.0`

## Deliverables

| Deliverable | Location | Status |
|---|---|---|
| Business objectives and metrics | `business-objectives.md` | Done |
| Analysis question map | `analysis-questions.md` | Done |
| Taxonomy v1 (human-readable) | `taxonomy-v1.md` | Done |
| Taxonomy v1 (machine-readable) | `../../schemas/taxonomy-v1.json` | Done |
| Canonical output schemas | `../../schemas/*.schema.json` | Done |
| Source inventory | `source-inventory.md` | Done |
| Insight quality rubric | `insight-quality-rubric.md` | Done |
| Insight vs hypothesis definitions | `insight-vs-hypothesis.md` | Done |
| Sample feedback walkthrough (25 items) | `../../data/phase-0/samples/phase-0-feedback-samples.json` | Done |
| Validation script | `../../src/instamart_analyser/validate_phase0.py` | Done |

## Run Validation

```bash
pip install -r requirements.txt
python -m instamart_analyser.validate_phase0
```

Run from the project root with `PYTHONPATH=src` or after installing the package.

## Exit Criteria (from eval.md)

| Criterion | Status |
|---|---|
| Business objective is explicit and measurable | Met |
| Taxonomy v1 is documented and usable | Met |
| Output schema is finalized for implementation | Met |
| Priority source list is agreed | Met |
| Insight rubric is written and accepted | Met |
| 20–30 sample feedback items classified against taxonomy | Met (25 items) |

## Key Outputs For Phase 1

Phase 1 should use:

- `schemas/feedback-record.schema.json` for raw/normalized storage
- `schemas/taxonomy-v1.json` for enrichment label validation
- `source-inventory.md` P0 sources: Play Store, App Store, Reddit
- Minimum volume target: 500 records in first batch

## Next Phase

Proceed to **Phase 1: Data Ingestion And Storage** per `Docs/implementationplan.md`.
