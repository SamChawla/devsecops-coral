# Source Setup Guide

Step-by-step instructions for configuring each data source for devsecops-coral.

---

## Prerequisites

- Coral CLI installed: `brew install withcoral/tap/coral`
- Python 3.10+
- Git and GitHub CLI (`gh`) installed

---

## 1. GitHub (Bundled Source)

You already have a GitHub account (SamChawla). This setup creates a demo repo with vulnerable dependencies to generate Dependabot alerts.

### Create the demo repository

```bash
# Create and push the demo repo
cd demo/fastapi_app
gh repo create coral-signal-seed --public --source=. --push

# Enable Dependabot alerts (usually on by default for public repos)
# Go to: https://github.com/SamChawla/coral-signal-seed/settings/security_analysis
# Enable: Dependabot alerts, Dependabot security updates
```

### Create realistic PRs

```bash
# PR 1: "Fix" Django vulnerability
git checkout -b fix/upgrade-django
sed -i 's/django==4.1.0/django==4.2.11/' requirements.txt
git add requirements.txt
git commit -m "fix: upgrade Django to 4.2.11 (CVE-2023-36053, CVE-2023-43665)"
gh pr create --title "fix: upgrade Django to 4.2.11" --body "Resolves critical CVEs in Django 4.1.x"
# Merge it
gh pr merge --squash

# PR 2: "Fix" requests vulnerability  
git checkout main && git pull
git checkout -b fix/upgrade-requests
sed -i 's/requests==2.25.0/requests==2.31.0/' requirements.txt
git add requirements.txt
git commit -m "fix: upgrade requests to 2.31.0 (CVE-2023-32681)"
gh pr create --title "fix: upgrade requests to 2.31.0" --body "Resolves Proxy-Authorization header leak"
# Leave this one OPEN (unmerged) — shows "in progress" remediation

# PR 3: A non-security PR for contrast
git checkout main && git pull
git checkout -b feat/add-healthcheck
echo '# Add /health endpoint' >> main.py
git add main.py
git commit -m "feat: add health check endpoint"
gh pr create --title "feat: add health check endpoint" --body "Non-security change for monitoring"
gh pr merge --squash
```

### Connect to Coral

```bash
# You need a GitHub Personal Access Token
# Go to: https://github.com/settings/tokens → Generate new token (classic)
# Scopes: repo (full), read:org
export GITHUB_TOKEN=ghp_your_token_here

coral source add --interactive github
# When prompted, enter your token

# Test
coral sql "SELECT number, title, state FROM github.pulls WHERE owner = 'SamChawla' AND repo = 'coral-signal-seed' LIMIT 5"
```

---

## 2. Sentry (Bundled Source)

### Sign up and create project

1. Go to https://sentry.io/signup/ → sign up with GitHub
2. Create organization (e.g., "coral-signal-seed")
3. Create project → Platform: Python → Framework: FastAPI
4. Copy your DSN (looks like `https://abc123@o123456.ingest.sentry.io/456789`)

### Generate real error data

```bash
cd demo/fastapi_app

# Set your Sentry DSN
export SENTRY_DSN="https://your-dsn@sentry.io/project-id"

# Install dependencies (in a virtualenv)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start the app
uvicorn main:app --reload --port 8000

# Generate errors (in another terminal)
# These create real Sentry events with stack traces and metadata
curl http://localhost:8000/vulnerable
curl http://localhost:8000/unhandled
curl http://localhost:8000/dependency-error
curl http://localhost:8000/generate-errors

# Hit them multiple times to create frequency patterns
for i in {1..10}; do curl -s http://localhost:8000/vulnerable > /dev/null; done
for i in {1..5}; do curl -s http://localhost:8000/unhandled > /dev/null; done
```

### Connect to Coral

```bash
# Get your Sentry auth token
# Go to: https://sentry.io/settings/account/api/auth-tokens/ → Create new token
# Scopes: org:read, event:read, member:read, project:read, project:releases

export SENTRY_ORG="your-org-slug"
export SENTRY_TOKEN="sntrys_your_token_here"

coral source add --interactive sentry

# Test
coral sql "SELECT title, level, count FROM sentry.issues WHERE level IN ('fatal', 'error') ORDER BY count DESC LIMIT 5"
```

---

## 3. Jira Cloud (Bundled Source)

### Sign up and create project

1. Go to https://www.atlassian.com/software/jira/free → sign up
2. Create site (e.g., "coral-signal-seed.atlassian.net")
3. Create project → Key: "SEC" → Template: Kanban

### Create security issues

Create these issues manually in the Jira UI:

| Key | Summary | Priority | Labels | Status |
|---|---|---|---|---|
| SEC-1 | CVE-2023-36053: Django ReDoS vulnerability requires upgrade to 4.2.x | Critical | security, cve, django | In Progress |
| SEC-2 | CVE-2023-32681: requests library leaks Proxy-Authorization header | High | security, cve, requests | Open |
| SEC-3 | Investigate Sentry error spike on /vulnerable endpoint | High | security, triage | Open |
| SEC-4 | Quarterly dependency audit — Q2 2026 | Medium | security, maintenance | Open |
| SEC-5 | CVE-2024-22195: Jinja2 XSS via xmlattr filter | Medium | security, cve, jinja2 | Done |
| SEC-6 | Implement Content-Security-Policy headers | Low | security, hardening | Backlog |

### Connect to Coral

```bash
# Get your Atlassian API token
# Go to: https://id.atlassian.com/manage-profile/security/api-tokens → Create token

export JIRA_BASE_URL="https://your-site.atlassian.net"
export JIRA_EMAIL="your-email@example.com"
export JIRA_API_TOKEN="your_token_here"

coral source add --interactive jira

# Test
coral sql "SELECT key, summary, status, priority FROM jira.issues WHERE labels LIKE '%security%' ORDER BY priority LIMIT 10"
```

---

## 4. Grafana Cloud (Bundled Source)

### Sign up and configure

1. Go to https://grafana.com/auth/sign-up/create-user → sign up (free tier)
2. Note your Grafana instance URL (e.g., `https://your-org.grafana.net`)
3. Create a Service Account:
   - Go to Administration → Service Accounts → Create
   - Role: Admin (for read access to all tables)
   - Generate token → copy it

### Create test alert rules and annotations

In the Grafana UI:
1. Create a simple alert rule: Alerting → Alert rules → New alert rule
   - Name: "Error Rate High"
   - Condition: Any (we just need the rule to exist for querying)
2. Add a deployment annotation:
   - Go to any dashboard → Settings → Annotations
   - Add annotation with text "Deploy: coral-signal-seed v0.1.0" and timestamp

### Connect to Coral

```bash
export GRAFANA_URL="https://your-org.grafana.net"
export GRAFANA_TOKEN="glsa_your_token_here"

coral source add --interactive grafana

# Test
coral sql "SELECT name, state FROM grafana.alert_rules LIMIT 5"
```

---

## 5. OSV (Custom Source)

No signup needed. Just register the source spec with Coral.

```bash
# Lint the source spec first (no credentials needed)
coral source lint sources/osv/osv.yaml

# Add the custom OSV source spec
coral source add --file sources/osv/osv.yaml

# Run validation tests
coral source test osv

# Test with real vulnerability data (search function syntax)
coral sql "SELECT id, summary, severity FROM osv.search_vulnerabilities(package => 'django', ecosystem => 'PyPI') LIMIT 5"
```

---

## Verify All Sources

```bash
# List all configured sources
coral source list

# Expected output:
# github    ✓ connected
# jira      ✓ connected  
# sentry    ✓ connected
# grafana   ✓ connected
# osv       ✓ connected

# Run a cross-source query to verify JOINs work
coral sql "
SELECT osv.id, osv.summary, g.title AS recent_pr
FROM osv.search_vulnerabilities(package => 'django', ecosystem => 'PyPI') osv
LEFT JOIN github.pulls g 
    ON g.state = 'merged' 
    AND g.repo = 'coral-signal-seed'
LIMIT 5
"
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `coral: command not found` | Run `brew install withcoral/tap/coral` or check PATH |
| Source auth fails | Re-run `coral source add --interactive <source>` with fresh token |
| Query returns empty results | Verify data exists by querying single source first |
| Cross-source JOIN returns no matches | Check that time windows overlap — use wider INTERVAL |
| OSV source spec invalid | Run `coral source validate --spec sources/osv/osv.yaml` |
