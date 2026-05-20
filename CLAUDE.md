# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KAM (Key Account Management) is a full-stack web application for managing client relationships, contracts, and team operations. It consists of:

- **`kam-backend/`** — Django 5 REST API with Celery async tasks
- **`kam-frontend/`** — React 19 + Vite SPA (TypeScript)
- **`kam-api-collection/`** — Bruno API collection (also importable to Postman/Insomnia)
- **`Social-Listening/`** — Research POC for web scraping + LLM analysis (not production)

## Commands

### Backend

```bash
# Start all services (Django, PostgreSQL 17, Redis 7, Celery)
docker compose up

# Run database migrations (applied automatically on container start)
docker compose exec web python manage.py migrate

# Django management shell
docker compose exec web python manage.py shell

# Create initial KAM team (seeding)
docker compose exec web python manage.py create_kam_team
```

> **Windows note:** WeasyPrint (PDF generation) requires C libraries (Pango, Cairo) only available in Docker. Run `manage.py` commands inside the container.

> **Line endings:** `entrypoint.*.sh` files must use LF (not CRLF) or the container will fail to start.

### Frontend

```bash
npm run dev       # Dev server at :5173 with HMR
npm run build     # TypeScript compile + Vite bundle
npm run lint      # ESLint — STRICT, fails on unused imports

npx playwright test   # E2E tests

# Docker — must specify env file to set backend URL
docker compose --env-file .env.docker.local up --build   # → local backend
docker compose --env-file .env.docker.dev up --build     # → staging backend
```

### Social-Listening POC

```bash
uv sync                                        # Install dependencies
uv run python social_listening_pipeline.py     # Full pipeline: Scrape → LLM → Notion
```

## Architecture

### Backend Django Apps

| App | Purpose |
|-----|---------|
| `api` | User auth, `CustomUser` model, `Organization` |
| `account360` | `Team` and `Company` management |
| `contract_management` | Contract lifecycle, OCR, document versioning |
| `mom` | Minutes of Meetings with WeasyPrint PDF generation |
| `tasks` | Task assignment and tracking |
| `notifications` | Real-time alerts via Django Channels + Redis |
| `auditlog` | User action audit trail |

**Request flow:** Nginx (frontend) → Uvicorn (Django/DRF) → PostgreSQL. Async work offloaded to Celery via Redis. Real-time updates via Django Channels WebSocket.

**File storage:** Local `media/` folder by default; switchable to Google Cloud Storage with signed URLs (60 min for profile pics, 10 min for documents).

**API docs:** Auto-generated Swagger/Redoc via `drf-spectacular` at `/api/schema/swagger-ui/`.

### Frontend Structure

```
src/
├── apis/          # Axios client + per-domain service modules
├── components/    # Reusable UI (organized by domain: account, company, task, etc.)
├── hooks/         # Custom React hooks (auth, data fetching)
├── interfaces/    # TypeScript type definitions
├── layouts/       # Page wrappers (Sidebar, Auth)
├── pages/         # Route-mapped views
├── routes/        # AppRoutes.tsx — React Router 7 config
├── store/         # Zustand global state
├── utils/         # Formatting, validation helpers
└── locales/       # i18n translations (Thai/English)
```

**State pattern:** React Query manages server state (caching, refetching). Zustand handles client/UI state. TypeScript strict mode — `any` is forbidden.

**Critical:** `VITE_API_URL` is baked in at build time, not runtime. Switching backends requires a full rebuild with `--build`.

### Deployment

| Environment | Backend | Frontend |
|-------------|---------|----------|
| Staging | `kam-backend-445438248473.asia-southeast1.run.app` | `kam-frontend-445438248473.asia-southeast1.run.app` |
| Production | `kam-bvtpa.aibrainlab.co` | same domain |

Deployed on Google Cloud Run. Database on Cloud SQL (PostgreSQL), accessed locally via Cloud SQL Auth Proxy. Secrets managed in GCP Secret Manager.

## Development Workflow

- **Branches:** `<initials>/<YYYYMMDD>/<feature_slug>` (e.g., `np/20260511/contract_export_pdf`)
- **Commits:** Short, capitalized imperative/past-tense. Stage individual files — never `git add .`
- **Migrations:** Must be committed as source code
- **PRs:** Do not merge your own PRs. Delete remote branch after merge.
- **No automated backend tests** — manual testing required before PR.

## Key Gotchas

- **ESLint blocks builds:** Unused imports fail `npm run lint` and therefore CI/CD. Remove them before committing.
- **Gemini (Google AI) is rate-limited to 0 quota on free tier in Thailand** — use Groq (Llama 3.3 70B) in the Social-Listening POC instead.
- **Migration files are source code** — always commit them.
- **Docker rebuild required** when changing `VITE_API_URL` — the dev HMR server does not apply to Docker builds.


## Team & Roles

The KAM repository contains work from multiple team members across different
specializations. The three original project folders — `kam-backend/`,
`kam-frontend/`, and `kam-api-collection/` — were established before the
current intern cohort joined.

The `Social-Listening/` folder is owned by the ML/Analyst intern (AI Brain Lab
internship), assigned directly by the project lead. All scraping POCs, LLM
pipeline experiments, and research under that folder were built independently
as exploratory work to evaluate tools and approaches for a future social
listening feature in KAM.

## Social-Listening — Context & Ownership

This folder is a research and POC workspace, not production code. The goal is
to evaluate scraping approaches and LLM analysis pipelines that could
eventually feed into KAM's Phase 3 social listening module for BVTPA (the
client).

### What has been built so far

- `test_beautifulsoup.py` — HTML scraper using requests + BeautifulSoup.
  Handles cookie-gate pattern found on Thai insurance sites.
- `test_firecrawl.py` — Cloud-based scraper (Firecrawl API) that returns
  clean Markdown, good for JS-rendered pages.
- `test_scrapegraphai.py` — LLM-powered extraction using ScrapeGraphAI +
  Groq (Llama 3.3 70B free tier). No CSS selectors needed; uses a plain
  English prompt to extract structured JSON.
- `scrape_to_notion.py` — BeautifulSoup scraper piped into Notion API.
  Handles Thai Buddhist Era (พ.ศ.) date conversion to ISO 8601.
- `social_listening_pipeline.py` — Full end-to-end pipeline: scrape →
  Groq LLM analysis (sentiment, topics, summary) → store in Notion.
  Confirmed working on Viriyah Insurance English news articles.

### Target sites tested

- [Viriyah Insurance](https://www.viriyah.co.th/en/) — initial POC target,
  confirmed working with cookie-gate workaround.

### Target sites assigned (in progress)

- https://www.axa.co.th/en
- https://www.thailife.com/?lang=en
- https://www.aia.co.th/en/health-wellness/vitality

### Current assigned tasks

1. Integrate Gemini (GCP) as the LLM backend — replace Groq with the
   Gemini API key provided by the project lead. Reference the existing
   Gemini integration pattern in `kam-backend/` for implementation guidance.
2. Research social listening tools in the market — understand what
   commercial tools (Brandwatch, Talkwalker, Meltwater, etc.) offer and
   how companies apply them, to inform what features to build.
3. Test scraping on the three new insurance sites listed above.

### Known issues & findings

- Thai insurance sites use a cookie-gate on first request. All scrapers
  must warm up via `requests.Session()` on the homepage before fetching
  article pages.
- Gemini free tier has 0 quota from Thailand — Groq is the working
  free-tier alternative. However, the project lead has provided a paid
  Gemini API key for current tasks.
- ScrapeGraphAI is the most flexible for multi-site extraction but is
  slow — not suitable for high-volume or real-time scraping.
- Firecrawl handles JS-rendered pages well but is a paid service.
