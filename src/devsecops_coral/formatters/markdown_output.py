"""Markdown report formatters."""

from __future__ import annotations

from typing import Any


def scan_markdown(rows: list[dict[str, Any]]) -> str:
    """Format scan results as Markdown."""
    lines = [
        "# Security Posture Scan",
        "",
        "| Package | CVE | Severity | Jira | Status |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        ticket = row.get("jira_ticket") or "—"
        status = (
            "Clean"
            if not row.get("cve")
            else ("Untracked" if not row.get("jira_ticket") else row.get("jira_status", "Tracked"))
        )
        lines.append(
            f"| {row.get('package', '—')} | {row.get('cve') or '—'} | {row.get('severity') or '—'} "
            f"| {ticket} | {status} |"
        )
    return "\n".join(lines) + "\n"


def correlate_markdown(rows: list[dict[str, Any]], *, since: str) -> str:
    """Format correlation results as Markdown."""
    lines = [
        f"# Vulnerability ↔ Error Correlation ({since})",
        "",
        "| CVE | Package | Severity | Errors | Signal |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.get('cve', '—')} | {row.get('package', '—')} | {row.get('severity', '—')} "
            f"| {row.get('error_count', 0)} | {row.get('signal', '—')} |"
        )
    return "\n".join(lines) + "\n"


def timeline_markdown(rows: list[dict[str, Any]], *, since: str) -> str:
    """Format timeline as Markdown."""
    lines = [f"# Security Event Timeline ({since})", ""]
    for row in rows:
        ts = str(row.get("event_time", ""))[:19]
        lines.append(f"- **{ts}** [{row.get('source')}] {row.get('title', '—')}")
    return "\n".join(lines) + "\n"


def ask_markdown(*, question: str, sql: str, analysis: str, row_count: int) -> str:
    """Format ask command output as Markdown."""
    return (
        f"# Security Query\n\n## Question\n\n{question}\n\n"
        f"## SQL\n\n```sql\n{sql}\n```\n\n"
        f"## Analysis\n\n{analysis}\n\n"
        f"*Returned {row_count} rows.*\n"
    )
