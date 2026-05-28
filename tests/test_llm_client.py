"""Tests for LLM provider resolution."""

import devsecops_coral.config as cfg
from devsecops_coral.config import resolve_llm_provider
from devsecops_coral.llm_client import active_provider_info


def test_resolve_llm_provider_explicit_euri(monkeypatch) -> None:
    """Explicit LLM_PROVIDER=euri selects EURI backend."""
    monkeypatch.setattr(cfg, "LLM_PROVIDER", "euri")
    monkeypatch.setattr(cfg, "EURI_API_KEY", "key")
    assert resolve_llm_provider() == "euri"


def test_resolve_llm_provider_auto_prefers_euri(monkeypatch) -> None:
    """Auto mode prefers EURI when EURI_API_KEY is set."""
    monkeypatch.setattr(cfg, "LLM_PROVIDER", "auto")
    monkeypatch.setattr(cfg, "EURI_API_KEY", "key")
    assert resolve_llm_provider() == "euri"


def test_resolve_llm_provider_auto_falls_back_to_cursor(monkeypatch) -> None:
    """Auto mode falls back to Cursor when EURI is not configured."""
    monkeypatch.setattr(cfg, "LLM_PROVIDER", "auto")
    monkeypatch.setattr(cfg, "EURI_API_KEY", "")
    assert resolve_llm_provider() == "cursor"


def test_active_provider_info_cursor(monkeypatch) -> None:
    """active_provider_info reports Cursor proxy URL when selected."""
    monkeypatch.setattr(cfg, "LLM_PROVIDER", "cursor")
    info = active_provider_info()
    assert info["provider"] == "cursor"
    assert "localhost" in info["base_url"]
