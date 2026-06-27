"""Tests for orchestrator wire parsing."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "applications" / "novel_cursor"))

from wire_parse import extract_wire_lines, normalise_options, parse_prose_payload  # noqa: E402


def test_extract_wire_lines_oln() -> None:
    text = "hello\n@OLN: OLN99|1|test|要点|对白|钩子|persistent\n"
    assert extract_wire_lines(text, "oln") == [
        "@OLN: OLN99|1|test|要点|对白|钩子|persistent"
    ]


def test_parse_prose_payload_fenced() -> None:
    text = '```json\n{"prose": "正文", "options": ["1"], "hud": "h"}\n```'
    obj = parse_prose_payload(text)
    assert obj is not None
    assert obj["prose"] == "正文"


def test_normalise_options_pads() -> None:
    assert len(normalise_options(["a", "b"])) == 6
