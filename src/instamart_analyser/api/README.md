# Phase 6A–6C: Backend API

Status: **implemented** (includes 6C hardening)

FastAPI backend that serves Phase 2–5 artifacts, review actions, feedback, and pipeline jobs.

## Run

```powershell
cd "c:\Users\purni\Instamart Analyser"
py -m pip install -r requirements.txt
$env:PYTHONPATH="src"
py -m uvicorn instamart_analyser.api.main:app --reload --port 8000
```

OpenAPI docs: http://localhost:8000/docs  
Unauthenticated probe: http://localhost:8000/healthz  

Production split deploy (Vercel UI + Railway API): `Docs/deployment-vercel-railway.md`

## Auth

| Role | Default demo token | Can do |
|---|---|---|
| viewer | `viewer-demo-token` | read APIs |
| reviewer | `reviewer-demo-token` | read + insight status + feedback |
| admin | `admin-demo-token` | all, including jobs |

## Key endpoints

- `GET /api/health`
- `GET /api/me`
- `GET /api/overview`
- `GET /api/research/summary` (Product Research Intelligence brief)
- `GET /api/explore/sources` (per-source volume, rating, sentiment, coverage)
- `GET /api/explore/reviews` (search/filter reviews; `q`, `source`, `sentiment`, `segment`, `mission`, `barrier`, `enriched_only`, `limit`, `offset`)
- `GET /api/explore/discovery-challenges`
- `GET /api/explore/segments`
- `GET /api/explore/root-causes`
- `GET /api/explore/unmet-needs`
- `GET /api/explore/journey`
- `GET /api/explore/validation`
- `GET /api/system/limitations`
- `GET /api/insights`
- `PATCH /api/insights/{id}/status`
- `GET /api/jobs`
- `POST /api/jobs/enrich|phase3|phase4|phase5`
- `POST /api/jobs/ingest_play|ingest_appstore|ingest_reddit_selenium|ingest_all`
- `POST /api/jobs/analysis_cascade`
- `POST /api/jobs/recover-stale`
- `POST /api/feedback` (also refreshes Phase 5 feedback summary)
- `GET /api/feedback/review-stats`

Research UX notes: `Docs/phases/phase-6-product-shell/research-intelligence-ux.md`

## Validation

```powershell
$env:PYTHONPATH="src"
py -m instamart_analyser.api.validate_phase6a
py -m instamart_analyser.api.validate_phase6c
```

Ops checklist: `Docs/phases/phase-6-product-shell/ops-checklist.md`
