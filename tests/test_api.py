"""Tests for FastAPI endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from devsecops_coral.api import app
from devsecops_coral.models import PostureResponse, QueryResult

client = TestClient(app)

SCAN_ROWS = [{"package": "django", "cve": "GHSA-x", "severity": "CRITICAL", "jira_ticket": None}]
CORRELATE_ROWS = [{"cve": "GHSA-x", "error_count": 47, "severity": "CRITICAL", "signal": "active"}]
TIMELINE_ROWS = [{"event_time": "2026-05-26", "source": "github", "title": "PR merged"}]


@pytest.fixture(autouse=True)
def _mock_api_layer(mocker):
    """Mock query runners at the API import site."""
    mocker.patch(
        "devsecops_coral.api.run_scan",
        return_value=QueryResult(data=SCAN_ROWS, sql="SELECT scan"),
    )
    mocker.patch(
        "devsecops_coral.api.run_correlate",
        return_value=QueryResult(data=CORRELATE_ROWS, sql="SELECT correlate"),
    )
    mocker.patch(
        "devsecops_coral.api.run_timeline",
        return_value=QueryResult(data=TIMELINE_ROWS, sql="SELECT timeline"),
    )
    mocker.patch(
        "devsecops_coral.api.run_posture",
        return_value=PostureResponse(
            critical=1,
            high=0,
            medium=0,
            low=0,
            untracked=1,
            total=1,
            sql="SELECT scan",
            ecosystem="PyPI",
            packages=["django"],
        ),
    )
    mocker.patch(
        "devsecops_coral.api.get_sources_metadata",
        return_value=(
            [
                {"name": "osv", "connected": True, "table_count": 2, "mode": "cli"},
                {"name": "github", "connected": True, "table_count": 5, "mode": "cli"},
            ],
            "SELECT schema_name FROM coral.tables",
        ),
    )
    mocker.patch(
        "devsecops_coral.api.run_agent_ask",
        return_value={
            "question": "test",
            "sql": "SELECT 1",
            "analysis": "ok",
            "rows": [{"x": 1}],
            "row_count": 1,
        },
    )
    mocker.patch(
        "devsecops_coral.api.execute_query",
        return_value=[{"x": 1}],
    )
    mocker.patch("devsecops_coral.api.add_bundled_source", return_value="connected")
    mocker.patch("devsecops_coral.api.add_custom_source", return_value="connected")
    mocker.patch("devsecops_coral.api.test_source", return_value="ok")
    mocker.patch("devsecops_coral.api.remove_source", return_value="removed")


def test_api_scan_returns_data_and_sql() -> None:
    """GET /api/scan returns vulnerability rows and executed SQL."""
    resp = client.get("/api/scan?packages=django")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "sql" in body
    assert body["sql"] == "SELECT scan"
    assert len(body["data"]) == 1


def test_api_correlate_returns_data_and_sql() -> None:
    """GET /api/correlate returns correlation rows and executed SQL."""
    resp = client.get("/api/correlate?packages=django&since=7d")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sql"] == "SELECT correlate"
    assert body["data"][0]["signal"] == "active"


def test_api_timeline_returns_data_and_sql() -> None:
    """GET /api/timeline returns event rows and executed SQL."""
    resp = client.get("/api/timeline?since=24h")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sql"] == "SELECT timeline"
    assert body["since"] == "24h"


def test_api_ask_returns_data_and_sql() -> None:
    """POST /api/ask returns agent analysis, rows, and generated SQL."""
    resp = client.post("/api/ask", json={"query": "show critical vulns"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["sql"] == "SELECT 1"
    assert body["analysis"] == "ok"
    assert body["row_count"] == 1


def test_api_sql_rejects_non_select() -> None:
    """POST /api/sql rejects non-SELECT statements."""
    resp = client.post("/api/sql", json={"query": "DELETE FROM osv.vulnerabilities"})
    assert resp.status_code == 400


def test_api_sql_executes_select() -> None:
    """POST /api/sql executes valid SELECT queries."""
    resp = client.post("/api/sql", json={"query": "SELECT 1 AS x"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["sql"] == "SELECT 1 AS x"
    assert body["row_count"] == 1


def test_api_sources_returns_sql() -> None:
    """GET /api/sources returns source metadata and metadata SQL."""
    resp = client.get("/api/sources")
    assert resp.status_code == 200
    body = resp.json()
    assert "sql" in body
    assert len(body["sources"]) == 2


def test_api_posture_returns_counts() -> None:
    """GET /api/posture returns aggregated severity counts."""
    resp = client.get("/api/posture?packages=django")
    assert resp.status_code == 200
    body = resp.json()
    assert body["critical"] == 1
    assert body["untracked"] == 1
    assert "sql" in body


def test_api_integrations_returns_catalog() -> None:
    """GET /api/integrations returns the connectable source catalog."""
    resp = client.get("/api/integrations")
    assert resp.status_code == 200
    body = resp.json()
    names = {item["name"] for item in body["integrations"]}
    assert {"osv", "github", "jira", "sentry", "grafana"}.issubset(names)


def test_api_connects_bundled_source() -> None:
    """POST /api/sources/connect accepts bundled source credentials."""
    resp = client.post(
        "/api/sources/connect",
        json={"name": "github", "values": {"GITHUB_TOKEN": "ghp_test"}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "github"
    assert body["ok"] is True


def test_api_connects_custom_source() -> None:
    """POST /api/sources/connect accepts custom sources without credentials."""
    resp = client.post("/api/sources/connect", json={"name": "osv", "values": {}})
    assert resp.status_code == 200
    assert resp.json()["source"] == "osv"


def test_api_connect_validates_required_fields() -> None:
    """POST /api/sources/connect returns 400 when required fields are missing."""
    resp = client.post("/api/sources/connect", json={"name": "jira", "values": {}})
    assert resp.status_code == 400
    assert "Missing required fields" in resp.json()["detail"]


def test_api_source_test_endpoint() -> None:
    """POST /api/sources/{name}/test validates an installed source."""
    resp = client.post("/api/sources/github/test")
    assert resp.status_code == 200
    assert resp.json()["source"] == "github"


def test_api_source_remove_endpoint() -> None:
    """DELETE /api/sources/{name} removes an installed source."""
    resp = client.delete("/api/sources/github")
    assert resp.status_code == 200
    assert resp.json()["source"] == "github"
