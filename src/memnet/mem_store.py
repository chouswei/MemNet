"""memStore — session store, indexes, graph queries."""

from __future__ import annotations

import time
from collections import deque

from memnet.config import Caps, DEFAULT_QUERY_DEPTH, DEFAULT_QUERY_MAX_ROWS
from memnet.exceptions import MemNetError
from memnet.filter import record_matches
from memnet.models import Record, TagMap
from memnet.output import emit_wrn


class MemStore:
    def __init__(self, tag_map: TagMap, caps: Caps | None = None) -> None:
        self.tag_map = tag_map
        self.caps = caps or Caps()
        self.by_id: dict[str, Record] = {}
        self.write_order: list[str] = []
        self._edges_by_src: dict[str, set[str]] = {}
        self._edges_by_dist: dict[str, set[str]] = {}

    def load_records(self, records: list[Record]) -> None:
        self.by_id.clear()
        self.write_order.clear()
        self._edges_by_src.clear()
        self._edges_by_dist.clear()
        for rec in records:
            self.by_id[rec.id] = rec
            self.write_order.append(rec.id)
            if rec.tag == "EDG":
                self._index_edge(rec)

    def row_count_non_law(self) -> int:
        return sum(1 for r in self.by_id.values() if r.tag != "LAW")

    def law_count(self) -> int:
        return sum(1 for r in self.by_id.values() if r.tag == "LAW")

    def upsert(
        self,
        record: Record,
        *,
        agent: str | None = None,
        allow_new_relation: bool = False,
        relations: set[str] | None = None,
    ) -> list[str]:
        warnings: list[str] = []
        rid = record.id
        existing = self.by_id.get(rid)
        if existing and existing.tag != record.tag:
            raise MemNetError(
                "id_conflict",
                f"id {rid} already used by tag {existing.tag}",
            )
        if record.tag == "LAW" and not existing:
            if self.law_count() >= self.caps.max_law:
                raise MemNetError(
                    "limit_exceeded",
                    f"law|{self.law_count() + 1}/{self.caps.max_law}",
                )
        elif record.tag != "LAW" and not existing:
            if self.row_count_non_law() >= self.caps.max_rows:
                raise MemNetError(
                    "limit_exceeded",
                    f"rows|{self.row_count_non_law() + 1}/{self.caps.max_rows}",
                )
        if record.tag == "EDG" and relations is not None:
            rel = record.fields.get("relation", "")
            if rel and rel not in relations:
                if not allow_new_relation:
                    known = ",".join(sorted(relations)) or "none"
                    raise MemNetError(
                        "unknown_relation",
                        f"{rel}|known: {known}",
                    )
                if len(relations) >= self.caps.max_relations:
                    raise MemNetError(
                        "limit_exceeded",
                        f"relations|{len(relations) + 1}/{self.caps.max_relations}",
                    )
                relations.add(rel)
        if record.tag == "EDG":
            for endpoint_key in ("src", "dist"):
                eid = record.fields.get(endpoint_key, "")
                if eid and eid not in self.by_id:
                    warnings.append(
                        f"dangling_endpoint|{endpoint_key} {eid} not found"
                    )
        if agent:
            record.agent = agent
        record.written_at = time.time()
        if existing and existing.tag == "EDG":
            self._unindex_edge(existing)
        if not existing:
            self.write_order.append(rid)
        self.by_id[rid] = record
        if record.tag == "EDG":
            self._index_edge(record)
        return warnings

    def add_row(
        self,
        record: Record,
        *,
        agent: str | None = None,
        allow_new_relation: bool = False,
        relations: set[str] | None = None,
    ) -> list[str]:
        existing = self.by_id.get(record.id)
        if existing:
            raise MemNetError(
                "id_exists",
                f"id {record.id} exists @{existing.tag}|use update",
            )
        return self.upsert(
            record,
            agent=agent,
            allow_new_relation=allow_new_relation,
            relations=relations,
        )

    def replace_row(
        self,
        record: Record,
        *,
        agent: str | None = None,
        allow_new_relation: bool = False,
        relations: set[str] | None = None,
    ) -> list[str]:
        if record.id not in self.by_id:
            raise MemNetError("not_found", f"id {record.id}|use add")
        return self.upsert(
            record,
            agent=agent,
            allow_new_relation=allow_new_relation,
            relations=relations,
        )

    def delete(self, record_id: str) -> Record | None:
        existing = self.by_id.get(record_id)
        if existing is None:
            return None
        if existing.tag == "EDG":
            self._unindex_edge(existing)
        rec = self.by_id.pop(record_id, None)
        if rec and record_id in self.write_order:
            self.write_order.remove(record_id)
        return rec

    def get(self, record_id: str) -> Record | None:
        return self.by_id.get(record_id)

    def list_records(
        self,
        tag: str | None = None,
        *,
        active_only: bool = False,
        where: list[tuple[str, str]] | None = None,
    ) -> list[Record]:
        rows = list(self.by_id.values())
        if tag:
            rows = [r for r in rows if r.tag == tag.upper()]
        if active_only:
            rows = [r for r in rows if not r.is_recyclable()]
        if where:
            rows = [r for r in rows if record_matches(r, where)]
        rows.sort(key=lambda r: r.id)
        return rows

    def _index_edge(self, edge: Record) -> None:
        src = edge.fields.get("src", "")
        dist = edge.fields.get("dist", "")
        if src:
            self._edges_by_src.setdefault(src, set()).add(edge.id)
        if dist:
            self._edges_by_dist.setdefault(dist, set()).add(edge.id)

    def _unindex_edge(self, edge: Record) -> None:
        src = edge.fields.get("src", "")
        dist = edge.fields.get("dist", "")
        if src:
            bucket = self._edges_by_src.get(src)
            if bucket:
                bucket.discard(edge.id)
                if not bucket:
                    del self._edges_by_src[src]
        if dist:
            bucket = self._edges_by_dist.get(dist)
            if bucket:
                bucket.discard(edge.id)
                if not bucket:
                    del self._edges_by_dist[dist]

    def _edge_records(self, edge_ids: set[str] | None) -> list[Record]:
        if not edge_ids:
            return []
        return sorted(
            (self.by_id[eid] for eid in edge_ids if eid in self.by_id),
            key=lambda r: r.id,
        )

    def _edges_from(self, node_id: str) -> list[Record]:
        return self._edge_records(self._edges_by_src.get(node_id))

    def _edges_to(self, node_id: str) -> list[Record]:
        return self._edge_records(self._edges_by_dist.get(node_id))

    def neighbors(
        self,
        node_id: str,
        depth: int = 1,
        *,
        fanout_warnings: list[str] | None = None,
    ) -> list[Record]:
        depth = min(depth, self.caps.max_depth)
        if node_id not in self.by_id:
            return []
        visited: set[str] = {node_id}
        node_results: list[Record] = []
        edge_results: list[Record] = []
        edge_seen: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])
        while queue:
            current, d = queue.popleft()
            if d >= depth:
                continue
            out_edges = self._edges_from(current)
            if len(out_edges) > self.caps.max_fanout:
                if fanout_warnings is not None:
                    fanout_warnings.append(
                        f"fanout_clamped|{current}|{len(out_edges)}/{self.caps.max_fanout}"
                    )
                out_edges = out_edges[: self.caps.max_fanout]
            in_edges = self._edges_to(current)
            for edge in out_edges + in_edges:
                if edge.id not in edge_seen:
                    edge_seen.add(edge.id)
                    edge_results.append(edge)
                for endpoint in (edge.fields.get("src"), edge.fields.get("dist")):
                    if not endpoint or endpoint in visited:
                        continue
                    if endpoint not in self.by_id:
                        continue
                    visited.add(endpoint)
                    node_results.append(self.by_id[endpoint])
                    queue.append((endpoint, d + 1))
        if node_id in self.by_id and self.by_id[node_id] not in node_results:
            node_results.insert(0, self.by_id[node_id])
        return node_results + edge_results

    def find_path(self, source_id: str, target_id: str) -> list[Record]:
        if source_id not in self.by_id or target_id not in self.by_id:
            return []
        if source_id == target_id:
            return [self.by_id[source_id]]
        depth = self.caps.max_depth
        queue: deque[tuple[str, list[str]]] = deque([(source_id, [source_id])])
        visited: set[str] = {source_id}
        while queue:
            current, path = queue.popleft()
            if len(path) > depth + 1:
                continue
            for edge in self._edges_from(current):
                nxt = edge.fields.get("dist", "")
                if not nxt or nxt not in self.by_id:
                    continue
                new_path = path + [nxt]
                if nxt == target_id:
                    return self._path_to_records(new_path)
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, new_path))
        return []

    def _path_to_records(self, node_path: list[str]) -> list[Record]:
        records: list[Record] = []
        for nid in node_path:
            records.append(self.by_id[nid])
        for i in range(len(node_path) - 1):
            src, dst = node_path[i], node_path[i + 1]
            for edge in self._edges_from(src):
                if edge.fields.get("dist") == dst:
                    records.append(edge)
                    break
        return records

    def default_anchor(self) -> str | None:
        for rid in reversed(self.write_order):
            rec = self.by_id.get(rid)
            if rec and rec.tag != "LAW":
                return rid
        return None

    def context_pack(
        self,
        *,
        anchor_id: str | None = None,
        depth: int = DEFAULT_QUERY_DEPTH,
        max_rows: int = DEFAULT_QUERY_MAX_ROWS,
        active_only: bool = False,
        stale_warnings: list[tuple[Record, str]] | None = None,
    ) -> list[Record]:
        depth = min(depth, self.caps.max_depth)
        law_rows = sorted(
            [r for r in self.by_id.values() if r.tag == "LAW"],
            key=lambda r: r.id,
        )
        if anchor_id is None:
            anchor_id = self.default_anchor()
        payload: list[Record] = []
        if anchor_id and anchor_id in self.by_id:
            fanout: list[str] = []
            subgraph = self.neighbors(anchor_id, depth, fanout_warnings=fanout)
            for w in fanout:
                emit_wrn(*w.split("|", 1))
            seen: set[str] = set()
            for rec in subgraph:
                if rec.id in seen:
                    continue
                if active_only and rec.is_recyclable():
                    if stale_warnings is not None:
                        stale_warnings.append((rec, "stale_in_context"))
                    continue
                seen.add(rec.id)
                payload.append(rec)
        nodes = [r for r in payload if r.kind == "node"]
        edges = [r for r in payload if r.kind == "edge"]
        combined = nodes + edges
        if len(combined) > max_rows:
            combined = combined[:max_rows]
        if not active_only and stale_warnings is not None:
            for rec in combined:
                if rec.is_recyclable():
                    stale_warnings.append((rec, "stale_in_context"))
        return law_rows + combined

    def to_jsonl_rows(self) -> list[dict]:
        rows: list[dict] = []
        for rid in self.write_order:
            rec = self.by_id.get(rid)
            if rec:
                rows.append(rec.model_dump())
        return rows

    @classmethod
    def from_jsonl_rows(cls, rows: list[dict], tag_map: TagMap, caps: Caps | None = None) -> MemStore:
        store = cls(tag_map, caps)
        records = [Record.model_validate(r) for r in rows]
        store.load_records(records)
        return store
