## AI Agent Architecture

This document describes the architecture for the Swiggy Instamart category-discovery AI agent **after Phase 5**.

Phases 0–5 delivered a working offline analysis pipeline (ingest → enrich → insight → opportunity → pilot handoff).  
The next product step is to wrap that pipeline in a **proper backend API** and **stakeholder frontend**, so growth, product, and research teams can use the system without running Python CLIs.

## Goals

- ingest user feedback from multiple public and internal-compatible sources
- normalize noisy text into a consistent analysis-ready format
- classify feedback into themes, jobs, barriers, and user segments
- detect repeated patterns across channels
- generate traceable insights with supporting evidence
- expose reusable outputs through a **backend API**
- present insights, opportunities, and experiment handoffs in a **frontend dashboard**
- keep human review and evidence traceability in the product experience

## Scope

### What exists today (V1 — Phases 0–5)

- Python pipelines for Phases 1–5
- Local SQLite + JSON/Markdown artifacts under `data/`
- Groq-powered enrichment and insight drafting
- Pilot, measurement, and growth handoff package

### What this architecture adds next (V1.5 — Product Shell)

- FastAPI backend that serves stored analysis results and triggers jobs
- React frontend dashboard for stakeholders
- Job status, enrichment progress, and artifact browsing
- Review workflow for draft → approved insights

### Still out of scope

- real-time personalization inside the Instamart consumer app
- direct ranking / merchandising changes in production
- autonomous decision-making without human review
- causal claims without experimental support

---

## System Overview

```text
┌──────────────────┐     ┌──────────────────────────────┐     ┌────────────────────┐
│ Public / seed    │     │ Backend (FastAPI)            │     │ Frontend (React)   │
│ sources          │────▶│                              │◀────│ Stakeholder UI     │
│ Play/App Store,  │     │ - REST API                   │     │ - Overview         │
│ Reddit, forums,  │     │ - Auth / roles               │     │ - Insights         │
│ social, seed     │     │ - Job runner (pipelines)     │     │ - Opportunities    │
└──────────────────┘     │ - Artifact service           │     │ - Experiments      │
                         │ - Review service             │     │ - Review queue     │
                         └──────────────┬───────────────┘     └────────────────────┘
                                        │
                         ┌──────────────▼───────────────┐
                         │ Data + Pipeline Core         │
                         │ Phase 1–5 Python packages    │
                         │ SQLite / JSON artifacts      │
                         │ Groq enrichment + synthesis  │
                         └──────────────────────────────┘
```

The analytical brain remains the Phase 1–5 pipeline.  
The backend and frontend are the product interface around that brain.

---

## Current State After Phase 5

| Layer | Status | Location |
|---|---|---|
| Taxonomy + schemas | Done | `schemas/`, Phase 0 docs |
| Ingestion + normalization | Done | `src/.../phase_1/`, `data/phase-1/` |
| Enrichment (Groq) | Done (partial cohort) | `src/.../phase_2/`, `data/phase-2/` |
| Themes + insights | Done | `src/.../phase_3/`, `data/phase-3/` |
| Recommendation framing | Done | `src/.../phase_4/`, `data/phase-4/` |
| Pilot + measurement handoff | Done | `src/.../phase_5/`, `data/phase-5/` |
| Backend API | **Done (Phase 6A/6C)** | `src/instamart_analyser/api/` |
| Frontend dashboard | **Done (Phase 6B/6C)** | `web/` |
| Research Intelligence UX | **Done (additive)** | `/api/research/summary` + Overview/Jobs upgrades |
| Research explorer pages | **Done (additive)** | `/api/explore/*` backing 9 nav pages + sidebar Pipeline Actions |

See `Docs/phases/phase-6-product-shell/research-intelligence-ux.md` for score formulas and
non-removal guarantees.

---

## High-Level Components

### 1. Source Connectors

Collectors pull data from:

- App Store reviews
- Play Store reviews
- Reddit discussions
- community forums
- social media posts
- product review pages
- other quick-commerce discussions

Each connector handles retrieval, rate-limit handling, pagination, retries, and metadata capture.

### 2. Raw And Normalized Data Store

All collected records are stored before and after transformation for auditability and reruns.

Typical fields:

- source
- source_record_id
- author handle if public
- timestamp
- rating if available
- title
- body text
- url
- language
- collection batch id

V1 storage:

- SQLite: `data/phase-1/db/instamart_raw.sqlite`
- Enriched SQLite: `data/phase-2/db/enriched.sqlite`
- Phase 3–5 JSON/Markdown reports under `data/phase-3/` … `data/phase-5/`

V1.5 storage direction:

- keep SQLite for local / pilot deployments
- optional Postgres (or Supabase Postgres) when multi-user backend is required
- keep artifact files for report export and audit trail

### 3. Cleaning And Normalization Layer

Removes duplicates, strips boilerplate, detects language, standardizes dates, and converts records into a unified schema.

Outputs:

- normalized text
- cleaned metadata
- dedupe hash
- confidence flags

### 4. Analysis And Enrichment Layer

Core AI layer using **Groq** prompts, deterministic rules, and schema validation.

Groq is used for:

- per-record taxonomy labeling (Phase 2)
- theme synthesis / insight drafting (Phase 3)
- optional recommendation phrasing support (Phase 4)

Expected tags:

- category mentioned
- adjacent category opportunity
- shopping mission
- sentiment
- friction type
- trust concern
- price concern
- discovery barrier
- experimentation signal
- user segment hypothesis
- urgency or replenishment context

### 5. Theme And Pattern Engine

Aggregates enriched feedback to quantify barriers, missions, segments, discovery triggers, and co-occurring themes.

### 6. Insight And Recommendation Layer

Produces:

- evidence-backed insights
- opportunity map
- prioritized hypothesis backlog
- experiment framing memo
- measurement framework + growth handoff

### 7. Review And Validation Layer

Human review before high-impact conclusions are treated as approved.

Reviewers check:

- evidence correctness
- theme interpretation
- actionability
- bias / uncertainty notes

### 8. Backend API Layer (new)

A FastAPI service that:

- reads pipeline outputs
- triggers Phase 1–5 jobs
- exposes status and progress
- supports insight review actions
- serves dashboard data safely to the frontend

### 9. Frontend Delivery Layer (new)

A React stakeholder app that replaces “open markdown files locally” with:

- live overview of enrichment and insight status
- browsable insights with evidence
- opportunity / hypothesis board
- pilot readiness and measurement views
- reviewer workflow

---

## Backend Architecture

### Responsibility

The backend is the only process the frontend talks to.  
It owns auth, job execution, artifact access, and write actions (review status, feedback).

### Recommended stack

| Concern | Choice | Why |
|---|---|---|
| API framework | **FastAPI** | Same Python runtime as existing pipelines |
| Job execution | Background tasks / simple worker queue | Enrichment can take minutes–hours |
| Auth | Session or JWT + role claims | Separate viewer vs reviewer vs admin |
| Validation | Pydantic models | Align with existing JSON schemas |
| Storage access | Repository layer over SQLite/Postgres | Keep pipeline code reusable |
| Config | `.env` + settings module | Reuse `GROQ_*` and path config |

Suggested package layout:

```text
src/instamart_analyser/
  api/                 # FastAPI app
    main.py
    deps.py
    routes/
      health.py
      overview.py
      insights.py
      opportunities.py
      jobs.py
      reviews.py
      reports.py
    schemas/
    services/
  phases/              # existing Phase 1–5 pipelines
  common/
web/                   # frontend app
```

### Core API surface

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Liveness |
| `GET` | `/api/overview` | Counts, coverage, bias notes, pilot readiness |
| `GET` | `/api/insights` | List insights (filter by confidence/status/segment) |
| `GET` | `/api/insights/{id}` | Insight detail + evidence |
| `PATCH` | `/api/insights/{id}/status` | draft → approved / rejected / hypothesis |
| `GET` | `/api/themes` | Theme clusters and barrier rankings |
| `GET` | `/api/opportunities` | Phase 4 opportunity map |
| `GET` | `/api/hypotheses` | Prioritized backlog |
| `GET` | `/api/measurement` | Metrics + guardrails |
| `GET` | `/api/reports/{name}` | Markdown/JSON report content |
| `GET` | `/api/jobs` | Recent pipeline jobs |
| `POST` | `/api/jobs/enrich` | Resume Phase 2 enrichment |
| `POST` | `/api/jobs/phase3` | Refresh insights |
| `POST` | `/api/jobs/phase4` | Refresh opportunities |
| `POST` | `/api/jobs/phase5` | Refresh pilot package |
| `GET` | `/api/jobs/{id}` | Job status / logs summary |
| `POST` | `/api/feedback` | Stakeholder feedback responses |

### Backend services

1. **ArtifactService**  
   Reads Phase 3–5 JSON/MD outputs and maps them to API responses.

2. **EnrichmentStatusService**  
   Reads enriched SQLite + usage tracker for coverage and quota state.

3. **JobService**  
   Starts Phase pipelines as background jobs; stores run id, status, timestamps, errors.

4. **ReviewService**  
   Updates insight/opportunity review status without rewriting evidence.

5. **HandoffService**  
   Serves measurement framework + growth handoff package for the Experiments page.

### Auth And Roles

| Role | Can view dashboards | Can approve insights | Can trigger jobs |
|---|---|---|---|
| viewer | yes | no | no |
| reviewer | yes | yes | no |
| analyst / admin | yes | yes | yes |

V1.5 can start with a simple shared-token or local login. Multi-tenant SSO is optional later.

### Job Model

Long-running work (especially Phase 2 enrichment) must not block HTTP requests.

```text
POST /api/jobs/enrich
  → create job record (queued)
  → worker runs: phase_2.pipeline enrich
  → updates progress from enriched_store checkpoints
  → frontend polls GET /api/jobs/{id}
```

Rules:

- only one enrichment job at a time per environment
- honor Groq daily caps already implemented in Phase 2
- never expose `GROQ_API_KEY` to the frontend

---

## Frontend Architecture

### Responsibility

Give non-technical stakeholders a clear product surface for:

- understanding why category expansion is hard
- reviewing evidence-backed insights
- prioritizing experiment hypotheses
- tracking pilot readiness

### Recommended stack

| Concern | Choice | Why |
|---|---|---|
| Framework | **React + TypeScript** (Vite) | Fast internal dashboard development |
| Data fetching | TanStack Query | Natural fit for polling jobs + cached lists |
| Routing | React Router | Simple multi-page app |
| Charts | Recharts or similar | Barrier / segment breakdowns |
| Styling | CSS modules or lightweight design tokens | Avoid overbuilt UI kits |
| Auth UI | Simple login gate | Match backend roles |

Suggested app structure:

```text
web/
  src/
    app/
    pages/
      OverviewPage.tsx
      InsightsPage.tsx
      InsightDetailPage.tsx
      OpportunitiesPage.tsx
      ExperimentsPage.tsx
      ReviewQueuePage.tsx
      PipelineJobsPage.tsx
    components/
    api/
    types/
```

### Primary screens

1. **Overview**
   - enriched coverage
   - top barriers / missions / segments
   - pilot ready badge
   - bias warning callout

2. **Insights**
   - filterable insight cards
   - confidence, segment, supporting count
   - click-through to evidence snippets

3. **Insight detail**
   - statement, implication, open questions
   - linked theme ids
   - raw evidence quotes with source
   - approve / reject / mark hypothesis

4. **Opportunities**
   - opportunity map by type (trust / discovery / pricing / assortment)
   - priority score and recommended moves

5. **Experiments**
   - hypothesis backlog
   - primary + guardrail metrics
   - link to measurement framework / handoff memo

6. **Review queue**
   - draft insights awaiting human review
   - stakeholder feedback form

7. **Pipeline jobs**
   - enrichment progress
   - last Phase 3/4/5 refresh
   - quota / rate-limit status

### UX principles for this product

- evidence first: every insight shows supporting quotes
- separate **evidence / interpretation / recommendation** visually
- always show sample size and bias caveats
- no fake precision: confidence and open questions stay visible
- designed for PM / growth / research, not engineers

---

## End-To-End Processing Flow

### Analytical pipeline (existing)

1. collect feedback from each source
2. store raw records with metadata
3. clean, dedupe, and normalize text
4. sample enrichment cohort (≤1,000) and enrich via throttled Groq calls
5. aggregate enriched records into themes
6. draft insights with citations
7. frame opportunities and hypotheses
8. build pilot + measurement handoff package

### Product flow (backend + frontend)

1. analyst triggers ingest/enrich/refresh from Jobs page
2. backend creates job and runs existing phase pipelines
3. artifacts land in `data/phase-*`
4. frontend Overview/Insights pages read through API
5. reviewers approve or reject draft insights
6. growth team uses Experiments page + handoff package to plan tests

---

## Data Architecture

### V1 (current)

```text
data/
  phase-1/db/instamart_raw.sqlite
  phase-2/db/enriched.sqlite
  phase-3/*.json|*.md
  phase-4/*.json|*.md
  phase-5/*.json|*.md
```

### V1.5 (product shell)

Keep file/SQLite artifacts as source of truth initially.  
Backend repositories read them and optionally mirror selected tables into an API DB:

| Table / collection | Contents |
|---|---|
| `jobs` | pipeline runs, status, progress |
| `insight_reviews` | insight_id, status, reviewer, notes |
| `stakeholder_feedback` | structured feedback responses |
| `users_roles` | local auth identities |

### V2 (optional scale-up)

- Postgres / Supabase for multi-user persistence
- object storage for large report exports
- scheduled workers for daily enrichment resume
- optional vector index only if evidence retrieval quality needs it

---

## Technical Stack (Updated)

| Layer | Technology |
|---|---|
| Pipeline language | Python |
| Pipeline packages | `src/instamart_analyser/phases/*` |
| Backend API | **FastAPI** |
| Frontend | **React + TypeScript (Vite)** |
| Local storage | SQLite + JSON/Markdown artifacts |
| Optional cloud DB | Postgres / Supabase |
| LLM | Groq (`llama-3.3-70b-versatile`) |
| Auth | JWT/session + roles |
| Reporting | API-served markdown/JSON + dashboard views |

### Groq configuration

```text
GROQ_API_KEY=<your-key>
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_MAX_TOKENS=384
GROQ_TEMPERATURE=0.1
GROQ_MAX_REQUESTS_PER_MINUTE=10
GROQ_ENRICHMENT_BATCH_SIZE=8
GROQ_ENRICHMENT_DAILY_CAP=130
```

### Groq rate limits (`llama-3.3-70b-versatile`)

| Limit | Quota | Binding constraint |
|---|---|---|
| RPM | 30 | Usually not binding if throttled to 10 |
| RPD | 1,000 | Headroom for enrichment + synthesis |
| TPM | 12,000 | Caps sustained throughput |
| TPD | 100,000 | Caps daily enrichment to ~130–150 reviews |

The backend must surface quota/progress state in the Jobs UI instead of failing silently.

---

## Deployment Topology

### Local / demo (recommended next)

```text
localhost:5173  →  React frontend
localhost:8000  →  FastAPI backend
                →  local data/ + Groq API
```

### Shared internal pilot

```text
HTTPS frontend  →  backend service
                →  shared volume or Postgres
                →  Groq API
                →  optional worker process for jobs
```

Secrets (`GROQ_API_KEY`, auth secrets) stay server-side only.

---

## Core Design Principles

- traceability over black-box summaries
- repeatable pipelines over one-off analysis
- source diversity over single-channel conclusions
- human review for high-impact conclusions
- clear separation between evidence, interpretation, and recommendation
- **backend owns execution and secrets; frontend owns decision-facing UX**
- **pipeline code stays reusable — UI/API should call it, not rewrite it**

## Non-Goals

- real-time consumer-app personalization
- direct ranking changes in Instamart production
- autonomous decision-making without human review
- causal claims without experimental support
- replacing growth experimentation platforms

## Key Risks

- public feedback overrepresents extreme opinions
- LLM labeling can drift over time
- duplicate discussions can inflate theme importance
- partial enrichment can make dashboards look more complete than the evidence is
- frontend charts may imply false precision if confidence/bias are hidden

## Success Criteria

The architecture is successful when:

1. the Phase 1–5 pipeline remains repeatable and evidence-backed
2. stakeholders can explore insights and opportunities in a frontend without CLI use
3. reviewers can approve/reject insights through the backend
4. growth teams can move from dashboard → hypothesis → measurement handoff
5. enrichment jobs and Groq limits are visible and controllable from the product UI

---

## Implementation Sequence After Phase 5

| Step | Work | Outcome |
|---|---|---|
| 1 | FastAPI skeleton + overview/insights read APIs | Backend can serve current `data/` artifacts |
| 2 | React Overview + Insights pages | Stakeholders can browse without opening files |
| 3 | Jobs API for Phase 2/3/4/5 refresh | Product can rerun analysis safely |
| 4 | Review workflow + feedback API | Human validation becomes part of the product |
| 5 | Experiments + measurement pages | Handoff package becomes interactive |
| 6 | Optional Postgres/Supabase | Multi-user persistence when needed |

This keeps the completed analytical system intact while turning it into a usable internal product.
