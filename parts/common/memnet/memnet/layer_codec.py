"""LayerCodec — proposed 1.x dual-EDGE / ports= / law= Write=display SSOT."""

from __future__ import annotations

from memnet.layer import (
    Document,
    Endpoint,
    LayerEdgeRec,
    LayerNodeRec,
    LintIssue,
    ParseError,
    emit,
    emit_item,
    ensure_layer_schema,
    is_layer_edge_record,
    lint,
    looks_like_layer,
    parse,
    parse_line,
    record_to_layer_edge,
    record_to_layer_node,
    soft_validate,
)

__all__ = [
    "LayerCodec",
    "Document",
    "Endpoint",
    "LayerEdgeRec",
    "LayerNodeRec",
    "LintIssue",
    "ParseError",
    "emit",
    "emit_item",
    "ensure_layer_schema",
    "is_layer_edge_record",
    "lint",
    "looks_like_layer",
    "parse",
    "parse_line",
    "record_to_layer_edge",
    "record_to_layer_node",
    "soft_validate",
]


class LayerCodec:
    """Parse / emit / soft-validate MemNet Layer (1.x overlay) dialect."""

    def parse(self, text: str) -> Document:
        return parse(text)

    def emit(self, doc: Document) -> str:
        return emit(doc)

    def lint(self, doc: Document) -> list[LintIssue]:
        return soft_validate(doc)

    def soft_validate(self, doc: Document) -> list[LintIssue]:
        return soft_validate(doc)
