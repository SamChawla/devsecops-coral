"""Jira REST API — create security tickets for untracked CVEs."""

from __future__ import annotations

import base64
from typing import Any

import httpx

from devsecops_coral.config import (
    JIRA_API_TOKEN,
    JIRA_BASE_URL,
    JIRA_EMAIL,
    JIRA_PROJECT_KEY,
)


class JiraError(Exception):
    """Raised when a Jira API call fails."""


def _auth_header() -> str:
    """Build Basic auth header for Jira Cloud API."""
    return "Basic " + base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()


def _adf_body(text: str) -> dict[str, Any]:
    """Wrap plain text in Atlassian Document Format (ADF) for Jira v3 API."""
    return {
        "type": "doc",
        "version": 1,
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
    }


def create_issue(
    *,
    summary: str,
    description: str,
    priority: str = "High",
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """Create a Jira issue in the configured security project.

    Args:
        summary: Issue title shown in the backlog.
        description: Body text explaining the CVE and recommended fix.
        priority: Jira priority name (``Critical``, ``High``, ``Medium``, ``Low``).
        labels: Additional labels to apply (``security`` and ``cve`` are always added).

    Returns:
        Dict with keys ``key`` (e.g. ``SEC-9``), ``id``, and ``url``.

    Raises:
        JiraError: If credentials are missing or the API returns an error.
    """
    if not JIRA_BASE_URL:
        raise JiraError("JIRA_BASE_URL is not set in .env")
    if not JIRA_EMAIL or not JIRA_API_TOKEN:
        raise JiraError("JIRA_EMAIL and JIRA_API_TOKEN must both be set in .env")

    url = f"{JIRA_BASE_URL.rstrip('/')}/rest/api/3/issue"
    headers = {
        "Authorization": _auth_header(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload: dict[str, Any] = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": summary,
            "issuetype": {"name": "Bug"},
            "priority": {"name": priority},
            "labels": list({*(labels or []), "security", "cve"}),
            "description": _adf_body(description),
        }
    }

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
    except httpx.HTTPError as exc:
        raise JiraError(f"Jira request failed: {exc}") from exc

    if response.status_code == 401:
        raise JiraError("Jira authentication failed — check JIRA_EMAIL and JIRA_API_TOKEN.")
    if response.status_code >= 400:
        raise JiraError(f"Jira API error ({response.status_code}): {response.text[:300]}")

    data = response.json()
    key = data.get("key", "UNKNOWN")
    return {
        "key": key,
        "id": data.get("id", ""),
        "url": f"{JIRA_BASE_URL.rstrip('/')}/browse/{key}",
    }
