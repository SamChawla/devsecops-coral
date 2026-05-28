"""Typer CLI for devsecops-coral."""

from __future__ import annotations

import sys
from enum import Enum
from typing import Annotated, NoReturn

import typer
from rich.console import Console

from devsecops_coral import __version__
from devsecops_coral.actions.executor import (
    ActionError,
    approve_action,
    approve_all,
    dismiss_action,
    load_actions,
)
from devsecops_coral.agent import AgentError
from devsecops_coral.agent import ask as run_agent_ask
from devsecops_coral.config import parse_packages
from devsecops_coral.coral_client import (
    CoralError,
    add_bundled_source,
    add_custom_source,
    list_sources,
)
from devsecops_coral.formatters import (
    ask_markdown,
    correlate_markdown,
    scan_markdown,
    timeline_markdown,
    to_json,
)
from devsecops_coral.formatters.rich_output import (
    print_ask_result,
    print_correlate,
    print_recommendations,
    print_scan,
    print_timeline,
)
from devsecops_coral.integrations import get_integration, list_integrations
from devsecops_coral.llm_client import active_provider_info, check_cursor_proxy
from devsecops_coral.queries import run_correlate, run_scan, run_timeline
from devsecops_coral.recommender import run_recommend

app = typer.Typer(
    name="devsecops-coral",
    help="Cross-stack security correlation powered by Coral SQL.",
    no_args_is_help=True,
    invoke_without_command=True,
)
integrations_app = typer.Typer(help="Manage Coral data source integrations.")
llm_app = typer.Typer(help="LLM provider settings (EURI or Cursor subscription).")
app.add_typer(integrations_app, name="integrations")
app.add_typer(llm_app, name="llm")

console = Console()
err_console = Console(stderr=True)


class OutputFormat(str, Enum):
    """CLI output format."""

    rich = "rich"
    json = "json"
    md = "md"


def _handle_error(exc: Exception, *, debug: bool) -> NoReturn:
    """Print a user-facing error and exit with code 1."""
    if debug:
        console.print_exception()
    else:
        err_console.print(f"[red]Error:[/red] {exc}")
    raise typer.Exit(code=1) from exc


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", "-V", help="Show version and exit."),
    ] = False,
) -> None:
    """devsecops-coral entrypoint."""
    if version:
        console.print(f"devsecops-coral {__version__}")
        raise typer.Exit()


@app.command()
def scan(
    ecosystem: Annotated[str, typer.Option(help="Package ecosystem, e.g. PyPI, npm")] = "PyPI",
    packages: Annotated[
        str, typer.Option(help="Comma-separated package names")
    ] = "django,flask,requests",
    fmt: Annotated[
        OutputFormat, typer.Option("--format", help="Output format")
    ] = OutputFormat.rich,
    debug: Annotated[bool, typer.Option("--debug", help="Show tracebacks and raw errors")] = False,
) -> None:
    """Run a security posture scan across OSV and Jira."""
    try:
        pkg_list = parse_packages(packages)
        result = run_scan(ecosystem=ecosystem, packages=pkg_list)
        rows = result.data
    except (CoralError, ValueError) as exc:
        _handle_error(exc, debug=debug)

    if debug:
        console.print(f"[dim]SQL:[/dim]\n{result.sql}\n")

    if fmt == OutputFormat.json:
        sys.stdout.write(
            to_json({"command": "scan", "ecosystem": ecosystem, "rows": rows, "sql": result.sql})
        )
        return
    if fmt == OutputFormat.md:
        sys.stdout.write(scan_markdown(rows))
        return
    print_scan(rows)


@app.command()
def correlate(
    ecosystem: Annotated[str, typer.Option(help="Package ecosystem")] = "PyPI",
    packages: Annotated[
        str, typer.Option(help="Comma-separated package names")
    ] = "django,flask,requests",
    since: Annotated[str, typer.Option(help="Time window, e.g. 7d, 24h")] = "7d",
    fmt: Annotated[
        OutputFormat, typer.Option("--format", help="Output format")
    ] = OutputFormat.rich,
    debug: Annotated[bool, typer.Option("--debug")] = False,
) -> None:
    """Correlate vulnerabilities with Sentry error spikes."""
    try:
        pkg_list = parse_packages(packages)
        result = run_correlate(ecosystem=ecosystem, packages=pkg_list, since=since)
        rows = result.data
    except (CoralError, ValueError) as exc:
        _handle_error(exc, debug=debug)

    if debug:
        console.print(f"[dim]SQL:[/dim]\n{result.sql}\n")

    if fmt == OutputFormat.json:
        sys.stdout.write(
            to_json({"command": "correlate", "since": since, "rows": rows, "sql": result.sql})
        )
        return
    if fmt == OutputFormat.md:
        sys.stdout.write(correlate_markdown(rows, since=since))
        return
    print_correlate(rows, since=since)


@app.command()
def timeline(
    since: Annotated[str, typer.Option(help="Time window, e.g. 24h, 7d")] = "24h",
    github_owner: Annotated[
        str | None,
        typer.Option("--github-owner", help="GitHub owner/org (or set GITHUB_OWNER)"),
    ] = None,
    github_repo: Annotated[
        str | None,
        typer.Option("--github-repo", help="GitHub repo name (or set GITHUB_REPO)"),
    ] = None,
    fmt: Annotated[
        OutputFormat, typer.Option("--format", help="Output format")
    ] = OutputFormat.rich,
    debug: Annotated[bool, typer.Option("--debug")] = False,
) -> None:
    """Build a unified security event timeline across sources."""
    try:
        result = run_timeline(since=since, owner=github_owner, repo=github_repo)
        rows = result.data
    except (CoralError, ValueError) as exc:
        _handle_error(exc, debug=debug)

    if debug:
        console.print(f"[dim]SQL:[/dim]\n{result.sql}\n")

    if fmt == OutputFormat.json:
        sys.stdout.write(
            to_json({"command": "timeline", "since": since, "rows": rows, "sql": result.sql})
        )
        return
    if fmt == OutputFormat.md:
        sys.stdout.write(timeline_markdown(rows, since=since))
        return
    print_timeline(rows, since=since)


@app.command("ask")
def ask_command(
    question: Annotated[str, typer.Argument(help="Natural language security question")],
    fmt: Annotated[
        OutputFormat, typer.Option("--format", help="Output format")
    ] = OutputFormat.rich,
    debug: Annotated[bool, typer.Option("--debug", help="Show SQL and tracebacks")] = False,
) -> None:
    """Ask a natural language question (translated to Coral SQL via EURI)."""
    try:
        result = run_agent_ask(question)
    except (AgentError, CoralError) as exc:
        _handle_error(exc, debug=debug)

    if debug:
        console.print(f"[dim]SQL:[/dim]\n{result['sql']}\n")

    if fmt == OutputFormat.json:
        sys.stdout.write(to_json(result))
        return
    if fmt == OutputFormat.md:
        sys.stdout.write(
            ask_markdown(
                question=result["question"],
                sql=result["sql"],
                analysis=result["analysis"],
                row_count=result["row_count"],
            )
        )
        return
    print_ask_result(
        question=result["question"],
        sql=result["sql"],
        analysis=result["analysis"],
        rows=result["rows"],
    )


@integrations_app.command("list")
def integrations_list() -> None:
    """List available and planned integrations."""
    console.print("\n[bold]Integration Catalog[/bold]\n")
    for item in list_integrations():
        kind_style = {"bundled": "green", "custom": "cyan", "planned": "dim"}.get(
            item.kind, "white"
        )
        spec = str(item.spec_path) if item.spec_path else "—"
        console.print(
            f"[{kind_style}]{item.kind:8}[/]  {item.name:<14}  {item.description}\n"
            f"           spec: {spec}"
        )


@integrations_app.command("add")
def integrations_add(
    name: Annotated[str, typer.Argument(help="Integration name, e.g. osv, github, jira")],
    file: Annotated[
        str | None,
        typer.Option("--file", help="Path to custom source YAML (overrides catalog spec)"),
    ] = None,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Add a Coral source integration."""
    try:
        integration = get_integration(name)
    except ValueError as exc:
        _handle_error(exc, debug=False)

    if integration.kind == "planned":
        err_console.print(
            f"[yellow]{name} is planned but not implemented yet.[/yellow]\n"
            "Add a source spec under sources/ and register with --file."
        )
        raise typer.Exit(code=1)

    if not yes:
        typer.confirm(f"Add integration '{name}' ({integration.description})?", abort=True)

    try:
        if integration.kind == "custom":
            spec = file or (str(integration.spec_path) if integration.spec_path else "")
            if not spec:
                raise CoralError("Custom integration requires --file or a catalog spec_path.")
            add_custom_source(spec)
        else:
            add_bundled_source(integration.name, interactive=True)
    except CoralError as exc:
        _handle_error(exc, debug=False)

    console.print(f"[green]✓[/green] Integration '{name}' added. Verify with: coral source list")


@llm_app.command("status")
def llm_status() -> None:
    """Show active LLM provider and probe Cursor proxy if configured."""
    info = active_provider_info()
    console.print("\n[bold]LLM Provider[/bold]\n")
    console.print(f"  Provider:  {info['provider']}")
    console.print(f"  Model:     {info['model']}")
    console.print(f"  Base URL:  {info['base_url']}")

    if info["provider"] == "cursor":
        console.print("\n[bold]Cursor Proxy Check[/bold]\n")
        probe = check_cursor_proxy()
        if probe.get("reachable"):
            console.print("[green]OK Proxy reachable[/green]")
            if probe.get("models"):
                console.print(f"  Models: {', '.join(probe['models'][:8])}")
        else:
            console.print("[yellow]X Proxy not reachable[/yellow]")
            console.print(
                "  Start a Cursor OpenAI proxy, then set LLM_PROVIDER=cursor:\n"
                "  npx cursor-agent-api-proxy   -> http://localhost:4646/v1\n"
                "  Docs: https://cursor.com/docs/account/pricing (API usage pool)"
            )
            if probe.get("error"):
                console.print(f"  Error: {probe['error']}")

    console.print("\n[dim]Usage dashboards:[/dim]")
    console.print("  Cursor: https://cursor.com/dashboard/usage")
    console.print("  EURI:   https://euron.one/euri")


@app.command("recommend")
def recommend(
    ecosystem: Annotated[str, typer.Option(help="Package ecosystem")] = "PyPI",
    packages: Annotated[
        str, typer.Option(help="Comma-separated package names")
    ] = "django,flask,requests,celery,pillow",
    since: Annotated[str, typer.Option(help="Time window for Sentry correlation")] = "7d",
    fmt: Annotated[
        OutputFormat, typer.Option("--format", help="Output format")
    ] = OutputFormat.rich,
    debug: Annotated[bool, typer.Option("--debug")] = False,
) -> None:
    """Analyze scan results and recommend remediation actions."""
    try:
        result = run_recommend(ecosystem=ecosystem, packages=packages, since=since)
    except (CoralError, ValueError) as exc:
        _handle_error(exc, debug=debug)

    if fmt == OutputFormat.json:
        sys.stdout.write(to_json({"actions": [a.model_dump() for a in result.actions]}))
        return

    print_recommendations(result.actions)


@app.command("act")
def act(
    approve: Annotated[int | None, typer.Option("--approve", help="Approve action by ID")] = None,
    approve_all_flag: Annotated[
        bool, typer.Option("--approve-all", help="Approve and execute all pending actions")
    ] = False,
    dismiss: Annotated[int | None, typer.Option("--dismiss", help="Dismiss action by ID")] = None,
    list_flag: Annotated[bool, typer.Option("--list", "-l", help="List pending actions")] = False,
    ecosystem: Annotated[str, typer.Option(help="Package ecosystem")] = "PyPI",
    packages: Annotated[
        str, typer.Option(help="Comma-separated package names")
    ] = "django,flask,requests,celery,pillow",
    since: Annotated[str, typer.Option(help="Time window for Sentry correlation")] = "7d",
    debug: Annotated[bool, typer.Option("--debug")] = False,
) -> None:
    """Approve or dismiss recommended remediation actions."""
    try:
        rec = run_recommend(ecosystem=ecosystem, packages=packages, since=since)
        load_actions(rec.actions)
    except (CoralError, ValueError) as exc:
        _handle_error(exc, debug=debug)

    if list_flag or (not approve and not approve_all_flag and not dismiss):
        print_recommendations(rec.actions)
        return

    if dismiss is not None:
        try:
            action = dismiss_action(dismiss)
            console.print(f"[dim]✗ Dismissed action {dismiss}: {action.title}[/dim]")
        except ActionError as exc:
            _handle_error(exc, debug=debug)
        return

    if approve is not None:
        try:
            action = approve_action(approve)
            _print_action_result(action)
        except ActionError as exc:
            _handle_error(exc, debug=debug)
        return

    if approve_all_flag:
        executed = approve_all()
        for action in executed:
            _print_action_result(action)
        done = sum(1 for a in executed if a.status.value == "done")
        failed = sum(1 for a in executed if a.status.value == "failed")
        console.print(f"\n[bold]{done} completed, {failed} failed[/bold]")


def _print_action_result(action) -> None:  # type: ignore[no-untyped-def]
    """Print a single action execution result line."""
    from devsecops_coral.models import ActionStatus

    if action.status == ActionStatus.DONE:
        result = action.result or {}
        detail = ""
        if "key" in result:
            detail = f" → {result['key']}"
        elif "url" in result:
            detail = f" → {result['url']}"
        elif "path" in result:
            detail = f" → {result['path']}"
        console.print(f"[green]✓[/green] {action.title}{detail}")
    elif action.status == ActionStatus.FAILED:
        error = (action.result or {}).get("error", "unknown error")
        console.print(f"[red]✗[/red] {action.title}: {error}")
    else:
        console.print(f"[dim]{action.status.value}: {action.title}[/dim]")


@app.command("serve")
def serve(
    host: Annotated[str, typer.Option(help="Bind host")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Bind port")] = 8000,
) -> None:
    """Launch the dashboard web server (FastAPI + built React frontend)."""
    from devsecops_coral.config import project_root

    dist = project_root() / "frontend" / "dist"
    if not dist.is_dir():
        console.print(
            "[yellow]Warning:[/yellow] frontend/dist not found. "
            "Run: cd frontend && npm install && npm run build"
        )

    import uvicorn

    console.print(f"[green]Starting devsecops-coral dashboard at http://{host}:{port}[/green]")
    uvicorn.run("devsecops_coral.api:app", host=host, port=port, reload=False)


@integrations_app.command("status")
def integrations_status() -> None:
    """Show connected Coral sources."""
    try:
        sources = list_sources()
    except CoralError as exc:
        _handle_error(exc, debug=False)

    if not sources:
        console.print("[dim]No sources configured. Run: devsecops-coral integrations add osv[/dim]")
        return

    console.print("\n[bold]Connected Sources[/bold]\n")
    for src in sources:
        name = src.get("name") or src.get("source") or str(src)
        status = src.get("status") or src.get("state") or "connected"
        console.print(f"  {name:<16} {status}")
