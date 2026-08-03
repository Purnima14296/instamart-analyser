## Core Analysis Questions

Each question below maps to taxonomy fields and schema outputs defined in Phase 0. This ensures downstream enrichment and insight generation answer the problem statement directly.

## Question Map

| # | Question (from problem statement) | Taxonomy / schema fields used | Expected aggregation |
|---|---|---|---|
| Q1 | Why do users repeatedly buy from the same categories? | `barriers[]`, `shopping_mission`, `habit_signal`, `categories_mentioned[]` | Barrier frequency by category and segment |
| Q2 | What prevents users from exploring new categories? | `barriers[]`, `trust_concerns[]`, `price_concerns[]`, `discovery_barriers[]` | Co-occurrence of barrier types |
| Q3 | How do users discover products today? | `discovery_channels[]`, `triggers[]`, `shopping_mission` | Discovery channel distribution |
| Q4 | What role do habits, trust, urgency, and convenience play? | `habit_signal`, `trust_concerns[]`, `urgency_context`, `convenience_signal` | Factor importance by segment |
| Q5 | What information do users need before trying a new category? | `information_gaps[]`, `trust_concerns[]`, `discovery_barriers[]` | Information gap themes |
| Q6 | What frustrations appear consistently across feedback? | `friction_types[]`, `sentiment`, `barriers[]` | Recurring frustration themes |
| Q7 | Which user segments are more open to experimentation? | `user_segment_hypothesis`, `experimentation_signal`, `triggers[]` | Segment × trigger matrix |

## Secondary Questions (from expected discovery engine output)

| # | Question | Taxonomy / schema fields used |
|---|---|---|
| Q8 | What triggers exploration into a new category? | `triggers[]`, `adjacent_category_opportunity`, `experimentation_signal` |
| Q9 | How much is behavior driven by habit vs poor discovery? | `habit_signal`, `discovery_barriers[]`, `discovery_channels[]` |
| Q10 | What role do trust, pricing, assortment, and product information play? | `trust_concerns[]`, `price_concerns[]`, `assortment_concerns[]`, `information_gaps[]` |
| Q11 | Which themes repeat across feedback channels? | `barriers[]`, `friction_types[]`, aggregated theme IDs |
| Q12 | Which segments, missions, or occasions lead to cross-category expansion? | `user_segment_hypothesis`, `shopping_mission`, `triggers[]`, `occasion_context` |

## Insight Types Each Question Should Produce

- **Descriptive:** "X% of feedback mentioning personal care cites trust concerns about product authenticity."
- **Comparative:** "Deal-seeking segments mention price barriers 2× more than family households."
- **Behavioral:** "Users who expand categories often cite life-event triggers (new pet, baby, moving)."
- **Diagnostic:** "Habit lock-in appears stronger for replenishment missions than urgent-need missions."

## Questions That Require Caution

Do not answer these with public feedback alone:

- Exact % of Instamart MAC affected (requires internal analytics)
- Causal impact of a specific UI change (requires experiments)
- Revenue lift from a recommendation (requires A/B testing)

These should be framed as **hypotheses** until validated with internal data or experiments. See `insight-vs-hypothesis.md`.
