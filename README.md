# 🪸 devsecops-coral

**One SQL query across your entire security & DevOps stack.**

> When a vulnerability is found, what else is happening? Which deploys shipped it? Are errors spiking? Is there a tracking ticket? devsecops-coral answers all of that in one Coral query — no ETL, no warehouse, no glue code.

[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Coral](https://img.shields.io/badge/powered%20by-Coral-398125)](https://withcoral.com)
[![Hackathon](https://img.shields.io/badge/hackathon-Pirates%20of%20the%20Coral--bean-gold)](https://www.wemakedevs.org/hackathons/coral)

---

## The Problem

Security and DevOps teams operate across fragmented tools. A vulnerability report in OSV, a merged PR in GitHub, an error spike in Sentry, a Jira ticket, a Grafana alert — all related, all in different dashboards. Correlating them manually takes 20-30 minutes per incident and junior engineers miss connections entirely.

## The Solution

devsecops-coral uses [Coral](https://withcoral.com) to join vulnerability intelligence, source control, error monitoring, issue tracking, and infrastructure observability into a single SQL query — executed locally, securely, with zero ETL.

```sql
-- Are we vulnerable, and if so — where, when, and who shipped it?
SELECT 
    osv.id AS cve, osv.severity,
    g.title AS pr_title, g.user_login AS author,
    se.title AS error, se.count AS frequency,
    j.key AS ticket, j.status
FROM osv.search_vulnerabilities(package => 'django', ecosystem => 'PyPI') osv
LEFT JOIN github.pulls g ON g.state = 'merged'
LEFT JOIN sentry.issues se ON se.level IN ('fatal', 'error')
LEFT JOIN jira.issues j ON j.labels LIKE '%security%'
WHERE osv.severity = 'CRITICAL'
ORDER BY se.count DESC;
```

## Data Sources

| Source | Type | What It Provides |
|---|---|---|
| **OSV** (osv.dev) | 🔧 Custom source spec | Known CVEs across PyPI, npm, Go, Maven, and 15+ ecosystems |
| **GitHub** | ✅ Bundled | PRs, commits, Dependabot alerts, workflow runs |
| **Sentry** | ✅ Bundled | Application errors, event frequency, severity |
| **Jira** | ✅ Bundled | Security tickets, triage status, priority |
| **Grafana** | ✅ Bundled | Alert rules, annotations, infrastructure health |

## Quick Start

### Prerequisites

- [Coral CLI](https://withcoral.com/docs/getting-started/installation) installed
- Python 3.10+
- Free accounts: [GitHub](https://github.com), [Sentry](https://sentry.io/signup/), [Jira Cloud](https://www.atlassian.com/software/jira/free), [Grafana Cloud](https://grafana.com/auth/sign-up/create-user)

### Install

```bash
# Clone the repo
git clone https://github.com/SamChawla/devsecops-coral.git
cd devsecops-coral

# Install the tool
pip install -e .
```

### Configure Coral Sources

```bash
# Add the custom OSV source
coral source add --file sources/osv/osv.yaml

# Add bundled sources (interactive — prompts for API tokens)
coral source add --interactive github
coral source add --interactive jira
coral source add --interactive sentry
coral source add --interactive grafana

# Verify all sources
coral source list
```

### Run

```bash
# Security posture scan
devsecops-coral scan --ecosystem PyPI --packages django,flask,requests,celery

# Vulnerability-deploy-error correlation
devsecops-coral correlate --since 7d

# Unified security timeline
devsecops-coral timeline --since 24h

# Ask anything in natural language
devsecops-coral ask "Are there any critical vulnerabilities without tracking tickets?"
```

## CLI Commands

### `scan` — Security Posture Overview

Checks your dependencies against OSV, cross-references with Jira tickets to find untracked vulnerabilities.

```
$ devsecops-coral scan --ecosystem PyPI --packages django,flask,requests

🔍 Security Posture Scan
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 Package    │ CVE            │ Severity │ Jira Ticket │ Status
────────────┼────────────────┼──────────┼─────────────┼────────
 django     │ GHSA-xxx-xxx   │ CRITICAL │ SEC-1       │ In Progress
 requests   │ GHSA-yyy-yyy   │ HIGH     │ —           │ ⚠ UNTRACKED
 flask      │ —              │ —        │ —           │ ✅ Clean

⚠ 1 CRITICAL, 1 HIGH vulnerability found
⚠ 1 vulnerability has NO tracking ticket
```

### `correlate` — Cross-Stack Signal Correlation

Joins CVE data with error monitoring to detect potential active exploitation.

```
$ devsecops-coral correlate --since 7d

🔗 Vulnerability ↔ Error Correlation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 CVE            │ Package  │ Severity │ Errors │ Signal
────────────────┼──────────┼──────────┼────────┼────────
 GHSA-xxx-xxx   │ django   │ CRITICAL │ 47     │ 🔴 ACTIVE
 GHSA-yyy-yyy   │ requests │ HIGH     │ 3      │ 🟡 MONITOR

🔴 Potential active exploitation: GHSA-xxx-xxx + 47 fatal errors
```

### `timeline` — Unified Security Event Timeline

Builds a chronological view across all sources.

### `ask` — Natural Language Queries

Uses an LLM agent to translate questions into Coral SQL.

```
$ devsecops-coral ask "Which PRs in the last week introduced vulnerable dependencies?"
```

## OSV Custom Source Spec

This project includes a custom Coral source spec for [OSV (Open Source Vulnerabilities)](https://osv.dev), Google's open-source vulnerability database.

- **Public API** — No authentication required
- **15+ ecosystems** — PyPI, npm, Go, Maven, Rust, Debian, and more
- **Real-time data** — Always current, no syncing needed

The spec is at `sources/osv/osv.yaml` and can be used independently of this project:

```bash
coral source add --file sources/osv/osv.yaml
coral sql "SELECT id, summary, severity FROM osv.search_vulnerabilities(package => 'django', ecosystem => 'PyPI') LIMIT 5"
```

See the [custom source spec guide](https://withcoral.com/docs/guides/write-a-custom-source) for how it's built.

## Architecture

```
User ──→ CLI (Typer + Rich) ──→ Agent (LLM) ──→ Coral MCP ──→ Sources
                                                      │
                                              ┌───────┼───────┐
                                              │       │       │
                                            OSV   GitHub   Sentry
                                          (custom) (bundled) (bundled)
                                                   Jira    Grafana
                                                 (bundled) (bundled)
```

All queries execute locally via Coral. No data leaves your machine. The LLM agent only sees query results, not raw API responses.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run linting
ruff check src/
```

## Built With

- [Coral](https://withcoral.com) — SQL interface for APIs, files, and data sources
- [Typer](https://typer.tiangolo.com/) — CLI framework
- [Rich](https://rich.readthedocs.io/) — Terminal formatting
- [Anthropic Claude API](https://docs.anthropic.com/) — LLM agent reasoning
- Python 3.10+

## Background

This project was built for the [Pirates of the Coral-bean](https://www.wemakedevs.org/hackathons/coral) hackathon (May 25-31, 2026), organized by WeMakeDevs and sponsored by Coral.

As an engineer who has spent 8+ years building integrations across security and DevOps tools — including multi-vendor EDR/SIEM normalization across CrowdStrike, SentinelOne, Microsoft Defender, Cortex XDR, and IBM QRadar — I've experienced firsthand how painful cross-platform signal correlation is. This project is the tool I wish I had: one SQL query to answer "what's happening across my entire security stack?"

## Blog Post

📝 [Building a Cross-Stack Security Correlator with Coral — From 5 Vendor APIs to One SQL Query](#) (Medium)

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.

## Acknowledgements

- [Coral](https://withcoral.com) team for building an incredible open-source query layer
- [OSV](https://osv.dev) by Google for the open vulnerability database
- [WeMakeDevs](https://wemakedevs.org) and [Kunal Kushwaha](https://www.linkedin.com/in/kunal-kushwaha) for organizing
