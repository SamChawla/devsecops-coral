"""In-memory action store and human-in-the-loop approval orchestration."""

from __future__ import annotations

import threading
from typing import Any

from devsecops_coral.models import ActionsResponse, ActionStatus, ActionType, RecommendedAction


class ActionError(Exception):
    """Raised when an action cannot be executed or is in an invalid state."""


_lock = threading.Lock()
_store: list[RecommendedAction] = []

# Map internal severity buckets to standard Jira Cloud priority names. Default
# Jira projects ship with Highest/High/Medium/Low/Lowest (no "Critical"), so
# CRITICAL maps to "Highest". The Jira action retries without priority if an
# instance uses a custom scheme that rejects these names.
_JIRA_PRIORITY: dict[str, str] = {
    "CRITICAL": "Highest",
    "HIGH": "High",
    "MEDIUM": "Medium",
    "LOW": "Low",
    "INFO": "Lowest",
}


# ---------------------------------------------------------------------------
# Store management
# ---------------------------------------------------------------------------


def load_actions(actions: list[RecommendedAction]) -> None:
    """Replace the current session action store with a fresh list.

    Args:
        actions: New list of recommended actions (all should be ``PENDING``).
    """
    global _store
    with _lock:
        _store = list(actions)


def get_actions() -> list[RecommendedAction]:
    """Return a snapshot of the current action store."""
    with _lock:
        return list(_store)


def actions_response() -> ActionsResponse:
    """Build an :class:`~devsecops_coral.models.ActionsResponse` from the store."""
    actions = get_actions()
    counts: dict[str, int] = {s.value: 0 for s in ActionStatus}
    for a in actions:
        counts[a.status.value] += 1
    return ActionsResponse(
        actions=actions,
        pending=counts.get("pending", 0),
        executing=counts.get("executing", 0),
        done=counts.get("done", 0),
        dismissed=counts.get("dismissed", 0),
        failed=counts.get("failed", 0),
    )


def _find(action_id: int) -> RecommendedAction:
    """Locate an action by ID (must be called with ``_lock`` held)."""
    for action in _store:
        if action.id == action_id:
            return action
    raise ActionError(f"Action {action_id} not found")


# ---------------------------------------------------------------------------
# Action dispatch
# ---------------------------------------------------------------------------


def _jira_summary(action: RecommendedAction) -> str:
    """Build a descriptive Jira issue title from a recommended action.

    Produces titles like ``[Security] HIGH vulnerability in pillow
    (GHSA-xxxx)`` so the ticket is self-explanatory in the backlog.
    """
    severity = str(action.severity or "").upper()
    package = action.package or "dependency"
    prefix = "[URGENT] " if action.urgent else ""
    title = f"{prefix}[Security] {severity} vulnerability in {package}".strip()
    if action.cve:
        title += f" ({action.cve})"
    return title


def _dispatch(action: RecommendedAction) -> dict[str, Any]:
    """Route an approved action to the correct handler module.

    Args:
        action: The action to execute (status must already be ``EXECUTING``).

    Returns:
        Result dict from the handler (e.g. ``{"key": "SEC-9", "url": "..."}``)

    Raises:
        ActionError: If the action type is unrecognised or the handler fails.
    """
    from devsecops_coral.actions import github, grafana, jira, report

    if action.type == ActionType.CREATE_JIRA:
        priority = _JIRA_PRIORITY.get(str(action.severity or "").upper(), "Medium")
        return jira.create_issue(
            summary=_jira_summary(action),
            description=action.detail,
            priority=priority,
            cve=action.cve,
            package=action.package,
            severity=action.severity,
            urgent=action.urgent,
        )
    if action.type == ActionType.CREATE_PR:
        return github.create_pull_request(
            title=action.title,
            body=(
                f"{action.detail}\n\nCVE: {action.cve or 'N/A'}\n"
                f"Package: `{action.package or 'N/A'}`"
            ),
            package=action.package or "unknown",
            cve=action.cve,
        )
    if action.type == ActionType.CREATE_GITHUB_ISSUE:
        return github.create_issue(title=action.title, body=action.detail)
    if action.type == ActionType.ANNOTATE_GRAFANA:
        return grafana.create_annotation(
            text=action.title,
            tags=["devsecops-coral", "cve-remediation"],
        )
    if action.type == ActionType.GENERATE_REPORT:
        return report.generate_markdown(actions=get_actions())
    raise ActionError(f"Unknown action type: {action.type.value}")


# ---------------------------------------------------------------------------
# Approval API
# ---------------------------------------------------------------------------


def approve_action(action_id: int) -> RecommendedAction:
    """Execute a single pending action after human approval.

    Args:
        action_id: ID of the action to approve.

    Returns:
        Updated :class:`~devsecops_coral.models.RecommendedAction` with
        status ``DONE`` and populated ``result``.

    Raises:
        ActionError: If the action is not ``PENDING`` or execution fails.
    """
    with _lock:
        action = _find(action_id)
        if action.status != ActionStatus.PENDING:
            raise ActionError(
                f"Action {action_id} is {action.status.value}, not PENDING — cannot approve."
            )
        action.status = ActionStatus.EXECUTING

    try:
        result = _dispatch(action)
        with _lock:
            action.status = ActionStatus.DONE
            action.result = result
    except Exception as exc:
        with _lock:
            action.status = ActionStatus.FAILED
            action.result = {"error": str(exc)}
        raise ActionError(str(exc)) from exc

    return action


def approve_all() -> list[RecommendedAction]:
    """Execute all pending actions sequentially.

    Returns:
        List of updated actions (both succeeded and failed).
    """
    with _lock:
        pending_ids = [a.id for a in _store if a.status == ActionStatus.PENDING]

    executed: list[RecommendedAction] = []
    for action_id in pending_ids:
        try:
            executed.append(approve_action(action_id))
        except ActionError:
            with _lock:
                try:
                    executed.append(_find(action_id))
                except ActionError:
                    pass
    return executed


def dismiss_action(action_id: int) -> RecommendedAction:
    """Dismiss a pending action without executing it.

    Args:
        action_id: ID of the action to dismiss.

    Returns:
        Updated action with status ``DISMISSED``.

    Raises:
        ActionError: If the action is not in a dismissible state.
    """
    with _lock:
        action = _find(action_id)
        if action.status not in (ActionStatus.PENDING,):
            raise ActionError(f"Cannot dismiss action {action_id} in state {action.status.value}.")
        action.status = ActionStatus.DISMISSED
    return action
