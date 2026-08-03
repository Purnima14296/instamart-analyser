# Deploy: Vercel (frontend) + Railway (API)

Split hosting for the Instamart Research Intelligence app.

| Piece | Host | What runs |
| --- | --- | --- |
| React UI | **Vercel** (`web/`) | Static Vite build |
| FastAPI | **Railway** (repo root Dockerfile) | API + SQLite/JSON under `data/` |

```text
Browser → Vercel (UI)
            └─ fetch VITE_API_BASE/api/... → Railway (FastAPI)
```

## Prerequisites

1. GitHub account + empty repo (e.g. `instamart-analyser`)
2. [Vercel](https://vercel.com) account
3. [Railway](https://railway.app) account
4. Local project already working (`npm run build` + API on `:8000`)

## 0. Push the project to GitHub

This folder was not a git repo yet. From the project root:

```powershell
cd "c:\Users\purni\Instamart Analyser"
git init
git add .
git commit -m "Prepare Vercel + Railway deployment"
# create empty repo on GitHub, then:
git branch -M main
git remote add origin https://github.com/YOUR_USER/instamart-analyser.git
git push -u origin main
```

Do **not** commit `.env` (ignored). Keep secrets only in Vercel / Railway dashboards.

---

## 1. Deploy the API on Railway

### 1.1 Create service

1. Railway → **New Project** → **Deploy from GitHub repo**
2. Select `instamart-analyser`
3. Railway should pick up `Dockerfile` + `railway.toml`
4. Wait for the first build

### 1.2 Generate a public URL

1. Open the service → **Settings** → **Networking** → **Generate Domain**
2. Copy it, e.g. `https://instamart-analyser-production.up.railway.app`
3. Confirm probe works in a browser:  
   `https://YOUR-RAILWAY-URL/healthz` → `{"status":"ok"}`

### 1.3 Set Railway variables

Service → **Variables** → add:

| Variable | Value |
| --- | --- |
| `PYTHONPATH` | `src` (already set in Dockerfile; optional to repeat) |
| `GROQ_API_KEY` | your Groq key (only if you will run enrichment jobs) |
| `API_VIEWER_TOKEN` | keep `viewer-demo-token` for first deploy, or a strong secret |
| `API_REVIEWER_TOKEN` | matching token |
| `API_ADMIN_TOKEN` | matching token |
| `API_CORS_ORIGINS` | `http://localhost:5173,https://YOUR-VERCEL-URL` (add Vercel after step 2) |
| `API_CORS_ORIGIN_REGEX` | `https://.*\.vercel\.app` (default in code if unset) |

Redeploy after changing variables.

### 1.4 Optional: persistent volume

The image ships the current `data/` (~7MB) so the dashboard works immediately.  
Writes from jobs (ingest / enrich) land **inside the container** and can be lost on redeploy unless you add a Railway volume mounted over `/app/data`.

For a read-only stakeholder demo, the baked-in data is enough.

### 1.5 What works on Railway vs local

| Feature | Railway |
| --- | --- |
| Overview / explore pages / insights | Yes |
| Phase 3–5 refresh jobs | Yes (if artifacts + Groq allow) |
| Enrichment | Yes if `GROQ_API_KEY` + quota |
| Selenium Reddit scrape | No (no Chrome in this image) — run locally |

---

## 2. Deploy the UI on Vercel

### 2.1 Import project

1. Vercel → **Add New** → **Project** → import the same GitHub repo
2. **Root Directory** → set to `web` (important)
3. Framework preset: Vite
4. Build command: `npm run build`
5. Output directory: `dist`

### 2.2 Set Vercel env vars

Project → **Settings** → **Environment Variables** (Production + Preview):

| Variable | Value |
| --- | --- |
| `VITE_API_BASE` | `https://YOUR-RAILWAY-URL` (**no** trailing slash) |
| `VITE_API_VIEWER_TOKEN` | same as Railway `API_VIEWER_TOKEN` |
| `VITE_API_REVIEWER_TOKEN` | same as Railway `API_REVIEWER_TOKEN` |
| `VITE_API_ADMIN_TOKEN` | same as Railway `API_ADMIN_TOKEN` |

`VITE_*` values are baked in at **build** time. After changing them, trigger a **Redeploy**.

### 2.3 Deploy

Click **Deploy**. Copy the production URL, e.g. `https://instamart-analyser.vercel.app`.

### 2.4 Point Railway CORS at Vercel

Back on Railway, set:

```text
API_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://instamart-analyser.vercel.app
```

Redeploy Railway (or restart). Preview deploys are covered by the default `*.vercel.app` regex.

---

## 3. End-to-end smoke test

1. Open the Vercel URL  
2. Sidebar role → **Viewer** — pages load  
3. Browser DevTools → Network — calls go to `YOUR-RAILWAY-URL/api/...` with status 200  
4. Switch to **Admin** — Pipeline Actions visible  
5. Run a light job (e.g. Refresh Phase 5), not Reddit scrape  
6. Open `https://YOUR-RAILWAY-URL/docs` for OpenAPI

If you see CORS errors, the Vercel origin is missing from `API_CORS_ORIGINS` / regex.  
If you see `401 Invalid API token`, frontend `VITE_API_*_TOKEN` values do not match Railway.

---

## 4. Local development still works

```powershell
# API
cd "c:\Users\purni\Instamart Analyser"
$env:PYTHONPATH="src"
py -m uvicorn instamart_analyser.api.main:app --reload --port 8000

# UI (leave VITE_API_BASE empty — Vite proxies /api → :8000)
cd web
npm run dev
```

---

## 5. Rotating tokens later

1. Set new values on **Railway** (`API_*_TOKEN`)  
2. Set the same values on **Vercel** (`VITE_API_*_TOKEN`)  
3. Redeploy **both** (Vercel must rebuild)  
4. Users should hard-refresh (or clear site localStorage) so old tokens are replaced

---

## Files added for this setup

| File | Purpose |
| --- | --- |
| `Dockerfile` | Railway API image |
| `railway.toml` | Build + `/healthz` probe |
| `.dockerignore` | Slimmer image |
| `web/vercel.json` | SPA fallback routes |
| `.gitignore` | Keep secrets / `node_modules` out of git |

API version: **0.6.6** (adds `/healthz` + Vercel CORS regex support).
