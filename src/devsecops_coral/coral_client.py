"""Coral CLI integration — the only module that executes Coral commands."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from typing import Any

from devsecops_coral.config import CORAL_BIN

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


def execute_query(sql: str, *, timeout: float = 120.0) -> list[dict[str, Any]]:
    """Run a SQL query via ``coral sql --format json`` and return row dicts."""
    result = _run_coral_command(["sql", "--format", "json", sql], timeout=timeout)

    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
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
