# DocDrift — Autonomous Documentation Drift Detection

---

## Problem Statement

### Technical Docs Go Stale the Moment Code Changes — and Nobody Notices Until It Costs Hours

A modern engineering team commits dozens of times a day. Every function rename, every new parameter, every removed endpoint silently invalidates the documentation that describes it. READMEs, API references, architecture notes, and runbooks drift away from the code they describe — invisibly, until a consumer trusts them and gets burned.

No existing tool knows *which specific code change* invalidated *which specific sentence* of documentation. Doc rot is discovered by accident, weeks or months after the fact, at the worst possible moment: during onboarding, during an incident, during an integration.

**Why it matters:** Stale docs cause integration bugs, slow onboarding, repeated questions to senior engineers, and broken handoffs. Documentation is treated as a manual afterthought rather than a living artifact the system maintains — which is exactly the kind of legacy assumption an AI-first production function should overturn.

### Proposed Solution

DocDrift links each documentation block to the code symbols it describes (functions, endpoints, config keys, schemas). On every commit it diffs the changed symbols, finds the docs that reference them, scores how far each doc has drifted, and an LLM drafts the corrected text as a suggested documentation PR. A Doc Health dashboard shows a freshness score per repo and surfaces the most stale, most-read docs first.

### Expected Impact
- Cut stale-documentation incidents by detecting drift the moment code changes — not months later
- Faster onboarding and fewer repeat questions to senior engineers
- Doc updates drafted in seconds as a reviewable PR rather than a forgotten chore
- A measurable Doc Health score that makes documentation quality visible to the team

---

## Overview

An autonomous pipeline that ingests a commit diff, extracts changed code symbols via AST parsing, maps those symbols to documentation blocks via a vector index, scores drift, drafts LLM rewrites, and delivers a prioritised Doc Health dashboard with a reviewable PR preview — all locally, with no external services required in demo mode.

---

## What Works Right Now vs What Needs Completion

### ✅ Works out of the box (built)

| Feature | Details |
|---------|---------|
| Demo pipeline (end-to-end) | 4 pre-authored commit scenarios run the full pipeline with zero credentials |
| Symbol extraction | `tree-sitter` AST parser extracts functions, classes, methods from Python diffs |
| Diff-text symbol extraction | Regex fallback extracts symbols from raw diff text (no local files needed) |
| Doc block parsing | Markdown files split at heading boundaries into stable-ID `DocBlock` objects |
| Symbol-to-doc linking | TF-IDF vector index (Qdrant in-memory) + regex explicit mention matching |
| Drift scoring | Weighted 0–100 algorithm: symbol coverage × recency decay (30-day half-life) |
| Mock LLM rewrites | Pre-authored, realistic rewrites for all demo sections — no API key needed |
| Real LLM rewrites | OpenAI-compatible endpoint wired — activate by providing any `sk-...` key |
| Local PR preview | Unified diff generated locally for every stale block — no GitHub write access needed |
| GitHub token validation | `POST /api/github/validate` — live scope check, returns login + scopes |
| Real GitHub commit fetching | `POST /api/github/commits` — fetches last N commits from any accessible repo |
| Real GitHub repo analysis | `POST /api/analyze/repo` — fetches real diff + markdown docs, runs full pipeline |
| Smart markdown filtering | Excludes `sample_*`, `test/`, `vendor/`, `node_modules/` from doc scans |
| REST API | All endpoints working — `/api/config`, `/api/jobs`, `/api/dashboard` |
| Background job runner | Async worker with in-memory job store; poll by `job_id` |
| Doc Health dashboard | Freshness gauge, stale/critical counts, drift results with filter controls |
| Drift cards | Expandable per-block cards with original doc, suggested rewrite, and symbol pills |
| PR preview modal | Unified diff viewer with +/- line colouring and metadata |
| Job progress tracker | Animated 5-step progress bar polling every 600 ms |
| Provenance banner | Dashboard shows exactly which repo, commit, and markdown files were analysed |
| GitHub token UI | Live validation with debounce — green "Connected as @user" or red error |
| GitHub repo picker | Enter `owner/repo` or paste full GitHub URL — auto-normalises |

### 🔶 Stubs / Partially built — needs completion

| Feature | What's missing | File to edit |
|---------|---------------|--------------|
| Real GitHub PR creation | PR preview is local only — no branch is pushed, no real PR opened | `backend/app/services/github_service.py` |
| Real webhook receiver | No GitHub push-event JSON parsing — only mock commits or custom patch supported | `backend/app/api/routes.py` |
| Persistent job storage | In-memory `_jobs` dict — cleared on backend restart | `backend/app/workers/analysis_worker.py` |
| Real embeddings | Vector index uses local TF-IDF hashing (256-dim) instead of a real embedding model | `backend/app/services/vector_index.py` |
| Read-count analytics | Page-view counts are hardcoded mock values — no real analytics source wired | `backend/app/mocks/mock_interfaces.py` |
| Azure DevOps / GitLab | GitHub only — no other git providers | `backend/app/services/github_fetcher.py` |
| Slack / Teams alerts | No notification channel integration | `backend/app/services/notifier.py` |
| Per-author doc-debt report | No attribution of stale docs to who last changed the code | `backend/app/services/doc_debt.py` |
| Executable doc examples | No verification that code snippets in docs still run | `backend/app/services/doc_executor.py` |
| Confidence-gated auto-merge | All doc updates require human approval — no auto-merge path | `backend/app/services/auto_merge.py` |

### What the pipeline produces today (before stubs are completed)

The full pipeline runs end-to-end. You will get real drift scores and rewrite suggestions. But:
- **PR preview** is a local diff only — no actual GitHub PR is created
- **Embeddings** are TF-IDF hashes — semantic similarity is approximate, not model-quality
- **Read counts** are hardcoded mock values — "most-read" ordering is simulated
- **Job history** is lost on backend restart — no persistence layer
- **Webhook** only works with mock commits or a custom patch — not wired to live GitHub push events

After completing all stub files, the system will open real reviewable PRs, use model-quality embeddings for more accurate drift detection, persist job history, and accept live webhook events from any GitHub repo.

---

## Project Structure

```
docdrift/
├── backend/                            ← Python 3.10 + FastAPI
│   ├── app/
│   │   ├── main.py                     ✅ BUILT — FastAPI app, CORS config
│   │   ├── core/config.py              ✅ BUILT — pydantic-settings, .env loader
│   │   ├── models/schemas.py           ✅ BUILT — all Pydantic models
│   │   ├── api/routes.py               ✅ BUILT — all REST endpoints
│   │   ├── workers/analysis_worker.py  ✅ BUILT — full 8-step pipeline orchestrator
│   │   ├── services/
│   │   │   ├── symbol_extractor.py     ✅ BUILT — tree-sitter AST + diff-text fallback
│   │   │   ├── doc_parser.py           ✅ BUILT — markdown → DocBlock (file + in-memory)
│   │   │   ├── drift_scorer.py         ✅ BUILT — 0-100 weighted scoring algorithm
│   │   │   ├── vector_index.py         🔶 PARTIAL — TF-IDF hashing (real embeddings TODO)
│   │   │   ├── llm_service.py          ✅ BUILT — OpenAI-compatible rewrite endpoint
│   │   │   ├── github_fetcher.py       ✅ BUILT — fetch commits + markdown from GitHub API
│   │   │   └── github_service.py       🔶 PARTIAL — PR creation stub (no branch push)
│   │   └── mocks/
│   │       └── mock_interfaces.py      ✅ BUILT — commits, LLM rewrites, PR, read counts
│   ├── requirements.txt                ✅ BUILT
│   └── .env.example                    ✅ BUILT — copy to .env
├── frontend/                           ← React 18 + Vite + TypeScript
│   ├── src/
│   │   ├── pages/Dashboard.tsx         ✅ BUILT — home / running / dashboard views
│   │   ├── components/
│   │   │   ├── DriftCard.tsx           ✅ BUILT — expandable result card with tabs
│   │   │   ├── PrPreviewModal.tsx      ✅ BUILT — unified diff viewer
│   │   │   ├── FreshnessGauge.tsx      ✅ BUILT — radial freshness chart
│   │   │   ├── JobProgress.tsx         ✅ BUILT — animated 5-step progress tracker
│   │   │   └── DriftBadge.tsx          ✅ BUILT — colour-coded score badge
│   │   ├── hooks/useApi.ts             ✅ BUILT — typed Axios API client
│   │   └── types/index.ts              ✅ BUILT — all TypeScript interfaces
│   └── vite.config.ts                  ✅ BUILT — Vite proxy to backend
├── sample_repo/                        ← Demo codebase for mock pipeline
│   ├── src/payments.py                 ✅ Demo source (payment functions)
│   ├── src/users.py                    ✅ Demo source (user management)
│   ├── src/notifications.py            ✅ Demo source (notification channels)
│   └── docs/api_reference.md           ✅ Demo docs (sections matched to mock commits)
├── start_backend.sh                    ✅ One-command backend launcher
├── start_frontend.sh                   ✅ One-command frontend launcher
└── README.md
```

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend runtime | Python 3.10 + FastAPI | Async-native, typed, fast |
| AST parsing | tree-sitter + tree-sitter-python | Real language-aware symbol extraction |
| Vector index | Qdrant (in-memory) + TF-IDF | Zero infra — no external service needed |
| LLM inference | OpenAI-compatible API (gpt-4o-mini) | Any provider; mock works without a key |
| GitHub integration | GitHub REST API v3 via httpx | Fetch commits, diffs, markdown files |
| Frontend | React 18 + Vite + TypeScript | Fast HMR, type-safe |
| Charts | Recharts | Freshness gauge |
| Styling | Tailwind CSS | Utility-first, dark theme |
| Icons | Lucide React | Consistent icon set |
| HTTP client | Axios (frontend) + httpx (backend) | Async, typed |

**No Redis. No PostgreSQL. No Docker required.**

---

## Quick Start

### Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- A free OpenAI-compatible API key *(optional — mock mode works without it)*
- A GitHub personal access token *(optional — demo mode works without it)*

### 1. Clone and configure

```bash
git clone <your-repo-url>
cd DocDrift

cp backend/.env.example backend/.env
# Edit backend/.env — paste LLM_API_KEY and/or GITHUB_TOKEN (or leave blank for demo mode)
```

### 2. Run — two terminals

**Terminal 1 — Backend (start this first):**
```bash
bash start_backend.sh
# ✅ DocDrift backend → http://localhost:8000
# ✅ API docs        → http://localhost:8000/docs
```

**Terminal 2 — Frontend:**
```bash
bash start_frontend.sh
# ✅ Frontend → http://localhost:3000
```

### 3. Try the demo pipeline (no credentials needed)
1. Open **http://localhost:3000**
2. Select any of the 4 commit scenarios
3. Click **Run Demo Analysis**
4. Watch the 5-step progress tracker
5. Expand a drift card — view the original doc, suggested rewrite, and PR preview diff

### 4. Try real GitHub analysis (token required)
1. Enter your `ghp_...` GitHub token in the UI — validates live
2. Enter any public repo as `owner/repo` or paste the full GitHub URL
3. Click **Fetch** — your last 5 commits appear
4. Select a commit then click **Analyze Real Repo**
5. Dashboard shows drift across your repo's actual markdown docs

### 5. Reset between runs
Jobs are stored in memory — restart the backend to reset:
```bash
pkill -f "uvicorn app.main:app"
bash start_backend.sh
```

---

## Environment Variables

Set in `backend/.env`:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USE_MOCKS` | No | `True` | `True` = demo mode, no credentials needed |
| `LLM_API_KEY` | No | — | OpenAI-compatible key. Without it, pre-authored mock rewrites are used |
| `LLM_API_BASE` | No | `https://api.openai.com/v1` | Override for any OpenAI-compatible provider |
| `LLM_MODEL` | No | `gpt-4o-mini` | Model name passed to the LLM endpoint |
| `GITHUB_TOKEN` | No | — | GitHub PAT. Without it, local PR preview is used |
| `GITHUB_API_BASE` | No | `https://api.github.com` | Override for GitHub Enterprise |
| `MOCK_LLM_DELAY` | No | `0.4` | Simulated LLM latency in seconds |
| `QDRANT_IN_MEMORY` | No | `True` | Keep True — no Qdrant server needed |

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/config` | Current feature flags and configuration |
| `POST` | `/api/webhook/github` | Trigger analysis on a mock commit (index 0–3) or custom patch |
| `POST` | `/api/analyze/repo` | Trigger analysis on a real GitHub commit |
| `POST` | `/api/github/commits` | Fetch recent commits from a GitHub repo |
| `POST` | `/api/github/validate` | Validate a GitHub token — returns login and scopes |
| `GET` | `/api/jobs/{job_id}` | Poll job status (pending → running → done / failed) |
| `GET` | `/api/jobs` | List all jobs, newest first |
| `GET` | `/api/dashboard/{job_id}` | Full dashboard metrics for a completed job |
| `GET` | `/api/mock/commits` | List the 4 demo commit scenarios |

---

## Pipeline — How It Works

```
  Commit diff (mock or real GitHub)
        │
        ▼
  ┌─────────────────────────────────────────┐
  │  1. Symbol Extraction                   │  ← which functions/classes changed?
  │     tree-sitter AST  or  diff-text regex│
  └──────────────────┬──────────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────────┐
  │  2. Doc Parsing (Markdown → DocBlocks)  │  ← what does the repo document?
  │     local files  or  GitHub API fetch   │
  └──────────────────┬──────────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────────┐
  │  3. Symbol-to-Doc Linking              │  ← which docs reference changed code?
  │     TF-IDF vector index + regex         │
  └──────────────────┬──────────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────────┐
  │  4. Drift Scoring  (0–100 per block)    │  ← how stale is each doc section?
  │     symbol coverage × recency decay     │
  └──────────────────┬──────────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────────┐
  │  5. LLM Rewrite  (stale blocks only)    │  ← draft corrected documentation
  │     mock pre-authored  OR  real API key │
  └──────────────────┬──────────────────────┘
                     │
                     ▼
  ┌─────────────────────────────────────────┐
  │  6. PR Preview  (local unified diff)    │  ← reviewable suggestion for humans
  │     🔶 real GitHub PR creation = TODO  │
  └──────────────────┬──────────────────────┘
                     │
                     ▼
       Doc Health Dashboard
       ├── Freshness score (0–100)
       ├── Stale blocks  (score > 40)
       ├── Critical blocks (score > 70)
       └── Per-block drift cards with rewrite + diff
```

---

## Demo Commit Scenarios

Four pre-authored scenarios exercise the full pipeline without any credentials:

| # | Commit message | File changed | What drifts |
|---|---------------|-------------|-------------|
| 0 | feat: multi-currency routing + regional tax | `src/payments.py` | `process_payment` docs |
| 1 | fix: hard-delete + GDPR erasure on deactivate_user | `src/users.py` | `deactivate_user` docs |
| 2 | refactor: drop webhook channel, add Slack, rate limits | `src/notifications.py` | `send_notification` docs |
| 3 | feat: payment v2 + GDPR combined | `payments.py` + `users.py` | Both doc sections |

---

## Contributor Tasks

Complete all 10 stubs to make the prototype fully functional. Each file contains detailed `TODO` comments with implementation steps and API references.

| # | File | What to implement | Difficulty |
|---|------|------------------|------------|
| 1 | `backend/app/services/github_service.py` | Implement `_push_file_changes_to_branch()` — create Git blobs, build a tree, commit to a new branch via GitHub Git Data API, then open a real PR | ★★★ |
| 2 | `backend/app/api/routes.py` | Implement `POST /webhook/push` — parse real GitHub push-event JSON, validate HMAC signature, extract commit SHA and repo, auto-trigger analysis | ★★ |
| 3 | `backend/app/services/vector_index.py` | Implement `embed_with_model()` — replace TF-IDF hashing with real sentence embeddings via OpenAI `text-embedding-3-small` or `sentence-transformers` | ★★★ |
| 4 | `backend/app/workers/analysis_worker.py` | Implement `PersistenceLayer` — replace in-memory `_jobs` dict with SQLite or Redis so job history survives restarts | ★★ |
| 5 | `backend/app/mocks/mock_interfaces.py` | Implement `fetch_real_read_counts()` — replace hardcoded page-view counts with GitHub Traffic API or a real analytics source | ★ |
| 6 | `backend/app/services/github_fetcher.py` | Implement `fetch_gitlab_commits()` and `fetch_azuredevops_commits()` — add GitLab and Azure DevOps as supported git providers | ★★ |
| 7 | `backend/app/services/notifier.py` | Implement `send_slack_message()` and `send_teams_message()` — post Block Kit / Adaptive Card alerts when high-traffic docs drift above threshold | ★★ |
| 8 | `backend/app/services/doc_debt.py` | Implement `_get_symbol_author()` and `generate_doc_debt_report()` — attribute stale docs to the engineer who last changed the referenced code via git blame or GitHub API | ★★★ |
| 9 | `backend/app/services/doc_executor.py` | Implement `execute_code_block()` — run fenced code blocks in a sandboxed subprocess with timeout, return pass/fail; wire into `verify_doc_examples()` | ★★★ |
| 10 | `backend/app/services/auto_merge.py` | Implement `score_rewrite_confidence()`, `_check_ci_status()`, and `merge_pr()` — auto-merge low-risk doc PRs when confidence is high and CI passes | ★★★ |

### Notes for contributors
- `USE_MOCKS=True` in `backend/.env` is the safe default — the full demo pipeline runs with zero credentials even while stubs are incomplete
- Use `GET http://localhost:8000/docs` for the auto-generated interactive API explorer
- `backend/app/services/github_fetcher.py` is the reference for GitHub API call patterns
- `backend/app/mocks/mock_interfaces.py` is the reference for the mock vs real interface contract
- Each stub file has `TODO` comments with step-by-step instructions, API links, and example code
- All real integrations are wired behind the same function signature — swap the stub for the real implementation without changing any callers
