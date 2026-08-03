# Instamart Category Discovery — Stakeholder Summary

**Status:** Draft insights (human review pending)  
**Generated:** 2026-07-28  
**Corpus:** 119 enriched public reviews (969 in full cohort; enrichment ongoing)

---

## Executive summary

Early analysis of Instamart feedback shows that **trust and operational failures are the dominant blockers** in public reviews. Users are primarily on **grocery replenishment missions**, and complaints cluster around **product quality, wrong/missing items, slow support, and refund friction**.

Category expansion is not yet the loudest signal in this sample. **Poor discovery and habit lock-in appear in the data**, but they are secondary to delivery and trust issues. Before nudging users into new categories, Instamart likely needs to **restore baseline trust** for replenishment shoppers—especially **family households**, who make up the largest affected segment.

**Caveat:** 95% of reviews are from Play Store and 85% are negative. Treat this as directional complaint-biased signal, not representative of all Instamart users.

---

## What we analyzed

| Metric | Value |
|---|---|
| Enriched reviews | 119 |
| Theme clusters found (≥3 records) | 16 |
| Insight drafts produced | 5 |
| Primary shopping mission | Replenishment (77%) |
| Dominant segment | Family household (45%) |

**Top barrier signals across corpus**

| Barrier | Reviews |
|---|---|
| Trust / quality concerns | 44 |
| Past bad experience | 39 |
| Poor discovery | 19 |
| Delivery fee threshold | 18 |
| Price sensitivity | 15 |
| Habit lock-in | 12 |

---

## Five draft insights

### 1. Product quality erodes trust before users explore new categories

**Confidence:** High · **Supporting records:** 17 · **Segment:** Family household

**Finding**  
Users report expired goods, wrong items, and weak resolution when quality issues occur. This undermines confidence in Instamart as a reliable replenishment channel.

**Why it matters for category expansion**  
Users will not experiment in personal care, baby, or pet categories if core grocery trust is broken.

**Representative voice**  
> "Typical Third world app… Instamart sends expired goods, delivery partners are always late, orders are misplaced."

**Suggested direction**  
Strengthen freshness checks, partner-store compliance, and fast quality-issue resolution before scaling discovery nudges.

**Open questions**
- Are expiry-date checks enforced consistently at partner stores?
- Can quality complaints be resolved in-app without email loops?

---

### 2. Past bad delivery and support experiences block repeat grocery use

**Confidence:** High · **Supporting records:** 10 · **Segment:** Family household

**Finding**  
Delayed deliveries, wrong items, missing items, and unresponsive support create lasting churn risk—even among long-time Swiggy users.

**Why it matters for category expansion**  
A user who stops trusting Instamart for weekly groceries is unlikely to try adjacent categories on the same app.

**Representative voice**  
> "Swiggy Instamart customer care is non respondent… it's been one month and no one from Swiggy has responded back."

**Suggested direction**  
Prioritize delivery accuracy SLAs and in-app support responsiveness for replenishment orders.

**Open questions**
- Where do support handoffs break (chat → email → no response)?
- Which failure types (missing vs wrong vs late) drive the most churn?

---

### 3. Support and refund friction amplifies trust issues

**Confidence:** Medium · **Supporting records:** 8 · **Segment:** Family household

**Finding**  
Beyond product quality, users cite slow refunds, coupon substitutes instead of cash back, and automated replies that do not resolve issues.

**Why it matters for category expansion**  
Refund pain increases perceived risk. Higher-risk categories (fresh food, personal care, baby) need stronger trust signals than grocery staples.

**Representative voice**  
> "Extremely difficult to make returns… The support staff is incompetent in any situation."

**Suggested direction**  
Simplify refund paths; reduce coupon-only compensation for quality failures.

---

### 4. Price competitiveness is a retention strength (minority signal)

**Confidence:** Medium · **Supporting records:** 7 · **Segment:** Family household

**Finding**  
A smaller set of positive reviews praise Instamart for lower prices and coupons vs competitors (Zepto, etc.).

**Why it matters for category expansion**  
Price-led users may try new categories **if** the offer is compelling—but only after trust basics are met.

**Representative voice**  
> "Instamart prices are really very low compared to other apps like zepto… it saves my money really well."

**Suggested direction**  
Use targeted offers to pull deal-seekers into one adjacent category per trip—paired with quality guarantees.

**Note:** This is the only positive-theme insight in the top 5; do not overweight it given overall negative skew.

---

### 5. Repeat service failures reinforce habit of avoiding Instamart

**Confidence:** Medium · **Supporting records:** 6 · **Segment:** Family household

**Finding**  
Users describe returning after a break, encountering the same issues, and leaving again—suggesting a **negative reinforcement loop** that strengthens competitor or offline habits.

**Why it matters for category expansion**  
Habit lock-in works both ways: bad experiences lock users *out* of Instamart, not into broader assortment.

**Representative voice**  
> "I stopped using it. I tried it again after a long time, and it's the same story."

**Suggested direction**  
Win-back flows should surface concrete service improvements, not generic coupons.

---

## Implications for the growth team

### Near-term (foundation)

1. **Fix trust before discovery** — Quality, delivery accuracy, and support are prerequisites for cross-category nudges.
2. **Target family households on replenishment** — Largest segment in data; most insights map to weekly grocery missions.
3. **Measure recovery, not just acquisition** — Win-back and issue-resolution metrics matter as much as new-category impressions.

### Medium-term (category expansion)

4. **Discovery barriers exist but are quieter** — `poor_discovery` (19) and `habit_lock_in` (12) are present; revisit after corpus grows.
5. **Test one adjacent category per trusted user** — e.g. personal care for habitual grocery replenisher with no recent complaints.
6. **Pair nudges with risk reducers** — Easy returns, freshness badges, and social proof for unfamiliar SKUs.

---

## What this summary does *not* claim

- Not representative of all Instamart MAUs (public review bias).
- Not causal—correlation between complaints and low category exploration only.
- Corpus is 12% enriched (119/969); insights will shift as Phase 2 completes.
- Category-discovery-specific signals are underrepresented vs operational complaints.

---

## Recommended next steps

| Priority | Action |
|---|---|
| 1 | Complete Phase 2 enrichment (remaining ~850 reviews) |
| 2 | Re-run Phase 3 aggregation when corpus ≥500 enriched |
| 3 | Human review of these 5 drafts; merge overlapping trust/support themes |
| 4 | Deep-dive `poor_discovery` and `habit_lock_in` clusters once trust noise is separated |
| 5 | Phase 4: map insights to experimentable hypotheses |

---

## Source files

- Full insights: `data/phase-3/insights.json`
- Theme clusters: `data/phase-3/theme-clusters.json`
- Technical report: `data/phase-3/insight-report.md`
