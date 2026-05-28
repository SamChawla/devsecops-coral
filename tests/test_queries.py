"""Tests for query builders and runners."""

from devsecops_coral.queries.correlate import build_correlate_query, classify_signal, run_correlate
from devsecops_coral.queries.scan import build_scan_query, run_scan
from devsecops_coral.queries.timeline import build_timeline_query


def test_build_scan_query_contains_package() -> None:
    """Scan query template includes OSV search args and Jira JOIN."""
    sql = build_scan_query(ecosystem="PyPI", package="django")
    assert "package => 'django'" in sql
    assert "ecosystem => 'PyPI'" in sql
    assert "jira.issues" in sql


def test_build_correlate_query_contains_interval() -> None:
    """Correlate query template joins Sentry and applies time window."""
    sql = build_correlate_query(ecosystem="PyPI", package="django", since="7d")
    assert "sentry.issues" in sql
    assert "INTERVAL '7' days" in sql


def test_build_timeline_query_unions_sources() -> None:
    """Timeline query unions GitHub, Sentry, Jira, and Grafana legs."""
    sql = build_timeline_query(since="24h", owner="myorg", repo="myrepo")
    assert "UNION ALL" in sql
    assert "github.pulls" in sql
    assert "g.owner = 'myorg'" in sql
    assert "g.repo = 'myrepo'" in sql
    assert "sentry.issues" in sql


def test_classify_signal_active() -> None:
    """High error volume with critical severity maps to active signal."""
    assert classify_signal({"error_count": 47, "severity": "CRITICAL"}) == "active"


def test_classify_signal_monitor() -> None:
    """Low error volume maps to monitor signal."""
    assert classify_signal({"error_count": 3, "severity": "LOW"}) == "monitor"


def test_run_scan_mocks_coral(mocker) -> None:
    """run_scan returns merged rows and SQL from mocked Coral responses."""
    mock_rows = [{"package": "django", "cve": "GHSA-x", "severity": "HIGH"}]
    mocker.patch("devsecops_coral.queries.scan.execute_query", return_value=mock_rows)
    result = run_scan(ecosystem="PyPI", packages=["django"])
    assert len(result.data) == 1
    assert result.data[0]["cve"] == "GHSA-x"
    assert "django" in result.sql


def test_run_correlate_adds_signal(mocker) -> None:
    """run_correlate annotates each row with a classified signal."""
    mock_rows = [{"cve": "GHSA-x", "error_count": 20, "severity": "CRITICAL"}]
    mocker.patch("devsecops_coral.queries.correlate.execute_query", return_value=mock_rows)
    result = run_correlate(ecosystem="PyPI", packages=["django"], since="7d")
    assert result.data[0]["signal"] == "active"
    assert "sentry.issues" in result.sql
