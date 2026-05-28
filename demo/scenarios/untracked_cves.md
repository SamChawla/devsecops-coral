# Demo Scenario: Untracked CVEs

Demonstrates FR-2.3 — surfacing CVEs that have no corresponding Jira security ticket.

## Setup (seed data required)

| Package | Jira Ticket | Expected Status |
|---------|-------------|-----------------|
| django  | SEC-1 (In Progress) | Tracked |
| requests | — | **UNTRACKED** |
| pillow  | — | **UNTRACKED** |
| celery  | SEC-4 (Open) | Tracked |

Ensure Jira project "SEC" has SEC-1 for django and SEC-4 for celery.
Do **not** create tickets for `requests` or `pillow` — the agent creates them.

## CLI Demo

```bash
devsecops-coral scan --ecosystem PyPI --packages django,requests,pillow,celery
```

Expected output:

```
Package    CVE            Severity  Jira Ticket  Status
django     GHSA-…         CRITICAL  SEC-1        In Progress
requests   GHSA-…         HIGH      —            UNTRACKED ⚠
pillow     GHSA-ppf2-m228 HIGH      —            UNTRACKED ⚠  (12 errors)
celery     GHSA-…         MEDIUM    SEC-4        Open
```

## Dashboard Demo

1. Open **Detect** tab → Scan Results
2. Filter by **Untracked** status — 2 rows highlighted in orange
3. Check **Posture Overview** strip: `Untracked: 2` shown in orange
4. Verify **SqlViewer** shows the `LEFT JOIN jira.issues` + `tracking_status` CASE expression

## What Judges See

- `CASE WHEN j.key IS NULL THEN 'UNTRACKED'` computed directly in Coral SQL
- Untracked count propagated to posture KPIs
- Orange highlighting draws attention to the security gap
