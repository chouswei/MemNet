"""PinMapComposer — live pin map emit as Tier A Write=display.

Layer (1.x) rows with ``src_port`` / ``dist_port`` / non-default ``wire`` emit
Layer wire forms; other rows stay on the 0.3 Tier A paren-label surface.

Optional ``view=`` (multi-layer grain): ``shell`` / ``interior`` taught;
``flowchart`` / ``parts`` / ``statechart`` accepted with soft shell caps
(grain-specific filters deferred).
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

# Soft shell caps (docs/grammar/memnet-multi-layer.md §3 flowchart / §5).
SHELL_MAX_NODES = 8
SHELL_MAX_EDGES = 12

# Teachable grains first; soft = accept param, shell-like budget for now.
PIN_MAP_VIEWS_TEACH = frozenset({"shell", "interior"})
PIN_MAP_VIEWS_SOFT = frozenset({"flowchart", "parts", "statechart"})
PIN_MAP_VIEWS = PIN_MAP_VIEWS_TEACH | PIN_MAP_VIEWS_SOFT


def normalize_view(view: str | None) -> str | None:
    """Return canonical view token, or None for default 0.3 Tier A behaviour."""
    if view is None:
        return None
    text = str(view).strip().lower()
    if not text or text in ("default", "all"):
        return None
    if text not in PIN_MAP_VIEWS:
        raise MemNetError(
            "bad_view",
            f"unknown view={view!r}; expected shell|interior"
            f"|flowchart|parts|statechart (or omit)",
        )
    return text


def resolve_view_budget(
    view: str | None,
    *,
    depth: int,
    max_rows: int,
) -> tuple[int, int, bool]:
    """Map ``view=`` to (depth, max_rows, apply_shell_soft_cap).

    * omit / default — honour caller depth/max_rows; no soft shell cap
    * ``interior`` — same; no soft shell cap (fuller neighbourhood)
    * ``shell`` — depth capped at 1; soft 8 NODE / 12 EDGE after pack
    * ``flowchart`` / ``parts`` / ``statechart`` — soft: shell-like budget
      (grain filters deferred)
    """
    v = normalize_view(view)
    if v is None or v == "interior":
        return depth, max_rows, False
    # shell + soft grain aliases
    return min(depth, 1), max_rows, True


def apply_shell_soft_cap(
    rows: list[Record],
    *,
    anchor: str | None,
    max_nodes: int = SHELL_MAX_NODES,
    max_edges: int = SHELL_MAX_EDGES,
) -> list[Record]:
    """Truncate NODE/EDGE payload to soft shell caps; keep LAW rows intact."""
    laws: list[Record] = []
    nodes: list[Record] = []
    edges: list[Record] = []
    for rec in rows:
        if rec.tag == "LAW":
            laws.append(rec)
        elif rec.tag == "EDG" or getattr(rec, "kind", None) == "edge":
            edges.append(rec)
        else:
            nodes.append(rec)

    if anchor:
        nodes = sorted(nodes, key=lambda r: (0 if r.id == anchor else 1, r.id))
    else:
        nodes = sorted(nodes, key=lambda r: r.id)
    nodes = nodes[:max_nodes]
    kept = {r.id for r in nodes}

    def _edge_rank(e: Record) -> tuple[int, str]:
        src = e.fields.get("src", "")
        dist = e.fields.get("dist", "")
        both = int(src in kept) + int(dist in kept)
        return (-both, e.id)

    filtered: list[Record] = []
    for e in sorted(edges, key=_edge_rank):
        src = e.fields.get("src", "")
        dist = e.fields.get("dist", "")
        if src in kept or dist in kept:
            filtered.append(e)
        if len(filtered) >= max_edges:
            break

    return laws + nodes + filtered


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
        view: str | None = None,
    ) -> tuple[list[Record], str]:
        """Return (records, shared-dialect text).

        ``view`` is optional/additive — omit for 0.3 Tier A depth/max_rows behaviour.
        """
        del law_prepend  # store.context_pack already prepends laws
        if require_anchor and not anchor:
            raise MemNetError("no_anchor", "pin map requires --anchor")
        stale_warnings: list = []
        if not anchor:
            anchor = self.ss.store.default_anchor()
            if not anchor:
                return [], ""
        eff_depth, eff_max_rows, soft_cap = resolve_view_budget(
            view, depth=depth, max_rows=max_rows
        )
        rows = self.ss.store.context_pack(
            anchor_id=anchor,
            depth=eff_depth,
            max_rows=eff_max_rows,
            active_only=active_only,
            stale_warnings=stale_warnings,
        )
        if soft_cap:
            rows = apply_shell_soft_cap(rows, anchor=anchor)
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
