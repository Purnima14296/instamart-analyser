# Phase 6B–6C: Frontend Dashboard

Status: **implemented** (includes 6C hardening)

React + TypeScript stakeholder dashboard for the Instamart category-discovery analyser.

## Run

Terminal 1 — API:

```powershell
cd "c:\Users\purni\Instamart Analyser"
$env:PYTHONPATH="src"
py -m uvicorn instamart_analyser.api.main:app --reload --port 8000
```

Terminal 2 — Frontend:

```powershell
cd "c:\Users\purni\Instamart Analyser\web"
npm install
npm run dev
```

Open: http://localhost:5173

## Phase 6C hardening in UI

- Role gates without page reload
- Review queue with approve/reject + Phase 5 feedback sync
- Jobs page shows quota blocked / active job / failure class + recovery hints
- Known limitations on Overview and Jobs
- Stale job recovery button for admins

Ops checklist: `../Docs/phases/phase-6-product-shell/ops-checklist.md`
