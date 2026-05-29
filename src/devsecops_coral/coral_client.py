"""Coral CLI integration — the only module that executes Coral commands."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import time
from typing import Any

from devsecops_coral.config import CORAL_BIN, QUERY_CACHE_TTL

_SINCE_PATTERN = re.compile(r"^(\d+)([hdwm])$", re.IGNORECASE)

_SINCE_UNITS = {
    "h": "hours",
    "d": "days",
    "w": "weeks",
    "m": "months",
}


class CoralError(Exception):
    """Raised when a Coral command fails."""


def parse_since(since: str) -> str:
    """Convert a duration like ``7d`` or ``24h`` to a SQL interval literal."""
    match = _SINCE_PATTERN.match(since.strip())
    if not match:
        msg = f"Invalid duration: {since!r}. Use format like 7d, 24h, 2w."
        raise ValueError(msg)
    amount, unit = match.group(1), match.group(2).lower()
    return f"INTERVAL '{amount}' {_SINCE_UNITS[unit]}"


def _coral_command() -> list[str]:
    """Resolve the Coral binary command."""
    return shlex.split(CORAL_BIN)


def _command_env(env: dict[str, str] | None = None) -> dict[str, str]:
    """Return a process environment with optional source credentials."""
    merged = os.environ.copy()
    if env:
        merged.update({key: value for key, value in env.items() if value})
    return merged


def _run_coral_command(
    args: list[str],
    *,
    timeout: float,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run Coral and normalize common execution errors."""
    cmd = _coral_command() + args
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=_command_env(env),
        )
    except FileNotFoundError as exc:
        raise CoralError(
            "Coral CLI not found. Install from "
            "https://withcoral.com/docs/getting-started/installation "
            "or set CORAL_BIN to the binary path."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise CoralError(f"Coral command timed out after {timeout}s") from exc


# SQL string -> (cached_at_monotonic, rows). Shared across all read queries so
# the Actions/recommend path reuses scan/correlate reads from the Detect tab.
_QUERY_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}


def clear_query_cache() -> None:
    """Drop all cached query results. Called on explicit refresh to force re-reads."""
    _QUERY_CACHE.clear()


# WSL prints these to stderr even on success; they are not Coral errors.
_WSL_NOISE = (
    "Failed to start the systemd user session",
    "See journalctl",
)


def _clean_coral_stderr(text: str) -> str:
    """Strip non-actionable WSL warnings from Coral stderr for clearer errors."""
    lines = [ln for ln in text.splitlines() if not any(n in ln for n in _WSL_NOISE)]
    return "\n".join(lines).strip()


def split_sql_statements(sql: str) -> list[str]:
    """Split SQL into individual runnable statements on top-level semicolons.

    Coral executes a single statement per call, so multi-statement input (for
    example the per-package scan SQL joined with ``;``) must be split before
    execution. Semicolons inside single-quoted string literals are ignored, and
    empty or comment-only fragments are dropped.
    """
    statements: list[str] = []
    buf: list[str] = []
    in_str = False
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if ch == "'":
            buf.append(ch)
            if in_str and i + 1 < n and sql[i + 1] == "'":  # escaped '' inside a literal
                buf.append(sql[i + 1])
                i += 2
                continue
            in_str = not in_str
            i += 1
            continue
        if ch == ";" and not in_str:
            stmt = "".join(buf).strip()
            if _has_executable_sql(stmt):
                statements.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if _has_executable_sql(tail):
        statements.append(tail)
    return statements


def _has_executable_sql(stmt: str) -> bool:
    """Return ``True`` when a fragment has SQL beyond whitespace and comments."""
    return any(
        line.strip() and not line.strip().startswith("--") for line in stmt.splitlines()
    )


def _execute_query_uncached(sql: str, *, timeout: float) -> list[dict[str, Any]]:
    """Run a SQL query via ``coral sql --format json`` and return row dicts."""
    result = _run_coral_command(["sql", "--format", "json", sql], timeout=timeout)

    if result.returncode != 0:
        stderr = _clean_coral_stderr((result.stderr or result.stdout or "").strip())
        raise CoralError(stderr or "Coral query failed with no error message")

    stdout = result.stdout.strip()
    if not stdout:
        return []

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise CoralError(f"Failed to parse Coral JSON output: {stdout[:200]}") from exc

    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "rows" in data:
        rows = data["rows"]
        return rows if isinstance(rows, list) else []
    if isinstance(data, dict) and "data" in data:
        rows = data["data"]
        return rows if isinstance(rows, list) else []
    return [data] if isinstance(data, dict) else []


def execute_query(
    sql: str,
    *,
    timeout: float = 120.0,
    use_cache: bool = True,
) -> list[dict[str, Any]]:
    """Run a SQL query, reusing a recent identical result within ``QUERY_CACHE_TTL``.

    Args:
        sql: The Coral SQL to execute.
        timeout: Per-command timeout in seconds.
        use_cache: When ``True`` (default), serve a cached result for identical SQL
            executed within the TTL window and store fresh results in the cache.

    Returns:
        A list of row dicts. Cache hits return a shallow copy so callers may safely
        mutate the returned list without corrupting the cache.
    """
    # Coral accepts one statement and rejects a trailing ';'. Normalize it away.
    sql = sql.strip()
    while sql.endswith(";"):
        sql = sql[:-1].rstrip()

    cacheable = use_cache and QUERY_CACHE_TTL > 0
    key = sql

    if cacheable:
        hit = _QUERY_CACHE.get(key)
        if hit is not None and (time.monotonic() - hit[0]) < QUERY_CACHE_TTL:
            return list(hit[1])

    rows = _execute_query_uncached(sql, timeout=timeout)

    if cacheable:
        _QUERY_CACHE[key] = (time.monotonic(), rows)
        return list(rows)
    return rows


def list_sources() -> list[dict[str, Any]]:
    """Return configured Coral sources via ``coral source list --format json``."""
    try:
        result = _run_coral_command(["source", "list", "--format", "json"], timeout=30.0)
    except CoralError as exc:
        raise CoralError("Coral CLI not found.") from exc

    if result.returncode != 0:
        # Fallback: plain text list
        plain = _run_coral_command(["source", "list"], timeout=30.0)
        if plain.returncode != 0:
            raise CoralError((plain.stderr or plain.stdout or "").strip())
        lines = [ln.strip() for ln in plain.stdout.splitlines() if ln.strip()]
        return [
            {"name": ln.split()[0], "status": "unknown"} for ln in lines if not ln.startswith("-")
        ]

    stdout = result.stdout.strip()
    if not stdout:
        return []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return []

    if isinstance(data, list):
        return data
    return []


def _inject_env_into_wsl(cmd: list[str], env: dict[str, str]) -> list[str]:
    """Prepend ``env KEY=VALUE …`` into a WSL command after the ``--`` separator.

    WSL does not forward arbitrary Windows subprocess environment variables into
    the Linux process, so credentials must be injected inline using the ``env``
    utility rather than relying on ``subprocess.run(env=...)``.
    """
    env_args = [f"{k}={v}" for k, v in env.items() if v]
    if not env_args:
        return cmd
    if "--" in cmd:
        idx = cmd.index("--") + 1
        return cmd[:idx] + ["env"] + env_args + cmd[idx:]
    return cmd


def add_bundled_source(
    name: str,
    *,
    interactive: bool = True,
    env: dict[str, str] | None = None,
) -> str:
    """Add a bundled Coral source, injecting credentials inline for WSL compatibility."""
    cmd = _coral_command()
    if env and "wsl" in CORAL_BIN.lower():
        cmd = _inject_env_into_wsl(cmd, env)
    cmd += ["source", "add"]
    if interactive:
        cmd.append("--interactive")
    cmd.append(name)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300.0,
        env=_command_env(env),  # still passed for non-WSL systems
    )
    if result.returncode != 0:
        raise CoralError((result.stderr or result.stdout or "").strip())
    return (result.stdout or "").strip()


def add_custom_source(
    spec_path: str,
    *,
    interactive: bool = False,
    env: dict[str, str] | None = None,
) -> str:
    """Add a custom Coral source from a YAML spec file."""
    cmd = _coral_command() + ["source", "add", "--file", spec_path]
    if interactive:
        cmd.insert(-2, "--interactive")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120.0,
        env=_command_env(env),
    )
    if result.returncode != 0:
        raise CoralError((result.stderr or result.stdout or "").strip())
    return (result.stdout or "").strip()


def test_source(name: str) -> str:
    """Run Coral's built-in source validation."""
    result = _run_coral_command(["source", "test", name], timeout=120.0)
    if result.returncode != 0:
        raise CoralError((result.stderr or result.stdout or "").strip())
    return (result.stdout or "").strip() or f"Source '{name}' validated successfully."


def remove_source(name: str) -> str:
    """Remove an installed Coral source."""
    result = _run_coral_command(["source", "remove", name], timeout=120.0)
    if result.returncode != 0:
        raise CoralError((result.stderr or result.stdout or "").strip())
    return (result.stdout or "").strip() or f"Source '{name}' removed."


EXPECTED_SOURCES = ("osv", "github", "jira", "sentry", "grafana")

SOURCES_METADATA_SQL = """
SELECT schema_name, COUNT(*) AS table_count
FROM coral.tables
WHERE schema_name IN ('osv', 'github', 'jira', 'sentry', 'grafana')
GROUP BY schema_name
ORDER BY schema_name
"""


def get_sources_metadata() -> tuple[list[dict[str, Any]], str]:
    """Return table counts per schema and the metadata SQL query."""
    try:
        rows = execute_query(SOURCES_METADATA_SQL.strip())
    except CoralError:
        rows = []

    table_counts = {
        str(row.get("schema_name", "")).lower(): int(row.get("table_count") or 0) for row in rows
    }

    configured: set[str] = set()
    try:
        for src in list_sources():
            name = str(src.get("name") or src.get("source") or "").lower()
            if name:
                configured.add(name.split(".")[0])
    except CoralError:
        pass

    metadata: list[dict[str, Any]] = []
    for name in EXPECTED_SOURCES:
        metadata.append(
            {
                "name": name,
                "connected": name in configured or name in table_counts,
                "table_count": table_counts.get(name, 0),
                "mode": "cli",
            }
        )
    return metadata, SOURCES_METADATA_SQL.strip()
