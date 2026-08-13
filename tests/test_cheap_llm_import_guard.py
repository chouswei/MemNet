"""CheapLlmImportGuard adapter (MN-REQ-12.11 / #63) — fake HTTP only."""

from __future__ import annotations

import json
from typing import Any

import pytest

from memnet.cheap_llm_import_guard import (
    ENV_API_KEY,
    ENV_BASE_URL,
    ENV_MODEL,
    CheapLlmImportGuardConfig,
    cheap_llm_guard,
    config_from_env,
    make_cheap_llm_guard,
    maybe_install_cheap_llm_import_guard,
    parse_guard_decision,
    summarise_slice,
)
from memnet.exceptions import MemNetError
from memnet.import_absorb import (
    ImportGuardDecision,
    WorkingMemorySlice,
    get_import_guard,
    import_slice,
    reset_import_guard_for_tests,
)
from memnet.models import Record
from memnet.mutate_gate import MutateGate
from memnet.session import open_session

_MAP = [
    "SCHEMA MOD ; fields=id path note",
    "SCHEMA SYM ; fields=id kind refdes",
    "SCHEMA TSK ; fields=id goal status recycle",
]

_SEED = [
    "CREATE (:MOD {id: 'MOD_amp', path: 'docs/note.md', note: 'amp'})",
    "CREATE (:SYM {id: 'SYM_Rin', kind: 'resistor', refdes: 'Rin'})",
    "CREATE (:SYM {id: 'SYM_scratch', kind: 'noise', refdes: 'X'})",
    "MATCH (a {id: 'MOD_amp'}), (b {id: 'SYM_Rin'})\n"
    "CREATE (a)-[:mentions {id: 'EDG_amp_rin', recycle: 'persistent'}]->(b)",
    "MATCH (a {id: 'MOD_amp'}), (b {id: 'SYM_scratch'})\n"
    "CREATE (a)-[:mentions {id: 'EDG_amp_scratch', recycle: 'persistent'}]->(b)",
]


@pytest.fixture(autouse=True)
def _clean_guard_env(monkeypatch):
    reset_import_guard_for_tests()
    for name in (ENV_API_KEY, ENV_BASE_URL, ENV_MODEL):
        monkeypatch.delenv(name, raising=False)
    yield
    reset_import_guard_for_tests()


def _pair():
    member = open_session(map_lines=_MAP)
    lead = open_session(map_lines=_MAP)
    MutateGate(member).apply(_SEED, mode="add", allow_new_relation=True)
    return member, lead


def _fake_chat_response(decision: dict[str, Any]) -> str:
    return json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(decision),
                    }
                }
            ]
        }
    )


def _slice_fixture() -> WorkingMemorySlice:
    return WorkingMemorySlice(
        source_session_id="ses_member",
        anchors=["MOD_amp"],
        depth=1,
        view=None,
        records=[
            Record(tag="MOD", fields={"id": "MOD_amp", "path": "p.md", "note": "n"}),
            Record(tag="SYM", fields={"id": "SYM_Rin", "kind": "r", "refdes": "Rin"}),
            Record(
                tag="EDG",
                fields={
                    "id": "EDG_amp_rin",
                    "src": "MOD_amp",
                    "dist": "SYM_Rin",
                    "relation": "mentions",
                    "recycle": "persistent",
                },
            ),
        ],
    )


def test_no_key_skips_install(monkeypatch):
    assert config_from_env() is None
    assert maybe_install_cheap_llm_import_guard() is False
    assert get_import_guard() is None


def test_key_installs_process_guard(monkeypatch):
    monkeypatch.setenv(ENV_API_KEY, "sk-test-not-a-real-key")
    assert maybe_install_cheap_llm_import_guard() is True
    assert get_import_guard() is cheap_llm_guard


def test_summarise_slice_is_bounded():
    slice_ = _slice_fixture()
    summary = summarise_slice(slice_)
    assert summary["anchors"] == ["MOD_amp"]
    assert summary["record_count"] == 3
    assert all("id" in r and "tag" in r for r in summary["records"])
    # Must not dump arbitrary long prose keys as free-form blobs.
    assert "chat" not in json.dumps(summary)


def test_parse_allow_trim_reject():
    slice_ = _slice_fixture()
    allow = parse_guard_decision(
        json.dumps({"outcome": "allow", "reason": "in scope"}),
        slice_,
    )
    assert allow.outcome == "allow"
    trim = parse_guard_decision(
        json.dumps(
            {
                "outcome": "trim",
                "reason": "drop scratch",
                "keep_ids": ["MOD_amp", "SYM_Rin", "EDG_amp_rin"],
            }
        ),
        slice_,
    )
    assert trim.outcome == "trim"
    assert trim.keep_ids == {"MOD_amp", "SYM_Rin", "EDG_amp_rin"}
    reject = parse_guard_decision(
        json.dumps({"outcome": "reject", "reason": "invented ids"}),
        slice_,
    )
    assert reject.outcome == "reject"


def test_key_allow_via_fake_http(memnet_temp, monkeypatch):
    del memnet_temp
    member, lead = _pair()
    monkeypatch.setenv(ENV_API_KEY, "sk-test")

    def post_json(url, headers, body, timeout_s):
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")
        assert "sk-test" not in url
        payload = json.loads(body.decode("utf-8"))
        assert payload["model"]
        assert "messages" in payload
        return _fake_chat_response({"outcome": "allow", "reason": "ok scope"})

    guard = make_cheap_llm_guard(
        CheapLlmImportGuardConfig(api_key="sk-test"),
        post_json=post_json,
    )
    result = import_slice(
        lead_session_id=lead.session_id,
        source_session_id=member.session_id,
        anchors=["MOD_amp"],
        id_policy="keep",
        enable_guard=True,
        guard=guard,
    )
    assert result.guard_skipped is False
    assert result.decision is not None
    assert result.decision.outcome == "allow"
    assert lead.store.get("MOD_amp") is not None


def test_key_trim_via_fake_http(memnet_temp, monkeypatch):
    del memnet_temp
    member, lead = _pair()

    def post_json(_url, _headers, _body, _timeout_s):
        return _fake_chat_response(
            {
                "outcome": "trim",
                "reason": "drop SYM_scratch",
                "keep_ids": ["MOD_amp", "SYM_Rin", "EDG_amp_rin"],
            }
        )

    guard = make_cheap_llm_guard(
        CheapLlmImportGuardConfig(api_key="sk-test"),
        post_json=post_json,
    )
    result = import_slice(
        lead_session_id=lead.session_id,
        source_session_id=member.session_id,
        anchors=["MOD_amp"],
        id_policy="keep",
        enable_guard=True,
        guard=guard,
    )
    assert result.decision is not None
    assert result.decision.outcome == "trim"
    assert lead.store.get("MOD_amp") is not None
    assert lead.store.get("SYM_scratch") is None


def test_key_reject_via_fake_http(memnet_temp, monkeypatch):
    del memnet_temp
    member, lead = _pair()

    def post_json(_url, _headers, _body, _timeout_s):
        return _fake_chat_response({"outcome": "reject", "reason": "off mission noise"})

    guard = make_cheap_llm_guard(
        CheapLlmImportGuardConfig(api_key="sk-test"),
        post_json=post_json,
    )
    with pytest.raises(MemNetError) as ei:
        import_slice(
            lead_session_id=lead.session_id,
            source_session_id=member.session_id,
            anchors=["MOD_amp"],
            id_policy="keep",
            enable_guard=True,
            guard=guard,
        )
    assert ei.value.code == "import_guard_reject"
    assert lead.store.get("MOD_amp") is None


def test_bad_json_passthrough_with_wrn(memnet_temp, monkeypatch, capsys):
    del memnet_temp
    member, lead = _pair()

    def post_json(_url, _headers, _body, _timeout_s):
        return _fake_chat_response({"outcome": "not-a-real-outcome", "reason": "x"})

    guard = make_cheap_llm_guard(
        CheapLlmImportGuardConfig(api_key="sk-test"),
        post_json=post_json,
    )
    result = import_slice(
        lead_session_id=lead.session_id,
        source_session_id=member.session_id,
        anchors=["MOD_amp"],
        id_policy="keep",
        enable_guard=True,
        guard=guard,
    )
    # Soft skip → allow passthrough; hard absorb still runs.
    assert result.decision is not None
    assert result.decision.outcome == "allow"
    assert "import_guard_skip" in (result.decision.reason or "")
    assert lead.store.get("MOD_amp") is not None
    err = capsys.readouterr().err
    assert "@WRN:" in err
    assert "import_guard_bad_json" in err


def test_http_error_passthrough(memnet_temp, monkeypatch, capsys):
    del memnet_temp
    member, lead = _pair()
    import urllib.error

    def post_json(_url, _headers, _body, _timeout_s):
        raise urllib.error.HTTPError(
            "https://api.openai.com/v1/chat/completions",
            503,
            "Unavailable",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )

    guard = make_cheap_llm_guard(
        CheapLlmImportGuardConfig(api_key="sk-test"),
        post_json=post_json,
    )
    result = import_slice(
        lead_session_id=lead.session_id,
        source_session_id=member.session_id,
        anchors=["MOD_amp"],
        enable_guard=True,
        guard=guard,
    )
    assert result.decision is not None
    assert result.decision.outcome == "allow"
    assert lead.store.get("MOD_amp") is not None
    assert "import_guard_http" in capsys.readouterr().err


def test_no_guard_flag_skips_even_with_key(memnet_temp, monkeypatch):
    del memnet_temp
    member, lead = _pair()
    monkeypatch.setenv(ENV_API_KEY, "sk-test")

    def boom(_slice: WorkingMemorySlice) -> ImportGuardDecision:
        return ImportGuardDecision(outcome="reject", reason="must not run")

    # Simulate installed cheap LLM / host hook; --no-guard / enable_guard=False wins.
    from memnet.import_absorb import set_import_guard

    set_import_guard(boom)
    result = import_slice(
        lead_session_id=lead.session_id,
        source_session_id=member.session_id,
        anchors=["MOD_amp"],
        enable_guard=False,
    )
    assert result.guard_skipped is True
    assert lead.store.get("MOD_amp") is not None


def test_api_key_never_appears_in_summary_or_stdout(capsys, monkeypatch):
    monkeypatch.setenv(ENV_API_KEY, "sk-super-secret-key-xyz")
    slice_ = _slice_fixture()
    summary = summarise_slice(slice_)
    blob = json.dumps(summary)
    assert "sk-super-secret-key-xyz" not in blob

    captured: dict[str, Any] = {}

    def post_json(url, headers, body, timeout_s):
        captured["url"] = url
        captured["body"] = body.decode("utf-8")
        # Key is only in Authorization header by design — never echo it.
        assert "sk-super-secret-key-xyz" not in url
        assert "sk-super-secret-key-xyz" not in body.decode("utf-8")
        return _fake_chat_response({"outcome": "allow", "reason": "ok"})

    guard = make_cheap_llm_guard(
        CheapLlmImportGuardConfig(api_key="sk-super-secret-key-xyz"),
        post_json=post_json,
    )
    decision = guard(slice_)
    assert decision.outcome == "allow"
    out = capsys.readouterr()
    assert "sk-super-secret-key-xyz" not in out.out
    assert "sk-super-secret-key-xyz" not in out.err


def test_env_base_url_and_model(monkeypatch):
    monkeypatch.setenv(ENV_API_KEY, "sk-test")
    monkeypatch.setenv(ENV_BASE_URL, "https://example.test/v1/")
    monkeypatch.setenv(ENV_MODEL, "tiny-cheap")
    cfg = config_from_env()
    assert cfg is not None
    assert cfg.base_url == "https://example.test/v1"
    assert cfg.model == "tiny-cheap"

    seen: dict[str, Any] = {}

    def post_json(url, headers, body, timeout_s):
        seen["url"] = url
        seen["model"] = json.loads(body.decode("utf-8"))["model"]
        return _fake_chat_response({"outcome": "allow", "reason": "ok"})

    guard = make_cheap_llm_guard(cfg, post_json=post_json)
    assert guard(_slice_fixture()).outcome == "allow"
    assert seen["url"] == "https://example.test/v1/chat/completions"
    assert seen["model"] == "tiny-cheap"
