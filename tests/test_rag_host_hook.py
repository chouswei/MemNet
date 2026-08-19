"""Extra 0.17: RagHostHook locators outside MemNetSystem; skip is valid."""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path

from memnet.config import examples_dir
from memnet.id_allocator import IdAllocator
from memnet.import_absorb import ImportAbsorb
from memnet.pin_map_composer import PinMapComposer
from memnet.pin_map_ingest import ingest_sysml
from memnet.rag_host_hook import (
    DESIGN_ONLY,
    FAIL_OPEN,
    HOST_SEARCH_INSIDE_SYSTEM,
    IMPLEMENTED,
    LOCATOR_ONLY,
    MCP_RAG_QUERY,
    SNAP_ON_SESSION,
    EnvRagHostHook,
    HostSearchCue,
    HostSearchResult,
    SkipRagHostHook,
    commit_locators,
    locators_to_gql,
    propose_and_commit,
    propose_locators,
    sanitise_locator,
    set_rag_host_hook,
)
from memnet.session import open_session


class _StubHook:
    def __init__(self, locators: list[dict[str, str]] | None = None, skipped: bool = False) -> None:
        self.locators = locators or []
        self.skipped = skipped
        self.seen: list[HostSearchCue] = []

    def propose(self, cue: HostSearchCue) -> HostSearchResult:
        self.seen.append(cue)
        if self.skipped:
            return HostSearchResult(skipped=True, reason="host_search_skip:stub")
        return HostSearchResult(
            skipped=False,
            locators=tuple(self.locators),
            reason="host_search_locators",
        )


def _codebase_session():
    return open_session(map_file=str(examples_dir() / "schema.codebase.example.txt"))


def test_module_honesty_flags():
    assert IMPLEMENTED is True
    assert DESIGN_ONLY is False
    assert FAIL_OPEN is True
    assert LOCATOR_ONLY is True
    assert SNAP_ON_SESSION is False
    assert MCP_RAG_QUERY is False
    assert HOST_SEARCH_INSIDE_SYSTEM is False


def test_skip_is_valid_when_unset(monkeypatch, memnet_temp):
    monkeypatch.delenv("MEMNET_HOST_SEARCH_URL", raising=False)
    monkeypatch.delenv("MEMNET_NEO4J_LIBRARY_DATABASE", raising=False)
    monkeypatch.delenv("MEMNET_NEO4J_URL", raising=False)
    set_rag_host_hook(None)
    ss = _codebase_session()
    proposed, committed = propose_and_commit(ss, "session_open")
    assert proposed.skipped is True
    assert proposed.locators == ()
    assert committed.skipped is True
    assert SkipRagHostHook().propose(HostSearchCue(question="x")).skipped is True


def test_locators_strip_chunks_and_hid():
    got = sanitise_locator(
        {
            "path": "parts/memnet-mcp/software/memnet_mcp/server.py",
            "line": "59",
            "note": "chunk body",
            "chunk": "the retrieved text",
            "embedding": "[0.1, 0.2]",
            "_memnet_hid": "el9",
            "hid": "secret",
            "generate": True,
            "rrf": "1",
        }
    )
    assert got == {
        "path": "parts/memnet-mcp/software/memnet_mcp/server.py",
        "line": "59",
    }
    gql = locators_to_gql([got])
    assert gql
    blob = " ".join(gql).lower()
    assert "create (:sym" in blob
    assert "server.py" in blob
    assert "note" not in blob
    assert "generate" not in blob
    assert "rag_query" not in blob
    assert "_memnet_hid" not in blob


def test_commit_locators_via_mutate_not_absorb(memnet_temp):
    set_rag_host_hook(_StubHook([{"path": "docs/SHAPE.md", "document_id": "DOC_shape"}]))
    ss = _codebase_session()
    proposed, committed = propose_and_commit(ss, "shape", session_id="mn_secret")
    assert proposed.skipped is False
    assert committed.skipped is False
    assert committed.mutate is not None
    assert "CREATE (:MOD" in " ".join(committed.gql_lines)
    mods = [r for r in ss.store.list_records("MOD") if r.fields.get("path") == "docs/SHAPE.md"]
    assert len(mods) == 1
    assert mods[0].fields.get("document_id") == "DOC_shape"
    assert mods[0].hid not in " ".join(committed.gql_lines)
    src = inspect.getsource(commit_locators)
    assert "allocate_from_locator" not in src
    assert "ImportAbsorb" not in src
    assert "import_slice" not in src
    set_rag_host_hook(None)


def test_hook_does_not_mutate_session(memnet_temp):
    ss = _codebase_session()
    hook = _StubHook([{"path": "docs/ROADMAP.md"}])
    before = list(ss.store.list_records("MOD"))
    result = hook.propose(HostSearchCue(question="roadmap", session_id="mn_cap"))
    after = list(ss.store.list_records("MOD"))
    assert result.skipped is False
    assert before == after
    assert hook.seen[0].session_id == "mn_cap"


def test_ingest_existing_path(memnet_temp, tmp_path: Path):
    ss = _codebase_session()
    src = tmp_path / "hello.py"
    src.write_text("def greet():\n    return 1\n", encoding="utf-8")
    committed = commit_locators(ss, [{"path": str(src)}])
    assert committed.skipped is False
    assert committed.ingest
    assert committed.ingest[0].committed is True
    assert committed.ingest[0].node_count >= 1


def test_http_host_timeout_skips(monkeypatch, memnet_temp):
    monkeypatch.setenv("MEMNET_HOST_SEARCH_URL", "http://127.0.0.1:1/search")
    monkeypatch.setenv("MEMNET_HOST_SEARCH_TIMEOUT_S", "0.2")
    monkeypatch.delenv("MEMNET_NEO4J_LIBRARY_DATABASE", raising=False)
    set_rag_host_hook(None)
    result = EnvRagHostHook().propose(HostSearchCue(question="x", timeout_s=0.2))
    assert result.skipped is True
    ss = _codebase_session()
    proposed, committed = propose_and_commit(ss, "x")
    assert proposed.skipped is True
    assert committed.skipped is True


def test_library_locators_consumed_as_host_source(monkeypatch):
    monkeypatch.setenv("MEMNET_NEO4J_URL", "bolt://127.0.0.1:7687")
    monkeypatch.setenv("MEMNET_NEO4J_LIBRARY_DATABASE", "library")
    monkeypatch.delenv("MEMNET_HOST_SEARCH_URL", raising=False)

    class _Lib:
        def emit_locators(self, cue, *, limit=8):
            assert cue == "shape"
            return [{"path": "docs/SHAPE.md", "_memnet_hid": "el1", "generate": True}]

        def close(self):
            return None

    monkeypatch.setattr(
        "memnet.rag_host_hook.make_library_client_from_env",
        lambda: _Lib(),
    )
    set_rag_host_hook(None)
    result = EnvRagHostHook().propose(HostSearchCue(question="shape"))
    assert result.skipped is False
    assert result.locators == ({"path": "docs/SHAPE.md"},)
    assert "generate" not in result.locators[0]
    assert "_memnet_hid" not in result.locators[0]


def test_locators_are_not_rag_query_and_pin_map_does_not_rrf():
    src = inspect.getsource(PinMapComposer)
    lowered = src.lower()
    for token in ("rrf", "ppr", "leiden", "reciprocal_rank", "generate("):
        assert token not in lowered
    hook_src = inspect.getsource(EnvRagHostHook)
    assert "rag_query" not in hook_src
    assert "pin_map.generate" not in hook_src
    absorb_src = inspect.getsource(ImportAbsorb)
    assert "RagHostHook" not in absorb_src
    ingest_src = inspect.getsource(ingest_sysml)
    assert "rag_query" not in ingest_src


def test_snap_on_session_forbidden_in_hook():
    hook_src = inspect.getsource(propose_locators) + inspect.getsource(EnvRagHostHook.propose)
    lowered = hook_src.lower()
    assert "embed" not in lowered
    assert "ann" not in lowered
    cue_src = inspect.getsource(HostSearchCue)
    assert "records" not in cue_src
    assert "pin_map" not in cue_src


def test_leftover_locator_pk_unused_by_host_commit():
    alloc_src = inspect.getsource(IdAllocator.allocate_from_locator)
    commit_src = inspect.getsource(commit_locators)
    assert "allocate_from_locator" not in commit_src
    assert "locator" in alloc_src


def test_mcp_does_not_register_rag_query(memnet_temp):
    from memnet_mcp.server import mcp

    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert "rag_query" not in names
    assert "host_search" not in names
    import memnet_mcp.server as server_mod

    server_src = inspect.getsource(server_mod)
    assert "@mcp.tool()\nasync def rag_query" not in server_src
    assert 'name="rag_query"' not in server_src
    assert "RagHostHook" not in server_src
