"""MutateGate — GQL parse → schema validate → pattern Commit (no NEW mint)."""

from __future__ import annotations

from dataclasses import dataclass, field

from memnet.exceptions import MemNetError
from memnet.gql import (
    ParseError,
    emit_item,
    looks_like_gql,
    looks_like_legacy_layer_or_tier_a,
    soft_validate,
)
from memnet.gql_codec import GqlCodec
from memnet.id_allocator import AssignedIdMap
from memnet.legacy_pipe_import import import_pipe_lines, looks_like_pipe
from memnet.models import Record
from memnet.output import emit_record
from memnet.same_thing_absorb import absorb_same_thing
from memnet.tier_a import EdgeRec, Field, NodeRec, Op, Section

_MERGE_TRUE = frozenset({"true", "1", "yes"})
_LEGACY_HINT = (
    "Layer / Tier A agent wire is retired (ADR-001 M2). "
    "Use gated GQL — see docs/grammar/gql-wire-profile.md"
)


def _split_rename_fields(
    fields: list[Field],
) -> tuple[str | None, bool, list[Field]]:
    """Pull id= / merge= off a patch; remaining fields apply as normal patches."""
    rename_to: str | None = None
    merge = False
    kept: list[Field] = []
    for f in fields:
        if f.key == "id" and f.op == "=":
            rename_to = f.value
            continue
        if f.key == "merge" and f.op == "=":
            merge = f.value.lower() in _MERGE_TRUE
            continue
        kept.append(f)
    return rename_to, merge, kept


def looks_like_tier_a(line: str) -> bool:
    """Deprecated detector — retained for seed dialect helpers only."""
    return looks_like_legacy_layer_or_tier_a(line)


def classify_batch(lines: list[str]) -> str:
    """Return 'gql', 'pipe', or 'empty'. Reject Layer/Tier A and mixed."""
    kinds: set[str] = set()
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if looks_like_pipe(s):
            kinds.add("pipe")
        elif looks_like_legacy_layer_or_tier_a(s):
            raise MemNetError(
                "legacy_dialect_retired",
                _LEGACY_HINT,
                example=("CREATE (:TSK {goal: '…', status: 'in_progress'})"),
            )
        elif looks_like_gql(s):
            kinds.add("gql")
        else:
            raise MemNetError(
                "invalid_line",
                f"unrecognised ingest line (expect GQL or @TAG pipe): {s[:80]}",
                example="CREATE (:PLR {identity: 'Hero'})",
            )
    if not kinds:
        return "empty"
    if kinds == {"gql"}:
        return "gql"
    if kinds == {"pipe"}:
        return "pipe"
    raise MemNetError(
        "mixed_dialect",
        "do not mix GQL and legacy @TAG pipe in one batch",
    )


@dataclass
class MutateResult:
    records: list[Record] = field(default_factory=list)
    ack_lines: list[str] = field(default_factory=list)
    assigned: AssignedIdMap = field(default_factory=AssignedIdMap)
    warnings: list[str] = field(default_factory=list)
    dialect: str = "gql"


class MutateGate:
    """Orchestrate mutate: GQL parse → mint → commit into GraphStore."""

    def __init__(self, session_store, *, codec: GqlCodec | None = None) -> None:
        self.ss = session_store
        self.codec = codec or GqlCodec()

    def apply(
        self,
        lines: list[str],
        *,
        mode: str,
        dry_run: bool = False,
        allow_new_relation: bool = False,
        agent: str | None = None,
        caller: str | None = None,
        mission_id: str | None = None,
        lease: str | None = None,
        write_scope: str | None = None,
        require_bind: bool = True,
        llm_id: str | None = None,
    ) -> MutateResult:
        from memnet.acl import check_bind, check_permission, parse_write_scope

        acl = getattr(self.ss, "acl", None)
        check_permission(acl, caller=caller, permission="mutate", agent=agent)
        check_bind(
            acl,
            mission_id=mission_id,
            lease=lease,
            require=require_bind,
        )
        override = parse_write_scope(write_scope)
        dialect = classify_batch(lines)
        if dialect == "empty":
            return MutateResult(dialect="empty")
        if dialect == "pipe" and mode == "mutate":
            raise MemNetError(
                "leftover_pipe",
                "product mutate is GQL Commit only; leftover add/update may import @TAG pipe",
            )
        if dialect == "pipe":
            return self._apply_pipe(
                lines,
                mode=mode,
                dry_run=dry_run,
                allow_new_relation=allow_new_relation,
                agent=agent,
                caller=caller,
                write_scope_override=override,
                llm_id=llm_id,
            )
        return self._apply_gql(
            lines,
            mode=mode,
            dry_run=dry_run,
            allow_new_relation=allow_new_relation,
            agent=agent,
            caller=caller,
            write_scope_override=override,
            llm_id=llm_id,
        )

    def _apply_pipe(
        self,
        lines: list[str],
        *,
        mode: str,
        dry_run: bool,
        allow_new_relation: bool,
        agent: str | None,
        caller: str | None = None,
        write_scope_override=None,
        llm_id: str | None = None,
    ) -> MutateResult:
        from memnet.acl import check_write_scope
        from memnet.neighbourhood_reserve import check_mutate_ids, touched_ids_from_records

        records = import_pipe_lines(lines, self.ss.tag_map, self.ss.caps)
        check_write_scope(
            getattr(self.ss, "acl", None),
            caller=caller,
            records=records,
            store=self.ss.store,
            agent=agent,
            override_scope=write_scope_override,
        )
        check_mutate_ids(
            self.ss.reserves,
            touched_ids=touched_ids_from_records(records),
            llm_id=llm_id,
            store=self.ss.store,
        )
        return self._commit_records(
            records,
            mode=mode,
            dry_run=dry_run,
            allow_new_relation=allow_new_relation,
            agent=agent,
            dialect="pipe",
        )

    def _apply_gql(
        self,
        lines: list[str],
        *,
        mode: str,
        dry_run: bool,
        allow_new_relation: bool,
        agent: str | None,
        caller: str | None = None,
        write_scope_override=None,
        llm_id: str | None = None,
    ) -> MutateResult:
        text = "\n".join(lines)
        try:
            doc = self.codec.parse(text)
        except ParseError as exc:
            raise MemNetError(
                getattr(exc, "code", None) or "parse_error",
                str(exc),
                example=f"line {exc.line}" if exc.line else None,
            ) from exc

        errors = [i for i in soft_validate(doc) if i.severity == "error"]
        if errors:
            first = errors[0]
            raise MemNetError(
                first.code,
                first.message,
                example=f"line {first.line}" if first.line else None,
            )

        for it in doc.items:
            if isinstance(it, Section):
                continue
            if it.op == Op.PRESENT:
                raise MemNetError(
                    "present_on_mutate",
                    "shaped pin-map lines are display-only; "
                    "use CREATE / MATCH…SET / MERGE / DELETE to mutate",
                )
            is_merge = isinstance(it, NodeRec) and it.raw.upper().lstrip().startswith("MERGE")
            is_absorb = isinstance(it, NodeRec) and it.same_thing
            if mode == "mutate":
                continue
            if mode == "add" and it.op in (Op.PATCH, Op.DROP) and not is_merge and not is_absorb:
                raise MemNetError(
                    "op_mode_mismatch",
                    f"{it.op.name} illegal on add; use update (or MERGE for upsert)",
                )
            if mode == "update" and it.op == Op.CREATE:
                raise MemNetError(
                    "op_mode_mismatch",
                    "CREATE illegal on update; use add (or MERGE / SET)",
                )

        existing = set(self.ss.store._by_hid.keys())
        # leftover IdAllocator / AssignedIdMap / NEW mint: not product Commit.
        assigned = AssignedIdMap()
        del existing

        # Expand MERGE into CREATE when pattern absent; track upsert by hid.
        # Do not copy hid onto NodeRec.id — ack/emit is labels+props / nickname only.
        merge_upsert_ids: set[str] = set()
        merge_bound: dict[int, Record] = {}
        for it in doc.items:
            if (
                isinstance(it, NodeRec)
                and it.op == Op.PATCH
                and it.raw.upper().lstrip().startswith("MERGE")
            ):
                hits = self._pattern_hits(it)
                if len(hits) > 1:
                    raise MemNetError(
                        "cue_conflict",
                        f"MERGE |Q|={len(hits)}; SHALL NOT pick one root or absorb",
                    )
                if not hits:
                    it.op = Op.CREATE
                else:
                    merge_upsert_ids.add(hits[0].hid)
                    merge_bound[id(it)] = hits[0]

        drops: list[str] = []
        records: list[Record] = []
        pending: list[Record] = []
        deferred_edges: list[EdgeRec] = []
        renames: list[tuple[str, str, bool, Record, set[str]]] = []
        ack_items: list[NodeRec | EdgeRec] = []
        absorbs: list[tuple[Record, Record, dict[str, str]]] = []
        for it in doc.items:
            if isinstance(it, Section):
                continue
            if isinstance(it, EdgeRec) and it.op == Op.DROP:
                hid = self._resolve_edge_drop(it)
                drops.append(hid)
                ack_items.append(it)
                continue
            if isinstance(it, NodeRec) and it.op == Op.DROP:
                hits = self._pattern_hits(it)
                if len(hits) > 1:
                    raise MemNetError(
                        "cue_conflict",
                        f"DELETE |Q|={len(hits)}; SHALL NOT pick one root or absorb",
                    )
                if not hits:
                    raise MemNetError("not_found", "DELETE matched no element")
                drops.append(hits[0].hid)
                ack_items.append(it)
                continue
            if isinstance(it, EdgeRec) and it.op == Op.CREATE:
                deferred_edges.append(it)
                continue
            if isinstance(it, (NodeRec, EdgeRec)) and it.op == Op.CREATE:
                for f in it.fields:
                    if f.op in ("+=", "-="):
                        raise MemNetError(
                            "invalid_field",
                            f"{f.key}{f.op} illegal on create; use =",
                            example=f"{f.key}={f.value}",
                        )
            if isinstance(it, NodeRec) and it.op == Op.PATCH and it.same_thing:
                keep_rec, drop_rec = self._same_thing_pair(it)
                rename_to, merge_flag, kept = _split_rename_fields(it.fields)
                if rename_to is not None or merge_flag:
                    raise MemNetError(
                        "invalid_merge",
                        "SameThingAbsorb is pattern collapse; "
                        "leftover merge=true / id= is not identity",
                    )
                extra: dict[str, str] = {}
                for f in kept:
                    if f.op != "=":
                        raise MemNetError(
                            "invalid_field",
                            f"{f.key}{f.op} illegal on SameThingAbsorb; use =",
                            example=f"{f.key}={f.value}",
                        )
                    extra[f.key] = f.value
                absorbs.append((keep_rec, drop_rec, extra))
                ack_items.append(it)
                continue
            if isinstance(it, NodeRec) and it.op == Op.PATCH:
                rename_to, merge_flag, kept = _split_rename_fields(it.fields)
                bound = None
                is_merge = it.raw.upper().lstrip().startswith("MERGE")
                if is_merge:
                    bound = merge_bound.get(id(it))
                    if bound is None and it.id in merge_upsert_ids:
                        bound = self.ss.store._by_hid.get(it.id)
                else:
                    hits = self._pattern_hits(it)
                    if len(hits) > 1:
                        raise MemNetError(
                            "cue_conflict",
                            f"SET |Q|={len(hits)}; SHALL NOT pick one root or absorb",
                        )
                    if not hits:
                        raise MemNetError("not_found", "SET matched no element|use add")
                    bound = hits[0]
                patch_it = NodeRec(
                    op=it.op,
                    kind=it.kind,
                    id=it.id,
                    fields=kept,
                    raw=it.raw,
                    match_props=it.match_props,
                )
                rec = self._item_to_record(patch_it)
                if bound is not None:
                    rec.hid = bound.hid
                    if "id" not in rec.fields and bound.id:
                        rec.fields["id"] = bound.id
                explicit = {f.key for f in kept if f.op == "="}
                if rename_to is not None:
                    old_hid = bound.hid if bound is not None else ""
                    if not old_hid:
                        found = self.ss.store.resolve_one(it.id)
                        old_hid = found.hid if found is not None else it.id
                    rec.hid = old_hid
                    renames.append((old_hid, rename_to, merge_flag, rec, explicit))
                    ack_items.append(
                        NodeRec(
                            op=Op.PATCH,
                            kind=rec.tag,
                            id=rename_to,
                            fields=kept,
                            raw=it.raw,
                        )
                    )
                    continue
                records.append(rec)
                ack_items.append(it)
                continue
            if isinstance(it, EdgeRec) and it.op == Op.PATCH:
                rename_to, merge_flag, kept = _split_rename_fields(it.fields)
                if rename_to is not None:
                    if merge_flag:
                        raise MemNetError(
                            "invalid_merge",
                            "merge=true applies to nodes only (not EDG)",
                        )
                    patch_it = EdgeRec(
                        op=it.op,
                        edge_id=it.edge_id,
                        frm=it.frm,
                        rel=it.rel,
                        to=it.to,
                        fields=kept,
                        raw=it.raw,
                    )
                    rec = self._item_to_record(patch_it)
                    found = self.ss.store.resolve_one(it.edge_id) if it.edge_id else None
                    old_eid = found.hid if found is not None else (it.edge_id or "")
                    rec.hid = old_eid
                    explicit = {f.key for f in kept if f.op == "="}
                    renames.append((old_eid, rename_to, False, rec, explicit))
                    ack_items.append(
                        EdgeRec(
                            op=Op.PATCH,
                            edge_id=rename_to,
                            frm=it.frm,
                            rel=it.rel,
                            to=it.to,
                            fields=kept,
                            raw=it.raw,
                        )
                    )
                    continue
            rec = self._item_to_record(it)
            records.append(rec)
            pending.append(rec)
            ack_items.append(it)

        for it in deferred_edges:
            for f in it.fields:
                if f.op in ("+=", "-="):
                    raise MemNetError(
                        "invalid_field",
                        f"{f.key}{f.op} illegal on create; use =",
                        example=f"{f.key}={f.value}",
                    )
            it.frm = self._resolve_end(it.frm, it.frm_label, it.frm_props, pending=pending)
            it.to = self._resolve_end(it.to, it.to_label, it.to_props, pending=pending)
            rec = self._item_to_record(it)
            records.append(rec)
            ack_items.append(it)

        from memnet.acl import check_write_scope
        from memnet.neighbourhood_reserve import check_mutate_ids, touched_ids_from_records

        # Include rename targets in scope check
        scope_records = list(records)
        for _old_id, _new_id, _merge, patch_rec, _explicit in renames:
            scope_records.append(patch_rec)
        check_write_scope(
            getattr(self.ss, "acl", None),
            caller=caller,
            records=scope_records,
            store=self.ss.store,
            agent=agent,
            override_scope=write_scope_override,
        )
        touched = touched_ids_from_records(scope_records)
        touched.update(drops)
        for keep_rec, drop_rec, _extra in absorbs:
            touched.add(keep_rec.hid)
            touched.add(drop_rec.hid)
        for old_id, new_id, _merge, _patch_rec, _explicit in renames:
            o = self.ss.store.resolve_one(old_id)
            n = self.ss.store.resolve_one(new_id)
            if o:
                touched.add(o.hid)
            if n:
                touched.add(n.hid)
        check_mutate_ids(
            self.ss.reserves,
            touched_ids=touched,
            llm_id=llm_id,
            store=self.ss.store,
        )

        if dry_run:
            ack = [emit_item(x, as_mutate=True) for x in ack_items]
            return MutateResult(
                records=records,
                ack_lines=ack,
                assigned=assigned,
                dialect="gql",
            )

        warnings: list[str] = []
        added: list[str] = []
        replaced: list[Record] = []
        deleted_backup: list[Record] = []
        # Successful rename_id ops — inverted on MemNetError (before upsert/drop undo).
        # Entry: (old_id, new_id, merge, source_backup, endpoint_changes).
        # endpoint_changes: (edge_id, "src"|"dist") that pointed at old_id before rename.
        applied_renames: list[tuple[str, str, bool, Record, list[tuple[str, str]]]] = []
        replaced_ids: set[str] = set()

        def _snapshot(rec: Record) -> Record:
            return Record(tag=rec.tag, fields=dict(rec.fields), hid=rec.hid)

        def _remember_replaced(rec: Record) -> None:
            if rec.hid not in replaced_ids:
                replaced.append(_snapshot(rec))
                replaced_ids.add(rec.hid)

        def _endpoint_changes_for(oid: str) -> list[tuple[str, str]]:
            store = self.ss.store
            changes: list[tuple[str, str]] = []
            affected = set(store._edges_by_src.get(oid, ())) | set(
                store._edges_by_dist.get(oid, ())
            )
            for eid in affected:
                edge = store._by_hid.get(eid)
                if edge is None or edge.tag != "EDG":
                    continue
                if edge.fields.get("src") == oid:
                    changes.append((eid, "src"))
                if edge.fields.get("dist") == oid:
                    changes.append((eid, "dist"))
            return changes

        try:
            absorb_warnings: list[str] = []
            for keep_rec, drop_rec, extra in absorbs:
                _remember_replaced(keep_rec)
                keep_hid, drop_hid = keep_rec.hid, drop_rec.hid
                for edge in list(self.ss.store.list_records("EDG")):
                    src = edge.fields.get("src", "")
                    dist = edge.fields.get("dist", "")
                    if src in (keep_hid, drop_hid) or dist in (keep_hid, drop_hid):
                        _remember_replaced(edge)
                deleted_backup.append(_snapshot(drop_rec))
                _keep, warns = absorb_same_thing(self.ss.store, keep_rec, drop_rec, extra=extra)
                absorb_warnings.extend(warns)
            warnings.extend(absorb_warnings)
            for eid in drops:
                old = self.ss.store.delete(eid)
                if old is None:
                    raise MemNetError("not_found", f"id {eid}|use add")
                deleted_backup.append(old)
            for rec in records:
                old = self.ss.store._by_hid.get(rec.hid)
                if old is None:
                    added.append(rec.hid)
                else:
                    _remember_replaced(old)
                if rec.hid in merge_upsert_ids and old is not None:
                    apply = self.ss.store.replace_row
                elif mode == "mutate":
                    apply = self.ss.store.add_row if old is None else self.ss.store.replace_row
                elif mode == "add" or (mode == "update" and old is None and rec.tag):
                    apply = self.ss.store.add_row if mode == "add" else self.ss.store.replace_row
                else:
                    apply = self.ss.store.replace_row if mode == "update" else self.ss.store.add_row
                if (
                    mode in ("update", "mutate") or rec.hid in merge_upsert_ids
                ) and old is not None:
                    merged = dict(old.fields)
                    merged.update({k: v for k, v in rec.fields.items() if v != "" or k == "id"})
                    rec = Record(
                        tag=old.tag if not rec.tag else rec.tag,
                        fields=merged,
                        hid=old.hid,
                    )
                if rec.hid in added and mode == "update":
                    apply = self.ss.store.add_row
                warns = apply(
                    rec,
                    agent=agent,
                    allow_new_relation=allow_new_relation,
                    relations=self.ss.relations,
                )
                warnings.extend(warns)
            for old_id, new_id, merge_flag, patch_rec, explicit in renames:
                if mode != "update":
                    raise MemNetError(
                        "op_mode_mismatch",
                        "id= rename requires update mode",
                    )
                old = self.ss.store.get(old_id)
                if old is None:
                    raise MemNetError("not_found", f"id {old_id}|use add")
                source_backup = _snapshot(old)
                ep_changes = _endpoint_changes_for(old.hid)
                field_keys = {k for k in explicit if k != "id"}
                if merge_flag:
                    if field_keys:
                        target_pre = self.ss.store.get(new_id)
                        if target_pre is not None:
                            _remember_replaced(target_pre)
                    warns = self.ss.store.rename_id(old.hid, new_id, merge=True)
                    warnings.extend(warns)
                    applied_renames.append((old.hid, new_id, True, source_backup, ep_changes))
                    if field_keys:
                        target = self.ss.store.get(new_id)
                        if target is None:
                            raise MemNetError("not_found", f"id {new_id}|use add")
                        merged = dict(target.fields)
                        for k in field_keys:
                            merged[k] = patch_rec.fields[k]
                        merged["id"] = new_id
                        warns = self.ss.store.replace_row(
                            Record(tag=target.tag, fields=merged, hid=target.hid),
                            agent=agent,
                            allow_new_relation=allow_new_relation,
                            relations=self.ss.relations,
                        )
                        warnings.extend(warns)
                else:
                    if field_keys:
                        _remember_replaced(old)
                        merged = dict(old.fields)
                        for k in field_keys:
                            merged[k] = patch_rec.fields[k]
                        warns = self.ss.store.replace_row(
                            Record(tag=old.tag, fields=merged, hid=old.hid),
                            agent=agent,
                            allow_new_relation=allow_new_relation,
                            relations=self.ss.relations,
                        )
                        warnings.extend(warns)
                    warns = self.ss.store.rename_id(old.hid, new_id, merge=False)
                    warnings.extend(warns)
                    orig_nick = source_backup.fields.get("id") or ""
                    if orig_nick != new_id:
                        applied_renames.append((old.hid, new_id, False, source_backup, ep_changes))
            self.ss.mark_written()
        except MemNetError:
            # Undo renames first (commit order: drops → upserts → renames).
            store = self.ss.store
            for old_id, new_id, merge_flag, source_backup, ep_changes in reversed(applied_renames):
                if merge_flag:
                    # Restore deleted source, then put retargeted endpoints back.
                    if old_id not in store._by_hid:
                        store._by_hid[old_id] = source_backup
                        if old_id not in store.write_order:
                            store.write_order.append(old_id)
                        store._index_tag(source_backup)
                    survivor = store.resolve_one(new_id)
                    survivor_hid = survivor.hid if survivor is not None else new_id
                    for eid, field in ep_changes:
                        edge = store._by_hid.get(eid)
                        if edge is None or edge.tag != "EDG":
                            continue
                        if edge.fields.get(field) != survivor_hid:
                            continue
                        store._unindex_edge(edge)
                        edge.fields[field] = old_id
                        store._index_edge(edge)
                else:
                    orig_nick = source_backup.fields.get("id") or ""
                    cur = store._by_hid.get(source_backup.hid)
                    if cur is not None and orig_nick and cur.fields.get("id") != orig_nick:
                        store.rename_id(source_backup.hid, orig_nick, merge=False)
            for rid in added:
                store.delete(rid)
            for old in replaced:
                cur = store._by_hid.get(old.hid)
                if cur is not None:
                    if cur.tag == "EDG":
                        store._unindex_edge(cur)
                    store._unindex_tag(cur)
                store._by_hid[old.hid] = old
                store._index_tag(old)
                if old.tag == "EDG":
                    store._index_edge(old)
            for old in deleted_backup:
                store._by_hid[old.hid] = old
                store.write_order.append(old.hid)
                store._index_tag(old)
                if old.tag == "EDG":
                    store._index_edge(old)
            raise

        ack = [emit_item(x, as_mutate=True) for x in ack_items]
        return MutateResult(
            records=records,
            ack_lines=ack,
            assigned=assigned,
            warnings=warnings,
            dialect="gql",
        )

    def _item_to_record(self, it: NodeRec | EdgeRec) -> Record:
        if isinstance(it, EdgeRec):
            return self._edge_to_record(it)
        return self._node_to_record(it)

    def _pattern_hits(self, it: NodeRec) -> list[Record]:
        store = self.ss.store
        if it.id and it.id in store._by_hid:
            return [store._by_hid[it.id]]
        props = dict(it.match_props or {})
        if it.id and "id" not in props:
            one = store.resolve_one(it.id)
            if one is not None and not props:
                return [one]
            if it.id:
                props["id"] = it.id
        tag = it.kind or None
        if not tag and not props:
            return []
        return store.match_nodes(tag=tag, props=props)

    def _same_thing_pair(self, it: NodeRec) -> tuple[Record, Record]:
        keep_hits = self._pattern_hits(
            NodeRec(
                op=Op.PATCH,
                kind=it.kind,
                id="",
                match_props=dict(it.match_props or {}),
            )
        )
        drop_hits = self._pattern_hits(
            NodeRec(
                op=Op.PATCH,
                kind=it.absorb_kind,
                id="",
                match_props=dict(it.absorb_match_props or {}),
            )
        )
        if len(keep_hits) > 1:
            raise MemNetError(
                "cue_conflict",
                f"SameThingAbsorb keep |Q|={len(keep_hits)}; SHALL NOT pick one root",
            )
        if len(drop_hits) > 1:
            raise MemNetError(
                "cue_conflict",
                f"SameThingAbsorb drop |Q|={len(drop_hits)}; SHALL NOT pick one root",
            )
        if not keep_hits or not drop_hits:
            raise MemNetError(
                "not_found",
                "SameThingAbsorb MATCH missed a pattern (labels+properties)",
            )
        if keep_hits[0].hid == drop_hits[0].hid:
            raise MemNetError(
                "cue_conflict",
                "SameThingAbsorb patterns hit the same element; name is a candidate only",
            )
        return keep_hits[0], drop_hits[0]

    def _resolve_end(
        self,
        token: str,
        label: str,
        props: dict[str, str],
        *,
        pending: list[Record] | None = None,
    ) -> str:
        store = self.ss.store
        want = {k: str(v) for k, v in (props or {}).items() if str(v) != ""}
        if label or want:
            hits = self._match_nodes_with_pending(tag=label or None, props=want, pending=pending)
            pending_set = {r.hid for r in (pending or [])}
            pending_hits = [h for h in hits if h.hid in pending_set]
            # Same-batch CREATE wins for wiring; not absorb of historical twins.
            if len(pending_hits) == 1:
                return pending_hits[0].hid
            if len(pending_hits) > 1:
                raise MemNetError(
                    "cue_conflict",
                    f"relationship end |Q|={len(pending_hits)}; SHALL NOT pick one root or absorb",
                )
            if len(hits) > 1:
                raise MemNetError(
                    "cue_conflict",
                    f"relationship end |Q|={len(hits)}; SHALL NOT pick one root or absorb",
                )
            if len(hits) == 1:
                return hits[0].hid
        rec = store.resolve_one(token)
        if rec is not None:
            return rec.hid
        for row in pending or []:
            if row.hid == token or row.fields.get("id") == token:
                return row.hid
        raise MemNetError(
            "not_found",
            f"relationship end {token!r} unmatched (labels+properties)",
        )

    def _match_nodes_with_pending(
        self,
        *,
        tag: str | None,
        props: dict[str, str],
        pending: list[Record] | None,
    ) -> list[Record]:
        hits = list(self.ss.store.match_nodes(tag=tag, props=props))
        seen = {r.hid for r in hits}
        tag_u = tag.upper() if tag else None
        want = {k: str(v) for k, v in (props or {}).items() if v is not None}
        for rec in pending or []:
            if rec.tag == "EDG" or rec.hid in seen:
                continue
            if tag_u and rec.tag.upper() != tag_u:
                continue
            if all(str(rec.fields.get(k, "")) == val for k, val in want.items()):
                hits.append(rec)
                seen.add(rec.hid)
        hits.sort(key=lambda r: r.hid)
        return hits

    def _resolve_edge_drop(self, it: EdgeRec) -> str:
        store = self.ss.store
        if it.edge_id:
            rec = store.resolve_one(it.edge_id)
            if rec is not None and rec.tag == "EDG":
                return rec.hid
        rel = it.rel
        for rec in store.list_records("EDG"):
            if rel and rec.fields.get("relation") != rel:
                continue
            if it.frm:
                src = store.resolve_one(it.frm)
                if src is None or rec.fields.get("src") != src.hid:
                    continue
            if it.to:
                dst = store.resolve_one(it.to)
                if dst is None or rec.fields.get("dist") != dst.hid:
                    continue
            return rec.hid
        raise MemNetError("not_found", "relationship DELETE matched no element")

    def _node_to_record(self, node: NodeRec) -> Record:
        kind = node.kind
        if node.op == Op.LAW:
            kind = "LAW"
        bound = None
        if node.op == Op.PATCH:
            hits = self._pattern_hits(node)
            if len(hits) == 1:
                bound = hits[0]
                if not kind:
                    kind = bound.tag
        unlabeled = not kind
        if unlabeled:
            kind = ""
        tag_def = self.ss.tag_map.get(kind) if kind else None
        if kind and not tag_def:
            known = ",".join(self.ss.tag_map.tag_names())
            raise MemNetError("unknown_tag", f"{kind} not in schema known: {known}")

        fields: dict[str, str] = {}
        base = dict(bound.fields) if bound else {}
        nick = node.id
        if nick and not str(nick).startswith("_el"):
            fields["id"] = nick
        elif bound and bound.id:
            fields["id"] = bound.id

        for f in node.fields:
            if f.op in ("+=", "-="):
                cur = base.get(f.key, fields.get(f.key, "0"))
                try:
                    cur_n = float(cur)
                    delta = float(f.value)
                except ValueError as exc:
                    raise MemNetError(
                        "bad_numeric",
                        f"{f.key}{f.op}{f.value} requires numeric field",
                        example=(f"MATCH (n) SET n.{f.key} = <number>"),
                    ) from exc
                result = cur_n + delta if f.op == "+=" else cur_n - delta
                fields[f.key] = str(result).rstrip("0").rstrip(".")
                if fields[f.key] == "-0":
                    fields[f.key] = "0"
            else:
                fields[f.key] = f.value

        if tag_def:
            for fname in tag_def.fields:
                fields.setdefault(fname, base.get(fname, ""))
            if not fields.get("id"):
                fields.pop("id", None)
        rec = Record(tag=kind, fields=fields)
        if bound is not None:
            rec.hid = bound.hid
        return rec

    def _edge_to_record(self, edge: EdgeRec) -> Record:
        tag_def = self.ss.tag_map.get("EDG")
        if not tag_def:
            raise MemNetError("unknown_tag", "EDG not in schema")
        eid = edge.edge_id or ""
        existing = self.ss.store.resolve_one(eid) if eid and edge.op == Op.PATCH else None
        base = dict(existing.fields) if existing else {}
        fields: dict[str, str] = {
            "src": edge.frm or base.get("src", ""),
            "relation": edge.rel or base.get("relation", ""),
            "dist": edge.to or base.get("dist", ""),
            "at": base.get("at", ""),
            "attrs": base.get("attrs", ""),
            "recycle": base.get("recycle", "persistent"),
        }
        if eid and not str(eid).startswith("_el"):
            fields["id"] = eid
        for k in ("src_port", "dist_port", "carries", "wire"):
            if k in base and base[k]:
                fields[k] = base[k]
        for f in edge.fields:
            if f.key in ("src", "relation", "dist", "at", "attrs", "recycle"):
                fields[f.key] = f.value
            elif f.key in ("fromPort", "src_port"):
                fields["src_port"] = f.value
            elif f.key in ("toPort", "dist_port"):
                fields["dist_port"] = f.value
            elif f.key in ("carries", "wire"):
                fields[f.key] = f.value
            elif f.key == "note":
                fields["attrs"] = f.value
            else:
                if fields["attrs"]:
                    fields["attrs"] = f"{fields['attrs']};{f.key}={f.value}"
                else:
                    fields["attrs"] = f"{f.key}={f.value}"
        for fname in tag_def.fields:
            fields.setdefault(fname, "")
        if not fields.get("id"):
            fields.pop("id", None)
        rec = Record(tag="EDG", fields=fields)
        if existing is not None:
            rec.hid = existing.hid
        return rec

    def _commit_records(
        self,
        records: list[Record],
        *,
        mode: str,
        dry_run: bool,
        allow_new_relation: bool,
        agent: str | None,
        dialect: str,
    ) -> MutateResult:
        if dry_run:
            ack = [emit_record(r, self.ss.tag_map) for r in records]
            return MutateResult(records=records, ack_lines=ack, dialect=dialect)

        warnings: list[str] = []
        added: list[str] = []
        replaced: list[Record] = []
        try:
            for rec in records:
                old = self.ss.store._by_hid.get(rec.hid)
                if old is None and rec.id:
                    old = self.ss.store.resolve_one(rec.id)
                    if old is not None:
                        rec.hid = old.hid
                if old is None:
                    added.append(rec.hid)
                else:
                    replaced.append(old)
                apply = self.ss.store.add_row if mode == "add" else self.ss.store.replace_row
                warns = apply(
                    rec,
                    agent=agent,
                    allow_new_relation=allow_new_relation,
                    relations=self.ss.relations,
                )
                warnings.extend(warns)
                if (
                    rec.tag == "TSK"
                    and rec.fields.get("status") == "settled"
                    and (old is None or old.fields.get("status") != "settled")
                ):
                    warnings.append(
                        f"mission_settled|{rec.id or rec.hid}|next read use query pin-map from cue"
                    )
            self.ss.mark_written()
        except MemNetError:
            for rid in added:
                self.ss.store.delete(rid)
            for old in replaced:
                self.ss.store._by_hid[old.hid] = old
                if old.tag == "EDG":
                    self.ss.store._index_edge(old)
            raise

        ack = [emit_record(r, self.ss.tag_map) for r in records]
        return MutateResult(
            records=records,
            ack_lines=ack,
            warnings=warnings,
            dialect=dialect,
        )
