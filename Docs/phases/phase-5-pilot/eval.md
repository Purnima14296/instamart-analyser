## Phase 5 Evaluation

## Purpose

Validate that the end-to-end AI agent is reliable enough for stakeholder use and ready to support downstream experimentation.

## What To Test

- the full pipeline runs end to end without manual recovery steps
- outputs are understandable and useful to stakeholders
- manual analysis and AI analysis align on major themes
- prompt, taxonomy, and threshold refinements are captured systematically
- the final output package supports decision-making for growth experiments

## Validation Methods

- run a pilot on a meaningful multi-source dataset
- compare agent outputs against a manually reviewed subset
- collect stakeholder feedback in structured form
- track defects, missing fields, and recurring review comments
- rerun after fixes to confirm improvements

## Exit Criteria

- end-to-end pipeline is stable on pilot scope
- major insights align with manual review
- stakeholder feedback is incorporated or explicitly deferred
- remaining known limitations are documented
- team agrees the system is ready for operational use in discovery work

## Failure Signals

- the pipeline works only with author intervention
- stakeholders do not trust or understand the output
- manual review repeatedly contradicts the agent's main conclusions
- the system produces reports that are hard to act on
