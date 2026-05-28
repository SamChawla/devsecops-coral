"""Tests for action executors and the in-memory approval store."""

from __future__ import annotations

import pytest

from devsecops_coral.actions.executor import (
    ActionError,
    actions_response,
    approve_action,
    approve_all,
    dismiss_action,
    load_actions,
)
from devsecops_coral.models import ActionStatus, ActionType, RecommendedAction

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_action(
    action_id: int = 1,
    action_type: ActionType = ActionType.CREATE_JIRA,
    *,
    urgent: bool = False,
) -> RecommendedAction:
    return RecommendedAction(
        id=action_id,
        type=action_type,
        status=ActionStatus.PENDING,
        title=f"Test action {action_id}",
        detail="Test detail",
        package="pillow",
        cve="GHSA-ppf2-m228",
        severity="HIGH",
        urgent=urgent,
    )


# ---------------------------------------------------------------------------
# Store management
# ---------------------------------------------------------------------------


def test_load_actions_replaces_store() -> None:
    """load_actions replaces the existing store contents."""
    load_actions([_make_action(1), _make_action(2)])
    load_actions([_make_action(99)])
    assert len(actions_response().actions) == 1
    assert actions_response().actions[0].id == 99


def test_actions_response_counts() -> None:
    """actions_response tallies statuses correctly."""
    a1 = _make_action(1)
    a2 = _make_action(2)
    a2.status = ActionStatus.DONE
    load_actions([a1, a2])
    resp = actions_response()
    assert resp.pending == 1
    assert resp.done == 1


# ---------------------------------------------------------------------------
# dismiss_action
# ---------------------------------------------------------------------------


def test_dismiss_marks_dismissed() -> None:
    """Dismissing a pending action sets its status to DISMISSED."""
    load_actions([_make_action(1)])
    action = dismiss_action(1)
    assert action.status == ActionStatus.DISMISSED


def test_dismiss_nonexistent_raises() -> None:
    """Dismissing an unknown ID raises ActionError."""
    load_actions([])
    with pytest.raises(ActionError, match="not found"):
        dismiss_action(999)


def test_dismiss_done_action_raises() -> None:
    """Cannot dismiss an already-executed action."""
    a = _make_action(1)
    a.status = ActionStatus.DONE
    load_actions([a])
    with pytest.raises(ActionError, match="Cannot dismiss"):
        dismiss_action(1)


# ---------------------------------------------------------------------------
# approve_action — mocked dispatch
# ---------------------------------------------------------------------------


def test_approve_calls_jira_handler(mocker) -> None:
    """approve_action dispatches CREATE_JIRA to jira.create_issue."""
    load_actions([_make_action(1, ActionType.CREATE_JIRA)])
    mock_create = mocker.patch(
        "devsecops_coral.actions.jira.create_issue",
        return_value={
            "key": "SEC-9",
            "id": "100",
            "url": "https://example.atlassian.net/browse/SEC-9",
        },
    )
    action = approve_action(1)
    mock_create.assert_called_once()
    assert action.status == ActionStatus.DONE
    assert action.result["key"] == "SEC-9"


def test_approve_calls_grafana_handler(mocker) -> None:
    """approve_action dispatches ANNOTATE_GRAFANA to grafana.create_annotation."""
    load_actions([_make_action(1, ActionType.ANNOTATE_GRAFANA)])
    mock_annotate = mocker.patch(
        "devsecops_coral.actions.grafana.create_annotation",
        return_value={
            "id": 42,
            "url": "https://grafana.example.com/api/annotations/42",
            "message": "ok",
        },
    )
    action = approve_action(1)
    mock_annotate.assert_called_once()
    assert action.status == ActionStatus.DONE
    assert action.result["id"] == 42


def test_approve_calls_report_handler(mocker) -> None:
    """approve_action dispatches GENERATE_REPORT to report.generate_markdown."""
    load_actions([_make_action(1, ActionType.GENERATE_REPORT)])
    mock_report = mocker.patch(
        "devsecops_coral.actions.report.generate_markdown",
        return_value={"path": "reports/posture-2026-05-28.md", "bytes": 512},
    )
    action = approve_action(1)
    mock_report.assert_called_once()
    assert action.status == ActionStatus.DONE
    assert "path" in action.result


def test_approve_calls_github_pr_handler(mocker) -> None:
    """approve_action dispatches CREATE_PR to github.create_pull_request."""
    load_actions([_make_action(1, ActionType.CREATE_PR)])
    mock_pr = mocker.patch(
        "devsecops_coral.actions.github.create_pull_request",
        return_value={
            "number": 45,
            "url": "https://github.com/org/repo/pull/45",
            "branch": "security/upgrade-pillow",
        },
    )
    action = approve_action(1)
    mock_pr.assert_called_once()
    assert action.status == ActionStatus.DONE
    assert action.result["number"] == 45


def test_approve_non_pending_raises() -> None:
    """Approving an already-done action raises ActionError."""
    a = _make_action(1)
    a.status = ActionStatus.DONE
    load_actions([a])
    with pytest.raises(ActionError, match="not PENDING"):
        approve_action(1)


def test_approve_handler_failure_marks_failed(mocker) -> None:
    """If the handler raises, the action is marked FAILED and ActionError is re-raised."""
    from devsecops_coral.actions.jira import JiraError

    load_actions([_make_action(1, ActionType.CREATE_JIRA)])
    mocker.patch(
        "devsecops_coral.actions.jira.create_issue",
        side_effect=JiraError("JIRA_BASE_URL is not set in .env"),
    )
    with pytest.raises(ActionError, match="JIRA_BASE_URL"):
        approve_action(1)
    assert actions_response().actions[0].status == ActionStatus.FAILED


# ---------------------------------------------------------------------------
# approve_all
# ---------------------------------------------------------------------------


def test_approve_all_executes_all_pending(mocker) -> None:
    """approve_all executes every PENDING action and returns results."""
    load_actions(
        [_make_action(1, ActionType.GENERATE_REPORT), _make_action(2, ActionType.GENERATE_REPORT)]
    )
    mocker.patch(
        "devsecops_coral.actions.report.generate_markdown",
        return_value={"path": "reports/posture-2026-05-28.md", "bytes": 100},
    )
    results = approve_all()
    assert len(results) == 2
    assert all(a.status == ActionStatus.DONE for a in results)


def test_approve_all_skips_non_pending(mocker) -> None:
    """approve_all ignores already-done or dismissed actions."""
    a1 = _make_action(1, ActionType.GENERATE_REPORT)
    a2 = _make_action(2, ActionType.GENERATE_REPORT)
    a2.status = ActionStatus.DISMISSED
    load_actions([a1, a2])
    mocker.patch(
        "devsecops_coral.actions.report.generate_markdown",
        return_value={"path": "reports/posture.md", "bytes": 100},
    )
    results = approve_all()
    assert len(results) == 1
    assert results[0].id == 1


def test_approve_all_continues_after_failure(mocker) -> None:
    """approve_all continues executing remaining actions even if one fails."""
    from devsecops_coral.actions.jira import JiraError

    load_actions(
        [
            _make_action(1, ActionType.CREATE_JIRA),
            _make_action(2, ActionType.GENERATE_REPORT),
        ]
    )
    mocker.patch(
        "devsecops_coral.actions.jira.create_issue",
        side_effect=JiraError("auth failed"),
    )
    mocker.patch(
        "devsecops_coral.actions.report.generate_markdown",
        return_value={"path": "reports/posture.md", "bytes": 100},
    )
    results = approve_all()
    statuses = {a.id: a.status for a in results}
    assert statuses[1] == ActionStatus.FAILED
    assert statuses[2] == ActionStatus.DONE
