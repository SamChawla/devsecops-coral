"""Configuration for devsecops-coral."""

from __future__ import annotations

import os
import re
from pathlib import Path

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

# LLM provider: auto | euri | cursor
# auto = use EURI if EURI_API_KEY is set, else Cursor proxy
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto")

# EURI (euron.one)
EURI_API_KEY: str = os.getenv("EURI_API_KEY", "")
EURI_MODEL: str = os.getenv("EURI_MODEL", "gemini-2.5-flash")
EURI_BASE_URL: str = os.getenv("EURI_BASE_URL", "https://api.euron.one/api/v1/euri")

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

# Demo defaults (override via env for your accounts)
GITHUB_OWNER: str = os.getenv("GITHUB_OWNER", "")
GITHUB_REPO: str = os.getenv("GITHUB_REPO", "coral-signal-seed")

PACKAGE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")
ECOSYSTEM_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")
GITHUB_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")


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
    """Resolve which LLM backend to use."""
    explicit = LLM_PROVIDER.strip().lower()
    if explicit in ("euri", "cursor"):
        return explicit
    if EURI_API_KEY:
        return "euri"
    return "cursor"
