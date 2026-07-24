"""MutateGate — Tier A parse → NEW mint → schema validate → strict commit."""

from __future__ import annotations

from dataclasses import dataclass, field

from memnet.exceptions import MemNetError
from memnet.id_allocator import AssignedIdMap, IdAllocator
from memnet.legacy_pipe_import import import_pipe_lines, looks_like_pipe
from memnet.models import Record
from memnet.output import emit_record
from memnet.tier_a import (
    EdgeRec,
    Field,
    NodeRec,
    Op,
    ParseError,
    Section,
    emit_item,
)
from memnet.tier_a_codec import TierACodec

_MERGE_TRUE = frozenset({"true", "1", "yes"})


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
    s = line.strip().lstrip("\ufeff")
    if not s or s.startswith("#"):
        return False
    if s.startswith("@"):
        return False
    if s.startswith("##"):
        return True
    if s.startswith(("+", "~", "-")):
        return True
    # Engine LAW01… or domain LAW-CODE01 / LAW_SNAP01
    if s.startswith("LAW") and len(s) > 3 and (s[3].isdigit() or s[3] in "-_"):
        return True
    return False


def classify_batch(lines: list[str]) -> str:
    """Return 'tier_a', 'pipe', or 'empty'. Reject mixed dialect."""
    kinds: set[str] = set()
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if looks_like_pipe(s):
            kinds.add("pipe")
        elif looks_like_tier_a(s):
            kinds.add("tier_a")
        else:
            raise MemNetError("invalid_line", f"unrecognised ingest line: {s[:80]}")
    if not kinds:
        return "empty"
    if kinds == {"tier_a"}:
        return "tier_a"
    if kinds == {"pipe"}:
        return "pipe"
    raise MemNetError("mixed_dialect", "do not mix Tier A and legacy @TAG pipe in one batch")


@dataclass
class MutateResult:
    records: list[Record] = field(default_factory=list)
    ack_lines: list[str] = field(default_factory=list)
    assigned: AssignedIdMap = field(default_factory=AssignedIdMap)
    warnings: list[str] = field(default_factory=list)
    dialect: str = "pipe"


class MutateGate:
    """Orchestrate mutate: parse → mint → commit into GraphStore."""

    def __init__(self, session_store, *, codec: TierACodec | None = None) -> None:
        self.ss = session_store
        self.codec = codec or TierACodec()

    def apply(
        self,
        lines: list[str],
        *,
        mode: str,
        dry_run: bool = False,
        allow_new_relation: bool = False,
        agent: str | None = None,
    ) -> MutateResult:
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
            )
        return self._apply_tier_a(
            lines,
            mode=mode,
            dry_run=dry_run,
            allow_new_relation=allow_new_relation,
            agent=agent,
        )

    def _apply_pipe(
        self,
        lines: list[str],
        *,
        mode: str,
        dry_run: bool,
        allow_new_relation: bool,
        agent: str | None,
    ) -> MutateResult:
        records = import_pipe_lines(lines, self.ss.tag_map, self.ss.caps)
        return self._commit_records(
            records,
            mode=mode,
            dry_run=dry_run,
            allow_new_relation=allow_new_relation,
            agent=agent,
            dialect="pipe",
        )

    def _apply_tier_a(
        self,
        lines: list[str],
        *,
        mode: str,
        dry_run: bool,
        allow_new_relation: bool,
        agent: str | None,
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

        for it in doc.items:
            if isinstance(it, Section):
                continue
            if it.op == Op.PRESENT:
                raise MemNetError(
                    "present_on_mutate",
                    "bare pin-map lines are display-only; use + / ~ / - to mutate",
                )
            if mode == "add" and it.op in (Op.PATCH, Op.DROP):
                raise MemNetError(
                    "op_mode_mismatch",
                    f"{it.op.value} illegal on add; use update",
                )
            if mode == "update" and it.op == Op.CREATE:
                raise MemNetError(
                    "op_mode_mismatch",
                    "+ create illegal on update; use add",
                )
            if mode == "update" and it.op == Op.LAW:
                raise MemNetError("op_mode_mismatch", "LAW lines are create-only via add")

        existing = set(self.ss.store.by_id.keys())
        alloc = IdAllocator(existing)
        assigned = alloc.mint_document(doc)

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
            if isinstance(it, NodeRec) and it.op == Op.CREATE:
                if any(f.key == "id" for f in it.fields):
                    raise MemNetError(
                        "invalid_field",
                        "id= illegal on create; put id in [brackets]",
                    )
            if isinstance(it, NodeRec) and it.op == Op.PATCH:
                rename_to, merge_flag, kept = _split_rename_fields(it.fields)
                patch_it = NodeRec(
                    op=it.op, kind=it.kind, id=it.id, fields=kept, raw=it.raw
                )
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

        if dry_run:
            ack = [emit_item(x) for x in ack_items]
            return MutateResult(
                records=records,
                ack_lines=ack,
                assigned=assigned,
                dialect="tier_a",
            )

        # Commit drops first on update
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
                if mode == "add" or (mode == "update" and old is None and rec.tag):
                    # Tier A CREATE after mint always uses add_row
                    apply = self.ss.store.add_row if mode == "add" else self.ss.store.replace_row
                else:
                    apply = self.ss.store.replace_row if mode == "update" else self.ss.store.add_row
                # Patch: merge fields onto existing
                if mode == "update" and old is not None:
                    merged = dict(old.fields)
                    merged.update({k: v for k, v in rec.fields.items() if v != "" or k == "id"})
                    # Apply += / -= already resolved into absolute values in _item_to_record
                    rec = Record(tag=old.tag if not rec.tag else rec.tag, fields=merged)
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
                # Only wire-explicit fields (not TagMap defaults filled by _node_to_record).
                field_keys = {k for k in explicit if k != "id"}
                if merge_flag:
                    # Merge first (drop source); then patch surviving target.
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
                    # Patch source in place, then re-key (fields travel with the row).
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

        ack = [emit_item(x) for x in ack_items]
        # Rewrite ack with assigned ground ids (already on items after mint)
        return MutateResult(
            records=records,
            ack_lines=ack,
            assigned=assigned,
            warnings=warnings,
            dialect="tier_a",
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
            if f.op == "+=":
                cur = base.get(f.key, fields.get(f.key, "0"))
                try:
                    fields[f.key] = str(float(cur) + float(f.value)).rstrip("0").rstrip(".")
                    if fields[f.key] == "-0":
                        fields[f.key] = "0"
                except ValueError as exc:
                    raise MemNetError("bad_numeric", f"{f.key}+={f.value}") from exc
            elif f.op == "-=":
                cur = base.get(f.key, fields.get(f.key, "0"))
                try:
                    fields[f.key] = str(float(cur) - float(f.value)).rstrip("0").rstrip(".")
                except ValueError as exc:
                    raise MemNetError("bad_numeric", f"{f.key}-={f.value}") from exc
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
        for f in edge.fields:
            if f.key in ("src", "relation", "dist", "at", "attrs", "recycle"):
                fields[f.key] = f.value
            elif f.key == "note":
                fields["attrs"] = f.value
            else:
                # stash unknown into attrs lightly
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
                        f"mission_settled|{rec.id}|next read use query warm --anchor <focus>"
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
