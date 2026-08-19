"""memStore — session store, indexes, graph queries."""

from __future__ import annotations

import re
import time
from collections import deque

from memnet.config import DEFAULT_QUERY_DEPTH, DEFAULT_QUERY_MAX_ROWS, Caps
from memnet.exceptions import MemNetError
from memnet.filter import record_matches
from memnet.models import Record, TagMap, new_hid
from memnet.output import emit_wrn

_ENGINE_LAW_IDS = frozenset({"LAW01", "LAW02", "LAW03", "LAW04", "LAW05"})
_LAW_LINK_RELATIONS = frozenset({"governs", "features", "constrains", "applies_to"})
_ENGINE_LAW_ID_RE = re.compile(r"^LAW0[1-5]$")
_ID_TOKEN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class MemStore:
    def __init__(self, tag_map: TagMap, caps: Caps | None = None) -> None:
        self.tag_map = tag_map
        self.caps = caps or Caps()
        # Graph is elements keyed by hidden handle (off the wire).
        self._by_hid: dict[str, Record] = {}
        self.write_order: list[str] = []
        self._edges_by_src: dict[str, set[str]] = {}
        self._edges_by_dist: dict[str, set[str]] = {}
        self._by_tag: dict[str, set[str]] = {}

    def load_records(self, records: list[Record]) -> None:
        self._by_hid.clear()
        self.write_order.clear()
        self._edges_by_src.clear()
        self._edges_by_dist.clear()
        self._by_tag.clear()
        nick_to_hid: dict[str, str] = {}
        loaded: list[Record] = []
        for rec in records:
            nick = rec.fields.get("id", "")
            if not rec.hid:
                rec.hid = nick or new_hid()
            if nick and nick not in nick_to_hid:
                nick_to_hid[nick] = rec.hid
            loaded.append(rec)
        for rec in loaded:
            if rec.tag == "EDG":
                for key in ("src", "dist"):
                    token = rec.fields.get(key, "")
                    if token and token not in self._by_hid and token in nick_to_hid:
                        rec.fields[key] = nick_to_hid[token]
                    elif token and token in {r.hid for r in loaded}:
                        rec.fields[key] = token
            self._by_hid[rec.hid] = rec
            self.write_order.append(rec.hid)
            self._index_tag(rec)
            if rec.tag == "EDG":
                self._index_edge(rec)

    def row_count_non_law(self) -> int:
        return sum(len(s) for t, s in self._by_tag.items() if t != "LAW")

    def law_count(self) -> int:
        return len(self._by_tag.get("LAW", set()))

    def upsert(
        self,
        record: Record,
        *,
        agent: str | None = None,
        allow_new_relation: bool = False,
        relations: set[str] | None = None,
    ) -> list[str]:
        warnings: list[str] = []
        if record.tag == "EDG":
            for key in ("src", "dist"):
                token = record.fields.get(key, "")
                resolved = self.resolve_one(token) if token else None
                if resolved is not None:
                    record.fields[key] = resolved.hid
        rid = record.hid
        existing = self._by_hid.get(rid)
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
                if eid and self.resolve_one(eid) is None and eid not in self._by_hid:
                    warnings.append(f"dangling_endpoint|{endpoint_key} {eid} not found")
        if agent:
            record.agent = agent
        record.written_at = time.time()
        if existing and existing.tag == "EDG":
            self._unindex_edge(existing)
        if not existing:
            self.write_order.append(rid)
            self._index_tag(record)
        self._by_hid[rid] = record
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
        existing = self._by_hid.get(record.hid)
        if existing:
            raise MemNetError(
                "id_exists",
                f"element {record.hid} exists @{existing.tag}|use update",
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
        if record.hid not in self._by_hid:
            raise MemNetError("not_found", f"element {record.hid}|use add")
        return self.upsert(
            record,
            agent=agent,
            allow_new_relation=allow_new_relation,
            relations=relations,
        )

    def delete(self, record_id: str) -> Record | None:
        target = self.resolve_one(record_id)
        hid = target.hid if target is not None else record_id
        existing = self._by_hid.get(hid)
        if existing is None:
            return None
        if existing.tag == "EDG":
            self._unindex_edge(existing)
        self._unindex_tag(existing)
        rec = self._by_hid.pop(hid, None)
        if rec and hid in self.write_order:
            self.write_order.remove(hid)
        return rec

    def rename_id(
        self,
        old_id: str,
        new_id: str,
        *,
        merge: bool = False,
    ) -> list[str]:
        """Leftover nickname SET. Identity stays the hidden handle.
        merge=true still collapses two elements (leftover; SameThingAbsorb is 0.12).
        """
        warnings: list[str] = []
        if old_id == new_id:
            return warnings
        if new_id == "NEW" or not _ID_TOKEN_RE.match(new_id):
            raise MemNetError("invalid_id", f"id {new_id}")
        old = self.resolve_one(old_id)
        if old is None:
            raise MemNetError("not_found", f"id {old_id}|use add")
        target = self.resolve_one(new_id)
        if target is not None and target.hid != old.hid and not merge:
            raise MemNetError(
                "id_occupied",
                f"id {new_id} occupied @{target.tag}|use merge=true to merge into existing",
            )
        if target is not None and target.hid != old.hid and merge:
            if old.tag == "EDG" or target.tag == "EDG":
                raise MemNetError(
                    "invalid_merge",
                    "merge=true applies to nodes only (not EDG)",
                )
            if old.tag != target.tag:
                raise MemNetError(
                    "id_conflict",
                    f"merge {old_id}@{old.tag} into {new_id}@{target.tag} tag mismatch",
                )
            self._retarget_endpoints(old.hid, target.hid)
            self.delete(old.hid)
            warnings.append(f"merged|{old_id}->{new_id}")
            return warnings

        old.fields["id"] = new_id
        return warnings

    def _retarget_endpoints(self, old_hid: str, new_hid: str) -> None:
        affected = set(self._edges_by_src.get(old_hid, ())) | set(
            self._edges_by_dist.get(old_hid, ())
        )
        for eid in affected:
            edge = self._by_hid.get(eid)
            if edge is None or edge.tag != "EDG":
                continue
            self._unindex_edge(edge)
            if edge.fields.get("src") == old_hid:
                edge.fields["src"] = new_hid
            if edge.fields.get("dist") == old_hid:
                edge.fields["dist"] = new_hid
            self._index_edge(edge)

    def match_nickname(self, nick: str) -> list[Record]:
        if not nick:
            return []
        return [r for r in self._by_hid.values() if r.fields.get("id") == nick]

    def resolve_one(self, token: str | None) -> Record | None:
        """Unique hid or unique nickname. None if missing or CueConflict cardinality."""
        if not token:
            return None
        if token in self._by_hid:
            return self._by_hid[token]
        hits = self.match_nickname(token)
        if len(hits) == 1:
            return hits[0]
        return None

    def match_nodes(
        self,
        *,
        tag: str | None = None,
        props: dict[str, str] | None = None,
    ) -> list[Record]:
        """Pattern lookup (labels + properties the node actually has)."""
        tag_u = tag.upper() if tag else None
        if tag_u:
            rows = [
                self._by_hid[i]
                for i in self._by_tag.get(tag_u, set())
                if i in self._by_hid
            ]
        else:
            rows = [r for r in self._by_hid.values() if r.tag != "EDG"]
        want = {k: str(v) for k, v in (props or {}).items() if v is not None}
        out: list[Record] = []
        for rec in rows:
            if rec.tag == "EDG":
                continue
            if all(str(rec.fields.get(k, "")) == val for k, val in want.items()):
                out.append(rec)
        out.sort(key=lambda r: r.hid)
        return out

    def get(self, record_id: str) -> Record | None:
        """Leftover read_get: unique nickname or hidden handle. Not a product command."""
        return self.resolve_one(record_id)

    def list_records(
        self,
        tag: str | None = None,
        *,
        active_only: bool = False,
        where: list[tuple[str, str]] | None = None,
    ) -> list[Record]:
        if tag:
            ids = self._by_tag.get(tag.upper(), set())
            rows = [self._by_hid[i] for i in ids if i in self._by_hid]
        else:
            rows = list(self._by_hid.values())
        if active_only:
            rows = [r for r in rows if not r.is_recyclable()]
        if where:
            rows = [r for r in rows if record_matches(r, where)]
        rows.sort(key=lambda r: r.hid)
        return rows

    def _index_tag(self, rec: Record) -> None:
        self._by_tag.setdefault(rec.tag, set()).add(rec.hid)

    def _unindex_tag(self, rec: Record) -> None:
        bucket = self._by_tag.get(rec.tag)
        if bucket:
            bucket.discard(rec.hid)
            if not bucket:
                del self._by_tag[rec.tag]

    def _index_edge(self, edge: Record) -> None:
        src = edge.fields.get("src", "")
        dist = edge.fields.get("dist", "")
        if src:
            self._edges_by_src.setdefault(src, set()).add(edge.hid)
        if dist:
            self._edges_by_dist.setdefault(dist, set()).add(edge.hid)

    def _unindex_edge(self, edge: Record) -> None:
        src = edge.fields.get("src", "")
        dist = edge.fields.get("dist", "")
        if src:
            bucket = self._edges_by_src.get(src)
            if bucket:
                bucket.discard(edge.hid)
                if not bucket:
                    del self._edges_by_src[src]
        if dist:
            bucket = self._edges_by_dist.get(dist)
            if bucket:
                bucket.discard(edge.hid)
                if not bucket:
                    del self._edges_by_dist[dist]

    def _edge_records(self, edge_ids: set[str] | None) -> list[Record]:
        if not edge_ids:
            return []
        return sorted(
            (self._by_hid[eid] for eid in edge_ids if eid in self._by_hid),
            key=lambda r: r.hid,
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
        rec0 = self.resolve_one(node_id)
        if rec0 is None:
            return []
        node_id = rec0.hid
        if node_id not in self._by_hid:
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
                    if endpoint not in self._by_hid:
                        continue
                    visited.add(endpoint)
                    node_results.append(self._by_hid[endpoint])
                    queue.append((endpoint, d + 1))
        if node_id in self._by_hid and self._by_hid[node_id] not in node_results:
            node_results.insert(0, self._by_hid[node_id])
        return node_results + edge_results

    def context_walk_hops(
        self,
        *,
        anchor_id: str | None = None,
        depth: int = DEFAULT_QUERY_DEPTH,
        max_rows: int = DEFAULT_QUERY_MAX_ROWS,
        active_only: bool = False,
    ) -> list[tuple[str, str, str]]:
        """BFS walk hops from anchor: (src, relation, dst) tuples."""
        depth = min(depth, self.caps.max_depth)
        rec0 = self.resolve_one(anchor_id) if anchor_id else None
        if rec0 is None:
            return []
        anchor_id = rec0.hid
        hops: list[tuple[str, str, str]] = []
        seen_edges: set[str] = set()
        visited: set[str] = {anchor_id}
        queue: deque[tuple[str, int]] = deque([(anchor_id, 0)])
        while queue and len(hops) < max_rows:
            current, d = queue.popleft()
            if d >= depth:
                continue
            out_edges = self._edges_from(current)
            if len(out_edges) > self.caps.max_fanout:
                out_edges = out_edges[: self.caps.max_fanout]
            in_edges = self._edges_to(current)
            for edge in out_edges + in_edges:
                if active_only and edge.is_recyclable():
                    continue
                if edge.id in seen_edges:
                    continue
                seen_edges.add(edge.id)
                src = edge.fields.get("src", "")
                dst = edge.fields.get("dist", "")
                rel = edge.fields.get("relation", "")
                if not rel or not src or not dst:
                    continue
                if src not in self._by_hid or dst not in self._by_hid:
                    continue
                if current not in (src, dst):
                    continue
                hops.append((src, rel, dst))
                if len(hops) >= max_rows:
                    break
                for endpoint in (src, dst):
                    if endpoint in visited:
                        continue
                    node = self._by_hid.get(endpoint)
                    if not node or (active_only and node.is_recyclable()):
                        continue
                    visited.add(endpoint)
                    queue.append((endpoint, d + 1))
        return sorted(hops, key=lambda t: (t[0], t[1], t[2]))

    def find_path(self, source_id: str, target_id: str) -> list[Record]:
        src_rec = self.resolve_one(source_id)
        dst_rec = self.resolve_one(target_id)
        if src_rec is None or dst_rec is None:
            return []
        source_id, target_id = src_rec.hid, dst_rec.hid
        if source_id not in self._by_hid or target_id not in self._by_hid:
            return []
        if source_id == target_id:
            return [self._by_hid[source_id]]
        depth = self.caps.max_depth
        queue: deque[tuple[str, list[str]]] = deque([(source_id, [source_id])])
        visited: set[str] = {source_id}
        while queue:
            current, path = queue.popleft()
            if len(path) > depth + 1:
                continue
            for edge in self._edges_from(current):
                nxt = edge.fields.get("dist", "")
                if not nxt or nxt not in self._by_hid:
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
            records.append(self._by_hid[nid])
        for i in range(len(node_path) - 1):
            src, dst = node_path[i], node_path[i + 1]
            for edge in self._edges_from(src):
                if edge.fields.get("dist") == dst:
                    records.append(edge)
                    break
        return records

    def default_anchor(self) -> str | None:
        for rid in reversed(self.write_order):
            rec = self._by_hid.get(rid)
            if rec and rec.tag != "LAW":
                return rid
        return None

    def _law_scope_mode(self) -> str:
        """Return ``linked`` when LAW06 requests EDG-scoped warm; else ``all``."""
        for rid in self._by_tag.get("LAW", set()):
            rec = self._by_hid.get(rid)
            if rec and rec.fields.get("mechanism") == "law_scope":
                mode = rec.fields.get("constraint", "all")
                return "linked" if mode == "linked_from_anchor" else "all"
        return "all"

    @staticmethod
    def _is_engine_law_id(law_id: str) -> bool:
        return law_id in _ENGINE_LAW_IDS or bool(_ENGINE_LAW_ID_RE.match(law_id))

    @staticmethod
    def _is_universal_law(rec: Record) -> bool:
        return rec.fields.get("constraint") == "*"

    def _collect_linked_law_ids(
        self,
        anchor_id: str | None,
        context_node_ids: set[str],
        *,
        link_depth: int,
        active_only: bool,
    ) -> set[str]:
        law_ids: set[str] = set()
        for rid in self._by_tag.get("LAW", set()):
            rec = self._by_hid.get(rid)
            if not rec:
                continue
            if self._is_engine_law_id(rec.id) or self._is_universal_law(rec):
                law_ids.add(rid)

        seeds = set(context_node_ids)
        if anchor_id:
            seeds.add(anchor_id)

        queue: deque[tuple[str, int]] = deque()
        seen: set[str] = set()
        for sid in seeds:
            if sid in self._by_hid and sid not in seen:
                seen.add(sid)
                queue.append((sid, 0))

        while queue:
            nid, d = queue.popleft()
            rec = self._by_hid.get(nid)
            if rec and rec.tag == "LAW":
                law_ids.add(nid)
            if d >= link_depth:
                continue
            for edge in self._edges_from(nid) + self._edges_to(nid):
                if active_only and edge.is_recyclable():
                    continue
                rel = edge.fields.get("relation", "")
                if rel not in _LAW_LINK_RELATIONS:
                    continue
                src = edge.fields.get("src", "")
                dist = edge.fields.get("dist", "")
                other = dist if src == nid else src if dist == nid else None
                if not other or other not in self._by_hid:
                    continue
                if other not in seen:
                    seen.add(other)
                    queue.append((other, d + 1))
        return law_ids

    def _law_rows_for_context(
        self,
        *,
        anchor_id: str | None,
        context_node_ids: set[str],
        depth: int,
        active_only: bool,
    ) -> list[Record]:
        if self._law_scope_mode() == "linked":
            link_depth = max(depth + 2, 4)
            linked = self._collect_linked_law_ids(
                anchor_id,
                context_node_ids,
                link_depth=link_depth,
                active_only=active_only,
            )
            return sorted(
                (self._by_hid[i] for i in linked if i in self._by_hid),
                key=lambda r: r.hid,
            )
        return sorted(
            (self._by_hid[i] for i in self._by_tag.get("LAW", set()) if i in self._by_hid),
            key=lambda r: r.hid,
        )

    def context_pack(
        self,
        *,
        anchor_id: str | None = None,
        anchor_ids: list[str] | None = None,
        depth: int = DEFAULT_QUERY_DEPTH,
        max_rows: int = DEFAULT_QUERY_MAX_ROWS,
        active_only: bool = False,
        stale_warnings: list[tuple[Record, str]] | None = None,
    ) -> list[Record]:
        depth = min(depth, self.caps.max_depth)
        ids: list[str] = []
        for aid in list(anchor_ids or []):
            rec = self.resolve_one(aid) if aid else None
            if rec is not None and rec.hid not in ids:
                ids.append(rec.hid)
        if anchor_id:
            rec = self.resolve_one(anchor_id)
            if rec is not None and rec.hid not in ids:
                ids.append(rec.hid)
        if not ids:
            fallback = self.default_anchor()
            if fallback:
                ids = [fallback]
        payload: list[Record] = []
        context_node_ids: set[str] = set()
        seen: set[str] = set()
        for aid in ids:
            if aid not in self._by_hid:
                continue
            fanout: list[str] = []
            subgraph = self.neighbors(aid, depth, fanout_warnings=fanout)
            for w in fanout:
                emit_wrn(*w.split("|", 1))
            for rec in subgraph:
                if rec.hid in seen:
                    continue
                if active_only and rec.is_recyclable():
                    if stale_warnings is not None:
                        stale_warnings.append((rec, "stale_in_context"))
                    continue
                seen.add(rec.hid)
                payload.append(rec)
                if rec.kind == "node":
                    context_node_ids.add(rec.hid)
        nodes = [r for r in payload if r.kind == "node"]
        edges = [r for r in payload if r.kind == "edge"]
        combined = nodes + edges
        if len(combined) > max_rows:
            combined = combined[:max_rows]
        if not active_only and stale_warnings is not None:
            for rec in combined:
                if rec.is_recyclable():
                    stale_warnings.append((rec, "stale_in_context"))
        law_anchor = ids[0] if ids else None
        law_rows = self._law_rows_for_context(
            anchor_id=law_anchor,
            context_node_ids=context_node_ids,
            depth=depth,
            active_only=active_only,
        )
        if self._law_scope_mode() == "linked":
            law_ids = {r.hid for r in law_rows}
            combined = [r for r in combined if r.tag != "LAW" or r.hid not in law_ids]
        return law_rows + combined

    def to_jsonl_rows(self) -> list[dict]:
        rows: list[dict] = []
        for rid in self.write_order:
            rec = self._by_hid.get(rid)
            if rec:
                rows.append(rec.model_dump())
        return rows

    @classmethod
    def from_jsonl_rows(
        cls, rows: list[dict], tag_map: TagMap, caps: Caps | None = None
    ) -> MemStore:
        store = cls(tag_map, caps)
        records = [Record.model_validate(r) for r in rows]
        store.load_records(records)
        return store
