"""Tests for the LLM-backed agent."""

import json

import pytest

from devsecops_coral.agent import (
    AgentError,
    _parse_sql_response,
    _unwrap_json_analysis,
    _validate_sql,
    format_sql,
    generate_sql,
)


def test_parse_sql_response_json() -> None:
    """Agent parser extracts SQL and reasoning from JSON LLM output."""
    content = json.dumps({"sql": "SELECT 1", "reasoning": "test"})
    sql, reasoning = _parse_sql_response(content)
    assert sql == "SELECT 1"
    assert reasoning == "test"


def test_parse_sql_response_sql_block() -> None:
    """Agent parser extracts SQL from fenced code blocks."""
    content = (
        "Here is the query:\n```sql\nSELECT id FROM osv.vulnerability_detail WHERE id = 'x'\n```"
    )
    sql, _ = _parse_sql_response(content)
    assert "SELECT id FROM osv" in sql


def test_validate_sql_rejects_insert() -> None:
    """Agent SQL validator rejects non-SELECT statements."""
    with pytest.raises(AgentError):
        _validate_sql("INSERT INTO t VALUES (1)")


def test_unwrap_json_analysis_passes_through_prose() -> None:
    """Markdown prose analysis is returned unchanged."""
    text = "**Critical:** django has an active exploit.\n\n- 12 Sentry errors"
    assert _unwrap_json_analysis(text) == text


def test_unwrap_json_analysis_extracts_field_from_json() -> None:
    """A JSON blob is unwrapped to its human-readable field instead of raw JSON."""
    content = json.dumps({"sql": "SELECT title FROM sentry.issues", "reasoning": "Check Sentry."})
    assert _unwrap_json_analysis(content) == "Check Sentry."


def test_format_sql_breaks_clauses_onto_lines() -> None:
    """A single-line query is split onto clause-aligned lines."""
    sql = "SELECT id, summary FROM osv.search_vulnerabilities(package => 'django') LIMIT 10"
    formatted = format_sql(sql)
    lines = formatted.split("\n")
    assert lines[0] == "SELECT id, summary"
    assert lines[1].startswith("FROM osv.search_vulnerabilities")
    assert lines[2] == "LIMIT 10"


def test_format_sql_preserves_string_literals() -> None:
    """Keywords inside quoted literals are never split onto new lines."""
    sql = "SELECT id FROM jira.issues WHERE summary LIKE '%upgrade and patch%'"
    formatted = format_sql(sql)
    assert "'%upgrade and patch%'" in formatted
    # the literal's internal 'and' must not have been turned into a newline
    assert "upgrade\n" not in formatted


def test_format_sql_leaves_multiline_untouched() -> None:
    """Already-formatted multi-line SQL is returned unchanged."""
    sql = "SELECT id\nFROM osv.search_vulnerabilities(package => 'django')"
    assert format_sql(sql) == sql


def test_generate_sql_requires_llm_config(monkeypatch) -> None:
    """generate_sql raises when no LLM provider is configured."""
    monkeypatch.delenv("EURI_API_KEY", raising=False)
    import devsecops_coral.config as cfg
    import devsecops_coral.llm_client as llm

    monkeypatch.setattr(cfg, "EURI_API_KEY", "")
    monkeypatch.setattr(cfg, "LLM_PROVIDER", "euri")
    # llm_client binds these at import time, so patch its references too
    monkeypatch.setattr(llm, "EURI_API_KEY", "")
    with pytest.raises(AgentError, match="EURI_API_KEY|No LLM configured"):
        generate_sql("List critical CVEs")
