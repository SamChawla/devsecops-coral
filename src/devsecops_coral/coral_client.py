"""Coral CLI integration — the only module that executes Coral commands."""

from __future__ import annotations

import json
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


def execute_query(sql: str, *, timeout: float = 120.0) -> list[dict[str, Any]]:
    """Run a SQL query via ``coral sql --format json`` and return row dicts."""
    cmd = _coral_command() + ["sql", "--format", "json", sql]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise CoralError(
            "Coral CLI not found. Install from https://withcoral.com/docs/getting-started/installation "
            "or set CORAL_BIN to the binary path."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise CoralError(f"Query timed out after {timeout}s") from exc

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
    cmd = _coral_command() + ["source", "list", "--format", "json"]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30.0,
            check=False,
        )
    except FileNotFoundError as exc:
        raise CoralError("Coral CLI not found.") from exc

    if result.returncode != 0:
        # Fallback: plain text list
        cmd_plain = _coral_command() + ["source", "list"]
        plain = subprocess.run(cmd_plain, capture_output=True, text=True, timeout=30.0)
        if plain.returncode != 0:
            raise CoralError((plain.stderr or plain.stdout or "").strip())
        lines = [ln.strip() for ln in plain.stdout.splitlines() if ln.strip()]
        return [{"name": ln.split()[0], "status": "unknown"} for ln in lines if not ln.startswith("-")]

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


def add_bundled_source(name: str, *, interactive: bool = True) -> None:
    """Add a bundled Coral source."""
    cmd = _coral_command() + ["source", "add"]
    if interactive:
        cmd.append("--interactive")
    cmd.append(name)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300.0)
    if result.returncode != 0:
        raise CoralError((result.stderr or result.stdout or "").strip())


def add_custom_source(spec_path: str) -> None:
    """Add a custom Coral source from a YAML spec file."""
    cmd = _coral_command() + ["source", "add", "--file", spec_path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120.0)
    if result.returncode != 0:
        raise CoralError((result.stderr or result.stdout or "").strip())
