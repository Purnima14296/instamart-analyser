# Phase 6C Ops Checklist

Use this checklist for a local demo or internal pilot of the Instamart Discovery Analyser.

## 1. Start services

```powershell
# Terminal A — API
cd "c:\Users\purni\Instamart Analyser"
$env:PYTHONPATH="src"
py -m uvicorn instamart_analyser.api.main:app --reload --port 8000

# Terminal B — Frontend
cd "c:\Users\purni\Instamart Analyser\web"
npm run dev
```

- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:5173

## 2. Role smoke check

| Role | Sidebar setting | Expected |
|---|---|---|
| Viewer | Viewer | Can browse; cannot approve or run jobs |
| Reviewer | Reviewer | Can approve/reject + submit feedback |
| Admin | Admin | Can trigger enrichment / Phase 3–5 jobs |

## 3. Reviewer workflow

1. Open **Review**
2. Approve one draft insight
3. Confirm it leaves the draft queue
4. Submit stakeholder feedback with an optional defect
5. Confirm message says Phase 5 summary was refreshed

## 4. Jobs / quota workflow

1. Open **Jobs**
2. Confirm coverage + remaining quota are visible
3. If quota is exhausted, enrichment button should be disabled and banner shown
4. As Admin, run **Refresh Phase 5**
5. Confirm job appears with status `completed` or a classified failure + recovery hint
6. Use **Recover stale jobs** if a job is stuck

## 5. Known limitations visible

On **Overview** and **Jobs**, confirm users can see:

- sample-size / Play Store bias caveats
- partial enrichment note
- non-causality reminder
- Groq quota / 429 operational note

## 6. Validation commands

```powershell
cd "c:\Users\purni\Instamart Analyser"
$env:PYTHONPATH="src"
py -m instamart_analyser.api.validate_phase6a
py -m instamart_analyser.api.validate_phase6c
cd web
npm run build
```

## 7. Optional daily enrichment resume

When Groq quota resets:

```powershell
cd "c:\Users\purni\Instamart Analyser"
$env:PYTHONPATH="src"
py -m instamart_analyser.phases.phase_2.pipeline enrich
# then refresh insights / opportunities / pilot
py -m instamart_analyser.phases.phase_3.pipeline run --dry-run --limit 8
py -m instamart_analyser.phases.phase_4.pipeline run
py -m instamart_analyser.phases.phase_5.pipeline run
```

Or trigger the same steps from the **Jobs** page as Admin.
