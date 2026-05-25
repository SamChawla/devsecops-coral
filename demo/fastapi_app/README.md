# coral-signal-seed

**Demo data repo** for the hackathon project **[devsecops-coral](https://github.com/SamChawla/devsecops-coral)**.

| Repository | What it is |
|------------|------------|
| **devsecops-coral** | The main tool — Coral SQL CLI + agent that correlates security signals |
| **coral-signal-seed** (this repo) | A fake vulnerable app that *produces* those signals (CVEs, PRs, Sentry errors) |

This repo is not the product. It exists so judges can see real data flowing through `devsecops-coral` queries.

## What it feeds into Coral

| Signal | Source |
|--------|--------|
| Known CVEs | OSV / Dependabot (via pinned vulnerable deps) |
| Code changes | GitHub PRs (fix branches you merge or leave open) |
| Runtime errors | Sentry (via `/vulnerable`, `/unhandled`, etc.) |

## Run locally

```bash
pip install -r requirements.txt
export SENTRY_DSN=   # optional
uvicorn main:app --reload --port 8000
```

## Security note

Do **not** deploy this app or use these dependency versions in production.
