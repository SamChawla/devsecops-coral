# demo/fastapi_app — Sentry Signal Seeder

Intentionally vulnerable FastAPI app that generates real Sentry errors for demo data seeding.
Part of **[devsecops-coral](https://github.com/SamChawla/devsecops-coral)**.

## What it feeds into Coral

| Signal | Source |
|--------|--------|
| Known CVEs | OSV / Dependabot (via pinned vulnerable deps) |
| Code changes | GitHub PRs (fix branches you merge or leave open) |
| Runtime errors | Sentry (via `/vulnerable`, `/unhandled`, etc.) |

## Run locally

```bash
cd demo/fastapi_app
pip install -r requirements.txt
export SENTRY_DSN=https://...   # from your Sentry project settings
uvicorn main:app --reload --port 8001
```

Then hit endpoints to seed Sentry:

```bash
curl http://localhost:8001/generate-errors   # batch: KeyError + TypeError + ZeroDivisionError
curl http://localhost:8001/vulnerable        # JSONDecodeError
curl http://localhost:8001/unhandled         # ValueError
```

## Security note

Do **not** deploy this app or use these dependency versions in production.
