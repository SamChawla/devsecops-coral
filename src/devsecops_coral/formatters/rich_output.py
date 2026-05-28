"""Rich terminal output formatters."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from devsecops_coral.config import SEVERITY_COLORS, SIGNAL_ICONS
from devsecops_coral.queries.correlate import classify_signal

console = Console()


def _severity_style(severity: str | None) -> str:
    """Return Rich markup style for a severity label."""
    if not severity:
        return "dim"
    return SEVERITY_COLORS.get(str(severity).upper(), "white")


def _status_for_scan(row: dict[str, Any]) -> str:
    """Return Rich markup for scan row tracking status (clean, tracked, or untracked)."""
    if not row.get("cve"):
        return "[green]✅ Clean[/green]"
    ticket = row.get("jira_ticket")
    if ticket:
        status = row.get("jira_status") or "Tracked"
        return f"[blue]{status}[/blue]"
    return "[bold yellow]⚠ UNTRACKED[/bold yellow]"


def print_scan(rows: list[dict[str, Any]]) -> None:
    """Render security posture scan results."""
    console.print("\n[bold]🔍 Security Posture Scan[/bold]")
    console.print("━" * 49)

    table = Table(show_header=True, header_style="bold")
    table.add_column("Package")
    table.add_column("CVE")
    table.add_column("Severity")
    table.add_column("Jira Ticket")
    table.add_column("Status")

    seen_clean: set[str] = set()
    critical = high = untracked = 0

    for row in rows:
        pkg = str(row.get("package") or "—")
        cve = str(row.get("cve") or "—")
        severity = str(row.get("severity") or "—")
        ticket = str(row.get("jira_ticket") or "—")
        status = _status_for_scan(row)

        if cve == "—":
            if pkg in seen_clean:
                continue
            seen_clean.add(pkg)
        else:
            sev_upper = severity.upper()
            if sev_upper == "CRITICAL":
                critical += 1
            elif sev_upper == "HIGH":
                high += 1
            if ticket == "—":
                untracked += 1

        table.add_row(
            pkg,
            cve,
            f"[{_severity_style(severity)}]{severity}[/]",
            ticket,
            status,
        )

    console.print(table)

    if critical or high:
        console.print(f"\n[yellow]⚠ {critical} CRITICAL, {high} HIGH vulnerability found[/yellow]")
    if untracked:
        console.print(
            f"[bold yellow]⚠ {untracked} vulnerability has NO tracking ticket[/bold yellow]"
        )
    if not any(r.get("cve") for r in rows):
        console.print("\n[green]✅ No known vulnerabilities found for scanned packages[/green]")


def print_correlate(rows: list[dict[str, Any]], *, since: str) -> None:
    """Render vulnerability-error correlation results."""
    console.print(f"\n[bold]🔗 Vulnerability ↔ Error Correlation (Last {since})[/bold]")
    console.print("━" * 49)

    table = Table(show_header=True, header_style="bold")
    table.add_column("CVE")
    table.add_column("Package")
    table.add_column("Severity")
    table.add_column("Errors")
    table.add_column("Level")
    table.add_column("Signal")

    active_count = 0
    for row in rows:
        signal = row.get("signal") or classify_signal(row)
        if signal == "active":
            active_count += 1
        icon = SIGNAL_ICONS.get(str(signal), SIGNAL_ICONS["unknown"])
        severity = str(row.get("severity") or "—")
        table.add_row(
            str(row.get("cve") or "—"),
            str(row.get("package") or "—"),
            f"[{_severity_style(severity)}]{severity}[/]",
            str(row.get("error_count") or "0"),
            str(row.get("error_level") or "—"),
            f"{icon} {str(signal).upper()}",
        )

    console.print(table)

    if active_count:
        console.print(
            f"\n[bold red]🔴 {active_count} potential active exploitation detected[/bold red]"
        )
        console.print("[dim]Recommended: investigate matching Jira tickets immediately[/dim]")
    elif rows:
        console.print("\n[green]🟢 No active exploitation signals detected[/green]")


def print_timeline(rows: list[dict[str, Any]], *, since: str) -> None:
    """Render unified security event timeline."""
    console.print(f"\n[bold]📅 Security Event Timeline (Last {since})[/bold]")
    console.print("━" * 49)

    if not rows:
        console.print("[dim]No events found in this time window.[/dim]")
        return

    source_icons = {
        "github": "🟢",
        "sentry": "🟡",
        "jira": "🔵",
        "grafana": "🟣",
        "osv": "🔴",
    }

    for row in rows:
        ts = str(row.get("event_time") or "—")[:16]
        source = str(row.get("source") or "unknown")
        icon = source_icons.get(source, "⚪")
        title = str(row.get("title") or "—")
        detail = str(row.get("detail") or "")
        line = f" {ts} │ {icon} {source:<8} │ {title}"
        if detail:
            line += f" ({detail})"
        console.print(line)


def print_ask_result(*, question: str, sql: str, analysis: str, rows: list[dict[str, Any]]) -> None:
    """Render natural language query results."""
    console.print(Panel(question, title="Question", border_style="cyan"))
    console.print(Panel(analysis, title="Analysis", border_style="green"))

    if rows:
        table = Table(show_header=True, header_style="bold")
        columns = list(rows[0].keys()) if rows else []
        for col in columns[:8]:
            table.add_column(str(col))
        for row in rows[:20]:
            table.add_row(*[str(row.get(c, ""))[:80] for c in columns[:8]])
        console.print(table)
        if len(rows) > 20:
            console.print(f"[dim]… and {len(rows) - 20} more rows[/dim]")
    else:
        console.print("[dim]Query returned no rows.[/dim]")
