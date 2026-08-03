"""Exploratory analysis of Phase 1 normalized reviews to inform pre-LLM strategy."""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DB_PATH = PROJECT_ROOT / "data" / "phase-1" / "db" / "instamart_raw.sqlite"
OUTPUT_PATH = PROJECT_ROOT / "data" / "phase-1" / "pre-llm-analysis.json"
DOCS_PATH = PROJECT_ROOT / "Docs" / "phases" / "phase-2-enrichment" / "pre-llm-strategy.md"

# Keyword buckets for pre-LLM theme signal detection (not final taxonomy labels)
THEME_SIGNALS = {
    "delivery_speed": [
        "delivery", "late", "delay", "minutes", "fast", "quick", "time", "slot",
    ],
    "delivery_quality": [
        "wrong item", "missing", "damaged", "spoiled", "expired", "rotten", "packaging",
    ],
    "customer_support": [
        "support", "refund", "complaint", "customer care", "chat", "resolve", "response",
    ],
    "pricing_offers": [
        "price", "expensive", "discount", "offer", "coupon", "fee", "charge", "mrp",
    ],
    "product_quality": [
        "quality", "fresh", "stale", "fake", "authentic", "brand",
    ],
    "app_ux_discovery": [
        "app", "search", "browse", "ui", "interface", "find", "category", "navigate", "clutter",
    ],
    "habit_reorder": [
        "reorder", "same", "repeat", "regular", "every week", "usual", "habit",
    ],
    "category_exploration": [
        "personal care", "pet", "baby", "grocery", "snacks", "household", "never tried",
        "didn't know", "discover", "new category",
    ],
    "comparison_competitor": [
        "blinkit", "zepto", "bigbasket", "amazon", "better than", "compared",
    ],
}

NEGATIVE_WORDS = {"bad", "worst", "pathetic", "terrible", "horrible", "poor", "disappointed", "frustrat"}
POSITIVE_WORDS = {"good", "great", "love", "excellent", "amazing", "best", "happy", "satisfied"}


def load_reviews() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT source, body_text, title, rating, timestamp, word_count_hint FROM ("
        "SELECT *, length(body_text) - length(replace(body_text, ' ', '')) + 1 as word_count_hint "
        "FROM normalized_feedback)"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def word_count(text: str) -> int:
    return len(text.split())


def detect_themes(text: str) -> list[str]:
    lowered = text.lower()
    return [theme for theme, keywords in THEME_SIGNALS.items() if any(kw in lowered for kw in keywords)]


def sentiment_hint(text: str) -> str:
    lowered = text.lower()
    neg = sum(1 for w in NEGATIVE_WORDS if w in lowered)
    pos = sum(1 for w in POSITIVE_WORDS if w in lowered)
    if neg > pos:
        return "negative"
    if pos > neg:
        return "positive"
    return "neutral"


def top_ngrams(texts: list[str], n: int = 2, top: int = 25) -> list[tuple[str, int]]:
    counter: Counter = Counter()
    for text in texts:
        words = re.findall(r"[a-z]{3,}", text.lower())
        for i in range(len(words) - n + 1):
            gram = " ".join(words[i : i + n])
            if "instamart" not in gram and not any(w in gram for w in ("swiggy", "the", "and", "for")):
                continue
            counter[gram] += 1
    return counter.most_common(top)


def analyze(reviews: list[dict]) -> dict:
    word_counts = [word_count(r["body_text"]) for r in reviews]
    ratings = [r["rating"] for r in reviews if r.get("rating")]
    by_source = Counter(r["source"] for r in reviews)

    theme_counts: Counter = Counter()
    theme_by_rating: dict[str, Counter] = defaultdict(Counter)
    sentiment_counts: Counter = Counter()
    multi_theme = 0
    no_theme_signal = 0

    for r in reviews:
        text = f"{r.get('title') or ''} {r['body_text']}"
        themes = detect_themes(text)
        sent = sentiment_hint(text)
        sentiment_counts[sent] += 1
        if not themes:
            no_theme_signal += 1
        elif len(themes) > 1:
            multi_theme += 1
        for t in themes:
            theme_counts[t] += 1
            if r.get("rating"):
                theme_by_rating[t][r["rating"]] += 1

    # Length buckets for LLM batching
    short = sum(1 for w in word_counts if w <= 15)
    medium = sum(1 for w in word_counts if 16 <= w <= 50)
    long_ = sum(1 for w in word_counts if w > 50)

    bodies = [r["body_text"] for r in reviews]
    bigrams = top_ngrams(bodies, 2, 20)
    trigrams = top_ngrams(bodies, 3, 15)

    # Records needing long-context LLM (verbose complaints)
    long_reviews_pct = round(long_ / len(reviews) * 100, 1)

    return {
        "total_reviews": len(reviews),
        "by_source": dict(by_source),
        "rating_distribution": dict(sorted(Counter(ratings).items())),
        "negative_review_pct": round(Counter(ratings).get(1, 0) / len(ratings) * 100, 1) if ratings else 0,
        "word_count": {
            "min": min(word_counts),
            "max": max(word_counts),
            "avg": round(sum(word_counts) / len(word_counts), 1),
            "median": sorted(word_counts)[len(word_counts) // 2],
            "short_lte_15": short,
            "medium_16_50": medium,
            "long_gt_50": long_,
            "long_pct": long_reviews_pct,
        },
        "sentiment_hint": dict(sentiment_counts),
        "theme_signal_counts": dict(theme_counts.most_common()),
        "multi_theme_reviews": multi_theme,
        "no_theme_signal_reviews": no_theme_signal,
        "theme_by_rating": {k: dict(v) for k, v in theme_by_rating.items()},
        "top_bigrams": bigrams,
        "top_trigrams": trigrams,
        "llm_batch_recommendation": recommend_batching(len(reviews), word_counts),
    }


def recommend_batching(total: int, word_counts: list[int]) -> dict:
    avg_tokens_est = int(sum(word_counts) / len(word_counts) * 1.3)  # rough token estimate
    return {
        "strategy": "per_record_classification",
        "rationale": (
            "969 reviews with avg ~{avg} words each. Per-record Groq calls with taxonomy "
            "prompt keep traceability. Avoid dumping all reviews in one prompt."
        ).format(avg=round(sum(word_counts) / len(word_counts), 1)),
        "recommended_batch_size": 20,
        "estimated_groq_calls": total,
        "estimated_tokens_per_review": avg_tokens_est,
        "phase_3_aggregation": "group enriched records by barrier + mission labels, then Groq synthesizes themes from top clusters only",
        "do_before_llm": [
            "Run keyword theme signals (done in this analysis) to validate taxonomy coverage",
            "Sample 30 reviews for manual gold-label set",
            "Split Play Store dominant source (96%) — weight insights by source diversity",
            "Flag reviews >50 words for higher max_tokens",
            "Deduplicate near-identical complaints before enrichment",
        ],
    }


def write_strategy_doc(analysis: dict) -> None:
    a = analysis
    doc = f"""## Pre-LLM Strategy (Phase 1 Data Analysis)

Generated from **{a['total_reviews']}** normalized Instamart reviews.

## Dataset snapshot

| Metric | Value |
|---|---|
| Total reviews | {a['total_reviews']} |
| Play Store share | {a['by_source'].get('play_store', 0)} ({round(a['by_source'].get('play_store', 0)/a['total_reviews']*100, 1)}%) |
| 1-star reviews | {a['rating_distribution'].get(1, 0)} ({a['negative_review_pct']}%) |
| Avg words per review | {a['word_count']['avg']} |
| Reviews >50 words | {a['word_count']['long_gt_50']} ({a['word_count']['long_pct']}%) |

### Source breakdown

"""
    for src, cnt in sorted(a["by_source"].items(), key=lambda x: -x[1]):
        doc += f"- **{src}**: {cnt}\n"

    doc += f"""
### Rating distribution

"""
    for rating, cnt in a["rating_distribution"].items():
        doc += f"- {rating} star: {cnt}\n"

    doc += f"""
## What the data tells us (before Groq)

### 1. Sentiment skew is extreme

{a['negative_review_pct']}% of rated reviews are 1-star. Public feedback is heavily complaint-driven.
**Strategy:** Do not treat sentiment distribution as representative of all Instamart users. Use insights directionally. Separate **delivery/support complaints** from **category-discovery signals**.

### 2. Pre-LLM theme signals (keyword-based)

These keyword buckets estimate which taxonomy themes are likely present:

| Theme signal | Review count | Likely taxonomy mapping |
|---|---|---|
"""
    for theme, cnt in a["theme_signal_counts"].items():
        mapping = {
            "delivery_speed": "friction_types: delivery_experience, barriers: mission_narrowness",
            "delivery_quality": "trust_concerns: freshness_expiry, friction_types: delivery_experience",
            "customer_support": "friction_types: customer_support, barriers: past_bad_experience",
            "pricing_offers": "price_concerns, barriers: price_sensitivity",
            "product_quality": "trust_concerns, barriers: trust_quality",
            "app_ux_discovery": "barriers: poor_discovery, friction_types: navigation_ux",
            "habit_reorder": "barriers: habit_lock_in, habit_signal: true",
            "category_exploration": "barriers: low_awareness, experimentation_signal",
            "comparison_competitor": "context only — exclude from Instamart-only insights",
        }.get(theme, "—")
        doc += f"| {theme} | {cnt} | {mapping} |\n"

    doc += f"""
- **{a['multi_theme_reviews']}** reviews match multiple theme signals (need multi-label Groq output)
- **{a['no_theme_signal_reviews']}** reviews match no keyword bucket (Groq still needed — may be generic praise/complaint)

### 3. Review length affects LLM approach

| Bucket | Count | LLM approach |
|---|---|---|
| Short (≤15 words) | {a['word_count']['short_lte_15']} | Single-shot classification, low tokens |
| Medium (16–50 words) | {a['word_count']['medium_16_50']} | Standard enrichment prompt |
| Long (>50 words) | {a['word_count']['long_gt_50']} | Higher max_tokens; extract multiple barriers per review |

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
"""
    DOCS_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOCS_PATH.write_text(doc, encoding="utf-8")


def main() -> int:
    if not DB_PATH.exists():
        print(f"No database at {DB_PATH}. Run Phase 1 pipeline first.")
        return 1

    reviews = load_reviews()
    # Fix word count in load - simpler approach
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    reviews = [dict(r) for r in conn.execute("SELECT * FROM normalized_feedback").fetchall()]
    conn.close()

    analysis = analyze(reviews)
    OUTPUT_PATH.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    write_strategy_doc(analysis)

    print(json.dumps({
        "total": analysis["total_reviews"],
        "theme_signals": analysis["theme_signal_counts"],
        "negative_pct": analysis["negative_review_pct"],
        "avg_words": analysis["word_count"]["avg"],
        "docs": str(DOCS_PATH),
        "json": str(OUTPUT_PATH),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
