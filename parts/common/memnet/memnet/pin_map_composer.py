"""PinMapComposer / PinMapShapedRead — live pin map as shaped GQL subgraph.

Emits openCypher-family node and relationship lines (gql-wire-profile §5).
Optional ``view=`` grain: ``shell`` / ``interior`` taught; ``flowchart`` /
``parts`` / ``statechart`` accepted with soft shell caps.
"""

from __future__ import annotations

from dataclasses import dataclass

from memnet.config import DEFAULT_QUERY_DEPTH, DEFAULT_QUERY_MAX_ROWS
from memnet.exceptions import MemNetError
from memnet.gql import emit_node_shaped
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
        nodes = sorted(nodes, key=lambda r: (0 if r.hid == anchor or r.id == anchor else 1, r.hid))
    else:
        nodes = sorted(nodes, key=lambda r: r.hid)
    nodes = nodes[:max_nodes]
    kept = {r.hid for r in nodes}

    def _edge_rank(e: Record) -> tuple[int, str]:
        src = e.fields.get("src", "")
        dist = e.fields.get("dist", "")
        both = int(src in kept) + int(dist in kept)
        return (-both, e.hid)

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
        src_line = _endpoint_shaped(store, src)
        dst_line = _endpoint_shaped(store, dist)
        rel = rec.fields.get("relation", "related") or "related"
        rel_fields = dict(rec.fields)
        from memnet.gql import _emit_props

        rel_props: dict[str, str] = {}
        nick = rec.id
        if nick:
            rel_props["id"] = nick
        for store_key, wire_key in (
            ("fromPort", "fromPort"),
            ("toPort", "toPort"),
            ("src_port", "fromPort"),
            ("dist_port", "toPort"),
            ("carries", "carries"),
        ):
            if store_key in rel_fields and rel_fields[store_key]:
                rel_props[wire_key] = rel_fields[store_key]
        rel_s = f":{rel} {_emit_props(rel_props)}" if rel_props else f":{rel}"
        return f"{src_line}-[{rel_s}]->{dst_line}"
    fields = {k: v for k, v in rec.fields.items() if k != "id"}
    return emit_node_shaped(rec.tag if rec.tag != "NODE" else rec.tag, rec.id, fields)


def _endpoint_shaped(store, token: str) -> str:
    rec = None
    if store is not None and hasattr(store, "resolve_one"):
        rec = store.resolve_one(token)
    if rec is None:
        nick = "" if str(token).startswith("_el") else token
        return emit_node_shaped("NODE", nick or "", {})
    fields = {k: v for k, v in rec.fields.items() if k != "id"}
    kind = rec.tag if rec.tag and rec.tag != "EDG" else "NODE"
    return emit_node_shaped(kind, rec.id, fields)


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
        anchors: list[str] | None = None,
        kind: str | None = None,
        locators: list[tuple[str, str]] | None = None,
        keyword: str | None = None,
        limit: int | None = None,
        depth: int = DEFAULT_QUERY_DEPTH,
        max_rows: int = DEFAULT_QUERY_MAX_ROWS,
        active_only: bool = True,
        require_anchor: bool = False,
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
        seed_ids: list[str] = []
        cue_on = bool(kind or locators or (keyword and str(keyword).strip()))
        leftover_nicks: list[str] = []
        for aid in list(anchors or []):
            if aid and aid not in leftover_nicks:
                leftover_nicks.append(aid)
        if anchor and anchor not in leftover_nicks:
            leftover_nicks.append(anchor)
        if require_anchor and not leftover_nicks and not cue_on:
            raise MemNetError("no_anchor", "pin map leftover --anchor is not product; cue with kind/locator/keyword")
        Q: list[Record] = []
        if cue_on:
            found = bounded_match_find(
                self.ss.store,
                kind=kind,
                locators=list(locators or []),
                keyword=keyword,
                limit=limit or max(1, max_rows),
            )
            Q = list(found.seeds)
            if found.total > len(Q):
                # MATCH_L listed Q; cardinality is the true hit count
                pass
            if found.conflict:
                text = emit_cue_conflict(found.seeds, cardinality=found.total, store=self.ss.store)
                return found.seeds, text
            if not Q:
                return [], ""
            seed_ids = [r.hid for r in Q]
        elif leftover_nicks:
            seen_h: set[str] = set()
            for nick in leftover_nicks:
                hits = self.ss.store.match_nickname(nick)
                one = self.ss.store.resolve_one(nick)
                if len(hits) > 1:
                    text = emit_cue_conflict(hits, cardinality=len(hits), store=self.ss.store)
                    return hits, text
                if one is None:
                    continue
                if one.hid not in seen_h:
                    seen_h.add(one.hid)
                    Q.append(one)
            if not Q:
                return [], ""
            seed_ids = [r.hid for r in Q]
        else:
            # Empty q skips (0.11 owns outline). Do not default-anchor.
            return [], ""
        stale_warnings: list = []
        eff_depth, eff_max_rows, soft_cap = resolve_view_budget(
            view, depth=depth, max_rows=max_rows
        )
        rows = self.ss.store.context_pack(
            anchor_ids=seed_ids,
            depth=eff_depth,
            max_rows=eff_max_rows,
            active_only=active_only,
            stale_warnings=stale_warnings,
        )
        if soft_cap:
            rows = apply_shell_soft_cap(rows, anchor=seed_ids[0])
        text = self.emit_gql(rows)
        from memnet.neighbourhood_reserve import emit_reserves_section, intersecting_leases
        from memnet.session import utc_now

        view_ids = {r.hid for r in rows}
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


def parse_find_locators(raw: list[str] | None) -> list[tuple[str, str]]:
    """Parse ``KEY=VAL`` locator cues."""
    out: list[tuple[str, str]] = []
    for item in raw or []:
        if "=" not in item:
            raise MemNetError("bad_locator", f"locator must be KEY=VAL, got {item!r}")
        key, val = item.split("=", 1)
        key = key.strip()
        if not key:
            raise MemNetError("bad_locator", f"locator must be KEY=VAL, got {item!r}")
        out.append((key, val))
    return out


@dataclass
class FindResult:
    seeds: list[Record]
    total: int

    @property
    def conflict(self) -> bool:
        return self.total > 1


def emit_cue_conflict(seeds: list[Record], *, cardinality: int, store=None) -> str:
    """Shaped emit mark: Q listed, |Q| visible. Not a product command."""
    lines = [f"## CueConflict |Q|={cardinality}"]
    for rec in seeds:
        lines.append(record_to_gql_line(rec, store=store))
    return "\n".join(lines) + ("\n" if lines else "")


def bounded_match_find(
    store,
    *,
    kind: str | None,
    locators: list[tuple[str, str]],
    keyword: str | None,
    limit: int,
) -> FindResult:
    """Seed-only codebook find (BoundedMatchFind). No k-hop. Hard LIMIT."""
    if limit < 1:
        raise MemNetError("bad_limit", "find --limit must be >= 1")
    kind_u = kind.upper() if kind else None
    if kind_u:
        rows = store.list_records(kind_u, active_only=True)
    else:
        rows = [r for r in store.list_records(active_only=True) if r.tag not in {"LAW", "EDG"}]
    needle = (keyword or "").strip().lower()

    def _loc_ok(rec: Record) -> bool:
        for key, val in locators:
            if str(rec.fields.get(key, "")) != val:
                return False
        return True

    def _kw_ok(rec: Record) -> bool:
        if not needle:
            return True
        return any(needle in str(v).lower() for v in rec.fields.values())

    hits = [r for r in rows if _loc_ok(r) and _kw_ok(r)]
    hits.sort(key=lambda r: r.hid)
    return FindResult(seeds=hits[:limit], total=len(hits))


# SysML-facing alias
PinMapShapedRead = PinMapComposer
BoundedMatchFind = bounded_match_find
