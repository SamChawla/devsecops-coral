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


# ---------------------------------------------------------------------------
# Atlassian Document Format (ADF) builders for rich descriptions
# ---------------------------------------------------------------------------


def _text(value: str) -> dict[str, Any]:
    """Return an ADF text node."""
    return {"type": "text", "text": value}


def _bold(value: str) -> dict[str, Any]:
    """Return a bold ADF text node."""
    return {"type": "text", "text": value, "marks": [{"type": "strong"}]}


def _link(value: str, href: str) -> dict[str, Any]:
    """Return an ADF text node rendered as a hyperlink."""
    return {"type": "text", "text": value, "marks": [{"type": "link", "attrs": {"href": href}}]}


def _paragraph(*nodes: dict[str, Any]) -> dict[str, Any]:
    """Wrap inline nodes in an ADF paragraph."""
    return {"type": "paragraph", "content": list(nodes)}


def _heading(value: str, level: int = 3) -> dict[str, Any]:
    """Return an ADF heading node."""
    return {"type": "heading", "attrs": {"level": level}, "content": [_text(value)]}


def _bullet_list(items: list[list[dict[str, Any]]]) -> dict[str, Any]:
    """Build an ADF bullet list from a list of inline-node groups."""
    return {
        "type": "bulletList",
        "content": [{"type": "listItem", "content": [_paragraph(*nodes)]} for nodes in items],
    }


def vulnerability_references(cve: str | None) -> list[tuple[str, str]]:
    """Return ``(label, url)`` reference links for a CVE/advisory identifier.

    Args:
        cve: An OSV/GHSA/CVE identifier (e.g. ``GHSA-xxxx`` or ``CVE-2024-1234``).

    Returns:
        Ordered list of reference links to authoritative advisory pages.
    """
    if not cve:
        return []
    refs: list[tuple[str, str]] = [("OSV Advisory", f"https://osv.dev/vulnerability/{cve}")]
    upper = cve.upper()
    if upper.startswith("GHSA"):
        refs.append(("GitHub Advisory", f"https://github.com/advisories/{cve}"))
    elif upper.startswith("CVE"):
        refs.append(("NVD Detail", f"https://nvd.nist.gov/vuln/detail/{cve}"))
    return refs


def build_description(
    *,
    rationale: str,
    cve: str | None,
    package: str | None,
    severity: str | None,
    urgent: bool,
) -> dict[str, Any]:
    """Build a structured ADF description that reads like a real security ticket.

    Args:
        rationale: Human-readable explanation of why the ticket was filed.
        cve: Vulnerability identifier, used for the details table and references.
        package: Affected package name.
        severity: Severity label (CRITICAL/HIGH/MEDIUM/LOW).
        urgent: Whether active exploitation was detected.

    Returns:
        An ADF ``doc`` node ready for the Jira v3 ``description`` field.
    """
    content: list[dict[str, Any]] = [_paragraph(_text(rationale))]

    details: list[list[dict[str, Any]]] = []
    if package:
        details.append([_bold("Package: "), _text(package)])
    if cve:
        details.append([_bold("Vulnerability: "), _text(cve)])
    if severity:
        details.append([_bold("Severity: "), _text(severity.upper())])
    details.append(
        [
            _bold("Exploitation: "),
            _text("Active — error spike correlated" if urgent else "No active signal detected"),
        ]
    )
    content.append(_heading("Vulnerability details"))
    content.append(_bullet_list(details))

    refs = vulnerability_references(cve)
    if refs:
        content.append(_heading("References"))
        content.append(
            _bullet_list([[_text(f"{label}: "), _link(href, href)] for label, href in refs])
        )

    content.append(_heading("Recommended action"))
    fix_target = package or "the affected dependency"
    content.append(
        _paragraph(
            _text(
                f"Upgrade {fix_target} to the latest patched release and verify the fix against "
                f"the advisories above. Link any remediation PR to this ticket."
            )
        )
    )

    content.append(
        _paragraph(
            {
                "type": "text",
                "text": "Filed automatically by the devsecops-coral agent after human approval.",
                "marks": [{"type": "em"}],
            }
        )
    )

    return {"type": "doc", "version": 1, "content": content}


def _post_issue(url: str, headers: dict[str, str], fields: dict[str, Any]) -> httpx.Response:
    """POST an issue payload to Jira, normalising transport errors."""
    try:
        return httpx.post(url, headers=headers, json={"fields": fields}, timeout=30.0)
    except httpx.HTTPError as exc:
        raise JiraError(f"Jira request failed: {exc}") from exc


def create_issue(
    *,
    summary: str,
    description: str,
    priority: str = "High",
    labels: list[str] | None = None,
    cve: str | None = None,
    package: str | None = None,
    severity: str | None = None,
    urgent: bool = False,
) -> dict[str, Any]:
    """Create a Jira issue in the configured security project.

    The ``description`` text is used as the lead rationale paragraph and is
    enriched with a vulnerability-details list, advisory reference links, and a
    recommended-action section so the ticket reads like a real security report.

    Args:
        summary: Issue title shown in the backlog.
        description: Lead rationale explaining why the ticket exists.
        priority: Jira priority name (``Highest``, ``High``, ``Medium``, ``Low``,
            ``Lowest``). Dropped automatically if the instance rejects it.
        labels: Additional labels to apply (``security`` is always added).
        cve: Vulnerability identifier used for references and labels.
        package: Affected package name.
        severity: Severity label, added as a label and to the details list.
        urgent: Whether active exploitation was detected.

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

    extra_labels = {"security"}
    if severity:
        extra_labels.add(severity.lower())
    if package:
        extra_labels.add(package.replace(" ", "-"))
    if urgent:
        extra_labels.add("active-exploitation")

    fields: dict[str, Any] = {
        "project": {"key": JIRA_PROJECT_KEY},
        "summary": summary,
        "issuetype": {"name": "Bug"},
        "priority": {"name": priority},
        "labels": sorted({*(labels or []), *extra_labels}),
        "description": build_description(
            rationale=description,
            cve=cve,
            package=package,
            severity=severity,
            urgent=urgent,
        ),
    }

    response = _post_issue(url, headers, fields)

    # Some Jira instances use a custom priority scheme that rejects standard
    # names. Rather than fail the action, drop the priority and retry so the
    # ticket is still created with the project's default priority.
    if response.status_code >= 400 and "priority" in response.text.lower():
        fields.pop("priority", None)
        response = _post_issue(url, headers, fields)

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
