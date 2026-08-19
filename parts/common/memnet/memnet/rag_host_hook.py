"""RagHostHook — host Snap locators outside MemNetSystem (extra 0.17).

Given a cue, return locators or skip. Default = skip (fail-open). Optional
``MEMNET_HOST_SEARCH_URL`` (do not vendor a RAG server) and optional extra
0.16 ``MEMNET_NEO4J_LIBRARY_DATABASE`` locators. Shape stays ``pin_map`` of
session S. Host search MUST NOT absorb. MUST NOT register MCP ``rag_query``.
MUST NOT Snap-on-session (no ANN of S). Hid / generate / chunk bodies stay
off the emit.

Commit path is existing MutateGate / PinMapIngest. leftover
``allocate_from_locator`` as PK stays leftover.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from memnet.durable.neo4j_library import locator_fields as library_locator_fields
from memnet.durable.neo4j_library import make_library_client_from_env
from memnet.gql import _emit_props
from memnet.mutate_gate import MutateGate, MutateResult
from memnet.pin_map_ingest import IngestResult, ingest_codebase, ingest_pcba, ingest_sysml

ENV_HOST_URL = "MEMNET_HOST_SEARCH_URL"
ENV_HOST_TIMEOUT = "MEMNET_HOST_SEARCH_TIMEOUT_S"

IMPLEMENTED = True
DESIGN_ONLY = False
FAIL_OPEN = True
LOCATOR_ONLY = True
SNAP_ON_SESSION = False
MCP_RAG_QUERY = False
HOST_SEARCH_INSIDE_SYSTEM = False

DEFAULT_TIMEOUT_S = 2.0
DEFAULT_MAX_HITS = 8

LOCATOR_KEYS = ("path", "line", "qname", "document_id", "session", "url")
_OFF_EMIT = frozenset(
    {
        "_memnet_hid",
        "_memnet_tag",
        "hid",
        "elementId",
        "element_id",
        "identity",
        "generate",
        "note",
        "chunk",
        "chunks",
        "text",
        "body",
        "embedding",
        "embeddings",
        "score",
        "rrf",
        "ppr",
    }
)

_INGEST_SUFFIX = {
    ".sysml": ingest_sysml,
    ".py": ingest_codebase,
    ".ato": ingest_pcba,
}


@dataclass(frozen=True)
class HostSearchCue:
    """Bounded host cue. MUST NOT carry session S."""

    question: str
    session_id: str | None = None
    anchor: str | None = None
    max_hits: int = DEFAULT_MAX_HITS
    timeout_s: float = DEFAULT_TIMEOUT_S


@dataclass(frozen=True)
class HostSearchResult:
    """Locator-only Snap, or skip. Empty locators with skipped=True is valid."""

    skipped: bool = True
    locators: tuple[dict[str, str], ...] = ()
    reason: str = "host_search_skip"


class RagHostHook(Protocol):
    """Outside MemNetSystem: cue → locators or skip. MUST NOT mutate S."""

    def propose(self, cue: HostSearchCue) -> HostSearchResult: ...


_installed: RagHostHook | None = None


def set_rag_host_hook(hook: RagHostHook | None) -> None:
    """Install a process hook (tests / host adapter). None restores env default."""
    global _installed
    _installed = hook


def active_hook() -> RagHostHook:
    if _installed is not None:
        return _installed
    return EnvRagHostHook()


def sanitise_locator(raw: Mapping[str, Any] | None) -> dict[str, str]:
    """Keep locator properties only; strip hid / generate / chunk bodies."""
    out: dict[str, str] = {}
    if not raw:
        return out
    for key, val in raw.items():
        if key in _OFF_EMIT or str(key).startswith("_memnet"):
            continue
        if key not in LOCATOR_KEYS:
            continue
        text = "" if val is None else str(val).strip()
        if text:
            out[key] = text
    return out


def locators_to_gql(locators: Sequence[Mapping[str, str]], *, kind: str = "MOD") -> list[str]:
    """CREATE locator property pins. Locators are properties, not a store key."""
    lines: list[str] = []
    for loc in locators:
        clean = sanitise_locator(loc)
        if not clean:
            continue
        label = "SYM" if "line" in clean else kind
        props = _emit_props(clean)
        lines.append(f"CREATE (:{label} {props})")
    return lines


class SkipRagHostHook:
    """Default fail-open: unset host → skip. Goldfish continues."""

    implemented = True

    def propose(self, cue: HostSearchCue) -> HostSearchResult:
        _ = cue
        return HostSearchResult(skipped=True, locators=(), reason="host_search_skip:unset")


class EnvRagHostHook:
    """Optional URL and/or 0.16 library locators. Miss / timeout → skip."""

    implemented = True

    def propose(self, cue: HostSearchCue) -> HostSearchResult:
        found: list[dict[str, str]] = []
        url = (os.environ.get(ENV_HOST_URL) or "").strip()
        if url:
            found.extend(_http_locators(url, cue))
        found.extend(_library_locators(cue))
        deduped = _dedupe(found)
        if not deduped:
            return HostSearchResult(
                skipped=True,
                locators=(),
                reason="host_search_skip:miss",
            )
        return HostSearchResult(
            skipped=False,
            locators=tuple(deduped[: max(1, int(cue.max_hits))]),
            reason="host_search_locators",
        )


def propose_locators(
    question: str,
    *,
    session_id: str | None = None,
    anchor: str | None = None,
    max_hits: int = DEFAULT_MAX_HITS,
    timeout_s: float | None = None,
    hook: RagHostHook | None = None,
) -> HostSearchResult:
    """Run the active (or given) hook. Skip is valid. MUST NOT mutate S."""
    timeout = DEFAULT_TIMEOUT_S if timeout_s is None else float(timeout_s)
    cue = HostSearchCue(
        question=question,
        session_id=session_id,
        anchor=anchor,
        max_hits=max_hits,
        timeout_s=timeout,
    )
    return (hook or active_hook()).propose(cue)


@dataclass
class HostLocatorCommit:
    """Commit outcome via existing MutateGate / ingest. Not ImportAbsorb."""

    skipped: bool = False
    mutate: MutateResult | None = None
    ingest: list[IngestResult] = field(default_factory=list)
    gql_lines: list[str] = field(default_factory=list)


def commit_locators(
    session,
    locators: Sequence[Mapping[str, str]],
    *,
    mutate: MutateGate | None = None,
    ingest_existing_paths: bool = True,
) -> HostLocatorCommit:
    """Commit locator properties. MUST NOT absorb. leftover locator-as-PK unused."""
    clean = [sanitise_locator(loc) for loc in locators]
    clean = [loc for loc in clean if loc]
    if not clean:
        return HostLocatorCommit(skipped=True)

    ingested: list[IngestResult] = []
    rest: list[dict[str, str]] = []
    if ingest_existing_paths:
        for loc in clean:
            result = _maybe_ingest_path(session, loc)
            if result is not None:
                ingested.append(result)
            else:
                rest.append(loc)
    else:
        rest = clean

    lines = locators_to_gql(rest)
    mutate_result: MutateResult | None = None
    if lines:
        gate = mutate or MutateGate(session)
        mutate_result = gate.apply(lines, mode="add", require_bind=False)
    return HostLocatorCommit(
        skipped=False,
        mutate=mutate_result,
        ingest=ingested,
        gql_lines=lines,
    )


def propose_and_commit(
    session,
    question: str,
    *,
    session_id: str | None = None,
    anchor: str | None = None,
    max_hits: int = DEFAULT_MAX_HITS,
    hook: RagHostHook | None = None,
) -> tuple[HostSearchResult, HostLocatorCommit]:
    """Snap then existing Commit. Skip both when the hook misses."""
    proposed = propose_locators(
        question,
        session_id=session_id,
        anchor=anchor,
        max_hits=max_hits,
        hook=hook,
    )
    if proposed.skipped or not proposed.locators:
        return proposed, HostLocatorCommit(skipped=True)
    return proposed, commit_locators(session, proposed.locators)


def _timeout_s() -> float:
    raw = (os.environ.get(ENV_HOST_TIMEOUT) or "").strip()
    if not raw:
        return DEFAULT_TIMEOUT_S
    try:
        return max(0.1, float(raw))
    except ValueError:
        return DEFAULT_TIMEOUT_S


def _http_locators(url: str, cue: HostSearchCue) -> list[dict[str, str]]:
    payload = {
        "question": cue.question,
        "anchor": cue.anchor,
        "max_hits": cue.max_hits,
        # capability only — not the session graph
        "session": cue.session_id,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    timeout = cue.timeout_s or _timeout_s()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return []
    return _parse_host_json(raw)


def _parse_host_json(raw: str) -> list[dict[str, str]]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    if data.get("skip") is True or data.get("skipped") is True:
        return []
    rows = data.get("locators")
    if rows is None:
        rows = data.get("hits")
    if not isinstance(rows, list):
        return []
    out: list[dict[str, str]] = []
    for row in rows:
        if isinstance(row, Mapping):
            loc = sanitise_locator(row)
            if loc:
                out.append(loc)
    return out


def _library_locators(cue: HostSearchCue) -> list[dict[str, str]]:
    client = make_library_client_from_env()
    if client is None:
        return []
    try:
        rows = client.emit_locators(cue.question, limit=cue.max_hits)
    except Exception:  # noqa: BLE001 — fail-open skip
        return []
    finally:
        try:
            client.close()
        except Exception:  # noqa: BLE001
            pass
    out: list[dict[str, str]] = []
    for row in rows:
        loc = sanitise_locator(library_locator_fields(row))
        if loc:
            out.append(loc)
    return out


def _maybe_ingest_path(session, loc: Mapping[str, str]) -> IngestResult | None:
    path_s = loc.get("path") or ""
    if not path_s:
        return None
    path = Path(path_s)
    if not path.is_file():
        return None
    fn = _INGEST_SUFFIX.get(path.suffix.lower())
    if fn is None:
        return None
    return fn(session, path)


def _dedupe(rows: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[tuple[str, str], ...]] = set()
    out: list[dict[str, str]] = []
    for row in rows:
        loc = sanitise_locator(row)
        if not loc:
            continue
        key = tuple(sorted(loc.items()))
        if key in seen:
            continue
        seen.add(key)
        out.append(loc)
    return out
