"""LLM chat completion (OpenAI-compatible HTTP). Thread-aware, per-role models."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Literal

from app_config import MODEL, MODEL_PROSE, MODEL_SCRIPT

Role = Literal["script", "prose"]

_DEFAULT_MOONSHOT_BASE = "https://api.moonshot.cn/v1"
_DEFAULT_OPENAI_BASE = "https://api.openai.com/v1"
_DEFAULT_DEEPSEEK_BASE = "https://api.deepseek.com"

_ROLE_KEY_ENV = {
    "script": ("LLM_API_KEY_SCRIPT", "DEEPSEEK_API_KEY"),
    "prose": ("LLM_API_KEY_PROSE", "MOONSHOT_API_KEY"),
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
    for name in ("LLM_API_KEY", "DEEPSEEK_API_KEY", "MOONSHOT_API_KEY", "OPENAI_API_KEY"):
        val = os.environ.get(name, "").strip()
        if val:
            return val
    val = os.environ.get("CURSOR_API_KEY", "").strip()
    if val:
        return val
    raise RuntimeError(
        "Set LLM_API_KEY, DEEPSEEK_API_KEY, MOONSHOT_API_KEY, OPENAI_API_KEY, or CURSOR_API_KEY"
    )


def _resolve_base_url(api_key: str, role: Role | None = None) -> str:
    if role:
        explicit = os.environ.get(_ROLE_BASE_ENV[role], "").strip()
        if explicit:
            return explicit.rstrip("/")
    explicit = os.environ.get("LLM_BASE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    if api_key == os.environ.get("DEEPSEEK_API_KEY", "").strip():
        return _DEFAULT_DEEPSEEK_BASE
    if api_key == os.environ.get("MOONSHOT_API_KEY", "").strip():
        return _DEFAULT_MOONSHOT_BASE
    model = _resolve_model(role)
    if model.startswith("deepseek"):
        return _DEFAULT_DEEPSEEK_BASE
    if model.startswith("kimi") or "moonshot" in model.lower():
        return _DEFAULT_MOONSHOT_BASE
    return _DEFAULT_OPENAI_BASE


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
    if os.environ.get("DEEPSEEK_API_KEY", "").strip() and role != "prose":
        return MODEL_SCRIPT
    return MODEL


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
    if _has_dedicated_llm_key(role):
        return _complete_http_messages(
            messages,
            stream=stream,
            role=role,
            model=model,
            config=config,
        )
    cursor_key = os.environ.get("CURSOR_API_KEY", "").strip()
    if cursor_key:
        if stream:
            print(
                f"[llm] fallback: Cursor Agent.prompt role={role or 'any'}",
                file=sys.stderr,
            )
        return _complete_cursor_thread(messages, api_key=cursor_key, role=role)
    raise RuntimeError(
        "Set LLM_API_KEY / DEEPSEEK_API_KEY / MOONSHOT_API_KEY / OPENAI_API_KEY, "
        "or CURSOR_API_KEY"
    )


def _has_dedicated_llm_key(role: Role | None = None) -> bool:
    if role:
        for name in _ROLE_KEY_ENV[role]:
            if os.environ.get(name, "").strip():
                return True
    for name in ("LLM_API_KEY", "DEEPSEEK_API_KEY", "MOONSHOT_API_KEY", "OPENAI_API_KEY"):
        if os.environ.get(name, "").strip():
            return True
    return False


def _complete_http_messages(
    messages: list[dict[str, str]],
    *,
    stream: bool,
    role: Role | None,
    model: str | None,
    config: Any = None,
) -> str:
    api_key = _resolve_api_key(role)
    base_url = _resolve_base_url(api_key, role)
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


def _complete_cursor_thread(
    messages: list[dict[str, str]],
    *,
    api_key: str,
    role: Role | None,
) -> str:
    import tempfile

    from cursor_sdk import Agent, AgentOptions, Client, LocalAgentOptions

    tmp = tempfile.mkdtemp(prefix="memnet_beat_")
    local = LocalAgentOptions(cwd=tmp, setting_sources=[])
    opts = AgentOptions(
        model=_resolve_model(role),
        api_key=api_key,
        local=local,
    )
    parts: list[str] = []
    for msg in messages:
        r, c = msg.get("role", ""), msg.get("content", "")
        if r == "system":
            parts.append(f"[system]\n{c}")
        elif r == "user":
            parts.append(f"[user]\n{c}")
        elif r == "assistant":
            parts.append(f"[assistant]\n{c}")
    parts.append(
        "\nReply as assistant to the latest [user] only. "
        "Do NOT use tools or read files."
    )
    client = Client.launch_bridge(workspace=tmp, local=local)
    try:
        result = Agent.prompt("\n\n".join(parts), opts, client=client)
    finally:
        client.close()
    status = getattr(result.status, "value", result.status)
    if str(status).lower() not in ("finished", "runstatus.finished"):
        raise RuntimeError(f"Cursor prompt status: {result.status}")
    text = (result.result or "").strip()
    if not text:
        raise RuntimeError("Cursor prompt returned empty result")
    return text
