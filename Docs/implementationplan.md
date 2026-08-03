## Phase-Wise Implementation Plan

This plan describes how the Swiggy Instamart category-discovery AI agent is implemented.

**Current status:** Phases **0–5 (analytical V1)** are complete.  
**Next work:** Phase **6 (product shell)** — FastAPI backend + React frontend — as defined in `Docs/architecture.md`.

Order of risk reduction:

1. problem framing and taxonomy
2. data pipeline
3. AI enrichment and insights
4. recommendation and pilot readiness
5. productize outputs through backend + frontend

Architecture reference: `Docs/architecture.md`

---

## Status Snapshot

| Phase | Name | Status |
|---|---|---|
| 0 | Problem Framing And Taxonomy | **Done** |
| 1 | Data Ingestion And Storage | **Done** |
| 2 | Cleaning, Normalization, And Enrichment | **Done** (partial enrichment; resume as quota allows) |
| 3 | Theme Detection And Insight Generation | **Done** |
| 4 | Recommendation Framing | **Done** |
| 5 | Pilot, Review, And Measurement Readiness | **Done** |
| 6A | Backend API | **Done** |
| 6B | Frontend Dashboard | **Done** |
| 6C | Review, Jobs, And Hardening | **Done** |

---

## Phase 0: Problem Framing And Taxonomy

Status: **Done**

Objective:
Define the business questions, output schema, taxonomy, and success metrics before building the pipeline.

Key tasks:

- align on the primary business goal: increase monthly new-category adoption
- define the core analysis questions from the problem statement
- create the first taxonomy for barriers, triggers, missions, and segments
- define the canonical output schema for each feedback item
- decide what qualifies as an insight versus a hypothesis

Deliverables:

- taxonomy v1 (later extended to v1.1.0 for discovery fields)
- structured analysis schema
- source inventory
- evaluation rubric for insight quality

Evaluation document:
`Docs/phases/phase-0-problem-framing/eval.md`

---

## Phase 1: Data Ingestion And Storage

Status: **Done**

Objective:
Collect feedback from target sources and store it in a reproducible raw-data layer.

Key tasks:

- build source connectors for priority sources
- capture raw text plus metadata
- create batch identifiers and logging
- handle retries, deduplication inputs, and ingestion failures
- define raw and normalized storage tables

Deliverables:

- working collectors for initial sources
- raw storage schema
- ingestion logging and batch tracking
- first seed dataset
- normalized SQLite store under `data/phase-1/`

Evaluation document:
`Docs/phases/phase-1-ingestion/eval.md`

---

## Phase 2: Cleaning, Normalization, And Enrichment

Status: **Done** (cohort enrichment continues as Groq quota resets)

Objective:
Transform a **capped cohort** of normalized feedback (up to **1,000 reviews**) into analysis-ready records enriched with structured AI labels using **Groq**, without exceeding free-tier rate limits.

LLM provider: **Groq** — model `llama-3.3-70b-versatile` for Phase 2 enrichment (Phases 3–4 use the same API with a reserved daily request budget).

### Groq rate limits (planning assumptions)

| Limit | Quota | How we stay under it |
|---|---|---|
| RPM | 30 | Client throttle: **10 requests/min** |
| RPD | 1,000 | ≤130 enrichment/day + **50 reserved** for Phase 3 / gold set |
| TPM | 12,000 | 10 RPM × ~650 tok/call ≈ 6,500 TPM (buffer) |
| TPD | 100,000 | **130 reviews/day** × ~650 tok ≈ 84.5K + headroom |

**Important:** 1,000 reviews at ~650 tokens each ≈ **650K tokens total** — enrichment spans **~7–8 calendar days**, not one run.

### Corpus cap and sampling

- Target: **1,000 reviews**
- Source: Phase 1 `normalized_feedback` (English, 5+ words, emoji-free)
- Sampling (see `Docs/phases/phase-2-enrichment/pre-llm-strategy.md`):
  1. Dedupe near-identical bodies
  2. Prioritize category-discovery signals (`category_exploration`, `habit_reorder`, `app_ux_discovery`)
  3. Stratify by star rating; retain all non–Play Store sources
  4. Random fill to 1,000; persist cohort in `data/phase-2/enrichment-cohort.json`

### Key tasks

**Pre-LLM (no API calls):**

- build deterministic enrichment cohort (≤1,000)
- manually gold-label **30 reviews** (10 short / 10 medium / 10 long)
- run keyword theme analysis (`analyze_pre_llm.py`)

**Groq enrichment (rate-limited):**

- process reviews in micro-batches of **8** by default (configurable in the **5–8** range); persist one enriched row per review
- compact taxonomy prompt; cap review body at **100 words** in the prompt
- validate output against `schemas/enriched-feedback.schema.json` and taxonomy
- checkpoint every **20** records; resume from last `record_id` on failure
- exponential backoff on HTTP 429; enforce daily cap before starting new batch

Deliverables:

- Groq enrichment client with throttle, checkpoint, and daily-cap logic
- `data/phase-2/enrichment-cohort.json`
- `data/phase-2/db/enriched.sqlite`
- versioned classification prompts
- gold-set export / evaluation path

Evaluation document:
`Docs/phases/phase-2-enrichment/eval.md`

---

## Phase 3: Theme Detection And Insight Generation

Status: **Done**

Objective:
Aggregate enriched records into repeated themes and turn them into traceable insights using **minimal Groq calls** (cluster summaries only).

Key tasks:

- group enriched records by barrier, mission, and category
- quantify theme frequency by source and segment
- identify co-occurring themes
- balance insights across discovery, behaviour, opportunity, and operational buckets
- draft evidence-linked insights (live Groq or dry-run)
- produce discovery / shopping-behaviour / category-opportunity / segment reports

Deliverables:

- theme aggregation logic
- insight generation pipeline
- evidence-linked insight report
- stakeholder summary
- category-discovery focused JSON reports under `data/phase-3/`

Evaluation document:
`Docs/phases/phase-3-insight-generation/eval.md`

---

## Phase 4: Recommendation Framing

Status: **Done**

Objective:
Convert validated insights into product opportunity areas without jumping directly to implementation.

Key tasks:

- map each validated barrier to one or more product opportunities
- classify opportunities as discovery, trust, pricing, assortment, or service
- estimate business relevance by affected segment size and strategic importance
- define experimentable hypotheses for the growth team
- keep non-causality caveats explicit

Deliverables:

- `data/phase-4/opportunity-map.json`
- `data/phase-4/hypothesis-backlog.json`
- `data/phase-4/experiment-framing-memo.md`

Evaluation document:
`Docs/phases/phase-4-recommendation-framing/eval.md`

---

## Phase 5: Pilot, Review, And Measurement Readiness

Status: **Done**

Objective:
Pilot the agent with stakeholders and confirm it is reliable enough to support experiment planning.

Key tasks:

- run the full pipeline on a meaningful sample
- compare AI themes against pre-LLM keyword analysis
- capture stakeholder feedback in structured form
- log prompt, taxonomy, and threshold refinements
- define experiment metrics and guardrails
- produce growth handoff package

Deliverables:

- `data/phase-5/pilot-report.md`
- `data/phase-5/stakeholder-feedback-summary.md`
- `data/phase-5/refinements-log.json`
- `data/phase-5/measurement-framework.json`
- `data/phase-5/growth-handoff-package.md`

Evaluation document:
`Docs/phases/phase-5-pilot/eval.md`

---

## Phase 6: Product Shell (Backend + Frontend)

Status: **Done** (6A + 6B + 6C)

Objective:
Turn the completed Phase 0–5 analysis engine into a usable internal product with a proper backend API and stakeholder frontend.

Architecture reference:
`Docs/architecture.md` (V1.5 Product Shell)

### Guiding rule

The product shell must **call existing Phase 1–5 pipelines**.  
It must **not** rewrite enrichment, aggregation, insight, recommendation, or pilot logic.

### Stack decision

| Layer | Choice |
|---|---|
| Backend | **FastAPI** |
| Frontend | **React + TypeScript (Vite)** |
| Pipeline reuse | `src/instamart_analyser/phases/*` |
| Storage (pilot) | Existing SQLite + `data/phase-*` artifacts |
| Storage (later) | Optional Postgres / Supabase |
| Auth | Simple JWT/session + roles (`viewer`, `reviewer`, `admin`) |
| LLM secrets | Server-side only (`GROQ_API_KEY` never sent to browser) |

### Suggested package layout

```text
src/instamart_analyser/
  api/                 # FastAPI app
    main.py
    routes/
    services/
    schemas/
  phases/              # existing Phase 1–5 code (unchanged responsibility)
web/                   # React frontend
  src/pages/
  src/components/
  src/api/
```

---

## Phase 6A: Backend API

Status: **Done**

Objective:
Expose analysis outputs and controlled pipeline jobs through a stable REST API.

### Key tasks

- create FastAPI app skeleton and health endpoint
- build artifact repositories that read Phase 2–5 outputs
- implement read APIs for overview, insights, themes, opportunities, hypotheses, measurement, and reports
- implement job APIs that trigger Phase 2 enrich / Phase 3–5 refresh as background jobs
- expose enrichment coverage and Groq quota/progress state
- add insight review status updates (`draft` / `approved` / `rejected` / `hypothesis`)
- accept stakeholder feedback submissions
- add basic auth/roles for viewer, reviewer, and admin

### Core endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Liveness |
| `GET` | `/api/overview` | Coverage, top themes, pilot readiness |
| `GET` | `/api/insights` | Insight list + filters |
| `GET` | `/api/insights/{id}` | Insight detail + evidence |
| `PATCH` | `/api/insights/{id}/status` | Review decision |
| `GET` | `/api/themes` | Theme clusters / barrier rankings |
| `GET` | `/api/opportunities` | Opportunity map |
| `GET` | `/api/hypotheses` | Hypothesis backlog |
| `GET` | `/api/measurement` | Metrics + guardrails |
| `GET` | `/api/reports/{name}` | Markdown/JSON report content |
| `GET` | `/api/jobs` | Job list |
| `POST` | `/api/jobs/enrich` | Resume Phase 2 enrichment |
| `POST` | `/api/jobs/phase3` | Refresh insights |
| `POST` | `/api/jobs/phase4` | Refresh opportunities |
| `POST` | `/api/jobs/phase5` | Refresh pilot package |
| `GET` | `/api/jobs/{id}` | Job status |
| `POST` | `/api/feedback` | Stakeholder feedback |

### Deliverables

- FastAPI service under `src/instamart_analyser/api/`
- OpenAPI docs for all endpoints
- Job runner that reuses Phase 2–5 CLI/pipeline entrypoints
- Review and feedback persistence (local SQLite table or JSON store initially)
- Backend README with run instructions

### Exit criteria

- frontend can load overview and insights from API without reading files directly
- enrichment job can be started and polled safely
- Groq key remains server-side only
- API responses include confidence, sample size, and bias notes where relevant

---

## Phase 6B: Frontend Dashboard

Status: **Done**

Objective:
Give product, research, and growth stakeholders a dashboard instead of requiring CLI or manual file browsing.

### Key tasks

- scaffold React + TypeScript (Vite) app in `web/`
- connect to FastAPI with typed API client
- build Overview page (coverage, top barriers, pilot badge, bias warning)
- build Insights list + insight detail with evidence quotes
- build Opportunities page by type and priority
- build Experiments page from hypothesis backlog + measurement framework
- show empty/loading/error states clearly
- keep evidence / interpretation / recommendation visually separated

### Primary screens

1. **Overview** — enrichment coverage, top themes, pilot readiness
2. **Insights** — filterable cards + detail with evidence
3. **Opportunities** — trust / discovery / pricing / assortment map
4. **Experiments** — hypotheses, metrics, guardrails, handoff summary
5. **Review queue** — draft insights awaiting decision
6. **Pipeline jobs** — run status, quota, last refresh times

### Deliverables

- React app under `web/`
- working local demo (`localhost:5173` → `localhost:8000`)
- frontend README with setup and env vars
- stakeholder-usable navigation across insights → opportunities → experiments

### Exit criteria

- non-technical user can understand top findings without opening `data/` files
- every insight detail shows supporting evidence
- bias and sample-size caveats are visible on Overview and Insights
- dashboard works for the current partial enrichment sample

---

## Phase 6C: Review, Jobs, And Hardening

Status: **Done**

Objective:
Make the product shell reliable enough for repeated internal use.

### Key tasks

- wire Review Queue actions to backend status updates
- add stakeholder feedback form in UI
- enforce single active enrichment job
- surface Groq daily-cap / 429 states in Jobs UI
- add basic role gates (viewer vs reviewer vs admin)
- add smoke tests for critical API routes
- optional: Postgres/Supabase when multi-user persistence is required
- optional: scheduled daily enrichment resume worker

### Deliverables

- end-to-end reviewer workflow
- jobs UI with progress and failure reasons
- feedback capture loop connected to Phase 5-style summary refresh
- short ops checklist for demo / internal pilot

### Exit criteria

- reviewer can approve/reject insights from UI
- admin can trigger Phase 3/4/5 refresh from UI
- enrichment failures are visible and recoverable
- known limitations remain documented in product UI

---

## Suggested Timeline

### Completed analytical V1

- Phase 0: 3 to 5 days
- Phase 1: 1 to 2 weeks
- Phase 2: 1 to 2 weeks (plus ongoing throttled enrichment)
- Phase 3: 1 week
- Phase 4: 3 to 5 days
- Phase 5: 1 week

### Planned product shell V1.5

- Phase 6A Backend API: **Done**
- Phase 6B Frontend Dashboard: **Done**
- Phase 6C Review / Jobs / Hardening: **Done**
- Research Intelligence UX (additive Overview + ingest jobs): **Done**
- Research explorer pages (sources, reviews, challenges, themes, segments, root causes, unmet
  needs, journey, validation) + persistent sidebar Pipeline Actions: **Done**

Ops checklist:
`Docs/phases/phase-6-product-shell/ops-checklist.md`

Research UX notes:
`Docs/phases/phase-6-product-shell/research-intelligence-ux.md`

---

## Dependencies Between Phases

- Phase 1 depends on source selection and schema decisions from Phase 0
- Phase 2 depends on Phase 1 normalized output and a configured `GROQ_API_KEY`
- Phase 3 depends on usable enrichment quality from Phase 2
- Phase 4 depends on validated insights from Phase 3
- Phase 5 depends on end-to-end outputs from Phases 1 to 4
- **Phase 6A depends on Phase 3–5 artifacts already existing under `data/`**
- **Phase 6B depends on Phase 6A read APIs**
- **Phase 6C depends on Phase 6A write/job APIs and Phase 6B screens**

---

## Definition Of Done

### Analytical V1 (Phases 0–5) — complete when:

- pipeline runs end to end
- insights are evidence-backed and repeatable
- opportunity / hypothesis handoff exists for growth

### Product shell V1.5 (Phase 6) — complete when:

- stakeholders can explore insights and opportunities in a frontend without CLI use
- backend serves artifacts and controlled pipeline jobs
- reviewers can approve/reject insights in-product
- growth can move from dashboard → hypothesis → measurement handoff
- enrichment progress and Groq limits are visible in the UI

---

## Immediate Next Actions

1. ~~Implement Phase **6A** FastAPI skeleton with `/api/overview` and `/api/insights`~~
2. ~~Implement Phase **6B** Overview + Insights pages against those APIs~~
3. ~~Harden Review + Jobs flows (Phase **6C**)~~
4. Continue Phase 2 enrichment whenever Groq quota resets
5. Refresh Phases 3–5 after meaningful enrichment growth, then re-serve via API/dashboard
6. Optional later: Postgres/Supabase multi-user persistence
