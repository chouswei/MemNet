"""PinMapComposer — live pin map emit as Tier A Write=display."""

from __future__ import annotations

from memnet.config import DEFAULT_QUERY_DEPTH, DEFAULT_QUERY_MAX_ROWS
from memnet.exceptions import MemNetError
from memnet.models import Record
from memnet.tier_a import Document, EdgeRec, Field, NodeRec, Op, Section, emit


def record_to_tier_a_item(rec: Record) -> NodeRec | EdgeRec:
    """Project an internal Record to a Tier A display item (ground ids)."""
    if rec.tag == "EDG":
        fields = [
            Field(key=k, op="=", value=v)
            for k, v in rec.fields.items()
            if k not in ("id", "src", "relation", "dist") and v
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


class PinMapComposer:
    """Compose anchored live pin map; emit Tier A (CLI: query pin-map)."""

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
        """Return (records, tier_a_text)."""
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
        items: list = []
        if laws:
            items.append(Section(name="Laws"))
            items.extend(record_to_tier_a_item(r) for r in laws)
        if nodes:
            items.append(Section(name="Nodes"))
            items.extend(record_to_tier_a_item(r) for r in nodes)
        if edges:
            items.append(Section(name="Edges"))
            items.extend(record_to_tier_a_item(r) for r in edges)
        return emit(Document(items=items))
