## Business Objectives

Platform: Swiggy Instamart

## Primary Objective

Increase the percentage of Monthly Active Customers (MAC) who purchase from at least one new category every month.

## Definition

- **Monthly Active Customer (MAC):** A user who places at least one Instamart order in a calendar month.
- **New category purchase:** A category the user has not purchased from in the prior 90 days.
- **Primary metric:** `% MAC with ≥1 new category purchase per month`

## Supporting Metrics

| Metric | Definition | Why it matters |
|---|---|---|
| Cross-category adoption rate | Share of orders containing items from 2+ categories | Measures basket breadth |
| Category penetration | % of MAC purchasing from each category | Identifies underexplored assortment |
| Repeat-category concentration | % of orders from a user's top 2 categories | Measures habit lock-in |
| Time to first adjacent-category trial | Days from first order to first purchase in an adjacent category | Measures exploration speed |
| Category discovery funnel | Impression → click → add-to-cart → purchase by category | Separates discovery vs conversion issues |

## Success Thresholds For The Discovery Engine (Phase 0–3)

The AI agent does not directly move the primary metric in Phase 0. Instead, Phase 0 defines what "good" looks like before building the pipeline:

- Analysis questions from the problem statement are explicitly mapped to taxonomy fields.
- Taxonomy v1 can classify sample feedback without ambiguous overlap.
- Output schema supports aggregation by barrier, trigger, mission, and segment.
- Insight rubric distinguishes evidence-backed findings from anecdotes.

## Strategic Context

Instamart users often form narrow shopping habits: groceries, snacks, and household essentials dominate repeat orders. Adjacent categories (personal care, pet supplies, baby products, home needs) remain underpenetrated despite being available on the platform.

The discovery engine must explain **why** this happens before recommending product interventions such as nudges, bundles, onboarding flows, or ranking changes.

## Out Of Scope For Phase 0

- Building data connectors
- Running LLM enrichment at scale
- Shipping user-facing product changes
- Claiming causal impact on MAC metrics
