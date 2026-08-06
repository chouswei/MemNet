"""PinMapComposer — live pin map emit as Tier A Write=display.

Layer (1.x) rows with ``src_port`` / ``dist_port`` / non-default ``wire`` emit
Layer wire forms; other rows stay on the 0.3 Tier A paren-label surface.
"""

from __future__ import annotations

from memnet.config import DEFAULT_QUERY_DEPTH, DEFAULT_QUERY_MAX_ROWS
from memnet.exceptions import MemNetError
from memnet.layer import (
    emit_item as emit_layer_item,
    is_layer_edge_record,
    record_to_layer_edge,
    record_to_layer_node,
)
from memnet.models import Record
from memnet.tier_a import EdgeRec, Field, NodeRec, Op, emit_item


def record_to_tier_a_item(rec: Record) -> NodeRec | EdgeRec:
    """Project an internal Record to a Tier A display item (ground ids)."""
    if rec.tag == "EDG":
        fields = [
            Field(key=k, op="=", value=v)
            for k, v in rec.fields.items()
            if k not in ("id", "src", "relation", "dist", "src_port", "dist_port", "wire", "carries")
            and v
        ]
        return EdgeRec(
            op=Op.PRESENT,
            edge_id=rec.id,
            frm=rec.fields.get("src", ""),
            rel=rec.fields.get("relation", ""),
            to=rec.fields.get("dist", ""),
            fields=fields,
        )
    if rec.tag == "LAW":
        fields = [
            Field(key=k, op="=", value=v)
            for k, v in rec.fields.items()
            if k != "id" and v
        ]
        return NodeRec(op=Op.LAW, kind="LAW", id=rec.id, fields=fields)
    fields = [
        Field(key=k, op="=", value=v)
        for k, v in rec.fields.items()
        if k != "id" and v
    ]
    return NodeRec(op=Op.PRESENT, kind=rec.tag, id=rec.id, fields=fields)


def _emit_record_line(rec: Record) -> str:
    """Emit one present line — Layer wire when ports/wire marked, else Tier A."""
    if rec.tag == "EDG" and is_layer_edge_record(rec):
        return emit_layer_item(record_to_layer_edge(rec))
    if rec.tag != "EDG" and (
        rec.fields.get("ports") or rec.fields.get("law") or rec.tag == "CST"
    ):
        return emit_layer_item(record_to_layer_node(rec))
    return emit_item(record_to_tier_a_item(rec))


class PinMapComposer:
    """Compose anchored live pin map; emit Tier A / Layer Write=display."""

    def __init__(self, session_store) -> None:
        self.ss = session_store

    def compose(
        self,
        *,
        anchor: str | None,
        depth: int = DEFAULT_QUERY_DEPTH,
        max_rows: int = DEFAULT_QUERY_MAX_ROWS,
        active_only: bool = True,
        require_anchor: bool = True,
        law_prepend: bool = True,
    ) -> tuple[list[Record], str]:
        """Return (records, shared-dialect text)."""
        del law_prepend  # store.context_pack already prepends laws
        if require_anchor and not anchor:
            raise MemNetError("no_anchor", "pin map requires --anchor")
        stale_warnings: list = []
        if not anchor:
            anchor = self.ss.store.default_anchor()
            if not anchor:
                return [], ""
        rows = self.ss.store.context_pack(
            anchor_id=anchor,
            depth=depth,
            max_rows=max_rows,
            active_only=active_only,
            stale_warnings=stale_warnings,
        )
        text = self.emit_tier_a(rows)
        return rows, text

    def emit_tier_a(self, rows: list[Record]) -> str:
        laws: list[Record] = []
        nodes: list[Record] = []
        edges: list[Record] = []
        for rec in rows:
            if rec.tag == "LAW":
                laws.append(rec)
            elif rec.tag == "EDG":
                edges.append(rec)
            else:
                nodes.append(rec)
        lines: list[str] = []
        if laws:
            lines.append("## Laws")
            lines.extend(_emit_record_line(r) for r in laws)
        if nodes:
            lines.append("## Nodes")
            lines.extend(_emit_record_line(r) for r in nodes)
        if edges:
            lines.append("## Edges")
            lines.extend(_emit_record_line(r) for r in edges)
        return "\n".join(lines) + ("\n" if lines else "")
