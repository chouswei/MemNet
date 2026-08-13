"""CheapLlmImportGuard — optional OpenAI-compatible soft ImportGuard (MN-REQ-12.11 / #63).

Off unless ``MEMNET_IMPORT_GUARD_API_KEY`` is set (GuardPassthrough / no host hook).
When enabled, reviews a *bounded* WorkingMemorySlice summary and returns
``ImportGuardDecision`` only — guard chat is never SSOT. Transport / parse
failures soft-skip (allow passthrough) with ``@WRN``; never hang import.
Does not replace ImportAbsorb hard gates. Path A never enters this module.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from memnet.import_absorb import ImportGuardDecision, WorkingMemorySlice, set_import_guard
from memnet.output import emit_wrn

ENV_API_KEY = "MEMNET_IMPORT_GUARD_API_KEY"
ENV_BASE_URL = "MEMNET_IMPORT_GUARD_BASE_URL"
ENV_MODEL = "MEMNET_IMPORT_GUARD_MODEL"

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_TIMEOUT_S = 8.0

# Bound the HTTP payload — never ship the whole artefact / chat dump.
_MAX_SUMMARY_RECORDS = 48
_MAX_FIELD_CHARS = 80
_MAX_REASON_CHARS = 200
_SHORT_FIELD_KEYS = (
    "path",
    "note",
    "kind",
    "goal",
    "status",
    "recycle",
    "refdes",
    "src",
    "dist",
    "relation",
)


@dataclass(frozen=True)
class CheapLlmImportGuardConfig:
    """Runtime config for the optional cheap-LLM ImportGuard adapter."""

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout_s: float = DEFAULT_TIMEOUT_S


PostJsonFn = Callable[[str, dict[str, str], bytes, float], str]


def config_from_env() -> CheapLlmImportGuardConfig | None:
    """Return config when ``MEMNET_IMPORT_GUARD_API_KEY`` is non-empty; else None."""
    key = (os.environ.get(ENV_API_KEY) or "").strip()
    if not key:
        return None
    base = (os.environ.get(ENV_BASE_URL) or "").strip() or DEFAULT_BASE_URL
    model = (os.environ.get(ENV_MODEL) or "").strip() or DEFAULT_MODEL
    return CheapLlmImportGuardConfig(api_key=key, base_url=base.rstrip("/"), model=model)


def summarise_slice(slice_: WorkingMemorySlice) -> dict[str, Any]:
    """Bounded slice digest for the LLM (ids / tags / short fields / anchors)."""
    records: list[dict[str, Any]] = []
    for rec in slice_.records[:_MAX_SUMMARY_RECORDS]:
        short: dict[str, str] = {}
        for key in _SHORT_FIELD_KEYS:
            val = rec.fields.get(key)
            if not val:
                continue
            text = str(val)
            if len(text) > _MAX_FIELD_CHARS:
                text = text[: _MAX_FIELD_CHARS - 1] + "…"
            short[key] = text
        records.append({"id": rec.id, "tag": rec.tag, "fields": short})
    return {
        "source_session_id": slice_.source_session_id,
        "anchors": list(slice_.anchors),
        "depth": slice_.depth,
        "view": slice_.view,
        "record_count": len(slice_.records),
        "records_truncated": len(slice_.records) > _MAX_SUMMARY_RECORDS,
        "records": records,
    }


def _system_prompt() -> str:
    return (
        "You are MemNet CheapLlmImportGuard (soft policy only). "
        "Review a bounded WorkingMemorySlice summary for Path-B session import. "
        "Reply with JSON only (no markdown fences) matching:\n"
        '{"outcome":"allow"|"trim"|"reject","reason":"<short>",'
        '"keep_ids":["id",...]}\n'
        "Rules: outcome=trim requires keep_ids (subtractive; ids to keep). "
        "outcome=allow|reject: omit keep_ids or use []. "
        "Never invent ids not present in the summary. "
        "Hard gates run after you — soft review only."
    )


def _user_prompt(summary: dict[str, Any]) -> str:
    return "Slice summary:\n" + json.dumps(summary, ensure_ascii=False, separators=(",", ":"))


def _post_json_urllib(
    url: str,
    headers: dict[str, str],
    body: bytes,
    timeout_s: float,
) -> str:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310 — URL from env
        return resp.read().decode("utf-8")


def _chat_completions_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/chat/completions"


def call_chat_completion(
    config: CheapLlmImportGuardConfig,
    *,
    summary: dict[str, Any],
    post_json: PostJsonFn | None = None,
) -> str:
    """POST OpenAI-compatible chat.completions; returns assistant message content.

    Never logs or returns the API key.
    """
    payload = {
        "model": config.model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": _user_prompt(summary)},
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    url = _chat_completions_url(config.base_url)
    poster = post_json or _post_json_urllib
    raw = poster(url, headers, body, config.timeout_s)
    data = json.loads(raw)
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("empty_choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("empty_content")
    return content


def _extract_json_object(text: str) -> dict[str, Any]:
    raw = text.strip()
    if raw.startswith("```"):
        # Tolerate accidental fences; still require a JSON object.
        lines = [ln for ln in raw.splitlines() if not ln.strip().startswith("```")]
        raw = "\n".join(lines).strip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            raise
        obj = json.loads(raw[start : end + 1])
    if not isinstance(obj, dict):
        raise ValueError("not_object")
    return obj


def parse_guard_decision(
    text: str,
    slice_: WorkingMemorySlice,
) -> ImportGuardDecision:
    """Map model JSON to ImportGuardDecision; raises on bad shape."""
    obj = _extract_json_object(text)
    outcome = str(obj.get("outcome") or "").strip().lower()
    reason = str(obj.get("reason") or "").strip() or f"cheap_llm:{outcome or 'unknown'}"
    reason = reason[:_MAX_REASON_CHARS]
    if outcome not in ("allow", "trim", "reject"):
        raise ValueError(f"bad_outcome:{outcome!r}")
    keep_ids: set[str] | None = None
    if outcome == "trim":
        raw_keep = obj.get("keep_ids")
        if not isinstance(raw_keep, list) or not raw_keep:
            raise ValueError("trim_requires_keep_ids")
        known = {r.id for r in slice_.records}
        keep_ids = {str(x) for x in raw_keep if str(x) in known}
        if not keep_ids:
            raise ValueError("trim_keep_ids_unknown")
    return ImportGuardDecision(outcome=outcome, reason=reason, keep_ids=keep_ids)  # type: ignore[arg-type]


def _soft_skip(code: str, detail: str) -> ImportGuardDecision:
    """Transport/parse failure → passthrough allow + @WRN (soft policy)."""
    msg = detail.replace("|", " ")[:160]
    emit_wrn(code, msg)
    return ImportGuardDecision(
        outcome="allow",
        reason=f"import_guard_skip:{code}:{msg}"[:_MAX_REASON_CHARS],
    )


def make_cheap_llm_guard(
    config: CheapLlmImportGuardConfig,
    *,
    post_json: PostJsonFn | None = None,
) -> Callable[[WorkingMemorySlice], ImportGuardDecision]:
    """Build a host-hook callable for ``set_import_guard``."""

    def guard(slice_: WorkingMemorySlice) -> ImportGuardDecision:
        try:
            summary = summarise_slice(slice_)
            content = call_chat_completion(config, summary=summary, post_json=post_json)
            return parse_guard_decision(content, slice_)
        except TimeoutError:
            return _soft_skip("import_guard_timeout", f"timeout>{config.timeout_s}s")
        except urllib.error.HTTPError as exc:
            return _soft_skip("import_guard_http", f"HTTP {exc.code}")
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            return _soft_skip("import_guard_http", f"URLError {type(reason).__name__}")
        except (json.JSONDecodeError, ValueError, KeyError, TypeError, OSError) as exc:
            return _soft_skip("import_guard_bad_json", f"{type(exc).__name__}")

    return guard


def cheap_llm_guard(slice_: WorkingMemorySlice) -> ImportGuardDecision:
    """Process-default guard: reads env each call (key must already be present)."""
    cfg = config_from_env()
    if cfg is None:
        # Should not be installed without a key; soft-skip if mis-wired.
        return _soft_skip("import_guard_no_key", "MEMNET_IMPORT_GUARD_API_KEY unset")
    return make_cheap_llm_guard(cfg)(slice_)


def maybe_install_cheap_llm_import_guard(*, overwrite: bool = False) -> bool:
    """Install ``cheap_llm_guard`` when the API key env is set.

    Returns True if the process-wide hook was set to the cheap-LLM adapter.
    Does not overwrite an existing host hook unless ``overwrite`` is True.
    Never prints the API key.
    """
    from memnet.import_absorb import get_import_guard

    cfg = config_from_env()
    if cfg is None:
        return False
    existing = get_import_guard()
    if existing is not None and not overwrite and existing is not cheap_llm_guard:
        return False
    set_import_guard(cheap_llm_guard)
    return True
