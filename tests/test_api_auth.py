"""Tests for the auth endpoints and the require_user gate on data routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from devsecops_coral import api, auth
from devsecops_coral.models import QueryResult


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A TestClient with auth enabled against a throwaway SQLite database."""
    monkeypatch.setattr(auth, "AUTH_DB_PATH", str(tmp_path / "auth.db"))
    monkeypatch.setattr(api, "AUTH_ENABLED", True)
    auth.init_db()
    # Keep the gated endpoint cheap — we only care about auth here.
    monkeypatch.setattr(
        api, "run_scan", lambda **_: QueryResult(data=[], sql="SELECT scan")
    )
    return TestClient(app=api.app)


def test_protected_route_requires_session(client) -> None:
    """Data endpoints return 401 without a valid session cookie."""
    resp = client.get("/api/scan?packages=django")
    assert resp.status_code == 401


def test_signup_login_me_logout_flow(client) -> None:
    """Full lifecycle: signup sets a cookie, /me reflects it, logout clears it."""
    signup = client.post(
        "/api/auth/signup",
        json={"email": "owner@example.com", "password": "supersecret", "org_name": "Acme"},
    )
    assert signup.status_code == 200
    assert signup.json()["org"]["name"] == "Acme"

    # Cookie now lets us reach a protected route.
    assert client.get("/api/scan?packages=django").status_code == 200

    me = client.get("/api/auth/me")
    assert me.json()["user"]["email"] == "owner@example.com"

    assert client.post("/api/auth/logout").status_code == 200
    # After logout the session is gone.
    assert client.get("/api/scan?packages=django").status_code == 401


def test_login_rejects_bad_password(client) -> None:
    """Login with the wrong password is rejected with 401."""
    client.post(
        "/api/auth/signup",
        json={"email": "user@example.com", "password": "supersecret", "org_name": "Acme"},
    )
    client.post("/api/auth/logout")
    resp = client.post(
        "/api/auth/login", json={"email": "user@example.com", "password": "nope"}
    )
    assert resp.status_code == 401
