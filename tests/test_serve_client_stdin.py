"""CLI dispatch forwards --stdin to TCP send_command."""

from __future__ import annotations

from memnet.serve_client import _stdin_for_proxy


def test_stdin_for_proxy_none_without_flag():
    assert _stdin_for_proxy(["add", "--session", "s1"]) is None


def test_stdin_for_proxy_reads_stdin(monkeypatch):
    import io
    import sys

    monkeypatch.setattr(sys, "stdin", io.StringIO("CREATE (:COM {id: 'COM_x'})\n"))
    text = _stdin_for_proxy(["add", "--stdin", "--session", "s1"])
    assert "COM_x" in text
