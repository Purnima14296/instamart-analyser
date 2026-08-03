## Insight vs Hypothesis

This document defines what qualifies as an **insight** versus a **hypothesis** in the Swiggy Instamart discovery engine. Clear separation prevents overconfident conclusions from thin or directional evidence.

## Definitions

### Insight

An **insight** is a validated, evidence-backed finding derived from analyzed feedback data.

Requirements:

| Criterion | Requirement |
|---|---|
| Evidence | Linked to ≥3 independent source records (or ≥2 if from different source types) |
| Traceability | Each claim cites specific snippets with source URLs or IDs |
| Relevance | Directly answers a core analysis question (see `analysis-questions.md`) |
| Confidence | Assigned confidence level: `high`, `medium`, or `low` |
| Review | Passed human review or automated quality checks |
| Reproducibility | Reappears across at least 2 pipeline runs or manual re-analysis |

Example insight:

> **Statement:** Users on replenishment missions rarely discover adjacent categories because they reorder from history without browsing the homepage.  
> **Evidence:** 14 of 22 sampled records mentioning "reorder" or "same list" also cite `habit_lock_in` or `poor_discovery`. Sources: Play Store (6), Reddit (5), App Store (3).  
> **Confidence:** medium  
> **Segment:** habitual_replenisher  
> **Business implication:** Discovery interventions may need to intercept the reorder flow, not just the homepage.

### Hypothesis

A **hypothesis** is a testable proposition that is directionally supported by evidence but not yet validated enough to be treated as an insight.

Characteristics:

- Supported by fewer than 3 records, or only from a single source type
- Plausible interpretation but alternative explanations exist
- Requires internal analytics or experiments to confirm
- May include causal claims that public feedback cannot prove

Example hypothesis:

> **Statement:** Showing cross-category bundles on the cart page would increase new-category adoption by 5%.  
> **Evidence:** 4 Reddit posts mention liking combo deals.  
> **Status:** hypothesis — needs A/B test to validate causal impact.

## Decision Tree

```
Does the finding answer a core analysis question?
├── No → Discard or reframe
└── Yes
    ├── Is it supported by ≥3 records from ≥1 source type?
    │   ├── No → Hypothesis
    │   └── Yes
    │       ├── Can claims be traced to source snippets?
    │       │   ├── No → Hypothesis (insufficient traceability)
    │       │   └── Yes
    │       │       ├── Does it make causal claims?
    │       │       │   ├── Yes → Hypothesis (needs experiment)
    │       │       │   └── No → Candidate insight
    │       │       │           ├── Passed review?
    │       │       │           │   ├── No → Draft insight
    │       │       │           │   └── Yes → Published insight
```

## Confidence Levels

| Level | Criteria |
|---|---|
| `high` | ≥10 supporting records, ≥2 source types, consistent theme, reviewer agreement |
| `medium` | 3–9 supporting records, theme is clear, minor ambiguity |
| `low` | 3 records minimum met, but thin coverage or single source type |

## What Is Never An Insight (Without Further Validation)

- Projected revenue or MAC impact percentages
- "Users will definitely do X if we build Y"
- Claims based on a single viral Reddit thread
- Findings that contradict internal analytics (flag for reconciliation)

## Output Schema Mapping

| Output type | Schema file | `status` field value |
|---|---|---|
| Draft finding | `schemas/insight.schema.json` | `draft` |
| Reviewed insight | `schemas/insight.schema.json` | `published` |
| Testable hypothesis | `schemas/insight.schema.json` | `hypothesis` |
