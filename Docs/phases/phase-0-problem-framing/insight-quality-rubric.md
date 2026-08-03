## Insight Quality Rubric

Used to score draft insights before they are published or promoted to hypotheses for experimentation.

## Scoring Dimensions

Each dimension is scored 1–5. Minimum total score of 18/25 required for `published` status.

### 1. Evidence Strength (1–5)

| Score | Criteria |
|---|---|
| 5 | ≥10 records, ≥2 source types, no contradictory evidence |
| 4 | 5–9 records, ≥2 source types |
| 3 | 3–4 records, consistent theme |
| 2 | 1–2 records, or contradictory evidence present |
| 1 | Anecdotal, single source, or unverifiable |

### 2. Traceability (1–5)

| Score | Criteria |
|---|---|
| 5 | Every claim links to specific snippets with URLs/IDs |
| 4 | Most claims linked; minor gaps |
| 3 | Summary-level citations only |
| 2 | Vague references ("users say…") |
| 1 | No source linkage |

### 3. Relevance To Business Objective (1–5)

| Score | Criteria |
|---|---|
| 5 | Directly explains why users don't explore new categories |
| 4 | Strongly related to category expansion or discovery |
| 3 | Related to Instamart experience but not category-specific |
| 2 | Tangentially related |
| 1 | Off-topic |

### 4. Actionability (1–5)

| Score | Criteria |
|---|---|
| 5 | Clear product intervention implied (e.g., "surface pet food on reorder screen") |
| 4 | Opportunity area identified with specific segment |
| 3 | Diagnostic value but intervention unclear |
| 2 | Interesting but no clear next step |
| 1 | Not actionable |

### 5. Clarity And Non-Overclaim (1–5)

| Score | Criteria |
|---|---|
| 5 | Precise language, confidence stated, limitations noted |
| 4 | Clear with minor ambiguity |
| 3 | Understandable but vague |
| 2 | Overgeneralizes from evidence |
| 1 | Makes unsupported causal or quantitative claims |

## Status Thresholds

| Total score | Status | Action |
|---|---|---|
| 22–25 | `published` | Ready for stakeholder delivery |
| 18–21 | `published` with notes | Publish; document caveats |
| 14–17 | `draft` | Revise and re-review |
| 10–13 | `hypothesis` | Needs more evidence or reframing |
| <10 | Reject | Discard or collect more data |

## Reviewer Checklist

- [ ] Insight statement is a single clear sentence
- [ ] Supporting evidence includes record count and source breakdown
- [ ] Confidence level matches evidence strength
- [ ] Affected segment is specified or marked as "general"
- [ ] Open questions or uncertainties are documented
- [ ] No causal claims without experimental support
- [ ] Not duplicated by an existing published insight

## Example Scoring

**Insight:** "Habitual replenishers who reorder from history rarely encounter adjacent categories because the reorder flow bypasses category browsing."

| Dimension | Score | Rationale |
|---|---|---|
| Evidence strength | 4 | 7 records, Play Store + Reddit |
| Traceability | 5 | All snippets linked |
| Relevance | 5 | Directly addresses Q1 and Q9 |
| Actionability | 5 | Suggests reorder-flow intervention |
| Clarity | 4 | Clear; could note sample size limitation |
| **Total** | **23** | **Published** |

## Automated Pre-Checks (Phase 3+)

Before human review, the pipeline should auto-reject insights that:

- Have fewer than 3 supporting record IDs
- Have no `source_breakdown` field
- Have `confidence: high` with fewer than 10 records
- Contain causal language ("will increase", "causes", "proves") without `status: hypothesis`
