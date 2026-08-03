## Taxonomy v1

Version: `1.0.0`  
Platform: Swiggy Instamart  
Status: approved for Phase 1 implementation

Machine-readable copy: `schemas/taxonomy-v1.json`

## Design Rules

1. Each label must have a clear definition and at least one example.
2. A single feedback item may have multiple labels across dimensions.
3. Prefer the most specific label; use `other` only when no label fits.
4. Barriers describe **why exploration fails**; triggers describe **what prompted action**.
5. Do not confuse `shopping_mission` (intent) with `barriers` (blockers).

---

## 1. Product Categories

| Label | Definition | Example |
|---|---|---|
| `grocery` | Fresh produce, staples, dairy, cooking ingredients | "Ordered vegetables and dal again" |
| `snacks_beverages` | Chips, drinks, ready-to-eat snacks | "Only buy Coke and chips late night" |
| `household_essentials` | Cleaning, laundry, tissues, disposables | "Detergent and dish soap every month" |
| `personal_care` | Skincare, haircare, grooming, hygiene | "Never tried their shampoo section" |
| `baby_products` | Diapers, baby food, infant care | "Didn't know they sell baby wipes" |
| `pet_supplies` | Pet food, litter, accessories | "Wish they had cat food" |
| `home_needs` | Kitchen tools, storage, home improvement | "Bought bulbs once, didn't browse more" |
| `health_wellness` | OTC health, supplements, wellness | "Couldn't find my vitamin brand" |
| `other` | Category not listed above | — |

---

## 2. Shopping Missions

| Label | Definition | Example |
|---|---|---|
| `replenishment` | Restocking regularly purchased items | "Same grocery list every week" |
| `urgent_need` | Immediate, time-sensitive purchase | "Needed milk in 10 minutes" |
| `browse_discover` | Exploring without a fixed list | "Just scrolling to see what's new" |
| `deal_hunting` | Motivated by discounts or offers | "Only order when there's a coupon" |
| `occasion_based` | Tied to an event or situation | "Party snacks for guests tonight" |
| `recipe_driven` | Shopping for a specific meal or recipe | "Needed ingredients for pasta" |
| `other` | Mission not listed above | — |

---

## 3. Barriers (Why users stay in familiar categories)

| Label | Definition | Example |
|---|---|---|
| `habit_lock_in` | Repeat behavior without considering alternatives | "I always order the same 10 items" |
| `poor_discovery` | User cannot find or notice other categories | "Never saw the pet food section" |
| `low_awareness` | User doesn't know Instamart carries the category | "Didn't know they sell baby products" |
| `trust_quality` | Doubts about product authenticity or freshness | "Worried about expiry dates on skincare" |
| `price_sensitivity` | Perceives new categories as too expensive | "Personal care is cheaper on other apps" |
| `assortment_gap` | Desired brands or SKUs unavailable | "They don't have my preferred pet food brand" |
| `information_gap` | Insufficient product details to decide | "No reviews or ingredient info" |
| `cognitive_overload` | Too many choices, decision fatigue | "App is overwhelming, I stick to search" |
| `mission_narrowness` | User enters with a single-item goal and exits | "Came for bread, left immediately" |
| `past_bad_experience` | Previous negative experience blocks retry | "Got wrong item once, won't try new stuff" |
| `delivery_fee_threshold` | Won't add items that push cart below free delivery | "Adding one item ruins my free delivery" |
| `other` | Barrier not listed above | — |

---

## 4. Triggers (What prompts category exploration)

| Label | Definition | Example |
|---|---|---|
| `life_event` | Major life change creates new need | "Got a puppy, started buying pet food" |
| `promotion_offer` | Discount or coupon drives trial | "50% off personal care made me try" |
| `recommendation` | Friend, influencer, or in-app suggestion | "Saw it in 'frequently bought together'" |
| `out_of_stock_substitute` | Usual item unavailable, tries alternative category | "My brand was OOS, tried a new one" |
| `seasonal_need` | Weather, festival, or season drives purchase | "Summer heat made me buy sunscreen" |
| `bundle_combo` | Cross-category bundle encourages trial | "Snack + drink combo introduced me to new brand" |
| `search_intent` | User actively searches for something new | "Searched for cat litter specifically" |
| `homepage_feature` | Featured collection or banner exposure | "Saw 'new arrivals' in personal care" |
| `other` | Trigger not listed above | — |

---

## 5. Discovery Channels (How users find products today)

| Label | Definition |
|---|---|
| `search` | Uses search bar with specific query |
| `reorder_previous` | Reorders from order history or saved list |
| `homepage_browse` | Scrolls homepage or category tiles |
| `recommendation_engine` | Clicks suggested or "you may also like" items |
| `promotional_banner` | Clicks offer banners or deal sections |
| `external_referral` | Arrives via social media, friend, or ad |
| `notification` | Opens app from push notification |
| `other` | Channel not listed above |

---

## 6. User Segment Hypotheses

| Label | Definition |
|---|---|
| `new_user` | First 30 days on Instamart |
| `habitual_replenisher` | Mostly repeat orders, same categories |
| `deal_seeker` | Price and offers drive behavior |
| `family_household` | Multi-person household, larger baskets |
| `single_professional` | Small, frequent, convenience-driven orders |
| `student` | Budget-conscious, snack-heavy |
| `parent` | Baby or child-related needs |
| `pet_owner` | Pet-related purchase patterns |
| `health_conscious` | Wellness and organic preferences |
| `explorer` | Already tries multiple categories |
| `other` | Segment not listed above |

---

## 7. Friction Types

| Label | Definition |
|---|---|
| `app_performance` | Crashes, slow load, bugs |
| `search_relevance` | Search returns poor or irrelevant results |
| `navigation_ux` | Hard to find categories or products |
| `checkout_payment` | Payment or checkout issues |
| `delivery_experience` | Late delivery, wrong items, packaging |
| `pricing_transparency` | Hidden fees, confusing MRP vs offer price |
| `product_information` | Missing images, descriptions, reviews |
| `customer_support` | Refund, complaint, or support issues |
| `other` | Friction not listed above |

---

## 8. Sentiment

| Label | Definition |
|---|---|
| `positive` | Expresses satisfaction or praise |
| `negative` | Expresses dissatisfaction or complaint |
| `mixed` | Contains both positive and negative elements |
| `neutral` | Factual, no clear sentiment |

---

## 9. Signal Flags (Boolean enrichments)

| Field | Definition |
|---|---|
| `habit_signal` | Evidence of repetitive, same-category behavior |
| `experimentation_signal` | Evidence of trying new categories or products |
| `urgency_context` | Time pressure mentioned |
| `convenience_signal` | Convenience or speed as primary motivator |

---

## 10. Concern Sub-Taxonomies

### Trust concerns (`trust_concerns[]`)

`authenticity`, `freshness_expiry`, `packaging_damage`, `counterfeit_fear`, `brand_reliability`, `other`

### Price concerns (`price_concerns[]`)

`too_expensive`, `better_price_elsewhere`, `delivery_fee`, `minimum_order`, `misleading_discount`, `other`

### Assortment concerns (`assortment_concerns[]`)

`brand_missing`, `sku_missing`, `limited_variety`, `out_of_stock`, `other`

### Information gaps (`information_gaps[]`)

`no_reviews`, `no_ingredients`, `no_size_guide`, `no_comparison`, `unclear_category_placement`, `other`

---

## Labeling Guidelines

1. **Barriers vs friction:** A barrier blocks category exploration; friction is any pain point (may or may not block exploration).
2. **Triggers vs discovery channels:** A trigger is the catalyst; a discovery channel is the mechanism used.
3. **Multiple labels allowed:** "I always reorder groceries and never noticed pet food" → `habit_lock_in` + `poor_discovery` + `low_awareness`.
4. **Confidence required:** Every enrichment must include a confidence score (0.0–1.0).

## Versioning

- Increment minor version when adding labels.
- Increment major version when renaming or removing labels.
- All pipeline runs must record `taxonomy_version` in enriched output.
