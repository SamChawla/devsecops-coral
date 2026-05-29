"""Configuration for devsecops-coral."""

from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=False)

# Severity styling (Rich markup)
SEVERITY_COLORS: dict[str, str] = {
    "CRITICAL": "bold red",
    "HIGH": "red",
    "MEDIUM": "yellow",
    "LOW": "green",
    "INFO": "blue",
}

SIGNAL_ICONS: dict[str, str] = {
    "active": "🔴",
    "monitor": "🟡",
    "clean": "🟢",
    "unknown": "⚪",
}

# LLM provider: auto | anthropic | euri | grok | cursor
# auto priority: anthropic → euri → grok → cursor proxy (first one configured wins)
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto")

# Anthropic (direct — recommended, uses the same key as Claude Code)
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# EURI (euron.one)
EURI_API_KEY: str = os.getenv("EURI_API_KEY", "")
EURI_MODEL: str = os.getenv("EURI_MODEL", "gemini-2.5-flash")
EURI_BASE_URL: str = os.getenv("EURI_BASE_URL", "https://api.euron.one/api/v1/euri")

# Grok (xAI — OpenAI-compatible API at https://api.x.ai/v1)
# The free tier exposes the fast models; override GROK_MODEL for paid tiers.
GROK_API_KEY: str = os.getenv("GROK_API_KEY", "")
GROK_MODEL: str = os.getenv("GROK_MODEL", "grok-4-fast")
GROK_BASE_URL: str = os.getenv("GROK_BASE_URL", "https://api.x.ai/v1")

# Cursor subscription (via local OpenAI-compatible proxy — see llm_client.check_cursor_proxy)
# Typical setup: npx cursor-agent-api-proxy → http://localhost:4646/v1
CURSOR_BASE_URL: str = os.getenv("CURSOR_BASE_URL", "http://localhost:4646/v1")
CURSOR_API_KEY: str = os.getenv("CURSOR_API_KEY", "not-needed")
CURSOR_MODEL: str = os.getenv("CURSOR_MODEL", "auto")

# Coral CLI — on Windows use WSL (see scripts/setup_windows.ps1)
CORAL_BIN: str = os.getenv(
    "CORAL_BIN",
    "wsl -d Ubuntu -e /root/.local/bin/coral",
)

# -- Authentication (SaaS shell) ---------------------------------------------
# The dashboard ships a lightweight org-scoped auth layer (SQLite + hashed
# passwords + httpOnly session cookies). Auth is enabled by default; set
# DEVSECOPS_AUTH_ENABLED=0 to run the API open (e.g. local CLI-only use).
AUTH_ENABLED: bool = os.getenv("DEVSECOPS_AUTH_ENABLED", "1").strip().lower() not in (
    "0",
    "false",
    "no",
    "",
)

# Where the auth SQLite database lives. Mount this path as a volume in
# production so users/orgs survive container restarts.
AUTH_DB_PATH: str = os.getenv(
    "AUTH_DB_PATH",
    str(Path(__file__).resolve().parents[2] / "data" / "auth.db"),
)

# Session lifetime in hours.
SESSION_TTL_HOURS: int = int(os.getenv("DEVSECOPS_SESSION_TTL_HOURS", "168"))

# Read-query result cache TTL (seconds). Identical Coral SQL executed within this
# window reuses the previous result instead of re-querying Coral — so opening the
# Actions tab reuses the scan/correlate reads already performed on the Detect tab.
# Explicit refresh busts the cache. Set to 0 to disable caching entirely.
QUERY_CACHE_TTL: float = float(os.getenv("DEVSECOPS_QUERY_CACHE_TTL", "90"))

# Demo defaults (override via env for your accounts)
GITHUB_OWNER: str = os.getenv("GITHUB_OWNER", "")
GITHUB_REPO: str = os.getenv("GITHUB_REPO", "devsecops-coral")

# Coral's bundled Jira source requires a constant, *bounded* JQL filter on the
# ``jql`` column (unbounded queries are rejected by the Jira API). This bounded
# default scopes the search to the last year; CVE/package matching is then done
# against the issue ``summary`` in the JOIN. Override via ``JIRA_SECURITY_JQL``.
JIRA_SECURITY_JQL: str = os.getenv("JIRA_SECURITY_JQL", "created >= -365d ORDER BY created DESC")

# -- Write credentials (Phase 3 ACT layer) -----------------------------------

# GitHub — fine-grained PAT with contents:write + pull_requests:write
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

# Jira Cloud — project admin API token
JIRA_BASE_URL: str = os.getenv("JIRA_BASE_URL", "")
JIRA_EMAIL: str = os.getenv("JIRA_EMAIL", "")
JIRA_API_TOKEN: str = os.getenv("JIRA_API_TOKEN", "")
JIRA_PROJECT_KEY: str = os.getenv("JIRA_PROJECT_KEY", "SEC")

# Grafana Cloud — service account token with Editor role
GRAFANA_URL: str = os.getenv("GRAFANA_URL", "")
GRAFANA_API_KEY: str = os.getenv("GRAFANA_API_KEY", "")
GRAFANA_DASHBOARD_UID: str = os.getenv("GRAFANA_DASHBOARD_UID", "")

# Sentry — DSN for SDK error/tracing; auth token used by Coral source
SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
SENTRY_TRACES_SAMPLE_RATE: float = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.2"))
SENTRY_ENVIRONMENT: str = os.getenv("SENTRY_ENVIRONMENT", "development")

PACKAGE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")
ECOSYSTEM_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")
GITHUB_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")
# OSV/GHSA/CVE identifiers, e.g. GHSA-2f9x-5v75-3qv4 or CVE-2024-1234.
VULN_ID_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")


def project_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parents[2]


def osv_spec_path() -> Path:
    """Path to the OSV Coral source spec."""
    return project_root() / "sources" / "osv" / "osv.yaml"


def validate_package_name(name: str) -> str:
    """Validate and return a package name safe for SQL interpolation."""
    cleaned = name.strip()
    if not cleaned or not PACKAGE_NAME_PATTERN.match(cleaned):
        msg = f"Invalid package name: {name!r}"
        raise ValueError(msg)
    return cleaned


def validate_ecosystem(ecosystem: str) -> str:
    """Validate and return an ecosystem name safe for SQL interpolation."""
    cleaned = ecosystem.strip()
    if not cleaned or not ECOSYSTEM_PATTERN.match(cleaned):
        msg = f"Invalid ecosystem: {ecosystem!r}"
        raise ValueError(msg)
    return cleaned


def validate_vuln_id(vuln_id: str) -> str:
    """Validate a CVE/GHSA/OSV identifier safe for SQL interpolation."""
    cleaned = vuln_id.strip()
    if not cleaned or not VULN_ID_PATTERN.match(cleaned):
        msg = f"Invalid vulnerability id: {vuln_id!r}"
        raise ValueError(msg)
    return cleaned


def validate_github_owner(owner: str) -> str:
    """Validate GitHub owner/org name for SQL interpolation."""
    cleaned = owner.strip()
    if not cleaned or not GITHUB_IDENTIFIER_PATTERN.match(cleaned):
        msg = f"Invalid GitHub owner: {owner!r}"
        raise ValueError(msg)
    return cleaned


def validate_github_repo(repo: str) -> str:
    """Validate GitHub repository name for SQL interpolation."""
    cleaned = repo.strip()
    if not cleaned or not GITHUB_IDENTIFIER_PATTERN.match(cleaned):
        msg = f"Invalid GitHub repo: {repo!r}"
        raise ValueError(msg)
    return cleaned


def resolve_github_scope(*, owner: str | None = None, repo: str | None = None) -> tuple[str, str]:
    """Return GitHub owner and repo, using env defaults when omitted."""
    resolved_owner = (owner or GITHUB_OWNER).strip()
    resolved_repo = (repo or GITHUB_REPO).strip()
    if not resolved_owner:
        raise ValueError(
            "GITHUB_OWNER is required for github.pulls queries. "
            "Set GITHUB_OWNER in .env or pass --github-owner."
        )
    return validate_github_owner(resolved_owner), validate_github_repo(resolved_repo)


def parse_packages(packages: str) -> list[str]:
    """Parse a comma-separated package list."""
    if not packages.strip():
        raise ValueError("At least one package is required")
    return [validate_package_name(p) for p in packages.split(",") if p.strip()]


def resolve_llm_provider() -> str:
    """Resolve which LLM backend to use.

    Priority (auto mode): anthropic → euri → grok → cursor proxy.
    """
    explicit = LLM_PROVIDER.strip().lower()
    if explicit in ("anthropic", "euri", "grok", "cursor"):
        return explicit
    if ANTHROPIC_API_KEY:
        return "anthropic"
    if EURI_API_KEY:
        return "euri"
    if GROK_API_KEY:
        return "grok"
    return "cursor"
