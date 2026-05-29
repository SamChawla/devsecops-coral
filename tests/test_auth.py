"""Tests for the lightweight org-scoped auth layer."""

from __future__ import annotations

import pytest

from devsecops_coral import auth


@pytest.fixture(autouse=True)
def _temp_db(tmp_path, monkeypatch):
    """Point the auth module at a throwaway SQLite file for each test."""
    db_path = tmp_path / "auth.db"
    monkeypatch.setattr(auth, "AUTH_DB_PATH", str(db_path))
    auth.init_db()
    yield


def test_signup_creates_org_and_owner() -> None:
    """Signup returns the new user (owner role) and organization."""
    result = auth.signup("owner@example.com", "supersecret", "Acme Security")
    assert result["user"]["email"] == "owner@example.com"
    assert result["user"]["role"] == "owner"
    assert result["org"]["name"] == "Acme Security"


def test_signup_rejects_duplicate_email() -> None:
    """A second signup with the same email is rejected."""
    auth.signup("dup@example.com", "supersecret", "Org One")
    with pytest.raises(auth.AuthError):
        auth.signup("dup@example.com", "supersecret", "Org Two")


def test_signup_validates_input() -> None:
    """Bad email, short password, and missing org name are rejected."""
    with pytest.raises(auth.AuthError):
        auth.signup("not-an-email", "supersecret", "Org")
    with pytest.raises(auth.AuthError):
        auth.signup("ok@example.com", "short", "Org")
    with pytest.raises(auth.AuthError):
        auth.signup("ok@example.com", "supersecret", "")


def test_authenticate_success_and_failure() -> None:
    """Correct credentials authenticate; wrong password is rejected."""
    auth.signup("user@example.com", "supersecret", "Acme")
    ok = auth.authenticate("user@example.com", "supersecret")
    assert ok["user"]["email"] == "user@example.com"
    with pytest.raises(auth.AuthError):
        auth.authenticate("user@example.com", "wrongpass")
    with pytest.raises(auth.AuthError):
        auth.authenticate("missing@example.com", "supersecret")


def test_session_lifecycle() -> None:
    """A created session resolves to its user, and logout invalidates it."""
    created = auth.signup("sess@example.com", "supersecret", "Acme")
    token = auth.create_session(created["user"]["id"])
    resolved = auth.session_user(token)
    assert resolved is not None
    assert resolved["user"]["email"] == "sess@example.com"
    assert resolved["org"]["name"] == "Acme"

    auth.delete_session(token)
    assert auth.session_user(token) is None
    assert auth.session_user(None) is None
