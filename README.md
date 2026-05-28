# CoralSentinel

**Security & Compliance Monitor — powered by Coral SQL**

> Surfaces risky access changes, secrets in commits, and cross-references them with known CVE databases and internal policy docs — all in one Coral SQL query.

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![Hackathon](https://img.shields.io/badge/hackathon-Pirates%20of%20the%20Coral--bean-orange)](https://www.wemakedevs.org/hackathons/coral)

**Sources:** GitHub · Slack · Notion · OSV · Sentry · Jira · Grafana

---

## Running Locally

### 1 — Prerequisites

| Tool | Version | Notes |
|---|---|---|
| [Coral CLI](https://withcoral.com/docs/getting-started/installation) | latest | The SQL runtime — install first |
| Python | 3.10+ | |
| Node.js | 18+ | Dashboard frontend only |
| npm | 9+ | Dashboard frontend only |

**On Windows**, Coral runs inside WSL. Install Ubuntu from the Microsoft Store, then inside it:

```bash
# Install Coral inside WSL Ubuntu
curl -fsSL https://install.withcoral.com | bash
```

### 2 — Clone & install the Python package

```bash
git clone https://github.com/SamChawla/devsecops-coral.git
cd devsecops-coral

# Install in editable mode (adds the `devsecops-coral` CLI command)
pip install -e .

# Verify the CLI is available
devsecops-coral --help
```

### 3 — Configure environment variables

```bash
# Copy the example and fill in your values
cp .env.example .env
```

Open `.env` and set the following:

```dotenv
# ── LLM provider (pick one) ─────────────────────────────────────────
# Option A — Cursor Pro (recommended if you have a subscription)
LLM_PROVIDER=cursor
CURSOR_BASE_URL=http://localhost:4646/v1
CURSOR_API_KEY=not-needed
CURSOR_MODEL=auto
# Start the proxy in a separate terminal: npx cursor-agent-api-proxy

# Option B — Anthropic API key
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...

# Option C — EURI (euron.one Plus)
# LLM_PROVIDER=euri
# EURI_API_KEY=your-key
# EURI_MODEL=gemini-2.5-flash

# ── Coral binary path (Windows with WSL) ────────────────────────────
CORAL_BIN=wsl -d Ubuntu -e /root/.local/bin/coral

# ── GitHub repo (required for github.pulls / timeline queries) ───────
GITHUB_OWNER=your-github-username
GITHUB_REPO=your-repo-name
```

> **Note:** Coral source tokens (GitHub PAT, Sentry auth, Jira token, Grafana key) are stored inside Coral's own encrypted config — never in `.env`.

### 4 — Add Coral data sources

**OSV** (public API — no auth needed):

```bash
coral source add --file sources/osv/osv.yaml

# Verify it works
coral sql "SELECT id, severity FROM osv.search_vulnerabilities(package => 'django', ecosystem => 'PyPI') LIMIT 3"
```

**Bundled sources** (each prompts for an API token interactively):

```bash
coral source add --interactive github   # needs a GitHub PAT with repo + read:org
coral source add --interactive sentry   # needs a Sentry auth token
coral source add --interactive jira     # needs a Jira API token + site URL
coral source add --interactive grafana  # needs a Grafana API key
```

> Free accounts work for all four: [GitHub](https://github.com), [Sentry](https://sentry.io/signup/), [Jira Cloud](https://www.atlassian.com/software/jira/free), [Grafana Cloud](https://grafana.com/auth/sign-up/create-user).

Check which sources are connected:

```bash
coral source list
```

### 5 — Run the CLI

```bash
# Security posture scan — checks packages against OSV + Jira tracking
devsecops-coral scan --ecosystem PyPI --packages django,flask,requests,celery

# Vulnerability ↔ error correlation (requires Sentry)
devsecops-coral correlate --since 7d

# Unified security event timeline
devsecops-coral timeline --since 24h

# Natural language agent query (requires LLM provider in .env)
devsecops-coral ask "Which critical vulnerabilities have no Jira tickets?"
```

### 6 — Run the dashboard

**Option A — Development mode** (two terminals, hot-reload on both sides):

```bash
# Terminal 1 — FastAPI backend on :8000
uvicorn devsecops_coral.api:app --reload

# Terminal 2 — Vite dev server on :5173
cd frontend
npm install        # first time only
npm run dev
```

Open **[http://localhost:5173](http://localhost:5173)**

---

**Option B — Production mode** (single command after building the frontend):

```bash
# Build the React app into frontend/dist/
cd frontend && npm install && npm run build && cd ..

# Serve frontend + API together on :8000
devsecops-coral serve
```

Open **[http://localhost:8000](http://localhost:8000)**

---

## The Problem

Security and DevOps teams operate across fragmented tools. A vulnerability report in OSV, a merged PR in GitHub, an error spike in Sentry, a Jira ticket, a Grafana alert — all related, all in different dashboards. Correlating them manually takes 20–30 minutes per incident and junior engineers miss connections entirely.

## The Solution

CoralSentinel uses [Coral](https://withcoral.com) to join vulnerability intelligence, source control, error monitoring, issue tracking, and infrastructure observability into a **single SQL query** — executed locally, securely, with zero ETL.

```sql
-- Are we vulnerable, and if so — where, when, and who shipped it?
SELECT
    osv.id          AS cve,
    osv.severity,
    g.title         AS pr_title,
    g.user_login    AS author,
    se.title        AS error,
    se.count        AS frequency,
    j.key           AS ticket,
    j.status
FROM osv.search_vulnerabilities(package => 'django', ecosystem => 'PyPI') osv
LEFT JOIN github.pulls  g  ON g.owner = 'your-org' AND g.repo = 'your-repo' AND g.state = 'merged'
LEFT JOIN sentry.issues se ON se.level IN ('fatal', 'error')
LEFT JOIN jira.issues   j  ON j.labels LIKE '%security%'
WHERE osv.severity = 'CRITICAL'
ORDER BY se.count DESC;
```

## Data Sources

| Source | Type | What It Provides |
|---|---|---|
| **OSV** (osv.dev) | Custom source spec | Known CVEs across PyPI, npm, Go, Maven, and 15+ ecosystems |
| **GitHub** | Bundled | PRs, commits, Dependabot alerts, workflow runs |
| **Sentry** | Bundled | Application errors, event frequency, severity |
| **Jira** | Bundled | Security tickets, triage status, priority |
| **Grafana** | Bundled | Alert rules, annotations, infrastructure health |

## Dashboard

The React dashboard provides a **Security Command Center** with dark/light theme toggle, severity-colored metrics, and a transparent SQL viewer.

| View | Description |
|---|---|
| **Posture Overview** | CRITICAL / HIGH / MEDIUM / LOW counters + risk score |
| **Vulnerability Scan** | Full CVE table with Jira tracking status and Sentry error counts |
| **Correlate** | Vulnerability ↔ error signal cards (🔴 ACTIVE / 🟡 MONITOR / 🟢 CLEAN) |
| **Timeline** | Chronological events from all connected sources |
| **Query Console** | Natural language or raw SQL input with live results |
| **SQL Viewer** | Shows the actual Coral SQL executed — cross-source JOIN transparency |

Every API response includes a `sql` field so the SQL Viewer always shows the real query.

## CLI Commands

### `scan`

```
$ devsecops-coral scan --ecosystem PyPI --packages django,flask,requests

 Package    │ CVE            │ Severity │ Jira Ticket │ Status
────────────┼────────────────┼──────────┼─────────────┼────────
 django     │ GHSA-xxx-xxx   │ CRITICAL │ SEC-1       │ In Progress
 requests   │ GHSA-yyy-yyy   │ HIGH     │ —           │ ⚠ UNTRACKED
 flask      │ —              │ —        │ —           │ ✅ Clean
```

### `correlate`

```
$ devsecops-coral correlate --since 7d

 CVE          │ Package  │ Severity │ Errors │ Signal
──────────────┼──────────┼──────────┼────────┼────────
 GHSA-xxx-xxx │ django   │ CRITICAL │ 47     │ 🔴 ACTIVE
 GHSA-yyy-yyy │ requests │ HIGH     │ 3      │ 🟡 MONITOR
```

### `timeline`

```bash
devsecops-coral timeline --since 24h
```

### `ask` (LLM agent)

```bash
devsecops-coral ask "Which PRs in the last week introduced vulnerable dependencies?"
```

### `serve` (dashboard)

```bash
devsecops-coral serve --host 127.0.0.1 --port 8000
```

## OSV Custom Source Spec

This project ships a custom Coral source spec for [OSV](https://osv.dev) — Google's open-source vulnerability database. It works without any API key and covers 15+ package ecosystems.

```bash
# Use independently of this project
coral source add --file sources/osv/osv.yaml
coral sql "SELECT id, summary, severity FROM osv.search_vulnerabilities(package => 'requests', ecosystem => 'PyPI') LIMIT 5"
```

See the [custom source spec guide](https://withcoral.com/docs/guides/write-a-custom-source) for how it's built.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              React Dashboard (frontend/)                     │
│  Posture │ Scan │ Correlate │ Timeline │ SQL Viewer          │
└────────────────────────────┬────────────────────────────────┘
                             │ REST /api/*
┌────────────────────────────┴────────────────────────────────┐
│              FastAPI — api.py                                │
│  /api/scan  /api/correlate  /api/timeline  /api/ask          │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────┐
│         Shared Query Engine — queries/                       │
│  CLI (Typer + Rich) ──── same runners ──── Agent (LLM)      │
└────────────────────────────┬────────────────────────────────┘
                             │ coral_client.py
┌────────────────────────────┴────────────────────────────────┐
│                    Coral Runtime                             │
│   OSV (custom) · GitHub · Sentry · Jira · Grafana           │
└─────────────────────────────────────────────────────────────┘
```

All queries execute locally via Coral. No data leaves your machine. The LLM agent only receives query results, not raw API responses.

## Demo Scenarios

- [Active exploitation](demo/scenarios/active_exploitation.md) — CVE + Sentry error spike correlation
- [Untracked CVEs](demo/scenarios/untracked_cves.md) — vulnerabilities without Jira tickets

Seed Sentry with real demo errors:

```bash
cd demo/fastapi_app
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
# Hit /vulnerable, /unhandled, /generate-errors to populate Sentry
```

## Development

```bash
pip install -e ".[dev]"   # includes pytest, ruff, pytest-mock

pytest tests/             # run tests
ruff check src/           # lint

cd frontend && npm run dev  # frontend hot-reload (needs backend on :8000)
```

Full testing runbook: [docs/TESTING.md](docs/TESTING.md)

## Built With

- [Coral](https://withcoral.com) — SQL interface for APIs and data sources
- [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) — Dashboard API server
- [React 19](https://react.dev/) + [Vite 6](https://vite.dev/) — Security command center UI
- [Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/) — CLI
- [Anthropic Claude](https://anthropic.com) — LLM agent layer
- Python 3.10+

## Background

Built for the [Pirates of the Coral-bean](https://www.wemakedevs.org/hackathons/coral) hackathon (May 25–31, 2026), organized by WeMakeDevs.

As an engineer who has spent 8+ years building integrations across security and DevOps tools — including multi-vendor EDR/SIEM normalization across CrowdStrike, SentinelOne, Microsoft Defender, Cortex XDR, and IBM QRadar — I've experienced firsthand how painful cross-platform signal correlation is. CoralSentinel is the tool I wish I had: one SQL query to answer "what's happening across my entire security stack?"

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.

## Acknowledgements

- [Coral](https://withcoral.com) team for building an incredible open-source query layer
- [OSV](https://osv.dev) by Google for the open vulnerability database
- [WeMakeDevs](https://wemakedevs.org) and [Kunal Kushwaha](https://www.linkedin.com/in/kunal-kushwaha) for organizing
