# Product Requirements Document (PRD)
# devsecops-coral — Cross-Stack Security Correlation Agent

**Version:** 1.0  
**Author:** Sumit Chawla (@sumit_sd)  
**Date:** May 16, 2026  
**Hackathon:** Pirates of the Coral-bean (WeMakeDevs × Coral)  
**Track:** Track 1 — Enterprise Agent  
**Duration:** May 25–31, 2026 (7 days)  
**Team Size:** Solo  

---

## 1. Problem Statement

Security and DevOps teams operate across fragmented tooling. When a vulnerability is discovered or an incident occurs, the first critical question — *"What else is happening across our stack?"* — requires manual cross-referencing across 4-6 different platforms:

- **Vulnerability databases** (OSV, NVD) report known CVEs
- **Source control** (GitHub) tracks code changes and dependency updates
- **Error monitoring** (Sentry) captures application-level failures
- **Issue trackers** (Jira) manage security tickets and triage status
- **Observability platforms** (Grafana) surface infrastructure anomalies

Today, a senior security engineer spends 20-30 minutes per incident manually correlating these signals. Junior engineers frequently miss cross-platform connections entirely. There is no single query language or interface that spans all of these sources.

### Who Feels This Pain

- **Security Engineers / Analysts** — Need to correlate vulnerability reports with codebase impact
- **DevOps / SRE Teams** — Need to assess whether a deploy introduced security regressions
- **Engineering Leads** — Need security posture visibility across projects
- **Compliance Teams** — Need audit trails connecting CVEs to remediation tickets

### Current Workarounds

1. Manual tab-switching across 4-6 dashboards
2. Custom Python scripts with per-vendor API integrations (brittle, unmaintained)
3. Expensive SOAR/SIEM platforms (Splunk, Datadog Security) — overkill for most teams
4. Spreadsheet-based tracking (common in smaller teams)

---

## 2. Proposed Solution

**devsecops-coral** is an AI-powered security correlation agent that uses Coral's SQL interface to query across vulnerability intelligence (OSV), source control (GitHub), error monitoring (Sentry), issue tracking (Jira), and observability (Grafana) — in a single SQL query, executed locally.

### Core Value Proposition

> Replace 30 minutes of manual cross-referencing with one SQL query that correlates security signals across your entire DevSecOps stack.

### How Coral Enables This

Without Coral, building this requires:
- 5 separate API integrations with auth, pagination, rate limiting
- Custom join logic in Python to correlate data across sources
- Token-heavy LLM tool calls (one per source)
- Brittle glue code that breaks when APIs change

With Coral:
- One SQL query JOINs all 5 sources
- Auth, pagination, rate limiting handled by Coral
- Data resolves inside Coral, not inside the LLM's context window
- SQL is inspectable, debuggable, and cacheable

---

## 3. Target Users

### Primary: Security-Aware Engineering Teams (5-50 engineers)

Teams that are too small for a dedicated SOC but too mature to ignore security. They use GitHub, Jira, Sentry, and possibly Grafana. They track CVEs but don't have automated correlation.

### Secondary: Developer Security Champions

Individual developers designated as security leads within their team. They need a quick way to check "are we exposed?" without deep security tooling expertise.

---

## 4. Functional Requirements

### FR-1: Coral Source Integration

| ID | Requirement | Source | Priority |
|---|---|---|---|
| FR-1.1 | Connect to GitHub and query PRs, commits, workflow runs, and Dependabot alerts | github (bundled) | P0 |
| FR-1.2 | Connect to Jira Cloud and query issues filtered by security labels | jira (bundled) | P0 |
| FR-1.3 | Connect to Sentry and query error events filtered by severity and time | sentry (bundled) | P0 |
| FR-1.4 | Connect to Grafana Cloud and query alert rules and annotations | grafana (bundled) | P1 |
| FR-1.5 | Build and register a custom OSV source spec for vulnerability data | osv (custom) | P0 |

### FR-2: Core SQL Queries

| ID | Requirement | Coral Feature Used | Priority |
|---|---|---|---|
| FR-2.1 | Correlate vulnerabilities (OSV) with merged PRs (GitHub) and security tickets (Jira) | Cross-source JOIN | P0 |
| FR-2.2 | Detect "active exploitation" pattern: known CVE + error spike (Sentry) in same time window | Temporal JOIN | P0 |
| FR-2.3 | Find untracked vulnerabilities: CVEs with no corresponding Jira ticket | LEFT JOIN with NULL check | P0 |
| FR-2.4 | Build unified incident timeline from all sources for a time window | UNION ALL + ORDER BY | P1 |
| FR-2.5 | Identify risky deploys: merged PRs that coincide with new threats or error spikes | Multi-source temporal JOIN | P1 |

### FR-3: AI Agent Layer

| ID | Requirement | Priority |
|---|---|---|
| FR-3.1 | Accept natural language security queries via CLI | P0 |
| FR-3.2 | Translate natural language to parameterized Coral SQL | P0 |
| FR-3.3 | Execute SQL via Coral MCP and parse results | P0 |
| FR-3.4 | Generate human-readable security analysis from query results | P0 |
| FR-3.5 | Support follow-up questions with context from previous queries | P2 |

### FR-4: CLI Interface

| ID | Requirement | Priority |
|---|---|---|
| FR-4.1 | `devsecops-coral scan` — Run security posture check across all sources | P0 |
| FR-4.2 | `devsecops-coral correlate` — Correlate vulnerabilities with deploys and errors | P0 |
| FR-4.3 | `devsecops-coral timeline --since 24h` — Build unified incident timeline | P1 |
| FR-4.4 | `devsecops-coral ask "natural language query"` — Free-form agent query | P0 |
| FR-4.5 | Rich terminal output with severity coloring (critical=red, high=orange, medium=yellow, low=green) | P0 |
| FR-4.6 | `devsecops-coral setup` — Interactive source configuration wizard | P2 |

### FR-5: Output Formats

| ID | Requirement | Priority |
|---|---|---|
| FR-5.1 | Rich terminal tables with color-coded severity | P0 |
| FR-5.2 | JSON output for piping to other tools (`--format json`) | P1 |
| FR-5.3 | Markdown report export (`--format md`) | P2 |

---

## 5. Non-Functional Requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-1 | All data stays local (Coral's security model) | No data leaves the machine |
| NFR-2 | Query response time for single-source queries | < 5 seconds |
| NFR-3 | Query response time for 5-source JOINs | < 15 seconds |
| NFR-4 | Zero external dependencies beyond Coral + Python | No Docker, no databases |
| NFR-5 | Works on macOS and Linux | Coral supports both |
| NFR-6 | Python 3.10+ compatibility | Match Coral's requirements |

---

## 6. OSV Custom Source Spec

### Scope

Build a Coral source spec that exposes the OSV (Open Source Vulnerabilities) database as SQL tables, enabling any Coral user or agent to query vulnerability data alongside their other data sources.

### API Details

| Aspect | Detail |
|---|---|
| Base URL | `https://api.osv.dev` |
| Auth | None (public API) |
| Rate Limits | None currently |
| Pagination | Cursor-based (`page_token` in response) |
| Response Format | JSON |

### Tables

#### `osv.vulnerabilities`

Queryable by package name, ecosystem, and version.

| Column | Type | Source Field | Description |
|---|---|---|---|
| id | STRING | `id` | OSV vulnerability ID (e.g., GHSA-xxx, PYSEC-xxx) |
| summary | STRING | `summary` | Short description |
| details | STRING | `details` | Full description (Markdown) |
| aliases | STRING | `aliases[]` joined | CVE aliases (e.g., CVE-2024-XXXX) |
| published | TIMESTAMP | `published` | Publication date |
| modified | TIMESTAMP | `modified` | Last modified date |
| severity | STRING | `database_specific.severity` or derived from CVSS | HIGH, MEDIUM, LOW, CRITICAL |
| package_name | STRING | `affected[].package.name` | Affected package name |
| ecosystem | STRING | `affected[].package.ecosystem` | Package ecosystem (PyPI, npm, Go, etc.) |
| fixed_version | STRING | `affected[].ranges[].events[].fixed` | Version that fixes the vulnerability |
| references | STRING | `references[].url` joined | Reference URLs |

#### `osv.ecosystems`

Static reference table of supported ecosystems.

| Column | Type | Description |
|---|---|---|
| name | STRING | Ecosystem name (PyPI, npm, Go, Maven, etc.) |

### Required Variables

```yaml
variables: []
# No variables needed — OSV is a public API with no authentication
```

### Query Mapping

| SQL Query Pattern | OSV API Call |
|---|---|
| `SELECT * FROM osv.vulnerabilities WHERE package_name = 'django' AND ecosystem = 'PyPI'` | `POST /v1/query {"package": {"name": "django", "ecosystem": "PyPI"}}` |
| `SELECT * FROM osv.vulnerabilities WHERE id = 'GHSA-xxx'` | `GET /v1/vulns/GHSA-xxx` |
| `SELECT * FROM osv.vulnerabilities WHERE package_name IN ('django', 'flask')` | `POST /v1/querybatch` with multiple queries |

---

## 7. Technical Architecture

### System Components

```
┌──────────────────────────────────────────────────────────┐
│                        CLI Layer                          │
│  (Python + Rich + Typer/Click)                           │
│                                                           │
│  Commands: scan | correlate | timeline | ask              │
└─────────────────────────┬────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│                      Agent Layer                          │
│  (LLM via Anthropic/OpenAI API)                          │
│                                                           │
│  - Intent parsing                                         │
│  - SQL template selection + parameterization              │
│  - Result analysis + natural language generation          │
└─────────────────────────┬────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│                    Coral Runtime                           │
│  (via MCP or CLI subprocess)                              │
│                                                           │
│  ┌─────────┐ ┌────────┐ ┌────────┐ ┌───────┐ ┌────────┐ │
│  │   OSV   │ │ GitHub │ │  Jira  │ │Sentry │ │Grafana │ │
│  │(custom) │ │(bundled)│ │(bundled)│ │(bundled)│ │(bundled)│ │
│  └─────────┘ └────────┘ └────────┘ └───────┘ └────────┘ │
│                                                           │
│  Cross-source JOINs, caching, schema discovery            │
└──────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| Language | Python 3.10+ | Primary skill; Coral MCP SDK available |
| CLI Framework | Typer + Rich | Modern Python CLI with beautiful output |
| LLM Integration | Anthropic Claude API or OpenAI | Agent reasoning for natural language queries |
| Coral Integration | Coral MCP (primary) or CLI subprocess (fallback) | Cross-source SQL execution |
| Testing | pytest | Standard Python testing |
| Packaging | pyproject.toml + pip | Standard Python packaging |

### Project Structure

```
devsecops-coral/
├── README.md
├── CLAUDE.md                    # Guardrails for Claude Code
├── pyproject.toml               # Package config
├── LICENSE                      # Apache 2.0
│
├── sources/
│   └── osv/
│       ├── osv.yaml             # OSV Coral source spec
│       └── README.md            # Source spec documentation
│
├── src/
│   └── devsecops_coral/
│       ├── __init__.py
│       ├── cli.py               # Typer CLI commands
│       ├── agent.py             # LLM agent (intent → SQL → analysis)
│       ├── coral_client.py      # Coral MCP/CLI integration
│       ├── queries/
│       │   ├── __init__.py
│       │   ├── correlate.py     # Vulnerability-deploy correlation queries
│       │   ├── scan.py          # Security posture scan queries
│       │   └── timeline.py      # Incident timeline queries
│       ├── formatters/
│       │   ├── __init__.py
│       │   ├── rich_output.py   # Rich terminal tables + colors
│       │   ├── json_output.py   # JSON export
│       │   └── markdown_output.py  # Markdown report
│       └── config.py            # Configuration management
│
├── tests/
│   ├── test_queries.py
│   ├── test_agent.py
│   ├── test_formatters.py
│   └── fixtures/                # Mock API responses for testing
│       ├── osv_response.json
│       ├── github_pulls.json
│       ├── sentry_issues.json
│       └── jira_issues.json
│
├── demo/
│   ├── seed_data.py             # Script to seed test data across all sources
│   ├── fastapi_app/             # Vulnerable FastAPI app for Sentry data
│   │   ├── main.py
│   │   └── requirements.txt     # Intentionally vulnerable deps
│   └── scenarios/               # Pre-built demo scenarios
│       ├── active_exploitation.md
│       └── untracked_cves.md
│
├── docs/
│   ├── SETUP.md                 # Source configuration guide
│   ├── QUERIES.md               # SQL query reference
│   └── ARCHITECTURE.md          # System architecture
│
└── blog/
    └── building-devsecops-coral.md  # Medium blog post draft
```

---

## 8. Data Seeding Plan

All data is real, generated from individual free-tier accounts.

### GitHub

1. Create public repo `coral-signal-seed` with intentionally vulnerable `requirements.txt`
2. Dependabot auto-creates alerts and PRs
3. Create manual PRs simulating "fix: upgrade django to 4.2.x"
4. Enable GitHub Actions with a simple CI workflow (to have workflow_runs data)
5. Create issues tagged with security labels

### Sentry

1. Free signup at sentry.io
2. Create project "coral-signal-seed"
3. Deploy FastAPI app with `sentry-sdk[fastapi]` installed
4. Generate real errors by hitting endpoints that raise exceptions
5. Errors will have realistic stack traces, timestamps, and frequency data

### Jira Cloud

1. Free signup at atlassian.com
2. Create project "SEC" (Security)
3. Create 5-8 realistic issues:
   - SEC-1: "CVE-2024-XXXX: Django < 4.2 SQL injection" [labels: security, critical]
   - SEC-2: "Upgrade requests library — known SSRF" [labels: security, high]
   - SEC-3: "Investigate Sentry error spike on /api/process" [labels: security, triage]
   - SEC-4: "Quarterly dependency audit Q2 2026" [labels: security, maintenance]
   - SEC-5: "Implement CSP headers on dashboard" [labels: security, medium]
4. Vary statuses: Open, In Progress, Done (realistic distribution)

### Grafana Cloud

1. Free signup at grafana.com
2. Create alert rule: "Error rate > threshold"
3. Add deployment annotations with timestamps matching GitHub PR merges

### OSV

No seeding needed — real vulnerability data from the public API.

---

## 9. Demo Scenarios

### Scenario 1: "Are we vulnerable?"

```bash
$ devsecops-coral scan --ecosystem PyPI --packages django,flask,requests,celery

🔍 Security Posture Scan
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 Package    │ CVE            │ Severity │ Jira Ticket │ Status
────────────┼────────────────┼──────────┼─────────────┼────────
 django     │ GHSA-xxx-xxx   │ CRITICAL │ SEC-1       │ In Progress
 requests   │ GHSA-yyy-yyy   │ HIGH     │ —           │ ⚠ UNTRACKED
 flask      │ —              │ —        │ —           │ ✅ Clean
 celery     │ GHSA-zzz-zzz  │ MEDIUM   │ SEC-4       │ Open

⚠ 1 CRITICAL, 1 HIGH vulnerability found
⚠ 1 vulnerability has NO tracking ticket — action needed
```

### Scenario 2: "Is this being actively exploited?"

```bash
$ devsecops-coral correlate --since 7d

🔗 Vulnerability ↔ Error Correlation (Last 7 Days)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 CVE            │ Package  │ Severity │ Error Count │ Error Level │ Signal
────────────────┼──────────┼──────────┼─────────────┼─────────────┼────────
 GHSA-xxx-xxx   │ django   │ CRITICAL │ 47          │ fatal       │ 🔴 ACTIVE
 GHSA-yyy-yyy   │ requests │ HIGH     │ 3           │ error       │ 🟡 MONITOR

🔴 1 potential active exploitation detected
   GHSA-xxx-xxx (Django) + 47 fatal errors in matching time window
   Recommended: Investigate SEC-1 immediately
```

### Scenario 3: "Build me a timeline of today's events"

```bash
$ devsecops-coral timeline --since 24h

📅 Security Event Timeline (Last 24 Hours)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 09:15 │ 🔴 osv     │ GHSA-xxx-xxx published (Django CRITICAL)
 10:30 │ 🟢 github  │ PR #42 merged: "fix: upgrade django to 4.2.11" by @samchawla
 10:45 │ 🟡 sentry  │ JSONDecodeError spike on /api/process (12 events)
 11:00 │ 🔵 jira    │ SEC-1 created: "CVE-2024-XXXX: Django SQL injection" [Critical]
 11:15 │ 🟡 sentry  │ Error rate normalized
 14:00 │ 🔵 jira    │ SEC-1 moved to "In Progress"
 16:30 │ 🟢 github  │ PR #43 opened: "fix: patch celery to 5.3.6" by @samchawla
```

---

## 10. Success Criteria

### Hackathon Submission Checklist

| # | Deliverable | Acceptance Criteria |
|---|---|---|
| 1 | Working CLI tool | All 4 commands (scan, correlate, timeline, ask) execute successfully |
| 2 | 5 Coral sources connected | GitHub, Jira, Sentry, Grafana (bundled) + OSV (custom) |
| 3 | Cross-source JOINs | At least 3 queries that JOIN 3+ sources |
| 4 | OSV source spec | Valid YAML, passes `coral source validate`, submitted to Coral repo |
| 5 | AI agent | Natural language → SQL → formatted output via Coral MCP |
| 6 | README | Installation, quickstart, screenshots/GIFs, architecture diagram |
| 7 | Blog post | Published on Medium, 2-3 pages, reproducible |
| 8 | Discord showcase | Posted in #how-i-coral with screenshots and write-up |
| 9 | Social posts | LinkedIn + X tagging @withcoral and @WeMakeDevs |
| 10 | Demo video | 3-5 minute screen recording walking through scenarios |

### Judging Criteria Mapping

| Criterion | Target Score | How We Achieve It |
|---|---|---|
| Potential Impact | 9/10 | Real problem, real tools, real data. Spoken from 8+ years of experience. |
| Creativity & Originality | 8/10 | Security + DevOps cross-correlation is unique. Nobody else will combine these 5 sources. |
| Learning & Growth | 9/10 | First-time Coral user. Built custom source spec. Learned Sentry. Documented journey. |
| Technical Implementation | 9/10 | 5 sources, complex JOINs, agent layer, rich CLI. |
| Aesthetics & UX | 8/10 | Severity-colored Rich CLI. Clear commands. Intuitive output. |
| Best Use of Coral | 9/10 | Cross-source JOINs, custom source, schema discovery, caching, SQL as universal security query. |

---

## 11. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Coral SQL doesn't support all query patterns | Medium | High | Test queries Day 1-2. Simplify if needed. Coral uses DataFusion (Apache Arrow) — standard SQL. |
| Grafana free tier too limited | Medium | Low | Drop to 4 sources. Grafana is P1, not P0. |
| OSV source spec takes longer than expected | Low | Medium | OSV API is simple (3 endpoints, no auth). Worst case: submit spec separately for bounty. |
| LLM agent integration complexity | Medium | Medium | Fallback: skip agent, use CLI with pre-built SQL templates. Still a valid submission. |
| Data seeding feels artificial | Low | Low | Use real vulnerable packages, real Sentry errors from real code. Nothing mocked. |
| 7 days too tight for solo | Medium | High | P0 features only in first 4 days. Days 5-7 are polish, docs, blog. Ship at 80%. |

---

## 12. Post-Hackathon Roadmap (mention in README)

- Slack integration for real-time security alerts
- Additional custom sources: Snyk, Trivy, GitHub Advanced Security
- Scheduled scans with cron/Celery
- Team dashboard (Streamlit/Plotly)
- CI/CD integration: run `devsecops-coral scan` in GitHub Actions
- Severity scoring algorithm with configurable weights
- Export to SARIF format for GitHub Code Scanning integration
