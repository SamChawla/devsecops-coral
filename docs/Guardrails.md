# Guardrails

Security, privacy, and safety guardrails for **devsecops-coral**.

> This is an independent personal hackathon project. These guardrails are
> **non-negotiable** and exist to keep secrets, employer/client information, and
> unsafe operations out of the codebase, git history, demos, and public posts.

For day-to-day AI-assisted development rules, see [`CLAUDE.md`](../CLAUDE.md).
This file is the human-facing summary of the same protections, plus the
pre-commit workflow to enforce them.

---

## 1. Core principles

| # | Principle | Why |
|---|---|---|
| 1 | **Read-only data layer** | Coral is the *only* path to data, and it is read-only. No source API is called directly for reads. |
| 2 | **Writes require approval** | Every write (Jira / GitHub / Grafana) goes through `actions/` and runs **only after explicit human approval**. |
| 3 | **No secrets in the repo** | Tokens, keys, DSNs, and `.env` files never get committed. Everything is read from environment variables. |
| 4 | **No employer/client data** | Company names, codenames, internal hostnames, colleague names, or business data never appear anywhere. |
| 5 | **Synthetic demo data only** | All demo data is fabricated in personal free-tier accounts — never copied from real systems. |
| 6 | **SELECT-only agent** | The LLM agent generates read-only SQL. No `INSERT/UPDATE/DELETE/DDL`, no `eval`/`exec`. |

---

## 2. Architecture guardrails (enforced in code)

These principles are backed by actual implementation, not just policy:

| Guardrail | Where it lives | What it does |
|---|---|---|
| Coral is the sole data layer | `coral_client.py` | Only file that talks to Coral. All reads go through it. |
| Writes isolated + approval-gated | `actions/executor.py` | In-memory action store; `approve`/`dismiss` orchestration. Nothing executes until approved. |
| SELECT-only SQL | `agent.py → _validate_sql()` | Rejects any query not starting with `SELECT`; blocks `INSERT/UPDATE/DELETE/DROP/CREATE/ALTER/TRUNCATE`. |
| Parameterized queries | `queries/*.py` | SQL templates with validated placeholders — no raw f-string interpolation of user input. |
| Credential redaction | `agent.py → AGENT_SYSTEM_PROMPT` | Instructs the model to redact `ghp_`, `sk-`, `AKIA`-style strings as `[REDACTED]` and never echo raw secrets. |

### Agent prompt safety (current `agent.py`)

The system prompt hard-codes these rules for every LLM call:

- Only generate `SELECT` queries. Never `INSERT`, `UPDATE`, `DELETE`, or DDL.
- Never include API keys, tokens, or credentials in queries or responses.
- Never reference specific company names, internal project names, or client data.
- If results contain credential-like strings (`ghp_`, `sk-`, `AKIA`), redact as `[REDACTED]`.

The response is then validated by `_validate_sql()` before execution — a defense-in-depth check independent of the prompt.

---

## 3. Secrets & credentials — NEVER commit

The following must never appear in any file, commit, PR, doc, comment, screenshot, recording, or social post:

- API tokens, keys, passwords, DSNs for **any** service (GitHub, Sentry, Jira, Grafana, Coral, Anthropic, …)
- OAuth client IDs/secrets, webhook URLs (often contain embedded tokens)
- SSH keys, certificates, `.pem`/`.key` files
- `.env`, `.env.local`, `.env.production`, or similar
- Sentry DSN strings — always `os.getenv("SENTRY_DSN")`
- Jira/Atlassian site URLs with org names — use `your-site.atlassian.net` in docs
- Grafana instance URLs — use `your-org.grafana.net` in docs

**Always read credentials from environment variables.** Never hardcode them, not even temporarily.

---

## 4. Employer / client information — NEVER disclose

This project is independent of any current or past employer/client. The following must never appear anywhere:

- Product names, codenames, or internal tool names from employers/clients
- Company names of clients or employers
- Infrastructure details — hostnames, IP ranges, domains, cloud account IDs, regions
- Internal architecture — microservice names, internal APIs, schemas, internal library names
- Colleague names, team structures, org charts
- Proprietary processes — playbooks, escalation procedures, vendor-specific patterns
- Business data — revenue, customer counts, contract terms, SLA details

### Private denylist (not committed)

Keep your personal list of sensitive terms (employer/client codenames) in a
**gitignored** file so it never enters history:

```
.guardrails-denylist.txt    # one term per line — already in .gitignore
```

The pre-commit scan (below) reads from this file instead of hardcoding any real
names into the repository.

### Safe narrative patterns

```
# ✅ SAFE — generic domain expertise
"As an engineer who has spent years building integrations across security and DevOps tools…"
"In my consulting work, I've normalized threat data across multiple EDR and SIEM vendors…"

# ❌ UNSAFE — names employers, clients, or projects
"At [Company], I built [Product Name] which integrates with…"
"My client [Client Name] uses our platform to…"
```

---

## 5. `.gitignore` enforcement

The repository's [`.gitignore`](../.gitignore) is itself a guardrail. It must block:

- Secrets: `.env`, `.env.*` (except `.env.example`), `*.pem`, `*.key`, `secrets/`, `credentials/`
- Coral config that may hold tokens: `.coral/`, `coral-config.yaml`
- Service configs: `.sentryclirc`, `grafana-config.json`, `.atlassian/`
- Private local docs with real org info: `ACCOUNTS.md`, `cursor.md`, `SHOWCASE.md`
- The private denylist: `.guardrails-denylist.txt`
- Build/test artifacts: `frontend/node_modules/`, `dist/`, `frontend/test-results/`, `frontend/playwright-report/`

Do not remove `.gitignore` entries without re-reading this file.

---

## 6. Pre-commit checklist

Run before **every** commit. If anything flags a real secret, company name, or internal URL — **STOP and fix before committing.**

```bash
# 1. Secret-like patterns
grep -rn "ghp_\|sntrys_\|glsa_\|sk-\|AKIA\|password\|secret\|token" \
  --include="*.py" --include="*.yaml" --include="*.md" --include="*.toml" \
  src/ demo/ docs/

# 2. Employer/client references — uses your private, gitignored denylist
#    (create .guardrails-denylist.txt with one term per line)
grep -rnif .guardrails-denylist.txt src/ demo/ docs/ ./*.md

# 3. Internal-looking URLs
grep -rn "atlassian.net\|sentry.io\|grafana.net" --include="*.py" src/

# 4. Review what you're actually staging
git diff --staged
```

### Git hygiene

- **Never `git add .`** — stage files individually (`git add <file>` or `git add -p`).
- **Review `git diff --staged`** before every commit.
- **Generic commit messages** — describe the change, not the client context.
- **If a secret is committed:** rotate the credential immediately, then purge git
  history (BFG / `git filter-repo`). Deleting it in a new commit is **not** enough.

---

## 7. Demo, recording & social rules

**Demo data** must be synthetic, created in personal free-tier accounts. Sentry
errors come only from the demo FastAPI app; Jira/GitHub content is generic.

**Before recording or screenshotting** for blog/Discord/social:

1. Close unrelated browser tabs; clear address-bar suggestions; hide bookmarks bar.
2. Disable desktop notifications (mail, chat, calendar).
3. Use a clean terminal profile — no work-related shell history, hostname, or paths.
4. Verify no client VPN indicator is visible in the system tray.
5. In the editor: close files from other projects; no work repos in the sidebar.

**Social posts (LinkedIn / X / Discord / Medium):**

- Frame experience as domain expertise, not specific employer work.
- Never tag employer/client accounts.
- If asked "which company?", decline politely: "I keep client details confidential."

---

## 8. Incident response — leaked secret

1. **Rotate the credential immediately** at the provider (don't wait).
2. Remove it from the working tree and confirm it's gitignored.
3. **Purge it from git history** (`git filter-repo` or BFG Repo-Cleaner).
4. Force-push the cleaned history **only** after coordinating, and re-clone locally.
5. Audit logs at the provider for any use during the exposure window.

> A secret that reached a remote is compromised forever — rotation is mandatory,
> not optional.
