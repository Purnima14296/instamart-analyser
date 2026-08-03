# Research Intelligence UX (Additive)

This layer makes the existing Instamart Analyser feel like a product-research dashboard
(inspired by Spotify-style Streamlit research apps) **without removing** Phase 1–6 features.

## What was added

- `GET /api/research/summary` — executive brief, portfolio metrics, sentiment, segment priority,
  category-discovery trust score, top opportunity, pipeline status strip
- Overview page research hero (keeps pilot badge, bias banner, quota notes, barriers, limitations)
- Jobs page ingest actions + analysis cascade (keeps enrich / Phase 3–5 / recover)
- Job kinds: `ingest_play`, `ingest_appstore`, `ingest_reddit_selenium`, `ingest_all`, `analysis_cascade`

### Research explorer pages

A dedicated navigation section mirrors the reference dashboard's page set. Every page is backed
by a real endpoint over Phase 1–5 artifacts — none of them are static mockups.

| Page | Route | Endpoint | Source of truth |
| --- | --- | --- | --- |
| Executive Summary | `/` | `/api/research/summary` | Phase 3–5 rollups |
| Source Analysis | `/sources` | `/api/explore/sources` | Phase 1 normalized store + Phase 2 labels |
| Review Discovery | `/reviews` | `/api/explore/reviews` | normalized store joined to enrichment |
| Discovery Challenges | `/challenges` | `/api/explore/discovery-challenges` | `phase-3/discovery-barriers.json` |
| Theme Explorer | `/themes` | `/api/themes` | `phase-3/theme-clusters.json` |
| Segment Explorer | `/segments` | `/api/explore/segments` | `phase-3/segment-analysis.json` + priority score |
| Root Cause Analysis | `/root-causes` | `/api/explore/root-causes` | derived from Phase 2 concern fields |
| Unmet Needs | `/unmet-needs` | `/api/explore/unmet-needs` | `information_gaps` + `assortment_concerns` |
| Discovery Journey | `/journey` | `/api/explore/journey` | mission → channel → trigger → barrier funnel |
| Validation | `/validation` | `/api/explore/validation` | `phase-5/manual-alignment.json` |

### Persistent Pipeline Actions

The sidebar now carries the pipeline controls on every page (admin role only), plus a live
status block showing the last job, active job, artifact counts, and source mix. The dedicated
Pipeline Jobs page is unchanged and still holds the full job history and recovery controls.

### Derivation notes

- **Root causes** group enriched reviews by barrier, then tally `trust_concerns`, `price_concerns`,
  `assortment_concerns`, `information_gaps`, and `friction_types` as candidate causes. Confidence is
  `high` at ≥25 supporting reviews, `medium` at ≥10, otherwise `low`.
- **Unmet needs** rank `information_gaps` and `assortment_concerns` mentions, and link the top
  Phase 4 opportunities so a need can be traced to the roadmap.
- **Discovery journey** is a descriptive five-stage funnel, not a measured conversion funnel; stage
  counts are label frequencies and do not sum to a single user path.

## Score formulas

### Category Discovery Trust (0–100)

```text
score = 100
        − trust_barrier_share × 35      (capped at 35)
        − discovery_barrier_share × 25  (capped at 25)
        − negative_sentiment_% × 0.25   (capped at 25)
        − focus_segment_discovery_rate × 10 (capped at 15)
```

- **trust barriers**: `trust_quality`, `past_bad_experience`, `lack_of_trust`
- **discovery barriers**: `poor_discovery`, `habit_lock_in`, `cognitive_overload`, `information_gap`
- Shares are computed from Phase 3 `theme-summary` barrier tallies over enriched record count.
- Labels: `strong` (≥70), `moderate` (≥45), else `weak`.

This is a **directional research heuristic**, not a causal product KPI.

### Segment priority

```text
priority_score = review_count × (discovery_barrier_rate + trust_barrier_rate)
```

- Rates come from Phase 3 `segment-analysis.json` barrier tallies / segment review count
  (each rate capped at 1.5).
- Higher score = larger segment with more discovery/trust friction.
- Recommended focus = rank 1 segment.

## Explicitly kept

- Insights / evidence / review workflow
- Opportunities / hypotheses / experiments
- Pilot readiness / measurement / growth handoff
- Role gates, quota guards, stale job recovery, feedback sync
