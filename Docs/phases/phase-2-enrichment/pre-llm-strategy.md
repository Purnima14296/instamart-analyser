## Pre-LLM Strategy (Phase 1 Data Analysis)

Generated from **969** normalized Instamart reviews.

## Dataset snapshot

| Metric | Value |
|---|---|
| Total reviews | 969 |
| Play Store share | 937 (96.7%) |
| 1-star reviews | 770 (81.1%) |
| Avg words per review | 44.2 |
| Reviews >50 words | 382 (39.4%) |

### Source breakdown

- **play_store**: 937
- **app_store**: 12
- **reddit**: 5
- **mouthshut**: 4
- **quora**: 3
- **youtube**: 3
- **twitter**: 3
- **facebook**: 2

### Rating distribution

- 1 star: 770
- 2 star: 50
- 3 star: 23
- 4 star: 29
- 5 star: 77

## What the data tells us (before Groq)

### 1. Sentiment skew is extreme

81.1% of rated reviews are 1-star. Public feedback is heavily complaint-driven.
**Strategy:** Do not treat sentiment distribution as representative of all Instamart users. Use insights directionally. Separate **delivery/support complaints** from **category-discovery signals**.

### 2. Pre-LLM theme signals (keyword-based)

These keyword buckets estimate which taxonomy themes are likely present:

| Theme signal | Review count | Likely taxonomy mapping |
|---|---|---|
| delivery_speed | 441 | friction_types: delivery_experience, barriers: mission_narrowness |
| app_ux_discovery | 436 | barriers: poor_discovery, friction_types: navigation_ux |
| customer_support | 394 | friction_types: customer_support, barriers: past_bad_experience |
| pricing_offers | 253 | price_concerns, barriers: price_sensitivity |
| delivery_quality | 182 | trust_concerns: freshness_expiry, friction_types: delivery_experience |
| product_quality | 112 | trust_concerns, barriers: trust_quality |
| habit_reorder | 101 | barriers: habit_lock_in, habit_signal: true |
| comparison_competitor | 88 | context only — exclude from Instamart-only insights |
| category_exploration | 61 | barriers: low_awareness, experimentation_signal |

- **628** reviews match multiple theme signals (need multi-label Groq output)
- **102** reviews match no keyword bucket (Groq still needed — may be generic praise/complaint)

### 3. Review length affects LLM approach

| Bucket | Count | LLM approach |
|---|---|---|
| Short (≤15 words) | 158 | Single-shot classification, low tokens |
| Medium (16–50 words) | 429 | Standard enrichment prompt |
| Long (>50 words) | 382 | Higher max_tokens; extract multiple barriers per review |

## Recommended pipeline strategy

### Phase 2 — Groq enrichment (per record)

```
normalized_feedback → [optional dedupe] → Groq classify (1 review per call)
                    → validate against taxonomy-v1.json → enriched_feedback
```

| Decision | Recommendation |
|---|---|
| **Granularity** | 1 review → 1 Groq call (keeps traceability) |
| **Batch size** | Process in batches of 20 for logging/rate limits, not as a single prompt |
| **Model** | `llama-3.3-70b-versatile` for accuracy on multi-label taxonomy |
| **Temperature** | 0.1 (consistent labels) |
| **Output** | Structured JSON per `enriched-feedback.schema.json` |
| **Pre-filter** | Skip records already keyword-classified with high confidence only if validated on gold set |

### Phase 3 — Theme generation (aggregate then synthesize)

**Do not** send all 969 reviews to Groq for summarization. Instead:

1. **Aggregate** enriched records by `barriers[]`, `shopping_mission`, `friction_types[]`
2. **Quantify** frequency per theme (count + % of corpus)
3. **Select top clusters** with ≥3 records (per insight rubric)
4. **Send only cluster summaries + 5–10 evidence snippets** to Groq for insight drafting
5. **Human review** before publishing

```
enriched_feedback → SQL/group-by aggregation → theme frequency table
                  → top N clusters (≥3 records each)
                  → Groq insight agent (cluster context only, not full corpus)
                  → insight.schema.json outputs
```

### What NOT to do

- Do not send all 969 reviews in one Groq prompt (context limits, lost traceability)
- Do not generate themes before per-record enrichment (no structured labels to aggregate)
- Do not treat 79% 1-star reviews as overall customer satisfaction
- Do not overweight Play Store (96%) without noting source bias in every insight

## Suggested Groq prompt order

1. **Enrichment prompt** (Phase 2): "Classify this Instamart review into taxonomy labels…"
2. **Theme validation prompt** (Phase 3): "Given these 8 reviews tagged `habit_lock_in`, state the pattern in one sentence with evidence."
3. **Insight prompt** (Phase 3): "Given theme `poor_discovery` (142 records, 15% of corpus), draft an insight with business implication for category expansion."

## Gold set recommendation

Before full Groq run, manually label **30 reviews** (10 short, 10 medium, 10 long) from `normalized_feedback`.
Compare Groq output to gold labels. Target ≥80% agreement on `barriers` and `shopping_mission` before processing all 969.

## Machine-readable output

Full analysis JSON: `data/phase-1/pre-llm-analysis.json`
