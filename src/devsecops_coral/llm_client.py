"""LLM provider clients — Anthropic, EURI (euron.one), and Cursor (via proxy)."""

from __future__ import annotations

from typing import Any

import httpx

from devsecops_coral.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    CURSOR_API_KEY,
    CURSOR_BASE_URL,
    CURSOR_MODEL,
    EURI_API_KEY,
    EURI_BASE_URL,
    EURI_MODEL,
    resolve_llm_provider,
)

PROVIDER_ANTHROPIC = "anthropic"
PROVIDER_EURI = "euri"
PROVIDER_CURSOR = "cursor"


class LLMError(Exception):
    """Raised when an LLM API call fails."""


def _openai_chat_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    timeout: float,
    provider_label: str,
) -> str:
    """Call an OpenAI-compatible ``/chat/completions`` endpoint."""
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": 4096,
        "temperature": temperature,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=timeout)
    except httpx.HTTPError as exc:
        raise LLMError(f"{provider_label} request failed: {exc}") from exc

    if response.status_code == 403:
        raise LLMError(
            f"{provider_label} quota exceeded. "
            "Check usage at https://cursor.com/dashboard/usage (Cursor) "
            "or https://euron.one/euri (EURI)."
        )
    if response.status_code >= 400:
        raise LLMError(f"{provider_label} error ({response.status_code}): {response.text[:300]}")

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"Unexpected {provider_label} response format") from exc


def _anthropic_chat_completion(
    messages: list[dict[str, str]],
    *,
    temperature: float,
    timeout: float,
) -> str:
    """Call the Anthropic Messages API directly using the ``anthropic`` SDK."""
    try:
        import anthropic as _anthropic
    except ImportError as exc:
        raise LLMError("anthropic package not installed. Run: pip install anthropic") from exc

    system_parts = [m["content"] for m in messages if m.get("role") == "system"]
    user_msgs = [m for m in messages if m.get("role") != "system"]
    system_text = "\n\n".join(system_parts) if system_parts else None

    try:
        client = _anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        kwargs: dict[str, Any] = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": 4096,
            "temperature": temperature,
            "messages": user_msgs,
        }
        if system_text:
            kwargs["system"] = system_text
        response = client.messages.create(**kwargs)
        return str(response.content[0].text)
    except Exception as exc:
        raise LLMError(f"Anthropic request failed: {exc}") from exc


def chat_completion(messages: list[dict[str, str]], *, temperature: float = 0.2) -> str:
    """Send a chat completion using the configured LLM provider."""
    provider = resolve_llm_provider()

    if provider == PROVIDER_ANTHROPIC:
        if not ANTHROPIC_API_KEY:
            raise LLMError(
                "ANTHROPIC_API_KEY is not set. Add it to .env or set LLM_PROVIDER=cursor."
            )
        return _anthropic_chat_completion(messages, temperature=temperature, timeout=60.0)

    if provider == PROVIDER_CURSOR:
        return _openai_chat_completion(
            base_url=CURSOR_BASE_URL,
            api_key=CURSOR_API_KEY,
            model=CURSOR_MODEL,
            messages=messages,
            temperature=temperature,
            timeout=180.0,
            provider_label="Cursor",
        )

    if not EURI_API_KEY:
        raise LLMError(
            "No LLM configured. Options:\n"
            "  1. Set ANTHROPIC_API_KEY in .env  (LLM_PROVIDER=anthropic)\n"
            "  2. Set EURI_API_KEY in .env        (LLM_PROVIDER=euri)\n"
            "  3. Run: npx cursor-agent-api-proxy  (LLM_PROVIDER=cursor)"
        )
    return _openai_chat_completion(
        base_url=EURI_BASE_URL,
        api_key=EURI_API_KEY,
        model=EURI_MODEL,
        messages=messages,
        temperature=temperature,
        timeout=90.0,
        provider_label="EURI",
    )


def active_provider_info() -> dict[str, str]:
    """Return the resolved provider and model for display/debug."""
    provider = resolve_llm_provider()
    if provider == PROVIDER_ANTHROPIC:
        return {
            "provider": PROVIDER_ANTHROPIC,
            "model": ANTHROPIC_MODEL,
            "base_url": "https://api.anthropic.com",
        }
    if provider == PROVIDER_CURSOR:
        return {"provider": PROVIDER_CURSOR, "model": CURSOR_MODEL, "base_url": CURSOR_BASE_URL}
    return {"provider": PROVIDER_EURI, "model": EURI_MODEL, "base_url": EURI_BASE_URL}


def check_cursor_proxy() -> dict[str, Any]:
    """Probe a local Cursor OpenAI-compatible proxy (health + models)."""
    health_url = CURSOR_BASE_URL.rstrip("/").removesuffix("/v1") + "/health"
    models_url = f"{CURSOR_BASE_URL.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {CURSOR_API_KEY}"} if CURSOR_API_KEY else {}

    result: dict[str, Any] = {"base_url": CURSOR_BASE_URL, "reachable": False}
    try:
        health = httpx.get(health_url, timeout=3.0)
        result["health_status"] = health.status_code
        result["reachable"] = health.status_code < 500
    except httpx.HTTPError as exc:
        result["error"] = str(exc)
        return result

    try:
        models = httpx.get(models_url, headers=headers, timeout=5.0)
        if models.status_code == 200:
            data = models.json()
            model_ids = [m.get("id") for m in data.get("data", []) if isinstance(m, dict)]
            result["models"] = model_ids[:20]
    except (httpx.HTTPError, ValueError):
        pass

    return result
