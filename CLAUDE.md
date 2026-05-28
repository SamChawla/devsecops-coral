# CLAUDE.md — Development Guardrails for devsecops-coral

This file provides context and rules for AI-assisted development of the devsecops-coral project using Claude Code, Cursor, or any MCP-compatible coding agent.

---

## Project Overview

devsecops-coral is a CLI tool and AI agent that correlates security signals across multiple DevSecOps platforms using Coral's SQL interface. It queries OSV (vulnerabilities), GitHub (code/deploys), Sentry (errors), Jira (tickets), and Grafana (infrastructure) through cross-source SQL JOINs.

**This is a hackathon project (May 25-31, 2026). Ship fast, ship clean, ship at 80%.**

---

## Architecture Rules

### Source of Truth

- Coral handles ALL data source communication. Never call GitHub/Sentry/Jira/Grafana/OSV APIs directly from Python.
- The Python code generates SQL queries, sends them to Coral (via MCP or CLI subprocess), and formats the results.
- The OSV source spec (`sources/osv/osv.yaml`) defines how Coral maps SQL to the OSV API. Do not bypass it.

### Coral Integration

- **Primary:** Use Coral over MCP when available (for agent integration)
- **Fallback:** Use `coral sql "..."` via subprocess when MCP isn't practical (for CLI commands)
- Always use parameterized queries — never string-interpolate user input into SQL
- Coral returns tabular results. Parse them as structured data, not regex.

### LLM Agent

- The agent translates natural language → Coral SQL → human-readable analysis
- Use Claude (Anthropic API) as the LLM. Model: `claude-sonnet-4-20250514`
- Keep system prompts minimal and focused. Include available table schemas.
- The agent should ONLY generate SELECT queries. Never INSERT, UPDATE, DELETE, or DDL.
- If the agent generates invalid SQL, catch the Coral error and retry once with the error message in context.

---

## Code Standards

### Python

- **Version:** Python 3.10+ (match Coral's requirements)
- **Style:** Follow PEP 8. Use `ruff` for linting.
- **Type hints:** Required on all function signatures
- **Docstrings:** Required on all public functions and classes
- **Imports:** Use absolute imports. Group: stdlib → third-party → local

### Dependencies (keep minimal)

```
# Core — these are the ONLY allowed production dependencies
typer>=0.9.0          # CLI framework
rich>=13.0.0          # Terminal formatting
httpx>=0.27.0         # HTTP client (for agent API calls only, NOT for data sources)
anthropic>=0.40.0     # Claude API for agent layer
pydantic>=2.0.0       # Data validation
fastapi>=0.115.0      # Dashboard REST API
uvicorn>=0.30.0       # ASGI server for devsecops-coral serve

# Dev only
pytest>=8.0.0
ruff>=0.5.0
```

**Do NOT add:**
- `requests` — use `httpx` (async-ready, modern)
- `flask`, `django` — use FastAPI for the dashboard API only
- `pandas`, `numpy` — overkill for formatting query results
- `langchain`, `crewai`, `autogen` — no agent frameworks. Keep it simple: raw Anthropic API calls.
- Any database drivers — Coral IS the database layer

### Error Handling

- Wrap all Coral calls in try/except. Surface clear error messages to the user.
- If a Coral source isn't configured, tell the user which source is missing and how to add it.
- If the OSV API is unreachable, fail gracefully with a cached-data fallback message.
- Never show raw tracebacks to the user. Use `rich.console.print_exception()` only in `--debug` mode.

---

## File Structure Rules

```
src/devsecops_coral/       # All source code here
├── cli.py                 # Typer app with commands: scan, correlate, timeline, ask, serve
├── api.py                 # FastAPI app — dashboard REST endpoints
├── models.py              # Pydantic request/response models
├── agent.py               # LLM integration — intent parsing, SQL generation, analysis
├── coral_client.py        # Coral MCP/CLI wrapper — the ONLY file that talks to Coral
├── queries/               # SQL query templates (parameterized)
│   ├── correlate.py       # Vulnerability-deploy-error correlation
│   ├── scan.py            # Security posture scan
│   ├── timeline.py        # Unified event timeline
│   └── posture.py         # Severity aggregation
├── formatters/            # Output formatting
│   ├── rich_output.py     # Rich terminal tables with severity colors
│   ├── json_output.py     # JSON export
│   └── markdown_output.py # Markdown report
└── config.py              # Configuration (Coral path, LLM settings)
```

**Rules:**
- `coral_client.py` is the ONLY file that executes Coral commands. All other modules go through it.
- `queries/` contains SQL templates as Python strings with `{parameter}` placeholders. Never raw string interpolation.
- `formatters/` transforms query results into display format. They receive structured data, not raw SQL output.
- Keep each file under 200 lines. Split if it grows beyond that.

---

## SQL Query Rules

### Parameterization

```python
# ✅ CORRECT — parameterized template
SCAN_QUERY = """
SELECT osv.id, osv.summary, osv.severity
FROM osv.vulnerabilities osv
WHERE osv.ecosystem = '{ecosystem}'
    AND osv.package_name IN ({packages})
ORDER BY osv.severity DESC
"""

def build_scan_query(ecosystem: str, packages: list[str]) -> str:
    # Validate inputs before interpolation
    assert ecosystem.isalpha(), "Ecosystem must be alphabetic"
    package_list = ", ".join(f"'{p.strip()}'" for p in packages)
    return SCAN_QUERY.format(ecosystem=ecosystem, packages=package_list)
```

```python
# ❌ WRONG — direct f-string with user input
query = f"SELECT * FROM osv.vulnerabilities WHERE package_name = '{user_input}'"
```

### Cross-Source JOIN Patterns

When writing JOINs across sources, follow these patterns:

1. **Temporal correlation:** Use time windows, not exact timestamps
   ```sql
   -- ✅ Time window (realistic)
   ON se.first_seen BETWEEN DATE_SUB(g.merged_at, INTERVAL 2 HOUR) AND DATE_ADD(g.merged_at, INTERVAL 6 HOUR)
   
   -- ❌ Exact match (will never match)
   ON se.first_seen = g.merged_at
   ```

2. **Text-based correlation:** Use LIKE with key identifiers
   ```sql
   -- ✅ Flexible matching
   ON j.summary LIKE CONCAT('%', osv.id, '%')
   
   -- ❌ Exact match (formatting differences will break this)
   ON j.summary = osv.id
   ```

3. **Always use LEFT JOIN for cross-source queries** — data may not exist in all sources
   ```sql
   -- ✅ Handles missing data gracefully
   LEFT JOIN jira.issues j ON ...
   
   -- ❌ Drops results when no Jira ticket exists
   INNER JOIN jira.issues j ON ...
   ```

### Query Testing

Before considering a query done:
1. Run it with `coral sql "..."` manually
2. Test with empty results (no matching data) — should return empty table, not error
3. Test with NULL fields — should handle gracefully
4. Test with large result sets — should not hang

---

## CLI Output Rules

### Severity Color Coding (ALWAYS use these)

```python
SEVERITY_COLORS = {
    "CRITICAL": "bold red",
    "HIGH": "red",  
    "MEDIUM": "yellow",
    "LOW": "green",
    "INFO": "blue",
}

SIGNAL_ICONS = {
    "active": "🔴",
    "monitor": "🟡",
    "clean": "🟢",
    "unknown": "⚪",
}
```

### Output Format

- Default: Rich terminal table
- `--format json`: JSON to stdout (no colors, no emoji)
- `--format md`: Markdown (for piping to files)
- `--debug`: Show raw SQL queries and Coral responses

### User Messages

- Be concise. No walls of text.
- Lead with the most critical finding.
- End with a recommended action when a threat is found.
- Never show raw SQL in default output. Only in `--debug` mode.

---

## OSV Source Spec Rules

The custom source spec at `sources/osv/osv.yaml` follows Coral DSL v3.

### Format Requirements (DSL v3)

1. **Required top-level fields:** `name`, `version`, `dsl_version: 3`, `backend: http`
2. **No `inputs` block** — OSV is a public API with no authentication
3. **Column types must be Coral types:** `Utf8` (not `string`), `Timestamp` (not `timestamp`), `Int64`, `Float64`, `Boolean`, `Json`
4. **Nested fields use `__` (double underscore):** `affected__package__name`, NOT `affected.package.name`
5. **Column expressions use `expr:` blocks:** `kind: path` with `path: [segments]`, NOT dot notation
6. **OSV `/v1/query` is a search function** with `kind: search` under `functions:`, NOT a regular table
7. **OSV `/v1/vulns/{id}` is a detail table** with a required filter on `id`
8. **Include `test_queries`** — cheap SELECT with LIMIT for `coral source test` validation

### Search Function SQL Syntax

OSV queries use **table function syntax** (named arguments), NOT WHERE clauses:

```sql
-- ✅ CORRECT — search function with named arguments
SELECT id, summary, severity
FROM osv.search_vulnerabilities(package => 'django', ecosystem => 'PyPI')
LIMIT 10

-- ❌ WRONG — this is NOT how search functions work
SELECT * FROM osv.vulnerabilities WHERE package_name = 'django'

-- ✅ CORRECT — cross-source JOIN with search function
SELECT osv.id, osv.severity, g.title AS pr_title
FROM osv.search_vulnerabilities(package => 'django', ecosystem => 'PyPI') osv
LEFT JOIN github.pulls g ON g.state = 'merged'

-- ✅ CORRECT — detail lookup by ID (regular table with required filter)
SELECT id, summary, details
FROM osv.vulnerability_detail
WHERE id = 'GHSA-xxxx-xxxx-xxxx'
```

### Coral CLI Commands (CORRECT — use these, not outdated ones)

```bash
# Lint — fast local precheck, no credentials or install needed
coral source lint ./sources/osv/osv.yaml

# Add — installs the source (validates on install)
coral source add --file ./sources/osv/osv.yaml

# Test — runs test_queries declared in the spec
coral source test osv

# Inspect schema — see what Coral actually exposes
coral sql "SELECT * FROM coral.tables WHERE schema_name = 'osv'"
coral sql "SELECT * FROM coral.columns WHERE schema_name = 'osv'"
coral sql "SELECT * FROM coral.table_functions WHERE schema_name = 'osv'"

# ❌ WRONG commands (do NOT use)
# coral source validate     ← does not exist
# coral source add --spec   ← wrong flag, use --file
```

---

## Testing Rules

- Tests go in `tests/` directory
- Use `pytest` with fixtures for mock data
- Mock Coral responses using JSON fixtures in `tests/fixtures/`
- Do NOT mock at the HTTP level — mock at the `coral_client.py` level
- Every query template must have at least one test with sample data
- Test formatters with both full and empty result sets

```python
# ✅ CORRECT — mock at coral_client level
def test_scan_query(mocker):
    mock_result = [{"id": "GHSA-xxx", "summary": "Test", "severity": "HIGH"}]
    mocker.patch("devsecops_coral.coral_client.execute_query", return_value=mock_result)
    result = scan(ecosystem="PyPI", packages=["django"])
    assert len(result) == 1
```

---

## Frontend / Dashboard Rules

### Architecture

- **React + Vite (inline styles, no CSS framework)** in `frontend/` directory
- **FastAPI** backend in `src/devsecops_coral/api.py` serves both the REST API and static frontend build
- Frontend calls backend API endpoints — NEVER calls Coral directly
- `devsecops-coral serve` starts FastAPI with the built frontend served from `frontend/dist/`

### Design Direction: Security Command Center

- **Dark theme only** — navy/slate background (`#020617`, `#0f172a`)
- **Severity colors are sacred:** CRITICAL=red, HIGH=orange, MEDIUM=yellow, LOW=green, INFO=blue
- **Monospace for data:** JetBrains Mono for CVE IDs, SQL queries, timestamps
- **Sans-serif for labels:** Inter for headings, descriptions, navigation
- **Ambient glow effects** for active threats — subtle radial gradients, not flashy
- **NO generic AI aesthetics** — no purple gradients, no rounded-everything, no Inter-only

### Component Rules

```
components/
├── SourceStatus.jsx      # Left sidebar: 5 sources with connection dots + MCP/cache status
├── PostureOverview.jsx   # Top cards: CRITICAL/HIGH/MED/LOW severity counters
├── ScanTable.jsx         # Full vulnerability table with all columns
├── CorrelationView.jsx   # Vuln ↔ Error signal cards (🔴 ACTIVE / 🟡 MONITOR / 🟢 CLEAN)
├── Timeline.jsx          # Vertical timeline with source-colored dots
├── QueryConsole.jsx      # Dual-mode input: natural language ↔ raw SQL + results
└── SqlViewer.jsx         # Shows generated Coral SQL (transparency for judges)
```

- Every component receives data from the API via `useApi` hooks — no hardcoded mock data in production
- **SqlViewer is CRITICAL** — this is what differentiates from a pretty wrapper. Show the actual 5-source JOIN query so judges see the Coral depth.
- Query Console must support BOTH natural language AND raw SQL mode with a toggle

### FastAPI Backend Endpoints

```python
# All endpoints must return both `data` AND `sql` fields
# The `sql` field contains the Coral SQL that was executed — for the SqlViewer

@app.get("/api/scan")
async def scan(ecosystem: str, packages: str) -> ScanResponse:
    """Returns vulnerability scan results + the Coral SQL used."""

@app.get("/api/correlate")
async def correlate(since: str = "7d") -> CorrelateResponse:
    """Returns vulnerability-error correlations + the Coral SQL used."""

@app.get("/api/timeline")
async def timeline(since: str = "24h") -> TimelineResponse:
    """Returns unified event timeline + the Coral SQL used."""

@app.post("/api/ask")
async def ask(query: AskRequest) -> AskResponse:
    """Agent: natural language → SQL → results → analysis."""

@app.get("/api/sources")
async def sources() -> SourcesResponse:
    """Returns connected source status (from coral.tables metadata)."""

@app.get("/api/posture")
async def posture() -> PostureResponse:
    """Returns aggregated severity counts."""
```

### What NOT to Do in Frontend

- Do NOT use localStorage/sessionStorage (doesn't work in all contexts)
- Do NOT make the dashboard depend on external CDNs at runtime (bundle everything)
- Do NOT add user authentication (it's a local tool, not a SaaS)
- Do NOT auto-refresh data on intervals (let the user trigger queries)
- Do NOT hide the SQL — the whole point is transparency

### Build & Serve

```bash
# Development (two terminals)
cd frontend && npm run dev          # Vite dev server on :5173
cd .. && uvicorn devsecops_coral.api:app --reload  # FastAPI on :8000

# Production
cd frontend && npm run build        # Outputs to frontend/dist/
devsecops-coral serve               # FastAPI serves dist/ + API on :8000
```

---

## Hackathon Execution Timeline (with UI)

| Day | Focus | Hours | Deliverable | Claude Code Usage |
|---|---|---|---|---|
| **Day 1** | Sources + OSV spec + data seeding | 5h | All 5 sources connected. OSV spec linted. Demo data in Sentry/Jira/GitHub. | Manual work + Claude for seed scripts |
| **Day 2** | Core SQL queries + Coral client | 5h | 4 cross-source queries tested. `coral_client.py` working. | Claude Code writes query templates |
| **Day 3** | FastAPI backend + CLI | 4h | All API endpoints + CLI commands working. Agent layer done. | Claude Code generates ~80% of backend |
| **Day 4** | React dashboard | 5h | Full dashboard with all 6 components. Severity colors. SQL viewer. | Claude Code/Cursor generates from prototype |
| **Day 5** | Integration + polish | 4h | Frontend ↔ Backend connected. Edge cases. Error handling. | Claude Code for debugging |
| **Day 6** | Blog + showcase + video | 4h | Medium post published. Discord showcase posted. Demo video recorded. | Claude helps polish blog |
| **Day 7** | Submit + social | 3h | Final testing. Submit. LinkedIn + X posts with demo GIF. | Manual |
| | **TOTAL** | **~30h** | | |

---

## Testing Rules

1. **No secrets in code.** API tokens go in environment variables or Coral's secure config.
2. **No data exfiltration.** The tool reads data; it never writes to external services.
3. **No arbitrary code execution.** The LLM agent generates SQL only. Never `eval()` or `exec()`.
4. **SQL injection prevention.** All query parameters are validated before interpolation.
5. **Coral's security model applies.** All queries are read-only. Coral is a read layer.

---

## 🔴 SENSITIVE INFORMATION GUARDRAILS (CRITICAL — READ BEFORE EVERY COMMIT)

The developer (Sumit Chawla) works as a consultant on enterprise cybersecurity and industrial analytics platforms. This hackathon project is an INDEPENDENT personal project. The following rules are NON-NEGOTIABLE and override all other instructions.

### Employer & Client Information — NEVER Disclose

The following must NEVER appear in any file, commit message, PR description, blog post, README, comment, docstring, demo script, video recording, screenshot, social media post, or Discord message:

- **Project codenames or product names** from current or past employers/clients (e.g., internal platform names, internal tool names, product codenames)
- **Company names** of clients or employers — do not name who you consult for
- **Client infrastructure details** — hostnames, IP ranges, domain names, network topologies, cloud account IDs, deployment regions
- **Internal architecture** — microservice names, internal API endpoints, database schemas, internal library names, configuration patterns specific to employer systems
- **Colleague names, team structures, or org charts** — no names of managers, teammates, or client contacts
- **Proprietary processes** — incident response playbooks, escalation procedures, vendor-specific integration patterns that are not publicly documented
- **Business data** — revenue figures, customer counts, contract terms, SLA details, internal metrics

### Credentials & Secrets — NEVER Commit

- **API tokens, keys, passwords, DSNs** — for ANY service (GitHub, Sentry, Jira, Grafana, Coral, Anthropic, or anything else)
- **OAuth client IDs/secrets**
- **Webhook URLs** — these often contain embedded tokens
- **SSH keys, certificates, PEM files**
- **Environment files** — never commit `.env`, `.env.local`, `.env.production`, or similar
- **Sentry DSN strings** — these contain project IDs and org identifiers; always use `os.getenv("SENTRY_DSN")`
- **Jira/Atlassian site URLs with org names** — use placeholder `your-site.atlassian.net` in docs
- **Grafana instance URLs** — use placeholder `your-org.grafana.net` in docs

### .gitignore Enforcement

The repository MUST contain a `.gitignore` that blocks:

```gitignore
# Secrets — NEVER commit
.env
.env.*
*.pem
*.key
secrets/
credentials/

# IDE
.idea/
.vscode/
*.code-workspace
.cursor/

# Python
__pycache__/
*.pyc
*.egg-info/
dist/
build/
.venv/
venv/

# OS
.DS_Store
Thumbs.db

# Coral config (may contain tokens)
.coral/
coral-config.yaml

# Sentry
.sentryclirc

# Demo data that might contain real info
demo/data/
*.sqlite3
```

### Safe Narrative Patterns

When writing README, blog posts, demo scripts, or social media:

```
# ✅ SAFE — generic experience reference
"As an engineer who has spent 8+ years building integrations across 
security and DevOps tools..."

"In my consulting work, I've integrated multiple EDR and SIEM vendors —
normalizing threat data across different platforms..."

"Having worked on cybersecurity case management platforms that correlate 
signals from CrowdStrike, SentinelOne, Defender, and QRadar..."

# ❌ UNSAFE — names employers, clients, or projects
"At [Company], I built [Product Name] which integrates with..."
"My client [Client Name] uses our platform to..."
"On the [Project Codename] project, we architected..."
```

### Demo Data Rules

- ALL demo data must be synthetic, created in personal free-tier accounts
- Never copy real incident data, real vulnerability reports, or real ticket content from work
- Jira ticket descriptions should be generic: "Django ReDoS vulnerability requires upgrade" — NOT copied from actual internal tickets
- Sentry errors come from the demo FastAPI app only — never import or reference real production errors
- If screenshotting tools for blog/demo, verify no client data is visible in the browser tabs, bookmarks bar, sidebar, or notifications

### Code Review Checklist (Run Before Every Commit)

```bash
# Search for potential secrets
grep -rn "ghp_\|sntrys_\|glsa_\|sk-\|AKIA\|password\|secret\|token" --include="*.py" --include="*.yaml" --include="*.md" --include="*.toml" src/ demo/ docs/

# Search for potential employer/client references  
grep -rni "sunrise\|phoenix\|emf\|shipco\|provab\|infobeans" --include="*.py" --include="*.yaml" --include="*.md" --include="*.toml" src/ demo/ docs/ README.md CLAUDE.md

# Search for hardcoded URLs that might be internal
grep -rn "atlassian.net\|sentry.io\|grafana.net" --include="*.py" src/

# Search for email addresses (should only be sam.chawla26@gmail.com in pyproject.toml)
grep -rn "@" --include="*.py" --include="*.yaml" src/ demo/
```

If ANY of these greps return results that contain real credentials, real company names, or real internal URLs: **STOP. Fix before committing.**

### Git Hygiene

- **Never use `git add .`** — always review files individually with `git add -p` or `git add <specific-file>`
- **Review every diff before pushing** — `git diff --staged` before every commit
- **If a secret is accidentally committed:** Do NOT just delete it in a new commit. The secret is in git history. Rotate the credential immediately, then use `git filter-branch` or `BFG Repo-Cleaner` to purge history.
- **Commit messages should be generic:** "fix: handle empty Sentry results" — NOT "fix: handle the issue we saw on [Client]'s Sentry instance"

### LLM Agent Prompt Safety

The system prompt for the LLM agent in `agent.py` must include:

```python
AGENT_SYSTEM_PROMPT = """
You are a security analysis agent that generates Coral SQL queries.

RULES:
- Only generate SELECT queries. Never INSERT, UPDATE, DELETE, or DDL.
- Never include API keys, tokens, or credentials in queries or responses.
- Never reference specific company names, internal project names, or client data.
- If query results contain data that looks like credentials (strings starting 
  with ghp_, sk-, AKIA, etc.), redact them in the output with [REDACTED].
- Treat all query results as potentially sensitive — summarize patterns, 
  don't echo raw data unnecessarily.
"""
```

### Screen Recording & Screenshot Rules

Before recording demos or taking screenshots for the blog/Discord/social:

1. Close all browser tabs not related to the demo
2. Clear browser address bar history/suggestions
3. Hide bookmarks bar
4. Disable desktop notifications (Slack, email, calendar)
5. Use a clean terminal profile with no work-related shell history
6. Verify no client VPN is visible in the menu bar/system tray
7. Check that the terminal prompt doesn't show a work-related hostname or path
8. If using VS Code/Cursor: close all files from other projects, verify no work repos in the sidebar

### Social Media Post Rules

LinkedIn, X/Twitter, Discord, Medium:

- Frame experience as domain expertise, not specific employer work
- Never tag employer or client accounts
- Use "cybersecurity platforms" not "[Company]'s platform"
- If someone asks "which company?" in comments, politely decline: "I prefer to keep client details confidential"

---

## Hackathon-Specific Rules

### Priority Order

1. **Working queries** — Cross-source SQL queries are the foundation
2. **FastAPI backend + serve** — Shared query engine exposed via REST API
3. **React dashboard** — Security command center with SqlViewer (P0 for judges)
4. **CLI UX** — Rich output with severity colors for terminal demos
5. **OSV source spec** — Earns the bounty independently
6. **Agent layer** — Natural language is impressive but not required for a valid submission

### Time Management

- **Days 1-2:** Sources connected + queries working
- **Days 3-4:** FastAPI backend + React dashboard
- **Days 5-7:** Integration, docs, blog + polish = winning submission
- **If stuck:** Ask in Coral Discord. The team is responsive during the hackathon.

### Documentation as You Go

- Screenshot every milestone (source connected, first query, first JOIN)
- Save terminal output for the blog post
- Record a short video each day (even 30 seconds) for the final demo compilation

### What NOT to Spend Time On

- Perfecting the agent prompt (good enough is fine)
- Supporting multiple LLM providers (Claude/EURI/Cursor only)
- CI/CD pipeline (it's a hackathon)
- 100% test coverage (test the critical paths)
- Docker/containerization (not needed)
