"""Tests for the LLM-backed agent."""

import json

import pytest

from devsecops_coral.agent import AgentError, _parse_sql_response, _validate_sql, generate_sql


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


def test_generate_sql_requires_llm_config(monkeypatch) -> None:
    """generate_sql raises when no LLM provider is configured."""
    monkeypatch.delenv("EURI_API_KEY", raising=False)
    import devsecops_coral.config as cfg

    monkeypatch.setattr(cfg, "EURI_API_KEY", "")
    monkeypatch.setattr(cfg, "LLM_PROVIDER", "euri")
    with pytest.raises(AgentError, match="EURI_API_KEY|No LLM configured"):
        generate_sql("List critical CVEs")
