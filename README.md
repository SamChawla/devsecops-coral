# devsecops-coral

**Cross-stack security operations agent — powered by Coral SQL**

> 🪸 coral reads → agent analyzes → human approves → agent acts

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![Hackathon](https://img.shields.io/badge/hackathon-Pirates%20of%20the%20Coral--bean-orange)](https://www.wemakedevs.org/hackathons/coral)

---

## What it does

Security and DevOps teams waste 30–60 minutes per incident manually correlating signals across 4–6 different tools. **devsecops-coral** replaces that with one agent workflow:

```
DETECT (Coral SQL reads)  →  RECOMMEND (agent analyzes)  →  ACT (agent executes, with approval)
```

| Phase | What happens |
|---|---|
| **DETECT** | Coral cross-source SQL JOINs read OSV + GitHub + Sentry + Jira + Grafana in one query |
| **RECOMMEND** | Agent identifies gaps: untracked CVEs, active exploitation, missing tickets |
| **ACT** | Creates Jira tickets, drafts GitHub PRs, annotates Grafana — **only after human approval** |

### Demo story

```
🔴 2 untracked CVEs        requests + pillow — no Jira tickets exist
🔴 Active exploitation     pillow CVE + 12 fatal Sentry errors in same window
🟢 CVE already being fixed django has SEC-1 In Progress

Agent recommends 5 actions:
  1. Create Jira SEC-8 for requests CVE
  2. Create Jira SEC-9 for pillow CVE  ← URGENT (active exploitation)
  3. Draft GitHub PR: upgrade pillow 9.0.0 → 10.3.0
  4. Annotate Grafana timeline
  5. Generate security posture report

Engineer clicks Approve All → done in 30 seconds.
```

---

## Documentation

- [Setup guide](docs/SETUP.md) — install Coral, connect sources, seed demo data
- [Product requirements (PRD)](docs/PRD.md) — full feature spec and phases
- [Guardrails](docs/Guardrails.md) — security, privacy, and safety rules

---

## Quick start

### Prerequisites

| Tool | Install |
|---|---|
| [Coral CLI](https://withcoral.com/docs/getting-started/installation) | `curl -fsSL https://install.withcoral.com \| bash` (Linux/WSL) |
| Python 3.10+ | [python.org](https://python.org) |
| Node.js 18+ | [nodejs.org](https://nodejs.org) — dashboard only |

**Windows:** Coral runs inside WSL. Install Ubuntu from the Microsoft Store, then inside WSL:
```bash
curl -fsSL https://install.withcoral.com | bash
# Coral installs to /root/.local/bin — copy to a shared path:
cp /root/.local/bin/coral /usr/local/bin/coral
```

### Install

```bash
git clone https://github.com/SamChawla/devsecops-coral.git
cd devsecops-coral
pip install -e .
devsecops-coral --version   # should print 0.1.0
```

### Configure

```bash
cp .env.example .env
```

Edit `.env` — minimum required:

```ini
# LLM (pick one)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...        # console.anthropic.com/settings/keys

# Coral binary (Windows WSL)
CORAL_BIN=wsl -d Ubuntu -- /usr/local/bin/coral

# GitHub (for timeline + PR actions)
GITHUB_OWNER=your-username
GITHUB_REPO=devsecops-demo
GITHUB_TOKEN=ghp_...               # repo:read + pull_requests:write
```

### Connect data sources

```bash
# OSV — public API, no auth needed
coral source add --file ./sources/osv/osv.yaml

# GitHub — reads token from GITHUB_TOKEN env var
wsl -d Ubuntu -- /usr/local/bin/coral source add github

# Jira, Sentry, Grafana — interactive (prompts for tokens)
wsl -d Ubuntu -- /usr/local/bin/coral source add --interactive jira
wsl -d Ubuntu -- /usr/local/bin/coral source add --interactive sentry
wsl -d Ubuntu -- /usr/local/bin/coral source add --interactive grafana
```

---

## Usage

### Dashboard

```bash
# Terminal 1 — backend
uvicorn devsecops_coral.api:app --reload --port 8000

# Terminal 2 — frontend dev server
cd frontend && npm install && npm run dev
# Open http://localhost:5173
```

Or serve the pre-built frontend:
```bash
devsecops-coral serve
# Open http://localhost:8000
```

**Tabs:**
- **Detect** — Scan vulnerabilities (OSV × Jira × Sentry), correlation view, SQL viewer, query console
- **Actions** — Recommended actions with Approve / Dismiss / Approve All
- **Timeline** — Chronological events across all sources

### Complete flow (DETECT → RECOMMEND → ACT)

Whether you drive it from the dashboard or the CLI, the workflow is the same:

1. **DETECT** — `scan` + `correlate` run cross-source Coral SQL to surface untracked CVEs and active exploitation (CVE + Sentry error spikes in the same window).
2. **RECOMMEND** — `recommend` analyzes the detection results and produces a typed, ordered action list (create Jira, draft PR, annotate Grafana, generate report), flagging urgent items.
3. **ACT** — you approve actions (`act --approve`, `--approve-all`, or the Actions tab). Only approved actions execute, via direct REST calls. Coral itself stays read-only.

```bash
# CLI end-to-end
devsecops-coral scan --packages django,requests,pillow,celery
devsecops-coral recommend --packages django,requests,pillow,celery
devsecops-coral act --list
devsecops-coral act --approve-all
```

> Performance: identical Coral reads are cached for `DEVSECOPS_QUERY_CACHE_TTL`
> seconds (default 90) so opening Actions reuses the Detect reads. Refresh / Run
> buttons bust the cache. Set the env var to `0` to disable caching.

### CLI

```bash
# Security posture scan
devsecops-coral scan --ecosystem PyPI --packages django,requests,pillow,celery

# Vulnerability ↔ error correlation
devsecops-coral correlate --since 7d --packages django,requests,pillow

# Show recommended actions
devsecops-coral recommend --packages django,requests,pillow,celery,pillow

# Execute an approved action
devsecops-coral act --list
devsecops-coral act --approve 2          # ✓ Created Jira SEC-9
devsecops-coral act --approve-all        # execute all pending

# Natural language query (requires LLM)
devsecops-coral ask "Which packages have untracked critical CVEs?"

# Unified event timeline
devsecops-coral timeline --since 7d
```

### Write credentials (for ACT phase)

Add to `.env` to enable each action type:

```ini
# Jira
JIRA_BASE_URL=https://your-site.atlassian.net
JIRA_EMAIL=you@example.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=SEC

# Grafana
GRAFANA_URL=https://your-org.grafana.net
GRAFANA_API_KEY=glsa_...
GRAFANA_DASHBOARD_UID=your-uid
```

---

## Architecture

```
DETECT (read)                     RECOMMEND            ACT (write, after approval)
-----------------------------     -----------------    ------------------------------
Coral SQL cross-source JOINs  ->  LLM agent        ->  httpx REST calls
OSV + GitHub + Jira + Sentry      analyzes gaps        Jira + GitHub + Grafana
Grafana + (custom OSV source)     builds action list   Local Markdown report
```

**Key rule:** Coral is read-only. All writes go through `src/devsecops_coral/actions/` and require explicit approval.

### Project structure

```
src/devsecops_coral/
+-- cli.py              # scan, correlate, timeline, recommend, act, ask, serve
+-- api.py              # FastAPI - all REST endpoints
+-- recommender.py      # rule-based action recommendation engine
+-- agent.py            # LLM NL -> SQL + analysis
+-- coral_client.py     # sole Coral CLI wrapper (read-only)
+-- actions/
|   +-- executor.py     # in-memory store, approve/dismiss orchestration
|   +-- jira.py         # POST /rest/api/3/issue
|   +-- github.py       # branch + commit + PR creation
|   +-- grafana.py      # POST /api/annotations
|   +-- report.py       # local Markdown export
+-- queries/
|   +-- scan.py         # OSV x Jira x Sentry (untracked CVE detection)
|   +-- correlate.py    # CVE x Sentry error spikes
|   +-- timeline.py     # 4-source UNION ALL
|   +-- posture.py      # severity aggregation
+-- formatters/         # Rich terminal, JSON, Markdown output
```

---

## Sources

| Source | Kind | What it provides |
|---|---|---|
| OSV | Custom spec | Vulnerability data (CVE IDs, severity, affected versions) |
| GitHub | Bundled | PRs, commits, Dependabot alerts |
| Jira | Bundled | Security tickets, triage status |
| Sentry | Bundled | Application errors, frequency, timing |
| Grafana | Bundled | Alert rules, annotations |

The OSV custom source spec (`sources/osv/osv.yaml`) is submitted separately for the Coral source bounty.

---

## Development & testing

```bash
# Install dev dependencies
pip install -e ".[dev]"
```

### Backend tests (pytest)

Coral is mocked at the `coral_client` level, so these run offline with no Coral
connection or credentials:

```bash
pytest tests/          # unit + API tests
```

### Frontend E2E tests (Playwright)

The dashboard suite mocks every `/api/*` call with deterministic fixtures, so it
verifies UI rendering and the approve / dismiss / approve-all flow without a
running backend or live Coral. Playwright auto-starts the Vite dev server.

```bash
cd frontend
npm install
npx playwright install chromium   # one-time browser download
npm run test:e2e                  # headless
npm run test:e2e:ui               # interactive runner
```

### Lint, format & build

```bash
ruff check src/ tests/
ruff format src/ tests/

cd frontend && npm run build       # production bundle → frontend/dist/
```

All three suites should be green before submitting: `pytest` (backend), `npm run test:e2e` (dashboard), and `ruff check` (lint).

---

## Hackathon

**Event:** Pirates of the Coral-bean (WeMakeDevs × Coral)  
**Track:** Track 1 — Enterprise Agent  
**Dates:** May 25–31, 2026
