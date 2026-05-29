"""Tests for query builders and runners."""

from devsecops_coral.coral_client import (
    CoralError,
    identify_failed_source,
    is_source_unavailable,
)
from devsecops_coral.queries.correlate import build_correlate_query, classify_signal, run_correlate
from devsecops_coral.queries.github_prs import build_github_prs_query, run_github_prs
from devsecops_coral.queries.posture import _count_untracked, run_posture
from devsecops_coral.queries.root_cause import (
    build_root_cause_query,
    run_root_cause,
    summarize_signals,
)
from devsecops_coral.queries.scan import build_scan_query, build_scan_query_osv_only, run_scan
from devsecops_coral.queries.timeline import build_timeline_query, run_timeline

_JIRA_TIMEOUT_MSG = (
    "Source request timed out: source API request timed out after 30s "
    "[GET] https://example.atlassian.net/rest/api/3/search/jql"
)


def test_build_scan_query_contains_package() -> None:
    """Scan query template includes OSV search args and Jira JOIN."""
    sql = build_scan_query(ecosystem="PyPI", package="django")
    assert "package => 'django'" in sql
    assert "ecosystem => 'PyPI'" in sql
    assert "jira.issues" in sql


def test_build_scan_query_has_tracking_status() -> None:
    """Scan query includes CASE expression for UNTRACKED detection in SQL output."""
    sql = build_scan_query(ecosystem="PyPI", package="pillow")
    assert "tracking_status" in sql
    assert "UNTRACKED" in sql
    assert "CASE WHEN j.key IS NULL" in sql


def test_build_scan_query_has_sentry_time_window() -> None:
    """Scan query filters Sentry errors to the last 30 days.

    ``last_seen`` is a Utf8 column in Coral's Sentry source, so it is cast to a
    timestamp before the comparison.
    """
    sql = build_scan_query(ecosystem="PyPI", package="pillow")
    assert "CAST(se.last_seen AS TIMESTAMP) >= NOW() - INTERVAL '30' DAY" in sql


def test_build_scan_query_osv_only_has_tracking_status() -> None:
    """OSV-only fallback scan query emits UNTRACKED as the tracking_status."""
    sql = build_scan_query_osv_only(ecosystem="PyPI", package="requests")
    assert "'UNTRACKED' AS tracking_status" in sql


def test_build_correlate_query_contains_interval() -> None:
    """Correlate query template joins Sentry and applies time window."""
    sql = build_correlate_query(ecosystem="PyPI", package="django", since="7d")
    assert "sentry.issues" in sql
    assert "INTERVAL '7' days" in sql


def test_build_correlate_query_filters_by_package() -> None:
    """Correlate Sentry JOIN filters errors by package name to avoid false signals.

    Coral's Sentry source has no ``culprit`` column, so matching is done on
    ``title`` only and the ``last_seen`` string is cast before comparison.
    """
    sql = build_correlate_query(ecosystem="PyPI", package="pillow", since="7d")
    assert "se.title LIKE CONCAT('%', 'pillow', '%')" in sql
    assert "se.culprit" not in sql
    assert "CAST(se.last_seen AS TIMESTAMP)" in sql


def test_count_untracked_identifies_no_ticket_rows() -> None:
    """_count_untracked counts CVE rows that have no jira_ticket."""
    rows = [
        {"cve": "GHSA-a", "jira_ticket": "SEC-1"},
        {"cve": "GHSA-b", "jira_ticket": None},
        {"cve": "GHSA-c", "jira_ticket": None},
        {"cve": None, "jira_ticket": None},  # no-CVE placeholder — should not count
    ]
    assert _count_untracked(rows) == 2


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


def test_is_source_unavailable_recognizes_timeout() -> None:
    """A 30s upstream timeout is treated as a source-unavailable condition."""
    assert is_source_unavailable(CoralError(_JIRA_TIMEOUT_MSG))
    assert is_source_unavailable("connection refused")
    assert not is_source_unavailable("syntax error near 'SELCT'")


def test_identify_failed_source_maps_jira_url() -> None:
    """A timeout reported only via an atlassian.net URL still maps to jira."""
    failed = identify_failed_source(CoralError(_JIRA_TIMEOUT_MSG), ("github", "sentry", "jira"))
    assert failed == "jira"


def test_run_scan_drops_jira_on_timeout_keeps_sentry(mocker) -> None:
    """A Jira timeout falls back to the OSV+Sentry query (Sentry data retained)."""
    sentry_rows = [
        {"package": "django", "cve": "GHSA-x", "severity": "HIGH", "error_count": 12}
    ]

    def fake_execute(sql: str, *args, **kwargs):
        if "jira.issues" in sql:
            raise CoralError(_JIRA_TIMEOUT_MSG)
        return sentry_rows

    mocker.patch("devsecops_coral.queries.scan.execute_query", side_effect=fake_execute)
    result = run_scan(ecosystem="PyPI", packages=["django"])

    assert result.data == sentry_rows
    assert "jira.issues" not in result.sql  # the Jira tier was abandoned
    assert "sentry.issues" in result.sql  # but Sentry data was preserved


def test_run_timeline_drops_jira_leg_on_timeout(mocker) -> None:
    """A Jira timeout drops only the Jira UNION leg; the timeline still returns."""
    timeline_rows = [{"source": "sentry", "title": "boom"}]

    def fake_execute(sql: str, *args, **kwargs):
        if "jira.issues" in sql:
            raise CoralError(_JIRA_TIMEOUT_MSG)
        return timeline_rows

    mocker.patch("devsecops_coral.queries.timeline.execute_query", side_effect=fake_execute)
    result = run_timeline(since="7d", owner=None, repo=None)

    assert result.data == timeline_rows
    assert "jira.issues" not in result.sql
    assert "sentry.issues" in result.sql


def test_build_correlate_query_with_github_adds_pr_url() -> None:
    """The GitHub-joined correlate query builds a clickable PR url column."""
    sql = build_correlate_query(
        ecosystem="PyPI", package="django", since="7d", owner="myorg", repo="myrepo"
    )
    assert "github.pulls" in sql
    assert "AS pr_url" in sql
    assert "https://github.com/myorg/myrepo/pull/" in sql


def test_build_github_prs_query_filters_security_titles() -> None:
    """GitHub PRs query scopes to a repo, a time window, and security titles."""
    sql = build_github_prs_query(owner="myorg", repo="myrepo", since="90d")
    assert "github.pulls" in sql
    assert "g.owner = 'myorg'" in sql
    assert "g.repo = 'myrepo'" in sql
    assert "INTERVAL '90'" in sql
    assert "g.title LIKE '%upgrade%'" in sql
    assert "https://github.com/myorg/myrepo/pull/" in sql


def test_build_github_prs_query_optional_state_filter() -> None:
    """A state WHERE filter is added only when a valid state is provided."""
    assert "AND g.state = 'merged'" in build_github_prs_query(
        owner="o", repo="r", state="merged"
    )
    # No state filter clause when state is omitted (g.state is still SELECTed).
    assert "AND g.state" not in build_github_prs_query(owner="o", repo="r")


def test_run_github_prs_empty_without_owner(monkeypatch) -> None:
    """run_github_prs returns an empty result (no error) when owner/repo are unset."""
    import devsecops_coral.queries.github_prs as gh

    monkeypatch.setattr(gh, "GITHUB_OWNER", "")
    monkeypatch.setattr(gh, "GITHUB_REPO", "")
    result = run_github_prs(owner="", repo="")
    assert result.data == []
    assert "not configured" in result.sql


def test_run_github_prs_returns_rows(mocker) -> None:
    """run_github_prs returns mocked PR rows and the SQL used."""
    rows = [{"number": 42, "title": "Bump django (security)", "state": "merged"}]
    mocker.patch("devsecops_coral.queries.github_prs.execute_query", return_value=rows)
    result = run_github_prs(owner="myorg", repo="myrepo")
    assert result.data == rows
    assert "github.pulls" in result.sql


def test_run_github_prs_empty_on_source_unavailable(mocker) -> None:
    """A missing GitHub source yields an empty panel rather than a hard failure."""
    mocker.patch(
        "devsecops_coral.queries.github_prs.execute_query",
        side_effect=CoralError("source not found: github"),
    )
    result = run_github_prs(owner="myorg", repo="myrepo")
    assert result.data == []


def test_build_root_cause_query_joins_all_sources() -> None:
    """Root-cause query joins OSV, Sentry, and GitHub PRs when owner/repo are set."""
    sql = build_root_cause_query(
        ecosystem="PyPI", package="django", since="30d",
        cve="GHSA-2f9x-5v75-3qv4", owner="myorg", repo="myrepo",
    )
    assert "osv.search_vulnerabilities" in sql
    assert "sentry.issues" in sql
    assert "github.pulls" in sql
    assert "g.owner = 'myorg'" in sql
    assert "WHERE osv.id = 'GHSA-2f9x-5v75-3qv4'" in sql


def test_build_root_cause_query_omits_github_without_repo() -> None:
    """Without owner/repo the GitHub PR leg is dropped (Sentry leg remains)."""
    sql = build_root_cause_query(ecosystem="PyPI", package="requests", since="30d")
    assert "github.pulls" not in sql
    assert "sentry.issues" in sql


def test_run_root_cause_returns_rows(mocker) -> None:
    """run_root_cause returns rows and SQL from a mocked Coral response."""
    rows = [{"cve": "GHSA-x", "package": "django", "pr_title": "Bump django", "error_count": 5}]
    mocker.patch("devsecops_coral.queries.root_cause.execute_query", return_value=rows)
    result = run_root_cause(ecosystem="PyPI", package="django", cve="GHSA-x")
    assert result.data == rows
    assert "osv.search_vulnerabilities" in result.sql


def test_run_root_cause_falls_back_to_osv_only(mocker) -> None:
    """If GitHub and Sentry are unavailable, run_root_cause falls back to OSV-only."""
    osv_rows = [{"cve": "GHSA-x", "package": "django"}]

    def fake_execute(sql: str, *args, **kwargs):
        if "sentry.issues" in sql or "github.pulls" in sql:
            raise CoralError("source not found: sentry")
        return osv_rows

    mocker.patch("devsecops_coral.queries.root_cause.execute_query", side_effect=fake_execute)
    result = run_root_cause(ecosystem="PyPI", package="django", owner="o", repo="r")
    assert result.data == osv_rows
    assert "sentry.issues" not in result.sql
    assert "github.pulls" not in result.sql


def test_summarize_signals_counts_errors_and_prs() -> None:
    """summarize_signals tallies distinct PRs and total error volume."""
    rows = [
        {"error_title": "boom", "error_count": 10, "pr_number": 1, "pr_title": "fix"},
        {"error_title": "boom2", "error_count": 5, "pr_number": 1, "pr_title": "fix"},
        {"error_title": None, "error_count": 0, "pr_number": 2, "pr_title": "bump"},
    ]
    summary = summarize_signals(rows)
    assert summary["error_signals"] == 2
    assert summary["total_error_count"] == 15
    assert summary["related_prs"] == 2


def test_run_posture_reports_untracked_count(mocker) -> None:
    """run_posture counts CVEs with no Jira ticket and includes them in PostureResponse."""
    mock_rows = [
        {"package": "django", "cve": "GHSA-a", "severity": "CRITICAL", "jira_ticket": "SEC-1"},
        {"package": "requests", "cve": "GHSA-b", "severity": "HIGH", "jira_ticket": None},
        {"package": "pillow", "cve": "GHSA-c", "severity": "HIGH", "jira_ticket": None},
    ]
    fake = type("R", (), {"data": mock_rows, "sql": "SELECT 1"})()
    mocker.patch("devsecops_coral.queries.posture.run_scan", return_value=fake)
    result = run_posture(ecosystem="PyPI", packages=["django", "requests", "pillow"])
    assert result.untracked == 2
    assert result.critical == 1
    assert result.high == 2
