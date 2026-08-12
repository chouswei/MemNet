"""GqlCodec — SysML part name; gated openCypher-shaped agent wire (M2)."""

from __future__ import annotations

from memnet.gql import (
    Document,
    EdgeRec,
    Field,
    LintIssue,
    NodeRec,
    Op,
    ParseError,
    Section,
    emit,
    emit_edge_shaped,
    emit_item,
    emit_node_shaped,
    looks_like_gql,
    looks_like_legacy_layer_or_tier_a,
    parse,
    round_trip_ok,
    soft_validate,
)

__all__ = [
    "GqlCodec",
    "Document",
    "EdgeRec",
    "Field",
    "LintIssue",
    "NodeRec",
    "Op",
    "ParseError",
    "Section",
    "emit",
    "emit_edge_shaped",
    "emit_item",
    "emit_node_shaped",
    "looks_like_gql",
    "looks_like_legacy_layer_or_tier_a",
    "parse",
    "round_trip_ok",
    "soft_validate",
]


class GqlCodec:
    """Primary agent wire SSOT: parse/emit gated openCypher-shaped GQL."""

    def parse(self, text: str) -> Document:
        return parse(text)

    def emit(self, doc: Document, *, as_mutate: bool = False) -> str:
        return emit(doc, as_mutate=as_mutate)

    def soft_validate(self, doc: Document) -> list[LintIssue]:
        return soft_validate(doc)

    def round_trip_ok(self, text: str) -> bool:
        return round_trip_ok(text)
