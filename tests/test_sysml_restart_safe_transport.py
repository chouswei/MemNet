"""Honesty-c: MN-REQ-06.19 restart-safe transport is modelled and matches the code."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
REQUIREMENTS = MODELS / "requirements.sysml"
VERIFY = MODELS / "verify.sysml"
IMPLEMENTATION = MODELS / "implementation.sysml"
DEPLOY = MODELS / "deploy.sysml"
BEHAVIOUR = MODELS / "behaviour.sysml"
MAP = ROOT / "sysml-models" / "outputs" / "ssot-to-code-allocate-map.md"


def test_requirement_verify_allocate():
    req = REQUIREMENTS.read_text(encoding="utf-8")
    assert "requirement def MN_REQ_06_19_RestartSafeTransport" in req
    assert 'attribute requirementId : String = "MN-REQ-06.19"' in req
    assert "MEMNET_SERVE_RETRY_S" in req
    ver = VERIFY.read_text(encoding="utf-8")
    assert "verification def MN_VER_06_S17_RestartSafeTransport" in ver
    assert 'attribute verificationId : String = "MN-VER-06-S17"' in ver
    assert "retryMod.replaysWriteAfterSend == false" in ver
    impl = IMPLEMENTATION.read_text(encoding="utf-8")
    assert "part def ServeRetryMod" in impl
    assert "allocation serveRetryToMod" in impl
    assert "attribute statelessHttp : Boolean = true" in impl
    deploy = DEPLOY.read_text(encoding="utf-8")
    assert "part clientRetry : ServeClientRetry" in deploy
    assert "attribute pausesThroughBackendRestart : Boolean = true" in deploy
    assert "action def ServeRetryChoice" in BEHAVIOUR.read_text(encoding="utf-8")
    assert "| serveRetryToMod |" in MAP.read_text(encoding="utf-8")


def test_verification_names_live_tests():
    ver = VERIFY.read_text(encoding="utf-8")
    body = ver.split("verification def MN_VER_06_S17_RestartSafeTransport", 1)[1]
    body = body.split("verification def ", 1)[0]
    retry = (ROOT / "tests" / "test_serve_restart_retry.py").read_text(encoding="utf-8")
    http = (ROOT / "tests" / "test_mcp_http.py").read_text(encoding="utf-8")
    for name in (
        "test_connect_refused_then_accept_succeeds_for_read_and_write",
        "test_draining_envelope_honours_retry_after_then_succeeds",
        "test_reset_after_send_on_write_is_not_retried",
        "test_reset_after_send_on_read_is_retried_and_succeeds",
        "test_gateway_pauses_through_backend_restart",
    ):
        assert name in body and f"def {name}(" in retry
    assert "test_tools_call_works_after_restart_without_session_header" in body
    assert "def test_tools_call_works_after_restart_without_session_header(" in http


def test_model_numbers_match_code():
    from memnet import serve_retry
    from memnet_mcp.server import mcp

    impl = IMPLEMENTATION.read_text(encoding="utf-8")
    mod = impl.split("part def ServeRetryMod", 1)[1].split("part def ", 1)[0]
    assert f'budgetEnv : String = "{serve_retry.ENV_RETRY_BUDGET}"' in mod
    assert f"defaultBudgetS : Real = {serve_retry.DEFAULT_RETRY_BUDGET_S}" in mod
    assert f"backoffBaseS : Real = {serve_retry.BACKOFF_BASE_S}" in mod
    assert f"backoffCapS : Real = {serve_retry.BACKOFF_CAP_S}" in mod
    assert mcp.settings.stateless_http is True and mcp.settings.json_response is True
