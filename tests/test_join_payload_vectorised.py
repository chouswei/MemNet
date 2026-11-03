"""wire.join_payload is vectorised, byte-identical to the old per-char loop."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import memnet.output
import memnet.wire
from memnet.config import Caps
from memnet.snapshot import load_snapshot, load_snapshot_text, snapshot_text
from memnet.wire import _SPLITLINES_ESC, escaped_utf8_len, join_payload

FIXTURES = Path(__file__).parent / "fixtures"
SNAPSHOTS = ["snapshot-0.19.18.snap", "snapshot-0.19.27.snap"]


def _old_join_payload(fields: list[str]) -> str:
    out: list[str] = []
    for field in fields:
        escaped: list[str] = []
        for ch in field:
            if ch == "\\":
                escaped.append("\\\\")
            elif ch == "|":
                escaped.append("\\|")
            elif ch in _SPLITLINES_ESC:
                escaped.append(_SPLITLINES_ESC[ch])
            else:
                escaped.append(ch)
        out.append("".join(escaped))
    return "|".join(out)


_ALPHABET = st.one_of(
    st.sampled_from(list("\\|\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029abc xyz0")),
    st.sampled_from(["\U0001f600", "\U00010348", "测", "é"]),
    st.characters(blacklist_categories=["Cs"]),
)
_FIELD = st.text(alphabet=_ALPHABET, max_size=60)
_FIELDS = st.one_of(
    st.just([]),
    st.just([""]),
    st.lists(_FIELD, max_size=8),
)


@settings(max_examples=300, deadline=None)
@given(_FIELDS)
def test_join_payload_matches_old_loop(fields):
    assert memnet.wire.join_payload(fields) == _old_join_payload(fields)


@settings(max_examples=300, deadline=None)
@given(_FIELD)
def test_escaped_utf8_len_matches_old_loop(value):
    assert escaped_utf8_len(value) == len(_old_join_payload([value]).encode("utf-8"))


def _without_header_ids(text: str) -> str:
    # the @SNAP line carries a fresh session id and timestamps on every load
    return "\n".join(ln for ln in text.split("\n") if not ln.startswith("@SNAP:"))


@pytest.mark.parametrize("name", SNAPSHOTS)
def test_snapshot_text_unchanged(memnet_temp, monkeypatch, name):
    ss = load_snapshot(FIXTURES / name, caps=Caps())
    current = snapshot_text(ss)
    monkeypatch.setattr(memnet.output, "join_payload", _old_join_payload)
    monkeypatch.setattr(memnet.wire, "join_payload", _old_join_payload)
    assert snapshot_text(ss) == current
    monkeypatch.undo()
    again = snapshot_text(load_snapshot_text(current, caps=Caps()))
    assert _without_header_ids(again) == _without_header_ids(current)


def _best(fn, fields, n=3):
    best = float("inf")
    for _ in range(n):
        t0 = time.perf_counter()
        fn(fields)
        best = min(best, time.perf_counter() - t0)
    return best


def test_join_payload_is_much_faster_than_old_loop():
    chunk = "plain text with words " * 1300 + "a|b\\c\nd " * 40
    fields = [chunk[:30000] for _ in range(36)]
    assert sum(len(f) for f in fields) > 1_000_000
    assert join_payload(fields) == _old_join_payload(fields)
    new = _best(memnet.wire.join_payload, fields)
    old = _best(_old_join_payload, fields)
    assert new <= old / 5, f"new={new:.4f}s old={old:.4f}s ratio={old / new:.2f}"
