"""DeepSeek chat completion (OpenAI-compatible HTTP). Thread-aware, per-role models."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Literal

from app_config import MODEL_PROSE, MODEL_SCRIPT

Role = Literal["script", "prose"]

_DEFAULT_DEEPSEEK_BASE = "https://api.deepseek.com"

_ROLE_KEY_ENV = {
    "script": ("LLM_API_KEY_SCRIPT", "DEEPSEEK_API_KEY"),
    "prose": ("LLM_API_KEY_PROSE", "DEEPSEEK_API_KEY"),
}
_ROLE_BASE_ENV = {
    "script": "LLM_BASE_URL_SCRIPT",
    "prose": "LLM_BASE_URL_PROSE",
}
_ROLE_MODEL_ENV = {
    "script": "LLM_MODEL_SCRIPT",
    "prose": "LLM_MODEL_PROSE",
}
_ROLE_THINKING_ENV = {
    "script": "LLM_THINKING_SCRIPT",
    "prose": "LLM_THINKING_PROSE",
}
# Legacy names → v4-flash (see https://api-docs.deepseek.com/quick_start/pricing)
_DEEPSEEK_LEGACY = {
    "deepseek-chat": "deepseek-v4-flash",
    "deepseek-reasoner": "deepseek-v4-flash",
}


def _resolve_api_key(role: Role | None = None) -> str:
    if role:
        for name in _ROLE_KEY_ENV[role]:
            val = os.environ.get(name, "").strip()
            if val:
                return val
    for name in ("LLM_API_KEY", "DEEPSEEK_API_KEY"):
        val = os.environ.get(name, "").strip()
        if val:
            return val
    raise RuntimeError(
        "Set DEEPSEEK_API_KEY (or LLM_API_KEY / LLM_API_KEY_SCRIPT / LLM_API_KEY_PROSE)"
    )


def _resolve_base_url(role: Role | None = None) -> str:
    if role:
        explicit = os.environ.get(_ROLE_BASE_ENV[role], "").strip()
        if explicit:
            return explicit.rstrip("/")
    explicit = os.environ.get("LLM_BASE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    return _DEFAULT_DEEPSEEK_BASE


def _resolve_model(role: Role | None = None, *, config: Any = None) -> str:
    if role:
        explicit = os.environ.get(_ROLE_MODEL_ENV[role], "").strip()
        if explicit:
            return explicit
        if config is not None:
            return config.model_script if role == "script" else config.model_prose
        if role == "script":
            return MODEL_SCRIPT
        if role == "prose":
            return MODEL_PROSE
    explicit = os.environ.get("LLM_MODEL", "").strip()
    if explicit:
        return explicit
    return MODEL_SCRIPT


def _normalize_model(name: str) -> str:
    key = name.strip().lower()
    return _DEEPSEEK_LEGACY.get(key, name)


def _thinking_enabled(role: Role | None, *, config: Any = None) -> bool | None:
    """Return True/False for DeepSeek v4; None if not applicable."""
    if role:
        env = os.environ.get(_ROLE_THINKING_ENV[role], "").strip().lower()
        if env in ("1", "true", "yes", "on"):
            return True
        if env in ("0", "false", "no", "off"):
            return False
        if config is not None:
            return bool(
                config.thinking_script if role == "script" else config.thinking_prose
            )
    return False


def model_for_role(role: Role, *, config: Any = None) -> str:
    return _resolve_model(role, config=config)


def complete(
    *,
    system: str,
    user: str,
    stream: bool = False,
    role: Role | None = None,
) -> str:
    """One-shot completion (stateless). Prefer complete_messages for threads."""
    return complete_messages(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        stream=stream,
        role=role,
    )


def complete_messages(
    messages: list[dict[str, str]],
    *,
    stream: bool = False,
    role: Role | None = None,
    model: str | None = None,
    config: Any = None,
) -> str:
    """Chat completion with full message history."""
    return _complete_http_messages(
        messages,
        stream=stream,
        role=role,
        model=model,
        config=config,
    )


def _complete_http_messages(
    messages: list[dict[str, str]],
    *,
    stream: bool,
    role: Role | None,
    model: str | None,
    config: Any = None,
) -> str:
    api_key = _resolve_api_key(role)
    base_url = _resolve_base_url(role)
    resolved_model = _normalize_model(model or _resolve_model(role, config=config))
    thinking = _thinking_enabled(role, config=config)

    body: dict[str, Any] = {
        "model": resolved_model,
        "messages": messages,
        "temperature": 0.6,
    }
    if resolved_model.startswith("deepseek-v4") or resolved_model in _DEEPSEEK_LEGACY.values():
        body["thinking"] = {
            "type": "enabled" if thinking else "disabled",
        }
        if thinking:
            body.pop("temperature", None)
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", errors="replace")
        print(f"error: LLM HTTP {err.code}: {detail[:500]}", file=sys.stderr)
        raise RuntimeError(f"LLM request failed: HTTP {err.code}") from err
    except urllib.error.URLError as err:
        raise RuntimeError(f"LLM request failed: {err}") from err

    if stream:
        label = role or "llm"
        print(
            f"[llm:{label}] model={resolved_model} thinking={thinking} base={base_url} "
            f"msgs={len(messages)}",
            file=sys.stderr,
        )

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("LLM returned no choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("LLM returned empty content")
    return content
