## Phase 3 Evaluation

## Purpose

Validate that the system can convert enriched records into meaningful, repeatable, and evidence-backed insights.

## What To Test

- aggregation logic groups records into coherent themes
- high-frequency themes are not inflated by duplicate or low-quality inputs
- generated insights accurately reflect the supporting evidence
- confidence levels are appropriate to evidence strength
- insights are useful to product and growth stakeholders

## Validation Methods

- compare AI-generated themes to analyst-generated themes on a shared sample
- inspect insight reports for citation quality and evidence traceability
- run reviewer scoring for clarity, correctness, novelty, and actionability
- test whether independent reviewers reach similar interpretations from the same evidence set

## Exit Criteria

- each published insight includes evidence and confidence
- reviewers confirm that insights match their source records
- repeated runs on the same input produce materially similar top themes
- stakeholders judge the output useful for decision-making
- uncertainty and open questions are explicitly called out

## Failure Signals

- insights sound plausible but lack support
- top themes change unpredictably on reruns
- outputs overgeneralize from thin evidence
- reviewers cannot trace a claim back to source data
