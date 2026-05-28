# Demo Scenario: Untracked CVEs

This scenario demonstrates FR-2.3 — CVEs with no corresponding Jira ticket.

## Prerequisites

1. OSV source connected with live vulnerability data
2. Jira project with security-labeled tickets (some packages tracked, others not)
3. Demo packages: `django,flask,requests,celery`

## Steps

### CLI

```bash
devsecops-coral scan --ecosystem PyPI --packages django,flask,requests,celery
```

Expected: at least one row with a CVE but **no Jira ticket** (UNTRACKED warning in output).

### Dashboard

1. Open **Scan** tab
2. Look for rows highlighted with UNTRACKED badge
3. Check **Posture Overview** for untracked count > 0
4. Verify SqlViewer shows OSV search + Jira LEFT JOIN

## What Judges Should See

- LEFT JOIN pattern handles missing Jira data gracefully
- Untracked vulnerabilities surfaced prominently
- Posture overview aggregates severity + untracked counts
