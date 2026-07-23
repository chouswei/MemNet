"""TierACodec — SysML part name wrapping memnet.tier_a (Write=display SSOT)."""

from __future__ import annotations

from memnet.tier_a import (
    Document,
    EdgeRec,
    Field,
    LintIssue,
    NodeRec,
    Op,
    ParseError,
    Section,
    emit,
    emit_item,
    lint,
    parse,
    parse_line,
    round_trip_ok,
)

__all__ = [
    "TierACodec",
    "Document",
    "EdgeRec",
    "Field",
    "LintIssue",
    "NodeRec",
    "Op",
    "ParseError",
    "Section",
    "emit",
    "emit_item",
    "lint",
    "parse",
    "parse_line",
    "round_trip_ok",
]


class TierACodec:
    """Canonical agent grammar SSOT: parse and emit Tier A Write=display."""

    def parse(self, text: str) -> Document:
        return parse(text)

    def emit(self, doc: Document) -> str:
        return emit(doc)

    def lint(self, doc: Document) -> list[LintIssue]:
        return lint(doc)

    def round_trip_ok(self, text: str) -> bool:
        return round_trip_ok(text)
