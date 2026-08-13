"""PinMapComposer / PinMapShapedRead — live pin map as shaped GQL subgraph.

Emits openCypher-family node and relationship lines (gql-wire-profile §5).
Optional ``view=`` grain: ``shell`` / ``interior`` taught; ``flowchart`` /
``parts`` / ``statechart`` accepted with soft shell caps.
"""

from __future__ import annotations

from memnet.config import DEFAULT_QUERY_DEPTH, DEFAULT_QUERY_MAX_ROWS
from memnet.exceptions import MemNetError
from memnet.gql import emit_edge_shaped, emit_node_shaped
from memnet.models import Record

# Soft shell caps (docs/grammar — view budget).
SHELL_MAX_NODES = 8
SHELL_MAX_EDGES = 12

PIN_MAP_VIEWS_TEACH = frozenset({"shell", "interior"})
PIN_MAP_VIEWS_SOFT = frozenset({"flowchart", "parts", "statechart"})
PIN_MAP_VIEWS = PIN_MAP_VIEWS_TEACH | PIN_MAP_VIEWS_SOFT


def normalize_view(view: str | None) -> str | None:
    """Return canonical view token, or None for default depth/max_rows behaviour."""
    if view is None:
        return None
    text = str(view).strip().lower()
    if not text or text in ("default", "all"):
        return None
    if text not in PIN_MAP_VIEWS:
        raise MemNetError(
            "bad_view",
            f"unknown view={view!r}; expected shell|interior|flowchart|parts|statechart (or omit)",
        )
    return text


def resolve_view_budget(
    view: str | None,
    *,
    depth: int,
    max_rows: int,
) -> tuple[int, int, bool]:
    """Map ``view=`` to (depth, max_rows, apply_shell_soft_cap)."""
    v = normalize_view(view)
    if v is None or v == "interior":
        return depth, max_rows, False
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


def _endpoint_label(store, node_id: str) -> str:
    rec = store.get(node_id) if store is not None else None
    if rec is not None and rec.tag and rec.tag != "EDG":
        return rec.tag
    return "NODE"


def record_to_gql_line(rec: Record, *, store=None) -> str:
    """Project an internal Record to one shaped GQL present line."""
    if rec.tag == "EDG":
        src = rec.fields.get("src", "")
        dist = rec.fields.get("dist", "")
        return emit_edge_shaped(
            src_kind=_endpoint_label(store, src),
            src_id=src,
            rel=rec.fields.get("relation", "related") or "related",
            dst_kind=_endpoint_label(store, dist),
            dst_id=dist,
            edge_id=rec.id,
            fields=dict(rec.fields),
        )
    fields = {k: v for k, v in rec.fields.items() if k != "id"}
    return emit_node_shaped(rec.tag, rec.id, fields)


class PinMapComposer:
    """Compose anchored live pin map; emit shaped openCypher-family subgraph.

    SysML target name: PinMapShapedRead.
    """

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
        caller: str | None = None,
        agent: str | None = None,
    ) -> tuple[list[Record], str]:
        """Return (records, shaped GQL text)."""
        from memnet.acl import check_permission

        del law_prepend  # store.context_pack already prepends laws
        check_permission(
            getattr(self.ss, "acl", None),
            caller=caller,
            permission="pin_map",
            agent=agent,
        )
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
        text = self.emit_gql(rows)
        from memnet.neighbourhood_reserve import emit_reserves_section, intersecting_leases
        from memnet.session import utc_now

        view_ids = {r.id for r in rows}
        leases = intersecting_leases(self.ss.reserves, view_ids, now=utc_now())
        reserve_text = emit_reserves_section(leases, now=utc_now())
        if reserve_text:
            text = reserve_text + ("\n" if text else "") + text
        return rows, text

    def emit_gql(self, rows: list[Record]) -> str:
        """Emit shaped subgraph lines (laws, then nodes, then edges)."""
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
        store = self.ss.store
        for r in laws:
            lines.append(record_to_gql_line(r, store=store))
        for r in nodes:
            lines.append(record_to_gql_line(r, store=store))
        for r in edges:
            lines.append(record_to_gql_line(r, store=store))
        return "\n".join(lines) + ("\n" if lines else "")

    # Back-compat alias used by older call sites / tests during M2 cutover
    def emit_tier_a(self, rows: list[Record]) -> str:
        return self.emit_gql(rows)


# SysML-facing alias
PinMapShapedRead = PinMapComposer
