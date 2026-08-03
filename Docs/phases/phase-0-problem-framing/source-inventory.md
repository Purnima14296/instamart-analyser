## Source Inventory

Platform focus: Swiggy Instamart user feedback and quick-commerce category-discovery discussions.

Priority sources are ranked for Phase 1 ingestion. P0 sources are required for the first pipeline run; P1 sources follow in subsequent iterations.

## Priority Matrix

| Priority | Source | Data type | Access method | Expected signal | Phase 1 scope |
|---|---|---|---|---|---|
| P0 | Google Play Store reviews | App reviews | Play Store scraper / API / export | Delivery, UX, habit, discovery friction | Yes |
| P0 | Apple App Store reviews | App reviews | App Store scraper / RSS / export | Same as Play Store, iOS user base | Yes |
| P0 | Reddit (r/swiggy, r/india, r/IndianFood, quick-commerce threads) | Community discussions | Reddit API (PRAW) / Pushshift archive | Unfiltered opinions, category behavior | Yes |
| P1 | Twitter / X | Social media | API / manual export | Real-time complaints, praise | No (Phase 1.1) |
| P1 | YouTube comments | Social media | YouTube Data API | Review-style feedback on Instamart | No (Phase 1.1) |
| P1 | MouthShut / Sitejabber | Product reviews | Web scraping | Detailed service reviews | No (Phase 1.1) |
| P2 | Quora | Community forums | Web scraping | Long-form opinions | No |
| P2 | Facebook groups | Community forums | Manual / limited API | Local community feedback | No |
| P2 | Competitor reviews (Blinkit, Zepto) | Comparative context | Play/App Store | Category exploration benchmarks | No |

## Source Metadata Requirements

Every record from any source must capture:

| Field | Required | Notes |
|---|---|---|
| `source` | Yes | Enum: see `schemas/feedback-record.schema.json` |
| `source_record_id` | Yes | Unique per source |
| `url` | Yes when available | Link back to original |
| `timestamp` | Yes | UTC ISO 8601 |
| `title` | No | Review title or post subject |
| `body_text` | Yes | Raw text content |
| `rating` | No | 1–5 for app reviews |
| `author` | No | Public handle only |
| `language` | Yes | ISO 639-1 code |
| `collection_batch_id` | Yes | Pipeline run identifier |

## Search Queries And Filters

### Reddit

- Subreddits: `swiggy`, `india`, `bangalore`, `mumbai`, `delhi`, `IndianFood`
- Keywords: `instamart`, `swiggy instamart`, `quick commerce`, `grocery delivery`, `10 minute delivery`
- Sort: relevance, top (past year), new
- Flair filters where available

### App Store / Play Store

- App: Swiggy (filter reviews mentioning Instamart/grocery)
- Sort: most recent, most helpful
- Rating filter: all (do not exclude low ratings)

## Known Limitations

| Source | Limitation | Mitigation |
|---|---|---|
| App Store reviews | Not all reviews mention Instamart specifically | Filter by keyword; accept lower recall |
| Reddit | Vocal minority, demographic skew | Treat as directional; cross-reference sources |
| Social media | High noise, bot content | Keyword filtering + manual sampling |
| Scraping | Rate limits, ToS restrictions | Respect robots.txt; use official APIs where possible |

## Volume Targets (Phase 1)

| Source | Minimum records (first batch) | Target records |
|---|---|---|
| Play Store | 200 | 500 |
| App Store | 200 | 500 |
| Reddit | 100 | 300 |
| **Total** | **500** | **1,300** |

## Data Retention

- Raw records: retained indefinitely (per decision D-003)
- Normalized records: retained with `taxonomy_version` tag
- PII: do not collect or store private user data beyond public handles
