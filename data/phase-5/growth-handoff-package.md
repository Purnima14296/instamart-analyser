# Growth Experimentation Handoff Package

- Generated at: `2026-07-30T15:48:30+00:00`
- Pilot ready: **yes**
- Enriched reviews in pilot: **164**
- Opportunities: **10**
- Hypotheses: **10**

## What This Package Is For

Use this package to move from evidence-backed insights to experiment design.
It separates evidence, interpretation, and recommendation. It does not authorize product changes without human review.

## Recommended First Bets

### 1. Rebuild trust before cross-sell
- Priority: `high`
- Segment: `family_household`
- User problem: Family Household users do not want to try more categories when core grocery or delivery experiences feel unreliable.
- First move: Surface freshness or replacement guarantees near adjacent-category modules.
- Linked insights: insight_d925042f

### 2. Rebuild trust before cross-sell
- Priority: `high`
- Segment: `family_household`
- User problem: Family Household users do not want to try more categories when core grocery or delivery experiences feel unreliable.
- First move: Surface freshness or replacement guarantees near adjacent-category modules.
- Linked insights: insight_165705d9

### 3. Lower the first-try price risk
- Priority: `high`
- Segment: `habitual_replenisher`
- User problem: Habitual Replenisher users hesitate to add new-category items because total cost feels uncertain or not worth the risk.
- First move: Bundle adjacent-category trials with staple reorder journeys.
- Linked insights: insight_4faef10a

## Hypothesis Backlog (Top 5)

### hyp_001
- If Instamart uses surface guarantees and post-order reassurance in adjacent-category prompts for Family Household users during replenishment missions, then new-category add-to-order rate among eligible users should improve for grocery opportunities.
- Primary metric: new-category add-to-order rate among eligible users
- Guardrails: overall order conversion, customer support contacts per order, refund or cancellation rate

### hyp_002
- If Instamart uses surface guarantees and post-order reassurance in adjacent-category prompts for Family Household users during replenishment missions, then new-category add-to-order rate among eligible users should improve for cross-category opportunities.
- Primary metric: new-category add-to-order rate among eligible users
- Guardrails: overall order conversion, customer support contacts per order, refund or cancellation rate

### hyp_003
- If Instamart uses show low-risk entry offers or bundles for adjacent categories for Habitual Replenisher users during replenishment missions, then trial conversion for promoted adjacent-category items should improve for grocery opportunities.
- Primary metric: trial conversion for promoted adjacent-category items
- Guardrails: overall order conversion, customer support contacts per order, refund or cancellation rate

### hyp_004
- If Instamart uses improve discovery prompts and category navigation in high-intent journeys for Family Household users during replenishment missions, then share of users who open or add from a new category should improve for grocery opportunities.
- Primary metric: share of users who open or add from a new category
- Guardrails: overall order conversion, customer support contacts per order, refund or cancellation rate

### hyp_005
- If Instamart uses surface guarantees and post-order reassurance in adjacent-category prompts for Family Household users during replenishment missions, then new-category add-to-order rate among eligible users should improve for grocery opportunities.
- Primary metric: new-category add-to-order rate among eligible users
- Guardrails: overall order conversion, customer support contacts per order, refund or cancellation rate

## Measurement Framework

- North star: Increase monthly new-category adoption among existing Instamart shoppers without harming core replenishment trust.
- Core metrics: **4**
- Guardrails: **4**

- `m_new_category_add` **new-category add-to-order rate**: Share of eligible sessions/orders that add an item from a category not purchased in the prior 30–90 days.
- `m_new_category_trial` **adjacent-category trial conversion**: Share of users exposed to a category-expansion intervention who purchase from the promoted adjacent category.
- `m_browse_depth` **new-category browse depth**: Average number of distinct non-staple categories opened per session among exposed users.
- `m_repeat_expansion` **30-day category expansion retention**: Share of first-time category triers who purchase from that category again within 30 days.

## Evidence Traceability

- Insights available: 10
- Manual alignment verdict: Major themes align between keyword pre-analysis and AI enrichment.
- Key source files:
  - `data/phase-3/insights.json`
  - `data/phase-3/stakeholder-summary.md`
  - `data/phase-4/opportunity-map.json`
  - `data/phase-4/hypothesis-backlog.json`
  - `data/phase-4/experiment-framing-memo.md`

## Stakeholder Review Status

- Feedback responses: 5
- Open defects: 2
- Deferred items: 1
- Incorporated items: 1

## Refinements Already Applied

- Prompt: 3
- Taxonomy: 2
- Thresholds: 3

## Explicit Non-Claims

- Feedback themes are not causal proof.
- Public reviews are complaint-biased.
- Partial enrichment means rankings may shift as more reviews are labeled.

## Suggested Next Actions

1. Review top 3 opportunities with product + growth.
2. Choose one trust and one discovery hypothesis for experiment design.
3. Define eligibility rules and success thresholds using the measurement framework.
4. Continue Phase 2 enrichment when Groq quota resets to strengthen evidence.
