"""MutateGate — GQL parse → NEW mint → schema validate → strict commit."""

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
from memnet.id_allocator import AssignedIdMap, IdAllocator
from memnet.legacy_pipe_import import import_pipe_lines, looks_like_pipe
from memnet.models import Record
from memnet.output import emit_record
from memnet.tier_a import EdgeRec, Field, NodeRec, Op, Section

_MERGE_TRUE = frozenset({"true", "1", "yes"})
_LEGACY_HINT = (
    "Layer / Tier A agent wire is retired (ADR-001 M2). "
    "Use gated openCypher-shaped GQL — see docs/grammar/gql-wire-profile.md"
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
                example=("CREATE (:TSK {id: 'NEW', goal: '…', status: 'in_progress'})"),
            )
        elif looks_like_gql(s):
            kinds.add("gql")
        else:
            raise MemNetError(
                "invalid_line",
                f"unrecognised ingest line (expect GQL or @TAG pipe): {s[:80]}",
                example="CREATE (:PLR {id: 'NEW', identity: 'Hero'})",
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
        if dialect == "pipe":
            return self._apply_pipe(
                lines,
                mode=mode,
                dry_run=dry_run,
                allow_new_relation=allow_new_relation,
                agent=agent,
                caller=caller,
                write_scope_override=override,
            )
        return self._apply_gql(
            lines,
            mode=mode,
            dry_run=dry_run,
            allow_new_relation=allow_new_relation,
            agent=agent,
            caller=caller,
            write_scope_override=override,
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
    ) -> MutateResult:
        from memnet.acl import check_write_scope

        records = import_pipe_lines(lines, self.ss.tag_map, self.ss.caps)
        check_write_scope(
            getattr(self.ss, "acl", None),
            caller=caller,
            records=records,
            store=self.ss.store,
            agent=agent,
            override_scope=write_scope_override,
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
    ) -> MutateResult:
        text = "\n".join(lines)
        try:
            doc = self.codec.parse(text)
        except ParseError as exc:
            raise MemNetError(
                "parse_error",
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
            if mode == "add" and it.op in (Op.PATCH, Op.DROP) and not is_merge:
                raise MemNetError(
                    "op_mode_mismatch",
                    f"{it.op.name} illegal on add; use update (or MERGE for upsert)",
                )
            if mode == "update" and it.op == Op.CREATE:
                raise MemNetError(
                    "op_mode_mismatch",
                    "CREATE illegal on update; use add (or MERGE / SET)",
                )

        existing = set(self.ss.store.by_id.keys())
        alloc = IdAllocator(existing)
        assigned = alloc.mint_document(doc)

        # Expand MERGE into CREATE when id absent; track upsert patches
        merge_upsert_ids: set[str] = set()
        for it in doc.items:
            if (
                isinstance(it, NodeRec)
                and it.op == Op.PATCH
                and it.raw.upper().lstrip().startswith("MERGE")
            ):
                if self.ss.store.get(it.id) is None:
                    it.op = Op.CREATE
                else:
                    merge_upsert_ids.add(it.id)

        drops: list[str] = []
        records: list[Record] = []
        renames: list[tuple[str, str, bool, Record, set[str]]] = []
        ack_items: list[NodeRec | EdgeRec] = []
        for it in doc.items:
            if isinstance(it, Section):
                continue
            if isinstance(it, EdgeRec) and it.op == Op.DROP:
                drops.append(it.edge_id or "")
                ack_items.append(it)
                continue
            if isinstance(it, NodeRec) and it.op == Op.DROP:
                drops.append(it.id)
                ack_items.append(it)
                continue
            if isinstance(it, (NodeRec, EdgeRec)) and it.op == Op.CREATE:
                for f in it.fields:
                    if f.op in ("+=", "-="):
                        raise MemNetError(
                            "invalid_field",
                            f"{f.key}{f.op} illegal on create; use =",
                            example=f"{f.key}={f.value}",
                        )
            if isinstance(it, NodeRec) and it.op == Op.PATCH:
                rename_to, merge_flag, kept = _split_rename_fields(it.fields)
                patch_it = NodeRec(op=it.op, kind=it.kind, id=it.id, fields=kept, raw=it.raw)
                rec = self._item_to_record(patch_it)
                explicit = {f.key for f in kept if f.op == "="}
                if rename_to is not None:
                    renames.append((it.id, rename_to, merge_flag, rec, explicit))
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
                    old_eid = it.edge_id or ""
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
            ack_items.append(it)

        from memnet.acl import check_write_scope

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
        try:
            for eid in drops:
                old = self.ss.store.delete(eid)
                if old is None:
                    raise MemNetError("not_found", f"id {eid}|use add")
                deleted_backup.append(old)
            for rec in records:
                old = self.ss.store.get(rec.id)
                if old is None:
                    added.append(rec.id)
                else:
                    replaced.append(old)
                if rec.id in merge_upsert_ids and old is not None:
                    apply = self.ss.store.replace_row
                elif mode == "add" or (mode == "update" and old is None and rec.tag):
                    apply = self.ss.store.add_row if mode == "add" else self.ss.store.replace_row
                else:
                    apply = self.ss.store.replace_row if mode == "update" else self.ss.store.add_row
                if (mode == "update" or rec.id in merge_upsert_ids) and old is not None:
                    merged = dict(old.fields)
                    merged.update({k: v for k, v in rec.fields.items() if v != "" or k == "id"})
                    rec = Record(tag=old.tag if not rec.tag else rec.tag, fields=merged)
                # MERGE expanded to CREATE uses add_row even when mode=update
                if rec.id in added and mode == "update":
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
                field_keys = {k for k in explicit if k != "id"}
                if merge_flag:
                    warns = self.ss.store.rename_id(old_id, new_id, merge=True)
                    warnings.extend(warns)
                    if field_keys:
                        target = self.ss.store.get(new_id)
                        if target is None:
                            raise MemNetError("not_found", f"id {new_id}|use add")
                        merged = dict(target.fields)
                        for k in field_keys:
                            merged[k] = patch_rec.fields[k]
                        merged["id"] = new_id
                        warns = self.ss.store.replace_row(
                            Record(tag=target.tag, fields=merged),
                            agent=agent,
                            allow_new_relation=allow_new_relation,
                            relations=self.ss.relations,
                        )
                        warnings.extend(warns)
                else:
                    if field_keys:
                        merged = dict(old.fields)
                        for k in field_keys:
                            merged[k] = patch_rec.fields[k]
                        merged["id"] = old_id
                        warns = self.ss.store.replace_row(
                            Record(tag=old.tag, fields=merged),
                            agent=agent,
                            allow_new_relation=allow_new_relation,
                            relations=self.ss.relations,
                        )
                        warnings.extend(warns)
                    warns = self.ss.store.rename_id(old_id, new_id, merge=False)
                    warnings.extend(warns)
            self.ss.mark_written()
        except MemNetError:
            for rid in added:
                self.ss.store.delete(rid)
            for old in replaced:
                self.ss.store.by_id[old.id] = old
                if old.tag == "EDG":
                    self.ss.store._index_edge(old)
            for old in deleted_backup:
                self.ss.store.by_id[old.id] = old
                self.ss.store.write_order.append(old.id)
                self.ss.store._index_tag(old)
                if old.tag == "EDG":
                    self.ss.store._index_edge(old)
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

    def _node_to_record(self, node: NodeRec) -> Record:
        kind = node.kind
        if node.op == Op.LAW:
            kind = "LAW"
        if node.op == Op.PATCH and not kind:
            existing = self.ss.store.get(node.id)
            if existing is None:
                raise MemNetError("not_found", f"id {node.id}|use add")
            kind = existing.tag
        if not kind:
            raise MemNetError("unknown_tag", "node kind missing")
        tag_def = self.ss.tag_map.get(kind)
        if not tag_def:
            known = ",".join(self.ss.tag_map.tag_names())
            raise MemNetError("unknown_tag", f"{kind} not in schema known: {known}")

        fields: dict[str, str] = {"id": node.id}
        existing = self.ss.store.get(node.id) if node.op == Op.PATCH else None
        base = dict(existing.fields) if existing else {}

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
                        example=(f"MATCH (n {{id: '{node.id}'}}) SET n.{f.key} = <number>"),
                    ) from exc
                result = cur_n + delta if f.op == "+=" else cur_n - delta
                fields[f.key] = str(result).rstrip("0").rstrip(".")
                if fields[f.key] == "-0":
                    fields[f.key] = "0"
            else:
                fields[f.key] = f.value

        for fname in tag_def.fields:
            fields.setdefault(fname, base.get(fname, ""))
        fields["id"] = node.id
        return Record(tag=kind, fields=fields)

    def _edge_to_record(self, edge: EdgeRec) -> Record:
        tag_def = self.ss.tag_map.get("EDG")
        if not tag_def:
            raise MemNetError("unknown_tag", "EDG not in schema")
        eid = edge.edge_id
        if not eid:
            raise MemNetError("invalid_id", "edge id missing after mint")
        existing = self.ss.store.get(eid) if edge.op == Op.PATCH else None
        base = dict(existing.fields) if existing else {}
        fields: dict[str, str] = {
            "id": eid,
            "src": edge.frm or base.get("src", ""),
            "relation": edge.rel or base.get("relation", ""),
            "dist": edge.to or base.get("dist", ""),
            "at": base.get("at", ""),
            "attrs": base.get("attrs", ""),
            "recycle": base.get("recycle", "persistent"),
        }
        # Preserve bind ports / carries from base on patch
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
        return Record(tag="EDG", fields=fields)

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
                old = self.ss.store.get(rec.id)
                if old is None:
                    added.append(rec.id)
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
                        f"mission_settled|{rec.id}|next read use query pin-map --anchor <focus>"
                    )
            self.ss.mark_written()
        except MemNetError:
            for rid in added:
                self.ss.store.delete(rid)
            for old in replaced:
                self.ss.store.by_id[old.id] = old
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
