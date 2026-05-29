"""Tests for the rule-based recommendation engine."""

from devsecops_coral.models import ActionStatus, ActionType
from devsecops_coral.recommender import _package_signal_map, build_recommendations, run_recommend

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SCAN_TRACKED = [
    {"package": "django", "cve": "GHSA-a", "severity": "CRITICAL", "jira_ticket": "SEC-1"},
]

_SCAN_UNTRACKED = [
    {"package": "requests", "cve": "GHSA-b", "severity": "HIGH", "jira_ticket": None},
    {"package": "pillow", "cve": "GHSA-c", "severity": "HIGH", "jira_ticket": None},
]

_CORRELATE_ACTIVE = [
    {"package": "pillow", "error_count": 12, "severity": "HIGH", "signal": "active"},
    {"package": "requests", "error_count": 3, "severity": "HIGH", "signal": "monitor"},
    {"package": "django", "error_count": 0, "severity": "CRITICAL", "signal": "clean"},
]


# ---------------------------------------------------------------------------
# _package_signal_map
# ---------------------------------------------------------------------------


def test_signal_map_picks_worst() -> None:
    """Active signal wins over monitor and clean for the same package."""
    rows = [
        {"package": "pillow", "signal": "clean"},
        {"package": "pillow", "signal": "active"},
        {"package": "pillow", "signal": "monitor"},
    ]
    m = _package_signal_map(rows)
    assert m["pillow"] == "active"


def test_signal_map_empty() -> None:
    """Empty correlate data returns empty map."""
    assert _package_signal_map([]) == {}


# ---------------------------------------------------------------------------
# build_recommendations — basic rule coverage
# ---------------------------------------------------------------------------


def test_untracked_high_generates_jira() -> None:
    """Each untracked HIGH/CRITICAL CVE produces a create_jira action."""
    actions = build_recommendations(_SCAN_UNTRACKED, _CORRELATE_ACTIVE)
    jira_actions = [a for a in actions if a.type == ActionType.CREATE_JIRA]
    assert len(jira_actions) == 2
    pkgs = {a.package for a in jira_actions}
    assert pkgs == {"requests", "pillow"}


def test_active_package_jira_is_urgent() -> None:
    """Jira action for an actively-exploited package is flagged urgent."""
    actions = build_recommendations(_SCAN_UNTRACKED, _CORRELATE_ACTIVE)
    pillow_jira = next(
        a for a in actions if a.type == ActionType.CREATE_JIRA and a.package == "pillow"
    )
    assert pillow_jira.urgent is True


def test_monitor_package_jira_not_urgent() -> None:
    """Jira action for a monitor-signal package is NOT flagged urgent."""
    actions = build_recommendations(_SCAN_UNTRACKED, _CORRELATE_ACTIVE)
    requests_jira = next(
        a for a in actions if a.type == ActionType.CREATE_JIRA and a.package == "requests"
    )
    assert requests_jira.urgent is False


def test_active_package_gets_pr() -> None:
    """A package with active or monitor signal gets a create_pr action."""
    actions = build_recommendations(_SCAN_UNTRACKED, _CORRELATE_ACTIVE)
    pr_actions = [a for a in actions if a.type == ActionType.CREATE_PR]
    assert len(pr_actions) >= 1
    pr_packages = {a.package for a in pr_actions}
    assert "pillow" in pr_packages or "requests" in pr_packages


def test_clean_only_no_pr() -> None:
    """Packages with only clean signals do not get create_pr actions."""
    correlate_clean = [
        {"package": "requests", "signal": "clean", "error_count": 0, "severity": "HIGH"},
        {"package": "pillow", "signal": "clean", "error_count": 0, "severity": "HIGH"},
    ]
    actions = build_recommendations(_SCAN_UNTRACKED, correlate_clean)
    assert not any(a.type == ActionType.CREATE_PR for a in actions)


def test_grafana_annotation_added_when_untracked() -> None:
    """An annotate_grafana action is always added when untracked CVEs exist."""
    actions = build_recommendations(_SCAN_UNTRACKED, _CORRELATE_ACTIVE)
    assert any(a.type == ActionType.ANNOTATE_GRAFANA for a in actions)


def test_generate_report_always_present() -> None:
    """A generate_report action is always appended regardless of scan state."""
    actions_with = build_recommendations(_SCAN_UNTRACKED, _CORRELATE_ACTIVE)
    actions_clean = build_recommendations(_SCAN_TRACKED, [])
    assert any(a.type == ActionType.GENERATE_REPORT for a in actions_with)
    assert any(a.type == ActionType.GENERATE_REPORT for a in actions_clean)


def test_tracked_only_no_jira() -> None:
    """If all CVEs are already tracked, no create_jira actions are generated."""
    actions = build_recommendations(_SCAN_TRACKED, [])
    assert not any(a.type == ActionType.CREATE_JIRA for a in actions)


def test_all_actions_pending_status() -> None:
    """All actions produced by Phase 2 recommender start in PENDING status."""
    actions = build_recommendations(_SCAN_UNTRACKED, _CORRELATE_ACTIVE)
    assert all(a.status == ActionStatus.PENDING for a in actions)


def test_action_ids_are_sequential() -> None:
    """Action IDs start at 1 and increase without gaps."""
    actions = build_recommendations(_SCAN_UNTRACKED, _CORRELATE_ACTIVE)
    ids = [a.id for a in actions]
    assert ids == list(range(1, len(actions) + 1))


def test_untracked_any_severity_generates_jira() -> None:
    """Untracked CVEs of any severity (MEDIUM/UNKNOWN included) trigger create_jira.

    Being untracked is the gap the tool surfaces, so the recommender no longer
    filters by severity — it only orders by it.
    """
    mixed_scan = [
        {"package": "celery", "cve": "GHSA-d", "severity": "MEDIUM", "jira_ticket": None},
        {"package": "flask", "cve": "GHSA-e", "severity": None, "jira_ticket": None},
    ]
    actions = build_recommendations(mixed_scan, [])
    jira_actions = [a for a in actions if a.type == ActionType.CREATE_JIRA]
    assert {a.package for a in jira_actions} == {"celery", "flask"}


def test_untracked_jira_ordered_by_severity() -> None:
    """create_jira actions surface the most severe untracked CVE first."""
    scan = [
        {"package": "a", "cve": "GHSA-low", "severity": "LOW", "jira_ticket": None},
        {"package": "b", "cve": "GHSA-crit", "severity": "CRITICAL", "jira_ticket": None},
        {"package": "c", "cve": "GHSA-med", "severity": "MEDIUM", "jira_ticket": None},
    ]
    actions = build_recommendations(scan, [])
    jira_cves = [a.cve for a in actions if a.type == ActionType.CREATE_JIRA]
    assert jira_cves == ["GHSA-crit", "GHSA-med", "GHSA-low"]


# ---------------------------------------------------------------------------
# run_recommend integration (mocked Coral)
# ---------------------------------------------------------------------------


def test_run_recommend_returns_response(mocker) -> None:
    """run_recommend returns a RecommendResponse with actions and metadata."""
    mocker.patch(
        "devsecops_coral.recommender.run_scan",
        return_value=type("R", (), {"data": _SCAN_UNTRACKED, "sql": "SELECT 1"})(),
    )
    mocker.patch(
        "devsecops_coral.recommender.run_correlate",
        return_value=type("R", (), {"data": _CORRELATE_ACTIVE, "sql": "SELECT 1"})(),
    )
    result = run_recommend(ecosystem="PyPI", packages=["requests", "pillow"], since="7d")
    assert result.ecosystem == "PyPI"
    assert "requests" in result.packages
    assert len(result.actions) >= 1
