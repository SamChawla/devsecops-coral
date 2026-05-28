# Product Requirements Document (PRD)
# devsecops-coral — Cross-Stack Security Operations Agent

**Version:** 3.0  
**Author:** Sumit Chawla (@sumit_sd)  
**Date:** May 27, 2026  
**Hackathon:** Pirates of the Coral-bean (WeMakeDevs × Coral)  
**Track:** Track 1 — Enterprise Agent  
**Duration:** May 25–31, 2026 (7 days)  
**Team Size:** Solo  
**Dev Tools:** Claude Code + Cursor for AI-accelerated development  
**UI Prototype:** `ui-prototype.jsx` (Detect → Actions → Timeline tabs)

---

## 1. Problem Statement

Security and DevOps teams operate across fragmented tooling. When a vulnerability is discovered or an incident occurs, the first critical question — *"What else is happening across our stack?"* — requires manual cross-referencing across 4–6 different platforms:

- **Vulnerability databases** (OSV, NVD) report known CVEs
- **Source control** (GitHub) tracks code changes and dependency updates
- **Error monitoring** (Sentry) captures application-level failures
- **Issue trackers** (Jira) manage security tickets and triage status
- **Observability platforms** (Grafana) surface infrastructure anomalies

Today, a senior security engineer spends 20–30 minutes per incident manually correlating these signals **and** another 20–30 minutes creating tickets, opening PRs, and updating dashboards. Junior engineers frequently miss cross-platform connections entirely. Existing tools either:

1. **Read-only dashboards** — show pretty tables but leave remediation to the human
2. **Expensive SOAR platforms** — automate response but require enterprise budgets and months of integration

There is no lightweight agent that **detects** cross-source patterns via SQL, **recommends** remediation actions, and **executes** them with human approval.

### Who Feels This Pain

- **Security Engineers / Analysts** — Need to correlate vulnerability reports with codebase impact and kick off remediation
- **DevOps / SRE Teams** — Need to assess whether a deploy introduced security regressions and annotate timelines
- **Engineering Leads** — Need security posture visibility and actionable next steps across projects
- **Compliance Teams** — Need audit trails connecting CVEs to remediation tickets and PRs

### Current Workarounds

1. Manual tab-switching across 4–6 dashboards, then manual ticket/PR creation
2. Custom Python scripts with per-vendor API integrations (brittle, unmaintained)
3. Expensive SOAR/SIEM platforms (Splunk, Datadog Security) — overkill for most teams
4. Spreadsheet-based tracking (common in smaller teams)

---

## 2. Proposed Solution

**devsecops-coral** is an AI-powered **security operations agent** that completes the full workflow:

```
DETECT (Coral reads)  →  RECOMMEND (Agent analyzes)  →  ACT (Agent executes with approval)
```

| Phase | Powered By | What Happens |
|---|---|---|
| **DETECT** | Coral cross-source SQL JOINs | Reads OSV + GitHub + Sentry + Jira + Grafana in one query |
| **RECOMMEND** | LLM Agent (Claude) | Analyzes gaps: untracked CVEs, active exploitation, missing PRs |
| **ACT** | Direct API calls (`httpx`) | Creates Jira tickets, drafts GitHub PRs, annotates Grafana — **after human approval** |

### Core Value Proposition

> Replace 30 minutes of manual cross-referencing **and** 30 minutes of remediation busywork with one agent workflow: Coral detects, the agent recommends, you approve, the agent acts.

### The Agent Pattern (What Wins Track 1)

This is **not** a dashboard. A dashboard reads and displays. An **agent** detects, reasons, recommends, and acts — with the human in the loop at the critical decision point. This human-in-the-loop approval pattern is exactly what won AgentHack.

**Tagline (footer, demo, judges):**

> 🪸 coral reads → agent analyzes → human approves → agent acts

### How Coral and Direct APIs Divide Labor

| Operation | Path | Rationale |
|---|---|---|
| Read / correlate / JOIN | **Coral SQL** (MCP or CLI) | Coral's design: unified read layer across sources |
| Write / create / update | **Direct REST APIs** via `httpx` | Coral is read-only; writes go to Jira, GitHub, Grafana APIs |
| Reason / recommend | **LLM Agent** | Translates detection results into structured action plans |
| Execute | **Action executor** (after approval) | Same tokens used for Coral source setup work for write ops |

Without Coral, building DETECT alone requires 5 separate API integrations with auth, pagination, rate limiting, and custom join logic. With Coral, one SQL query JOINs all 5 sources. The ACT layer then uses the same credentials you already configured for those sources.

---

## 3. Target Users

### Primary: Security-Aware Engineering Teams (5–50 engineers)

Teams that are too small for a dedicated SOC but too mature to ignore security. They use GitHub, Jira, Sentry, and possibly Grafana. They track CVEs but don't have automated correlation **or** remediation.

### Secondary: Developer Security Champions

Individual developers designated as security leads within their team. They need a quick way to check "are we exposed?" and approve fixes without deep security tooling expertise.

---

## 4. The Use Case (Demo Story for Judges)

A security engineer starts their day. The agent has already scanned dependencies against OSV, correlated them with Sentry errors and GitHub deploys, and found gaps. They open the dashboard and see:

| Finding | Signal |
|---|---|
| 🔴 2 untracked CVEs | No Jira tickets exist for requests and pillow |
| 🔴 1 potential active exploitation | Pillow CVE + 12 fatal Sentry errors in the same window |
| 🟢 1 CVE already being fixed | Django has SEC-1 In Progress |

The agent then **recommends 5 actions**:

1. Create Jira ticket SEC-8 for requests CVE
2. Create Jira ticket SEC-9 for pillow CVE (flagged urgent — active exploitation)
3. Draft GitHub PR to upgrade pillow from 9.0.0 → 10.3.0
4. Annotate Grafana timeline with "CVE remediation initiated"
5. Generate security posture report for team review

The engineer clicks **Approve All** — the agent executes each action sequentially with real API calls. Done in 30 seconds instead of 30 minutes.

---

## 5. Functional Requirements

### FR-1: Coral Source Integration (DETECT foundation)

| ID | Requirement | Source | Priority | Phase |
|---|---|---|---|---|
| FR-1.1 | Connect to GitHub and query PRs, commits, workflow runs | github (bundled) | P0 | 0 ✅ |
| FR-1.2 | Connect to Jira Cloud and query issues filtered by security labels | jira (bundled) | P0 | 0 ✅ |
| FR-1.3 | Connect to Sentry and query error events filtered by severity and time | sentry (bundled) | P0 | 0 ✅ |
| FR-1.4 | Connect to Grafana Cloud and query alert rules and annotations | grafana (bundled) | P1 | 0 ✅ |
| FR-1.5 | Build and register custom OSV source spec for vulnerability data | osv (custom) | P0 | 0 ✅ |

### FR-2: Core SQL Queries (DETECT)

| ID | Requirement | Coral Feature Used | Priority | Phase |
|---|---|---|---|---|
| FR-2.1 | Correlate vulnerabilities (OSV) with merged PRs (GitHub) and security tickets (Jira) | Cross-source JOIN | P0 | 0 ✅ |
| FR-2.2 | Detect "active exploitation": known CVE + error spike (Sentry) in same time window | Temporal JOIN | P0 | 1 |
| FR-2.3 | Find untracked vulnerabilities: CVEs with no corresponding Jira ticket | LEFT JOIN + NULL check | P0 | 1 |
| FR-2.4 | Build unified incident timeline from all sources for a time window | UNION ALL + ORDER BY | P1 | 0 ✅ |
| FR-2.5 | Aggregate posture: CRITICAL/HIGH/MED/LOW counts + untracked CVE count | Aggregation | P0 | 1 |

### FR-3: Recommendation Engine (RECOMMEND)

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR-3.1 | Analyze scan + correlate results to identify remediation gaps | P0 | 2 |
| FR-3.2 | Generate structured action recommendations (typed, with severity, CVE link) | P0 | 2 |
| FR-3.3 | Flag urgent actions when active exploitation pattern detected | P0 | 2 |
| FR-3.4 | Include human-readable rationale per recommended action | P0 | 2 |
| FR-3.5 | Support rule-based recommendations as LLM fallback (no API key required for demo) | P1 | 2 |
| FR-3.6 | Natural language queries that return detection + recommended actions | P0 | 2 |

**Action types the recommender must produce:**

| Type | Trigger | Output |
|---|---|---|
| `create_jira` | Untracked HIGH/CRITICAL CVE | Jira issue with severity, labels, CVE references |
| `create_pr` | CVE with known fixed version in OSV | PR updating `requirements.txt` |
| `create_github_issue` | CVE needing visibility but no auto-fix | GitHub issue flagging vulnerable dependency |
| `annotate_grafana` | Remediation workflow started | Timeline annotation |
| `generate_report` | End of review session | Local Markdown security report |

### FR-4: Action Executor (ACT — human-in-the-loop)

| ID | Requirement | API | Priority | Phase |
|---|---|---|---|---|
| FR-4.1 | Create Jira ticket | `POST /rest/api/3/issue` | P0 | 3 |
| FR-4.2 | Open GitHub issue | GitHub REST API | P1 | 3 |
| FR-4.3 | Draft GitHub PR (update requirements.txt) | GitHub REST API | P0 | 3 |
| FR-4.4 | Annotate Grafana timeline | Grafana Annotations API | P1 | 3 |
| FR-4.5 | Generate Markdown security report | Local file export | P0 | 3 |
| FR-4.6 | All write actions require explicit user approval before execution | — | P0 | 3 |
| FR-4.7 | Return execution result (ticket key, PR URL, annotation ID) per action | — | P0 | 3 |
| FR-4.8 | Support approve-one, approve-all, and dismiss per action | — | P0 | 3 |
| FR-4.9 | Never execute writes without approval — no auto-act | — | P0 | 3 |

**Credentials:** Same env vars as Coral source setup (`JIRA_*`, `GITHUB_*`, `GRAFANA_*`). Tokens stored in `.env`, never committed.

### FR-5: CLI Interface

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR-5.1 | `devsecops-coral scan` — security posture check | P0 | 0 ✅ |
| FR-5.2 | `devsecops-coral correlate` — vulnerability ↔ error correlation | P0 | 0 ✅ |
| FR-5.3 | `devsecops-coral timeline --since 24h` — unified event timeline | P1 | 0 ✅ |
| FR-5.4 | `devsecops-coral ask "..."` — natural language agent query | P0 | 2 |
| FR-5.5 | `devsecops-coral recommend` — show pending recommended actions | P0 | 2 |
| FR-5.6 | `devsecops-coral act --approve <id>` / `--approve-all` — execute approved actions | P0 | 3 |
| FR-5.7 | Rich terminal output with severity coloring | P0 | 0 ✅ |
| FR-5.8 | `devsecops-coral serve` — launch dashboard web server | P0 | 0 ✅ |

### FR-6: Web Dashboard (React)

**Design rule:** Adopt **features and layout** from `ui-prototype.jsx`; keep **existing CoralSentinel styling** (`theme/tokens.js`, `ui/Primitives.jsx`, sidebar shell, dark/light theme). Do **not** replace the design system with the prototype's zinc palette or simplified single-column layout.

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR-6.1 | Three-tab navigation: **Detect** · **Actions** · **Timeline** (replaces Scan / Correlate / Timeline) | P0 | 4 |
| FR-6.2 | Detect tab: CommandBar filters, scan table, correlation view, SQL viewer, query console | P0 | 4 |
| FR-6.3 | Actions tab: `ActionsPanel` with Approve / Dismiss / Approve All | P0 | 4 |
| FR-6.4 | Timeline tab: chronological events from all sources | P1 | 0 ✅ |
| FR-6.5 | Source Status sidebar — 5 connected sources, connect/test/remove (keep current) | P0 | 0 ✅ |
| FR-6.6 | Posture Overview — CRITICAL/HIGH/MED/LOW + untracked count (always visible above tabs) | P0 | 1 |
| FR-6.7 | SQL Viewer — Detect tab: Coral JOIN SQL; Actions tab: DETECT SQL + ACT API comment block | P0 | 4 |
| FR-6.8 | Query Console — NL + raw SQL toggle; analysis block + "Switch to Actions tab" link | P0 | 2 |
| FR-6.9 | Footer tagline: "coral reads → agent analyzes → human approves → agent acts" | P0 | 4 |
| FR-6.10 | Action cards: type badge (JIRA / GITHUB PR / GRAFANA / REPORT), severity, status | P0 | 4 |
| FR-6.11 | Live execution feedback: pending → executing → done / dismissed | P0 | 4 |
| FR-6.12 | Keep DashboardHeader, theme toggle, CommandBar, ActionButton primitives | P0 | 0 ✅ |
| FR-6.13 | Approve button uses `ActionButton tone="accent"`; Dismiss uses default ghost style | P0 | 4 |
| FR-6.14 | "Approve All (N)" in ActionsPanel header; "N completed" pill when done | P0 | 4 |
| FR-6.15 | SqlViewer + QueryConsole hidden on Timeline tab; shown on Detect; SqlViewer only on Actions | P0 | 4 |

### FR-7: FastAPI Backend

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR-7.1 | `GET /api/scan` — scan results + SQL | P0 | 0 ✅ |
| FR-7.2 | `GET /api/correlate` — correlation data + SQL | P0 | 0 ✅ |
| FR-7.3 | `GET /api/timeline` — timeline events + SQL | P1 | 0 ✅ |
| FR-7.4 | `GET /api/posture` — severity counts + untracked count | P0 | 1 |
| FR-7.5 | `GET /api/sources` — connected source status | P0 | 0 ✅ |
| FR-7.6 | `POST /api/ask` — agent query → SQL + analysis + recommendations | P0 | 2 |
| FR-7.7 | `GET /api/actions` — list recommended actions with status | P0 | 3 |
| FR-7.8 | `POST /api/actions/{id}/approve` — approve and execute one action | P0 | 3 |
| FR-7.9 | `POST /api/actions/approve-all` — approve and execute all pending | P0 | 3 |
| FR-7.10 | `POST /api/actions/{id}/dismiss` — dismiss without executing | P0 | 3 |
| FR-7.11 | `POST /api/recommend` — regenerate recommendations from current detection state | P0 | 2 |
| FR-7.12 | All read endpoints return generated Coral SQL in response body | P0 | 0 ✅ |

### FR-8: Output Formats

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR-8.1 | Rich terminal tables with color-coded severity | P0 | 0 ✅ |
| FR-8.2 | JSON output (`--format json`) | P1 | 0 ✅ |
| FR-8.3 | Markdown report export (via `generate_report` action) | P0 | 3 |

### FR-9: Code Quality — Docstrings, Linting & Formatting

All Python code in `src/devsecops_coral/` and `tests/` must meet these standards. **Every phase commit** must pass `ruff check` and `ruff format --check` before merge.

| ID | Requirement | Tool / Standard | Priority | Phase |
|---|---|---|---|---|
| FR-9.1 | Docstrings on all **public** modules, classes, and functions | Google-style docstrings | P0 | 1+ |
| FR-9.2 | Docstrings on Pydantic models — class docstring + field descriptions where non-obvious | `models.py`, action/recommend types | P0 | 2+ |
| FR-9.3 | Docstrings on FastAPI route handlers — summary of behavior, params, and return shape | `api.py` | P0 | 1+ |
| FR-9.4 | Docstrings on SQL query builders — describe query purpose and parameters | `queries/*.py` | P0 | 1+ |
| FR-9.5 | Lint with **ruff** — no errors on touched files | `ruff check src/ tests/` | P0 | 1+ |
| FR-9.6 | Format with **ruff** — consistent style across codebase | `ruff format src/ tests/` | P0 | 1+ |
| FR-9.7 | Import sorting via ruff (`I` rules) | isort-compatible | P0 | 1+ |
| FR-9.8 | Type hints on all function signatures (existing rule, enforced by review + ruff where applicable) | PEP 484 | P0 | 0 ✅ |
| FR-9.9 | Backfill docstrings on existing modules when editing them in a phase | Boy Scout rule | P1 | 1–5 |
| FR-9.10 | Full codebase passes `ruff check` with docstring rules before submission | `D` pydocstyle rules | P0 | 5 |

**Docstring standard (Google convention):**

```python
def build_scan_query(ecosystem: str, packages: list[str]) -> str:
    """Build a parameterized Coral SQL scan query.

    Args:
        ecosystem: Package ecosystem (e.g. ``PyPI``).
        packages: Affected package names to include in the query.

    Returns:
        Parameterized SQL string ready for Coral execution.

    Raises:
        ValueError: If ecosystem is not alphabetic or packages list is empty.
    """
```

**Required on:** `def`, `class`, and module-level docstrings for every file under `src/devsecops_coral/`.  
**Optional on:** private helpers (`_prefixed`), test functions (one-line summary is enough), and `__init__.py` re-exports.

**Ruff commands (run before each phase commit):**

```bash
pip install -e ".[dev]"

# Lint — must exit 0
ruff check src/ tests/

# Format — apply fixes
ruff format src/ tests/

# Verify formatting in CI / pre-commit (no writes)
ruff format --check src/ tests/
```

**Configuration:** `pyproject.toml` → `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.format]`, `[tool.ruff.lint.pydocstyle]`.

**Phase gate:** No phase is complete until new/changed Python files in that phase have docstrings and pass ruff lint + format.

---

## 6. Implementation Phases

Phases are designed for **incremental commits**. Each phase is independently demoable and builds on the previous one.

**Cross-cutting (every phase):** New or modified Python files must include docstrings (FR-9) and pass `ruff check` + `ruff format --check` before the phase commit.

### Phase 0 — Foundation (COMPLETE ✅)

**Goal:** Coral reads 5 sources; dashboard displays detection data.

**Deliverables:**
- OSV custom source spec (linted, registered)
- GitHub, Jira, Sentry, Grafana connected via Coral
- Core queries: scan, correlate, timeline, posture
- FastAPI backend with read endpoints
- React dashboard: scan table, correlation view, timeline, query console, SQL viewer
- CLI: `scan`, `correlate`, `timeline`, `serve`
- Demo FastAPI app + seed scripts

**Commit message pattern:** `feat: coral read layer — scan, correlate, timeline dashboard`

**Status:** Built. This is the current codebase — a capable **data viewer**, not yet an agent.

---

### Phase 1 — DETECT Hardening

**Goal:** Detection queries reliably surface the demo story (untracked CVEs, active exploitation, tracked fixes).

**Backend:**
- [ ] Refine `queries/scan.py` — untracked CVE detection via LEFT JOIN on Jira (NULL ticket)
- [ ] Refine `queries/correlate.py` — temporal window for Sentry error spikes
- [ ] Add `queries/untracked.py` or extend scan with explicit untracked filter
- [ ] Posture endpoint returns `untracked_count` alongside severity buckets
- [ ] Demo seed data aligned to prototype: django (SEC-1 In Progress), requests + pillow (untracked), pillow (12 errors)

**Frontend:**
- [ ] Posture card shows untracked count with orange highlight when > 0
- [ ] Scan table highlights UNTRACKED rows; error column bold when > 10

**Demo scenarios:**
- [ ] `demo/scenarios/untracked_cves.md` — requests + pillow untracked
- [ ] `demo/scenarios/active_exploitation.md` — pillow + 12 Sentry errors

**Acceptance criteria:**
```bash
devsecops-coral scan --ecosystem PyPI --packages django,requests,pillow,celery
# Shows: django → SEC-1 In Progress; requests, pillow → UNTRACKED; pillow → 12 errors

ruff check src/ tests/ && ruff format --check src/ tests/
# Must pass on all touched files
```

**Code quality:**
- [ ] Docstrings on modified query builders and API handlers touched in this phase
- [ ] `ruff check` + `ruff format` clean on changed files

**Commit message:** `feat(detect): untracked CVE queries and posture untracked count`

**Estimated effort:** 3–4 hours

---

### Phase 2 — RECOMMEND (Agent Analysis Layer)

**Goal:** Agent analyzes detection results and produces structured, typed action recommendations.

**Backend:**
- [ ] New module: `src/devsecops_coral/recommender.py`
  - Input: scan + correlate + posture results
  - Output: list of `RecommendedAction` objects (Pydantic model)
  - Rule-based engine first (deterministic, demo-safe):
    - Untracked HIGH/CRITICAL → `create_jira`
    - Untracked + active exploitation → `create_jira` (urgent flag)
    - CVE with `fixed_version` in OSV → `create_pr`
    - Any remediation started → `annotate_grafana`
    - Always → `generate_report`
  - LLM enhancement: Claude analyzes gaps and enriches rationale text
- [ ] Extend `agent.py` — NL queries return detection + recommendations
- [ ] `GET /api/recommend` — regenerate from current state
- [ ] Extend `POST /api/ask` — response includes `recommendations[]`
- [ ] Pydantic models: `RecommendedAction`, `ActionType`, `ActionStatus` (pending only at this phase)

**CLI:**
- [ ] `devsecops-coral recommend` — print recommended actions table

**Frontend:**
- [ ] Query console shows "Agent Analysis + Recommended Actions" block (prototype pattern)
- [ ] Link text: "Switch to Actions tab to review and approve"

**Acceptance criteria:**
```bash
devsecops-coral recommend
# Lists 5 pending actions matching prototype ACTIONS_DATA

ruff check src/devsecops_coral/recommender.py src/devsecops_coral/agent.py
# Zero errors; new modules have Google docstrings
```

**Commit message:** `feat(recommend): agent recommendation engine from detection results`

**Estimated effort:** 4–5 hours

---

### Phase 3 — ACT (Action Executor with Approval)

**Goal:** Approved actions execute via direct REST APIs. Human-in-the-loop is mandatory.

**Backend:**
- [ ] New module: `src/devsecops_coral/actions/` (keep files under 200 lines each)
  - `jira.py` — `create_issue(summary, description, priority, labels)` → ticket key
  - `github.py` — `create_pull_request(branch, title, body, file_changes)` → PR URL
  - `github.py` — `create_issue(title, body, labels)` → issue URL (P1)
  - `grafana.py` — `create_annotation(text, tags, time)` → annotation ID
  - `report.py` — `generate_markdown(findings)` → file path
  - `executor.py` — orchestrates approve/dismiss/approve-all; updates action status
- [ ] In-memory action store (session-scoped; no DB needed for hackathon)
- [ ] Config: `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY`
- [ ] Config: `GITHUB_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO`
- [ ] Config: `GRAFANA_URL`, `GRAFANA_API_KEY`, `GRAFANA_DASHBOARD_UID`
- [ ] API endpoints: approve, approve-all, dismiss (FR-7.7–7.10)
- [ ] Return execution results: `{ "ticket": "SEC-9", "url": "..." }`

**CLI:**
- [ ] `devsecops-coral act --approve 2`
- [ ] `devsecops-coral act --approve-all`
- [ ] `devsecops-coral act --list`

**Tests:**
- [ ] Mock httpx at action module level (not HTTP layer)
- [ ] Test each action type with fixture responses
- [ ] Test approval gate — unapproved actions never execute

**Acceptance criteria:**
```bash
devsecops-coral recommend
devsecops-coral act --approve 2
# Output: ✓ Created Jira SEC-9 for GHSA-ppf2-m228 (pillow)

ruff check src/devsecops_coral/actions/
# All action modules documented and lint-clean
```

**Commit message:** `feat(act): human-approved action executor — Jira, GitHub PR, Grafana, report`

**Estimated effort:** 6–8 hours

---

### Phase 4 — Dashboard Agent UX

**Goal:** Port prototype **features** into the existing CoralSentinel shell — not a visual redesign.

**Styling (unchanged):**
- `theme/tokens.js` — orange accent, SEV colors, sidebar width, frosted header
- `ui/Primitives.jsx` — `Card`, `CardHeader`, `ActionButton`, `Badge`, `Pill`
- Sidebar + `DashboardHeader` + dark/light theme toggle
- `CommandBar` for ecosystem / packages / since filters

**Layout changes (from prototype):**

| Area | Current | Target |
|---|---|---|
| Tabs | Scan · Correlate · Timeline | **Detect** · **Actions** · **Timeline** |
| Detect tab content | ScanTable only | ScanTable + CorrelationView (stacked) |
| Actions tab | — | **ActionsPanel** (new) + SqlViewer |
| Timeline tab | Timeline + SqlViewer + QueryConsole always visible | Timeline only |
| SqlViewer / QueryConsole | Always at bottom | Detect: both; Actions: SqlViewer only; Timeline: neither |
| Footer | Sidebar "hackathon · 2026" only | Main footer with agent tagline |

**New component: `ActionsPanel.jsx`** (prototype behavior, production styling):
- [ ] Card with accent glow when pending actions exist (reuse `Card accent={T.accent}`)
- [ ] Header: "Recommended Actions" + `{doneCount} completed` Pill + **Approve All (N)** `ActionButton`
- [ ] Action row per recommendation:
  - Type icon + `Pill` badge: JIRA · GITHUB PR · GRAFANA · REPORT
  - `Badge` for severity (skip for INFO actions)
  - Title (13px semibold) + detail text (12px secondary)
  - Status line: `⟳ Executing...` (accent mono) or `✓ Executed` (green)
  - Pending only: **Approve** (`ActionButton tone="accent"`) + **Dismiss** (ghost)
- [ ] Row background shifts by status: pending → executing (accent tint) → done (green tint) → dismissed (40% opacity)
- [ ] Wire to `/api/actions`, `/api/recommend`, approve / approve-all / dismiss

**Detect tab refinements:**
- [ ] Keep `PostureOverview` + `CommandBar` above tab content (always visible)
- [ ] Stack `ScanTable` then `CorrelationView` (replaces separate Correlate tab)
- [ ] Bottom grid: `SqlViewer` | `QueryConsole` (2-column, existing gap/spacing)

**QueryConsole extension (Phase 2 backend, Phase 4 UI):**
- [ ] When `result.analysis` or `result.recommendations` present, show green-bordered block:
  - Label: "Agent Analysis + Recommended Actions"
  - Body: analysis text
  - Link/button: "Review in Actions tab →" (switches tab)

**SqlViewer on Actions tab:**
- [ ] Show last DETECT SQL + commented ACT block (from prototype `SQL_EXAMPLES.act` pattern):
  ```
  -- The agent then ACTS via direct API calls:
  -- 1. POST /rest/api/3/issue → Create Jira SEC-8
  -- ...
  -- All actions require human approval first.
  ```

**App.jsx changes:**
- [ ] Update `TABS` constant: `{ id: "detect", label: "Detect", desc: "Scan & Correlate" }`, etc.
- [ ] Tab bar keeps current sticky header styling (bottom border accent, mono icon)
- [ ] Add main-area footer below `<main>` with tagline in `T.mono` 11px
- [ ] `useApi.js`: `getActions`, `getRecommend`, `approveAction`, `approveAllActions`, `dismissAction`

**Acceptance criteria:**
- Visual regression: dashboard still looks like CoralSentinel (sidebar, header, tokens)
- Click Actions tab → 5 pending recommendations with Approve / Dismiss
- Click Approve on pillow Jira → "Executing..." → "✓ Executed"
- Approve All cascades with staggered completion (prototype timing OK for demo)
- Footer: `coral reads → agent analyzes → human approves → agent acts`

**Commit message:** `feat(ui): Actions tab with approve/dismiss — agent workflow dashboard`

**Estimated effort:** 5–6 hours

---

### Phase 5 — Demo Polish & Submission

**Goal:** 3-minute demo script, docs, video, blog — submission-ready.

**Deliverables:**
- [ ] End-to-end demo script (see Section 10)
- [ ] `docs/TESTING.md` — add action approval test steps + ruff commands
- [ ] `SHOWCASE.md` — update narrative for agent workflow
- [ ] README — lead with DETECT → RECOMMEND → ACT, not "dashboard"
- [ ] **Backfill docstrings** on all remaining `src/devsecops_coral/` modules
- [ ] **Full ruff pass:** `ruff check src/ tests/` and `ruff format src/ tests/`
- [ ] Record 3–5 minute demo video
- [ ] Medium blog post
- [ ] Discord showcase + social posts
- [ ] OSV source spec submitted to Coral repo (bounty)

**Acceptance criteria:** Full demo runs in under 3 minutes without manual API calls.

**Commit message:** `docs: demo script and submission materials for agent workflow`

**Estimated effort:** 4–5 hours

---

### Phase Summary

| Phase | Name | Key Deliverable | Demoable As |
|---|---|---|---|
| **0** ✅ | Foundation | Coral reads + dashboard | "Here's what Coral found" |
| **1** | DETECT Hardening | Untracked CVEs + active exploitation queries | "2 untracked, 1 active exploitation" |
| **2** | RECOMMEND | Agent recommendation engine | "Agent recommends 5 actions" |
| **3** | ACT | Approved API execution | "SEC-9 created in Jira" |
| **4** | Dashboard UX | Actions tab + approve flow | Full agent workflow in UI |
| **5** | Demo Polish | Video, blog, submission | 3-minute judge demo |

**Total estimated effort (Phases 1–5):** ~22–28 hours

---

## 7. Technical Architecture

### Read vs Write Paths

```
┌─────────────────────────────────────────────────────────────────┐
│                     React Dashboard                              │
│   Detect Tab          Actions Tab           Timeline Tab         │
│   scan + correlate    approve/dismiss       events only          │
└────────────┬──────────────────┬──────────────────────────────────┘
             │ REST              │ REST
┌────────────▼──────────────────▼──────────────────────────────────┐
│                     FastAPI Backend                               │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │ Query Engine │  │ Recommender  │  │ Action Executor       │ │
│  │ (read only)  │  │ (LLM + rules)│  │ (write, after approve)│ │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────┘ │
│         │                 │                       │              │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌───────────▼───────────┐ │
│  │ coral_client │  │ agent.py     │  │ actions/              │ │
│  │ .py          │  │              │  │ jira · github · grafana│ │
│  └──────┬───────┘  └──────────────┘  └───────────┬───────────┘ │
└─────────┼─────────────────────────────────────────┼────────────┘
          │ Coral MCP / CLI                           │ httpx REST
          ▼                                           ▼
┌─────────────────────┐              ┌────────────────────────────┐
│   Coral Runtime     │              │  Direct Source APIs        │
│   (READ ONLY)       │              │  (WRITE after approval)    │
│  OSV · GitHub ·     │              │  Jira REST · GitHub REST · │
│  Jira · Sentry ·    │              │  Grafana Annotations API   │
│  Grafana            │              └────────────────────────────┘
└─────────────────────┘
```

### Updated Project Structure (Phases 2–3 additions)

```
src/devsecops_coral/
├── api.py                    # + /api/actions, /api/recommend endpoints
├── models.py                 # + RecommendedAction, ActionResult models
├── agent.py                  # Extended: NL → detect + recommend
├── recommender.py            # NEW Phase 2: detection → action list
├── coral_client.py           # READ ONLY — unchanged rule
├── actions/                  # NEW Phase 3
│   ├── __init__.py
│   ├── executor.py           # Approve/dismiss orchestration
│   ├── jira.py               # POST /rest/api/3/issue
│   ├── github.py             # PR + issue creation
│   ├── grafana.py            # Annotation API
│   └── report.py             # Local Markdown export
├── queries/
│   ├── scan.py
│   ├── correlate.py
│   ├── timeline.py
│   └── posture.py
└── config.py                 # + JIRA_*, GITHUB_*, GRAFANA_* write creds

frontend/src/components/
├── ActionsPanel.jsx          # NEW Phase 4 — from ui-prototype.jsx
├── ScanTable.jsx
├── PostureOverview.jsx
├── Timeline.jsx
├── QueryConsole.jsx
├── SqlViewer.jsx
└── SourceStatus.jsx
```

### Action Data Model

```python
class ActionType(str, Enum):
    CREATE_JIRA = "create_jira"
    CREATE_PR = "create_pr"
    CREATE_GITHUB_ISSUE = "create_github_issue"
    ANNOTATE_GRAFANA = "annotate_grafana"
    GENERATE_REPORT = "generate_report"

class ActionStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    DONE = "done"
    DISMISSED = "dismissed"
    FAILED = "failed"

class RecommendedAction(BaseModel):
    id: int
    type: ActionType
    status: ActionStatus
    title: str
    detail: str
    cve: str | None
    package: str | None
    severity: str
    urgent: bool = False
    result: dict | None = None  # Populated after execution
```

### Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Frontend** | React + Vite (inline styles) | CoralSentinel tokens + prototype workflow features |
| **Backend API** | FastAPI | Shared query + recommend + act engine |
| **CLI** | Typer + Rich | Power-user approve/act from terminal |
| **LLM Agent** | Anthropic Claude API | NL → SQL + recommendation rationale |
| **Coral Integration** | MCP (primary) / CLI subprocess (fallback) | Cross-source READ |
| **Write APIs** | httpx | Jira, GitHub, Grafana WRITE (after approval) |
| **Testing** | pytest + httpx mock | Mock at coral_client and actions module level |

### Coral Features Showcased

| Coral Feature | Where Demonstrated |
|---|---|
| **SQL Interface** | Every DETECT query |
| **Cross-source JOINs** | Scan + correlate (5 sources) |
| **Schema Learning** | Source status panel |
| **Caching** | Repeat queries return instantly |
| **MCP Integration** | Agent + dashboard MCP status |
| **Custom Source Spec** | OSV bounty submission |

| Agent Feature | Where Demonstrated |
|---|---|
| **Reasoning** | Recommender analyzes gaps |
| **Human-in-the-loop** | Approve / Dismiss / Approve All |
| **Multi-step workflow** | Detect → Recommend → Act |
| **Transparency** | SQL viewer + action API summary |

---

## 8. OSV Custom Source Spec

*(Unchanged from v2.0 — see `sources/osv/osv.yaml`)*

Build a Coral source spec exposing OSV as SQL tables. Required for DETECT phase. Submitted separately for Coral bounty.

Key tables/functions:
- `osv.search_vulnerabilities(package => '...', ecosystem => 'PyPI')` — search function
- `osv.vulnerability_detail` — detail lookup by ID

---

## 9. Data Seeding Plan

All data is real, from individual free-tier accounts. Seeding must support the **demo story**:

| Package | CVE Severity | Jira Ticket | Sentry Errors | Demo Role |
|---|---|---|---|---|
| django | CRITICAL | SEC-1 (In Progress) | 47 | Already being fixed |
| requests | HIGH | — (untracked) | 3 | Untracked CVE |
| pillow | HIGH | — (untracked) | 12 | Active exploitation |
| celery | MEDIUM | SEC-4 (Open) | 0 | Tracked, lower priority |
| jinja2 | MEDIUM | SEC-5 (Done) | 0 | Resolved |

### GitHub

1. Public repo `devsecops-demo` with intentionally vulnerable `requirements.txt` (`pillow==9.0.0`)
2. Dependabot alerts enabled
3. Manual PRs simulating dependency upgrades
4. GitHub Actions CI workflow

### Sentry

1. Free project "devsecops-demo"
2. FastAPI demo app generates real errors (pillow-related endpoints for exploitation scenario)
3. Seed script: `scripts/seed_sentry_errors.ps1`

### Jira Cloud

1. Project "SEC" with tickets SEC-1 through SEC-5 (see table above)
2. **Do not** pre-create tickets for requests or pillow — agent will create SEC-8, SEC-9 on approval

### Grafana Cloud

1. Alert rules + deployment annotations
2. Dashboard UID in config for annotation API

### OSV

No seeding — real vulnerability data from public API.

---

## 10. Demo Script (3 Minutes for Judges)

```
[0:00] Open dashboard → Detect tab
       "Here's what the agent found this morning"
       → Show posture: 1 CRITICAL, 2 HIGH, 2 untracked
       → Show scan table: pillow with 12 errors, no ticket

[0:45] Switch to Actions tab
       "The agent recommends 5 actions based on the correlation"
       → Show pending actions: Jira tickets, GitHub PR, Grafana annotation, report

[1:15] Click Approve on pillow Jira ticket
       → Watch status: Executing... → ✓ Executed
       → "SEC-9 created in Jira"

[1:45] Click Approve on GitHub PR
       → "PR #45 opened: upgrade pillow to 10.3.0"

[2:00] Click Approve All for remaining actions
       → Watch cascade: Grafana annotation → report generated

[2:30] Show SQL on Actions tab
       "Here's what Coral did under the hood — one SQL query joining 5 sources"
       → Point to DETECT SQL + ACT API comments

[2:45] Query console: "Are there any other untracked vulnerabilities?"
       → Agent generates SQL, responds with analysis + recommendations

[3:00] Footer: "coral reads → agent analyzes → human approves → agent acts"
```

### CLI Demo (backup if UI fails)

```bash
devsecops-coral scan --ecosystem PyPI --packages django,requests,pillow
devsecops-coral correlate --since 7d
devsecops-coral recommend
devsecops-coral act --approve 2
devsecops-coral act --approve-all
```

---

## 11. Success Criteria

### Hackathon Submission Checklist

| # | Deliverable | Acceptance Criteria | Phase |
|---|---|---|---|
| 1 | **Agent workflow** | DETECT → RECOMMEND → ACT with human approval | 2–4 |
| 2 | Working dashboard | Three tabs: Detect, Actions, Timeline | 4 |
| 3 | Action execution | At least 3 real write actions (Jira, GitHub PR, report) | 3 |
| 4 | Human-in-the-loop | No write without explicit Approve click | 3 |
| 5 | 5 Coral sources | GitHub, Jira, Sentry, Grafana + OSV | 0 ✅ |
| 6 | Cross-source JOINs | 3+ queries JOIN 3+ sources | 0 ✅ |
| 7 | OSV source spec | Passes `coral source lint`, submitted to Coral repo | 0 ✅ |
| 8 | AI agent | NL → SQL + recommendations | 2 |
| 9 | SQL transparency | Detect tab shows Coral SQL; Actions tab shows API summary | 4 |
| 10 | CLI | scan, correlate, recommend, act commands | 2–3 |
| 11 | README | Lead with agent workflow, not dashboard | 5 |
| 12 | Demo video | 3-minute screen recording of full workflow | 5 |
| 13 | Blog + social | Medium post, Discord showcase, LinkedIn + X | 5 |
| 14 | **Code quality** | Full `src/` + `tests/` pass `ruff check` and `ruff format --check`; public API docstrings complete | 5 |

### Judging Criteria Mapping

| Criterion | Target | How We Achieve It |
|---|---|---|
| Potential Impact | 9/10 | Full remediation workflow, not just detection |
| Creativity & Originality | 9/10 | Only team with DETECT + ACT via Coral reads + direct writes |
| Learning & Growth | 9/10 | First Coral user; custom source; action executor |
| Technical Implementation | 9/10 | 5-source JOINs + LLM + REST write APIs + approval gate |
| Aesthetics & UX | 8/10 | CoralSentinel styling + Actions tab approve flow; severity colors |
| Best Use of Coral | 9/10 | Cross-source JOINs as read layer; SQL transparency |
| **Enterprise Agent** | **10/10** | **Complete agent loop with human-in-the-loop approval** |

---

## 12. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Jira/GitHub write API auth fails on demo | Medium | High | Test approve flow Day 1 of Phase 3; fallback to `generate_report` (local, always works) |
| GitHub PR creation requires branch permissions | Medium | Medium | Use fine-grained PAT with contents:write; test on demo repo |
| LLM unavailable during demo | Low | Medium | Rule-based recommender works without API key |
| Coral SQL doesn't support all JOIN patterns | Medium | High | Simplify queries; test Day 1 of Phase 1 |
| Action execution too slow for live demo | Low | Medium | Pre-warm connections; stagger UI animation like prototype |
| 7 days too tight for solo | Medium | High | Phases 1–3 are P0; Phase 5 polish can ship at 80% |

---

## 13. Non-Functional Requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-1 | Coral reads stay local (Coral's security model) | No read data leaves the machine |
| NFR-2 | Write actions only after explicit approval | Zero auto-execute |
| NFR-3 | Credentials in `.env` only | Never committed |
| NFR-4 | Query response time (single-source) | < 5 seconds |
| NFR-5 | Query response time (5-source JOIN) | < 15 seconds |
| NFR-6 | Action execution time (per action) | < 10 seconds |
| NFR-7 | Python 3.10+ | Match Coral requirements |
| NFR-8 | Lint cleanliness | `ruff check src/ tests/` exits 0 before submission |
| NFR-9 | Format consistency | `ruff format --check src/ tests/` exits 0 before submission |
| NFR-10 | Docstring coverage | All public modules, classes, and functions in `src/devsecops_coral/` documented |

---

## 14. Post-Hackathon Roadmap

- Slack notifications when actions complete
- Persistent action history (SQLite)
- Scheduled detect → recommend cycles
- Additional action types: Snyk ignore rules, Dependabot auto-merge
- CI/CD: `devsecops-coral scan && devsecops-coral recommend` in GitHub Actions
- SARIF export for GitHub Code Scanning integration

---

## Appendix A: UI Design Specification

Reference prototype: `ui-prototype.jsx` (shared May 2026).  
Production codebase: `frontend/src/` with CoralSentinel design system.

### A.1 Design Principle

| Adopt from prototype | Keep from current UI |
|---|---|
| 3-tab workflow: Detect → Actions → Timeline | Sidebar shell (280px), `SourceStatus` manager |
| ActionsPanel with Approve / Dismiss / Approve All | `DashboardHeader`, source chips, theme toggle |
| Action type badges, status transitions | `theme/tokens.js`, `SEV`, orange accent |
| Agent analysis block in query console | `CommandBar`, filter controls |
| Footer agent tagline | `Card`, `ActionButton`, `Badge`, `Pill` primitives |
| Tab-specific SqlViewer content | Dark + light theme via `data-theme` |
| Correlation merged into Detect tab | Existing scan/correlate/timeline components |

**Do not port:** prototype's `#09090b` zinc palette, Geist fonts, top-only source grid, or single-column max-width layout.

### A.2 Shell Layout (unchanged)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ DashboardHeader — CoralSentinel · source chips · theme toggle           │
├──────────────┬──────────────────────────────────────────────────────────┤
│ Sidebar      │ Sticky tab bar: Detect | Actions | Timeline              │
│ (fixed)      ├──────────────────────────────────────────────────────────┤
│              │ PostureOverview (always)                                 │
│ SourceStatus │ CommandBar (always)                                      │
│ connect/test ├──────────────────────────────────────────────────────────┤
│              │ [Tab content — see A.3]                                  │
│              │                                                          │
│              │ Footer tagline (Phase 4)                                 │
└──────────────┴──────────────────────────────────────────────────────────┘
```

### A.3 Tab Content Matrix

| Tab | Visible components | Hidden |
|---|---|---|
| **Detect** | ScanTable, CorrelationView, SqlViewer, QueryConsole | ActionsPanel |
| **Actions** | ActionsPanel, SqlViewer (DETECT + ACT comments) | ScanTable, CorrelationView, QueryConsole |
| **Timeline** | Timeline | SqlViewer, QueryConsole, ActionsPanel |

### A.4 Component Mapping

| Prototype | Production | Notes |
|---|---|---|
| `ScanTable` | `ScanTable.jsx` | Keep row actions (focus package, ask) |
| `Posture` | `PostureOverview.jsx` | Add untracked count (Phase 1) |
| `SourcePanel` | `SourceStatus.jsx` | Stays in sidebar, not top grid |
| `ActionsPanel` | `ActionsPanel.jsx` **new** | Use `ActionButton`, not prototype raw `<button>` |
| `Timeline` | `Timeline.jsx` | Unchanged |
| `SqlViewer` | `SqlViewer.jsx` | Context prop: `mode="detect"` \| `"actions"` |
| `QueryConsole` | `QueryConsole.jsx` | Add recommendations block |
| Tab nav | `App.jsx` sticky header | Keep bottom-border active state |
| Footer | `App.jsx` main footer | New in Phase 4 |

### A.5 ActionsPanel — Feature Spec

Each action card displays:

```
┌─────────────────────────────────────────────────────────────────────┐
│ [icon] [JIRA] [HIGH]                              [Approve] [Dismiss]│
│        Create Jira ticket for GHSA-ppf2-m228 (pillow)                │
│        HIGH severity CVE with 12 active Sentry errors…               │
└─────────────────────────────────────────────────────────────────────┘
```

| Field | Source | UI element |
|---|---|---|
| `type` | API | `Pill` — JIRA / GITHUB PR / GRAFANA / REPORT |
| `severity` | API | `Badge` (hidden when INFO) |
| `title` | API | 13px semibold |
| `detail` | API | 12px `T.textSecondary` |
| `status` | Local + API | pending / executing / done / dismissed |
| `urgent` | API | Optional red left border or "URGENT" Pill |

**Header controls:**

| Control | Style | Behavior |
|---|---|---|
| Approve All (N) | `ActionButton tone="accent"` | Calls `POST /api/actions/approve-all` |
| N completed | `Pill color={T.green}` | Shown when `doneCount > 0` |
| Approve | `ActionButton tone="accent"` | Single action execute |
| Dismiss | `ActionButton` ghost | Marks dismissed, no API write |

**Status styling (use existing tokens):**

| Status | Row background | Border |
|---|---|---|
| pending | `T.cardDim` | `T.border` |
| executing | `T.accentGlow` | `T.accentBorder` |
| done | `rgba(16,185,129,0.04)` | `rgba(16,185,129,0.15)` |
| dismissed | transparent | `T.border`, opacity 0.4 |

### A.6 QueryConsole — Recommendations Block

When agent returns analysis (prototype lines 354–358):

```
┌─ Agent Analysis + Recommended Actions ─────────────────────────────┐
│ Found 2 untracked HIGH-severity CVEs… Recommended: create Jira     │
│ tickets, draft PR, annotate Grafana.                               │
│ [ Review in Actions tab → ]                                        │
└────────────────────────────────────────────────────────────────────┘
```

- Green-tinted block (`rgba(16,185,129,0.04)` border) — matches existing success patterns
- "Review in Actions tab →" switches `tab` to `"actions"` via callback prop

### A.7 SqlViewer — Actions Tab Content

Second panel below ActionsPanel. Content = last DETECT SQL + static ACT comment block:

```sql
-- DETECT: (last executed Coral query)

-- ACT: The agent executes via direct API calls after approval:
-- POST /rest/api/3/issue        → Jira ticket
-- POST /repos/.../pulls         → GitHub PR
-- POST /api/annotations         → Grafana mark
-- Local file write              → Markdown report
```

Copy button and syntax styling unchanged from current `SqlViewer.jsx`.

## Appendix B: Action API Details

| Action | Method | Endpoint | Payload Summary |
|---|---|---|---|
| Create Jira ticket | POST | `/rest/api/3/issue` | `{ fields: { project, summary, issuetype, priority, labels, description } }` |
| Create GitHub PR | POST | `/repos/{owner}/{repo}/pulls` | `{ title, head, base, body }` (+ prior branch commit updating requirements.txt) |
| Create GitHub issue | POST | `/repos/{owner}/{repo}/issues` | `{ title, body, labels }` |
| Grafana annotation | POST | `/api/annotations` | `{ dashboardUID, time, text, tags }` |
| Generate report | Local | — | Write Markdown to `./reports/posture-{date}.md` |
