"""Typed directed walks (MN-REQ-14.3, issue #247 items 1-3).

One edge type, direction out / in / both, 1..k hops (k <= 10), BFS. Each node is
reached at most once (the start never), so cycles end. Rows go in hop order,
then parents' BFS order, then the edge first-insert sequence (the RecordTable
insertion order): never id value, hid or property value. Each hop reads only the
adjacency bucket for (node, type, direction).

The start is a nickname looked up through the id index (EDG rows excluded);
hids are never accepted or emitted. ``WHERE`` is a predicate on ``n``, the row's
end node, with the #250 rules (``gql.parse_where_clause`` / ``gql.eval_where``).

Module constants are read at call time (tests may lower them).
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass

from memnet.config import DEFAULT_QUERY_MAX_ROWS, normalize_relation
from memnet.exceptions import MemNetError
from memnet.gql import ParseError, WherePred, emit_node_shaped, eval_where, parse_where_clause
from memnet.mem_store import MemStore
from memnet.models import Record

WALK_MAX_HOPS = 10  # k ceiling
WALK_DEFAULT_LIMIT = DEFAULT_QUERY_MAX_ROWS  # 50
WALK_MAX_LIMIT = 500  # result-size ceiling (rows)
WALK_MAX_EXAMINED = 20_000  # typed edge reads per call (bounds visited + frontier)
WALK_MAX_REPLY_BYTES = 1_048_576  # emitted reply bytes (under the 4 MiB serve frame)
DIRECTIONS = ("out", "in", "both")

_RE_WHERE_KW = re.compile(r"^\s*WHERE\b", re.IGNORECASE)


@dataclass(frozen=True)
class WalkStep:
    edge: Record  # EDG record followed
    node: Record  # node reached by this step
    forward: bool  # True: followed src->dist; False: dist->src


@dataclass(frozen=True)
class WalkPath:
    start: Record
    steps: tuple[WalkStep, ...]  # 1..max_hops, in walk order

    @property
    def end(self) -> Record:
        return self.steps[-1].node


@dataclass(frozen=True)
class WalkResult:
    relation: str  # folded type followed
    direction: str
    min_hops: int
    max_hops: int
    limit: int
    paths: tuple[WalkPath, ...]  # rows, in the D6 order
    truncated: str | None  # None | "limit" | "budget"
    examined: int  # typed edge reads from the adjacency index
    visited: int  # distinct nodes reached, start included
    cursor: str | None = None  # reserved for paging (#247 item 4); always None here


def _check_where_vars(pred: WherePred) -> None:
    """Refuse any variable other than ``n`` (first one in reading order)."""
    if pred.children:
        for child in pred.children:
            _check_where_vars(child)
        return
    if pred.key and pred.var != "n":
        name = f"{pred.var}.{pred.key}" if pred.var else pred.key
        raise MemNetError("unsupported_predicate", f"WHERE {name}: walk WHERE names n only")


def _parse_where(where: str | None) -> WherePred | None:
    if where is None:
        return None
    text = _RE_WHERE_KW.sub("", where, count=1).strip()
    if not text:
        return None
    try:
        pred = parse_where_clause(text)
    except ParseError as exc:
        raise MemNetError(exc.code, str(exc)) from exc
    _check_where_vars(pred)
    return pred


def _start_node(store: MemStore, start: str) -> Record:
    hits = [r for r in store.match_nickname(start) if r.tag != "EDG"]
    if not hits:
        raise MemNetError("not_found", f"walk start {start} not found")
    if len(hits) > 1:
        raise MemNetError("cue_conflict", f"walk start {start} matches {len(hits)} nodes")
    return hits[0]


def typed_walk(
    store: MemStore,
    *,
    start: str,
    relation: str,
    direction: str = "out",
    min_hops: int = 1,
    max_hops: int = 1,
    where: str | None = None,
    limit: int = WALK_DEFAULT_LIMIT,
) -> WalkResult:
    """Walk ``relation`` edges from the node nicknamed ``start`` (score D3-D7)."""
    if not start:
        raise MemNetError("no_anchor", "query typed-walk requires --from")
    if direction not in DIRECTIONS:
        raise MemNetError("invalid_direction", f"direction '{direction}' must be out, in or both")
    max_k = WALK_MAX_HOPS
    if not 1 <= min_hops <= max_hops <= max_k:
        raise MemNetError(
            "hops_out_of_range",
            f"hops {min_hops}..{max_hops} must satisfy 1 <= min <= max <= {max_k}",
        )
    max_limit = WALK_MAX_LIMIT
    if not 1 <= limit <= max_limit:
        raise MemNetError("limit_out_of_range", f"limit {limit} must be 1..{max_limit}")
    rel = normalize_relation(relation)
    pred = _parse_where(where)
    origin = _start_node(store, start)
    budget = WALK_MAX_EXAMINED

    by_hid = store._by_hid
    want_out = direction in ("out", "both")
    want_in = direction in ("in", "both")
    # hid -> (parent hid, step); the start has no entry.
    reached: dict[str, tuple[str, WalkStep] | None] = {origin.hid: None}
    rows: list[WalkPath] = []
    truncated: str | None = None
    examined = 0
    frontier: deque[tuple[str, int]] = deque([(origin.hid, 0)])

    def _path_to(hid: str) -> WalkPath:
        steps: list[WalkStep] = []
        cur = reached[hid]
        while cur is not None:
            parent, step = cur
            steps.append(step)
            cur = reached[parent]
        steps.reverse()
        return WalkPath(start=origin, steps=tuple(steps))

    while frontier and truncated is None:
        node_hid, depth = frontier.popleft()
        if depth >= max_hops:
            continue
        for edge in store.typed_edges(node_hid, rel, direction):
            if examined >= budget:
                truncated = "budget"
                break
            examined += 1
            src = edge.fields.get("src", "")
            dist = edge.fields.get("dist", "")
            if want_out and src == node_hid:
                far, forward = dist, True
            elif want_in and dist == node_hid:
                far, forward = src, False
            else:
                continue
            if not far or far in reached:
                continue
            far_rec = dict.get(by_hid, far)
            if far_rec is None:
                continue
            reached[far] = (node_hid, WalkStep(edge=edge, node=far_rec, forward=forward))
            hop = depth + 1
            if hop < max_hops:
                frontier.append((far, hop))
            if hop < min_hops or (pred is not None and not eval_where(far_rec, pred)):
                continue
            if len(rows) >= limit:
                truncated = "limit"
                break
            rows.append(_path_to(far))

    return WalkResult(
        relation=rel,
        direction=direction,
        min_hops=min_hops,
        max_hops=max_hops,
        limit=limit,
        paths=tuple(rows),
        truncated=truncated,
        examined=examined,
        visited=len(reached),
    )


def _node_head(rec: Record) -> str:
    nick = rec.fields.get("id") or ""
    return emit_node_shaped(rec.tag, nick, {"id": nick} if nick else {})


def _edge_seg(rel: str, step: WalkStep) -> str:
    nick = step.edge.fields.get("id") or ""
    body = f":{rel} {{id: '{_quote(nick)}'}}" if nick else f":{rel}"
    return f"-[{body}]->" if step.forward else f"<-[{body}]-"


def _quote(val: str) -> str:
    return val.replace("\\", "\\\\").replace("'", "\\'")


def shaped_path(result: WalkResult, path: WalkPath) -> str:
    """Start and intermediates as kind + id, edges by type + id, END with properties."""
    parts = [_node_head(path.start)]
    last = len(path.steps) - 1
    for i, step in enumerate(path.steps):
        parts.append(_edge_seg(result.relation, step))
        if i == last:
            node = step.node
            parts.append(emit_node_shaped(node.tag, node.fields.get("id") or "", dict(node.fields)))
        else:
            parts.append(_node_head(step.node))
    return "".join(parts)


def _stat_lines(rows: int, limit: int, truncated: str | None) -> list[str]:
    return [
        f"@STAT: walk_rows|{rows}|{limit}",
        f"@STAT: walk_truncated|{truncated or 'none'}|-",
        "@STAT: walk_cursor|-|-",
    ]


def _size(lines: list[str]) -> int:
    return sum(len(ln.encode("utf-8")) + 1 for ln in lines)


def emit_walk(result: WalkResult, *, max_bytes: int | None = None) -> list[str]:
    """D9 reply lines; stops before the row line that would pass ``max_bytes``."""
    cap = WALK_MAX_REPLY_BYTES if max_bytes is None else max_bytes
    header = (
        f"@WALK: type={result.relation}|dir={result.direction}"
        f"|hops={result.min_hops}..{result.max_hops}|limit={result.limit}"
    )
    body = [
        f"@PATH: {i}|{len(p.steps)}|{shaped_path(result, p)}"
        for i, p in enumerate(result.paths, start=1)
    ]
    full = [header, *body, *_stat_lines(len(body), result.limit, result.truncated)]
    if _size(full) <= cap:
        return full
    label = result.truncated or "bytes"
    used = _size([header])
    kept: list[str] = []
    for line in body:
        n = len(kept) + 1
        if used + _size([line]) + _size(_stat_lines(n, result.limit, label)) > cap:
            break
        kept.append(line)
        used += _size([line])
    return [header, *kept, *_stat_lines(len(kept), result.limit, label)]
