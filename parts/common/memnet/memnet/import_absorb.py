"""ImportAbsorb (hard) / ImportGuard (soft) — path B only (MN-REQ-12.9–12.11).

Lead-owned absorb of a bounded member slice into the mission session.
Product verb = import (not SessionMerge*; not micro merge=true; not append).

Path A (shared session re-pin_map) never enters this module. Path B spine:
optional ImportGuard host soft hook → ImportAbsorb engine hard gates
(schema/caps, ACL, LawVocabExclude, id_policy keep=MERGE-by-id | reject |
remint, nodes then edges).
"""

from __future__ import annotations

import copy
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from memnet.config import DEFAULT_QUERY_DEPTH, DEFAULT_QUERY_MAX_ROWS
from memnet.exceptions import MemNetError
from memnet.id_allocator import IdAllocator
from memnet.models import Record, new_hid
from memnet.pin_map_composer import PinMapComposer
from memnet.session import SessionStore, get_session

IdPolicy = Literal["keep", "reject", "remint"]
GuardOutcome = Literal["allow", "trim", "reject"]

_ID_POLICY = frozenset({"keep", "reject", "remint"})
_PREFIX_RE = re.compile(r"^([A-Za-z_]+)")


@dataclass
class WorkingMemorySlice:
    """Bounded member WM export for path B (MN-REQ-12.10)."""

    source_session_id: str
    anchors: list[str]
    depth: int
    view: str | None
    records: list[Record] = field(default_factory=list)

    @property
    def node_ids(self) -> set[str]:
        return {r.id for r in self.records if r.tag != "EDG" and r.tag != "LAW"}

    @property
    def edge_ids(self) -> set[str]:
        return {r.id for r in self.records if r.tag == "EDG"}


@dataclass
class ImportGuardDecision:
    """Structured soft-policy outcome (MUST NOT be chat SSOT)."""

    outcome: GuardOutcome
    reason: str
    # When outcome=trim: keep only these record ids (nodes + edges).
    keep_ids: set[str] | None = None


@dataclass
class ImportAbsorbResult:
    imported_ids: list[str] = field(default_factory=list)
    reminted: dict[str, str] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)
    decision: ImportGuardDecision | None = None
    guard_skipped: bool = True


# Optional process-wide ImportGuard soft gate (MN-REQ-12.11). None = skip.
_HOST_GUARD: Callable[[WorkingMemorySlice], ImportGuardDecision] | None = None


def set_import_guard(
    guard: Callable[[WorkingMemorySlice], ImportGuardDecision] | None,
) -> None:
    """Install or clear the optional process-wide ImportGuard host hook."""
    global _HOST_GUARD
    _HOST_GUARD = guard


def get_import_guard() -> Callable[[WorkingMemorySlice], ImportGuardDecision] | None:
    return _HOST_GUARD


def reset_import_guard_for_tests() -> None:
    set_import_guard(None)


def normalize_id_policy(policy: str | None) -> IdPolicy:
    text = (policy or "keep").strip().lower()
    # Nest IdPolicyKeep: keep = MERGE-by-id upsert; aliases only at normalise.
    if text in ("merge", "upsert"):
        text = "keep"
    if text not in _ID_POLICY:
        raise MemNetError(
            "bad_id_policy",
            f"id_policy={policy!r}; expected keep|reject|remint "
            "(keep = MERGE-by-id upsert into lead SSOT; not append)",
        )
    return text  # type: ignore[return-value]


def export_working_memory_slice(
    source: SessionStore,
    *,
    anchors: list[str],
    depth: int = DEFAULT_QUERY_DEPTH,
    max_rows: int = DEFAULT_QUERY_MAX_ROWS,
    view: str | None = None,
    caller: str | None = None,
    agent: str | None = None,
) -> WorkingMemorySlice:
    """Export a bounded pin-map slice from the member session (not whole-store)."""
    if not anchors:
        raise MemNetError(
            "no_anchor",
            "WorkingMemorySlice requires at least one anchor (MN-REQ-12.10)",
        )
    composer = PinMapComposer(source)
    by_id: dict[str, Record] = {}
    for anchor in anchors:
        a = str(anchor).strip()
        if not a:
            continue
        rows, _ = composer.compose(
            anchor=a,
            depth=depth,
            max_rows=max_rows,
            view=view,
            caller=caller,
            agent=agent,
            require_anchor=True,
        )
        for rec in rows:
            # LawVocabExclude: LAW / session-local vocab is not import payload.
            if rec.tag == "LAW":
                continue
            by_id[rec.id] = copy.deepcopy(rec)
    if not by_id:
        raise MemNetError(
            "empty_slice",
            "WorkingMemorySlice export produced no nodes/edges under anchors",
        )
    # Soft budget: never exceed max_rows * anchors (bounded; MN-REQ-12.10).
    budget = max(1, max_rows) * max(1, len([a for a in anchors if str(a).strip()]))
    if len(by_id) > budget:
        raise MemNetError(
            "slice_budget",
            f"slice has {len(by_id)} records; budget={budget} "
            f"(max_rows={max_rows} × anchors) — tighten anchors/depth "
            "(MN-REQ-12.10; no whole-store dump)",
        )
    # Nodes before edges in stable order.
    nodes = sorted(
        (r for r in by_id.values() if r.tag != "EDG"),
        key=lambda r: r.id,
    )
    edges = sorted(
        (r for r in by_id.values() if r.tag == "EDG"),
        key=lambda r: r.id,
    )
    return WorkingMemorySlice(
        source_session_id=source.session_id,
        anchors=[str(a).strip() for a in anchors if str(a).strip()],
        depth=depth,
        view=view,
        records=nodes + edges,
    )


def _apply_guard(
    slice_: WorkingMemorySlice,
    *,
    guard: Callable[[WorkingMemorySlice], ImportGuardDecision] | None,
    enable_guard: bool,
) -> tuple[WorkingMemorySlice, ImportGuardDecision | None, bool]:
    """Run optional soft guard. Returns (slice, decision, guard_skipped)."""
    active = guard if enable_guard else None
    if active is None and enable_guard:
        active = _HOST_GUARD
    if active is None:
        return slice_, None, True
    decision = active(slice_)
    if not isinstance(decision, ImportGuardDecision):
        raise MemNetError(
            "bad_guard_decision",
            "ImportGuard must return ImportGuardDecision",
        )
    if decision.outcome == "reject":
        raise MemNetError(
            "import_guard_reject",
            decision.reason or "ImportGuard rejected slice",
        )
    if decision.outcome == "trim":
        keep = decision.keep_ids
        if keep is None:
            raise MemNetError(
                "bad_guard_trim",
                "ImportGuard trim requires keep_ids",
            )
        trimmed = [r for r in slice_.records if r.id in keep]
        # Drop edges whose endpoints were trimmed away.
        node_ids = {r.id for r in trimmed if r.tag != "EDG"}
        kept: list[Record] = []
        for r in trimmed:
            if r.tag != "EDG":
                kept.append(r)
                continue
            src = r.fields.get("src", "")
            dist = r.fields.get("dist", "")
            if src in node_ids and dist in node_ids:
                kept.append(r)
        if not kept:
            raise MemNetError(
                "import_guard_trim_empty",
                decision.reason or "ImportGuard trim left empty slice",
            )
        slice_ = WorkingMemorySlice(
            source_session_id=slice_.source_session_id,
            anchors=list(slice_.anchors),
            depth=slice_.depth,
            view=slice_.view,
            records=kept,
        )
        return slice_, decision, False
    if decision.outcome != "allow":
        raise MemNetError(
            "bad_guard_outcome",
            f"ImportGuard outcome={decision.outcome!r}; expected allow|trim|reject",
        )
    return slice_, decision, False


def _prefix_for(rid: str) -> str:
    m = _PREFIX_RE.match(rid or "")
    return m.group(1) if m else "N"


def _remap_record(rec: Record, id_map: dict[str, str]) -> Record:
    out = copy.deepcopy(rec)
    new_id = id_map.get(out.id, out.id)
    out.fields["id"] = new_id
    if out.tag == "EDG":
        src = out.fields.get("src", "")
        dist = out.fields.get("dist", "")
        if src in id_map:
            out.fields["src"] = id_map[src]
        if dist in id_map:
            out.fields["dist"] = id_map[dist]
    return out


def _record_decision_atom(
    lead: SessionStore,
    decision: ImportGuardDecision,
    *,
    agent: str | None,
) -> str | None:
    """Optionally record ImportGuardDecision as a structured atom (not chat)."""
    alloc = IdAllocator(set(lead.store._by_hid.keys()))
    rid = alloc.mint("IGD")
    # Soft: only write if SCHEMA for a free-form tag is not required;
    # use CFG-like fields on a dedicated tag only when map knows it.
    # Prefer a SYS/CFG-free approach: skip if no compatible tag.
    # Use explicit fields on a synthetic note via existing flexible path:
    # if 'IGD' not in tag_map, skip silently (decision still returned).
    if lead.tag_map.get("IGD") is None and lead.tag_map.get("SYS") is None:
        return None
    tag = "IGD" if lead.tag_map.get("IGD") is not None else "SYS"
    fields = {"id": rid, "outcome": decision.outcome, "reason": decision.reason[:200]}
    # Pad required schema fields with empty defaults where needed.
    tag_def = lead.tag_map.get(tag)
    if tag_def is not None:
        for name in tag_def.fields:
            fields.setdefault(name, "")
        fields["id"] = rid
        if "outcome" in tag_def.fields:
            fields["outcome"] = decision.outcome
        if "reason" in tag_def.fields:
            fields["reason"] = decision.reason[:200]
        if "note" in tag_def.fields:
            fields["note"] = f"import_guard:{decision.outcome}:{decision.reason[:120]}"
    rec = Record(tag=tag, fields=fields)
    try:
        lead.store.upsert(rec, agent=agent, allow_new_relation=True, relations=lead.relations)
    except MemNetError:
        return None
    return rid


def absorb_working_memory_slice(
    lead: SessionStore,
    slice_: WorkingMemorySlice,
    *,
    id_policy: str | IdPolicy = "keep",
    guard: Callable[[WorkingMemorySlice], ImportGuardDecision] | None = None,
    enable_guard: bool = True,
    agent: str | None = None,
    caller: str | None = None,
    mission_id: str | None = None,
    lease: str | None = None,
    write_scope: str | None = None,
    require_bind: bool = True,
    record_decision: bool = True,
) -> ImportAbsorbResult:
    """ImportAbsorb hard-gate into lead/mission session (MN-REQ-12.9 / 12.10).

    Id policy (IdPolicyApply):
      - keep: MERGE-by-id upsert into lead SSOT (not append / second copy)
      - reject: fail if any id already exists in lead
      - remint: mint new ids for conflicts; remap edge endpoints

    DistinctSessionGate runs before ImportGuard so path A never reaches the
    soft hook.
    """
    from memnet.acl import check_bind, check_permission, check_write_scope, parse_write_scope

    if lead.session_id == slice_.source_session_id:
        raise MemNetError(
            "same_session_import",
            "path B import requires a distinct member session; "
            "path A is shared-session re-pin_map (MN-REQ-12.9)",
        )
    policy = normalize_id_policy(id_policy if isinstance(id_policy, str) else id_policy)

    acl = getattr(lead, "acl", None)
    check_permission(acl, caller=caller, permission="mutate", agent=agent)
    check_bind(acl, mission_id=mission_id, lease=lease, require=require_bind)

    work, decision, guard_skipped = _apply_guard(slice_, guard=guard, enable_guard=enable_guard)

    # LawVocabExclude: skip LAW on absorb too (guard MUST NOT reintroduce).
    skipped: list[str] = [r.id for r in work.records if r.tag == "LAW"]
    nodes = [r for r in work.records if r.tag not in ("EDG", "LAW")]
    edges = [r for r in work.records if r.tag == "EDG"]
    if not nodes and not edges:
        raise MemNetError("empty_slice", "nothing to import after guard")

    # Validate edges reference known nodes in slice or already in lead.
    lead_hids = set(lead.store._by_hid.keys())
    slice_node_hids = {r.hid for r in nodes}
    for e in edges:
        for key in ("src", "dist"):
            eid = e.fields.get(key, "")
            if eid and eid not in slice_node_hids and eid not in lead_hids:
                if lead.store.resolve_one(eid) is None:
                    raise MemNetError(
                        "dangling_import_endpoint",
                        f"edge {e.hid} {key}={eid} not in slice or lead session",
                    )

    id_map: dict[str, str] = {}
    reminted: dict[str, str] = {}

    if policy == "reject":
        # leftover façade: unique nickname collision — not product.
        conflicts = [
            r.id for r in nodes + edges if r.id and lead.store.resolve_one(r.id) is not None
        ]
        if conflicts:
            raise MemNetError(
                "id_conflict",
                "leftover id_policy=reject nickname already in lead: "
                + ",".join(sorted(conflicts)[:12]),
            )
    elif policy == "remint":
        alloc = IdAllocator(lead_hids)
        for r in nodes + edges:
            if r.id and lead.store.resolve_one(r.id) is not None:
                new_id = alloc.mint(_prefix_for(r.id))
                id_map[r.id] = new_id
                reminted[r.id] = new_id
            elif r.id:
                alloc.observe(r.id)
    # keep: upsert; no remint map

    prepared_nodes = [_remap_record(r, id_map) for r in nodes]
    prepared_edges = [_remap_record(r, id_map) for r in edges]

    # CapsPolicy WorkerWriteScope on the absorb payload.
    override = parse_write_scope(write_scope)
    check_write_scope(
        acl,
        caller=caller,
        records=prepared_nodes + prepared_edges,
        store=lead.store,
        agent=agent,
        override_scope=override,
    )

    imported: list[str] = []
    with lead.lock(exclusive=True):
        if decision is not None and record_decision:
            _record_decision_atom(lead, decision, agent=agent)
        for rec in prepared_nodes:
            work_rec = rec
            if policy == "keep":
                props = {k: v for k, v in rec.fields.items() if k != "id" and v}
                hits = lead.store.match_nodes(tag=rec.tag, props=props)
                if len(hits) > 1:
                    skipped.append(rec.id or rec.hid)
                    continue
                if len(hits) == 1:
                    merged = dict(hits[0].fields)
                    merged.update(rec.fields)
                    work_rec = Record(tag=rec.tag, fields=merged, hid=hits[0].hid)
                    lead.store.replace_row(
                        work_rec,
                        agent=agent,
                        allow_new_relation=True,
                        relations=lead.relations,
                    )
                    imported.append(work_rec.hid)
                    continue
                work_rec = Record(tag=rec.tag, fields=dict(rec.fields), hid=new_hid())
                lead.store.add_row(
                    work_rec,
                    agent=agent,
                    allow_new_relation=True,
                    relations=lead.relations,
                )
            else:
                lead.store.add_row(
                    work_rec,
                    agent=agent,
                    allow_new_relation=True,
                    relations=lead.relations,
                )
            imported.append(work_rec.hid)
        for rec in prepared_edges:
            work_rec = rec
            if policy == "keep":
                rel = rec.fields.get("relation", "")
                src = rec.fields.get("src", "")
                dist = rec.fields.get("dist", "")
                src_r = lead.store.resolve_one(src)
                dst_r = lead.store.resolve_one(dist)
                matched = None
                if src_r and dst_r:
                    for e in lead.store.list_records("EDG"):
                        if (
                            e.fields.get("relation") == rel
                            and e.fields.get("src") == src_r.hid
                            and e.fields.get("dist") == dst_r.hid
                        ):
                            matched = e
                            break
                if matched is not None:
                    merged = dict(matched.fields)
                    merged.update(rec.fields)
                    merged["src"] = src_r.hid if src_r else merged.get("src", "")
                    merged["dist"] = dst_r.hid if dst_r else merged.get("dist", "")
                    work_rec = Record(tag="EDG", fields=merged, hid=matched.hid)
                    lead.store.replace_row(
                        work_rec,
                        agent=agent,
                        allow_new_relation=True,
                        relations=lead.relations,
                    )
                    imported.append(work_rec.hid)
                    continue
                fields = dict(rec.fields)
                if src_r:
                    fields["src"] = src_r.hid
                if dst_r:
                    fields["dist"] = dst_r.hid
                work_rec = Record(tag="EDG", fields=fields, hid=new_hid())
                lead.store.add_row(
                    work_rec,
                    agent=agent,
                    allow_new_relation=True,
                    relations=lead.relations,
                )
            else:
                lead.store.add_row(
                    work_rec,
                    agent=agent,
                    allow_new_relation=True,
                    relations=lead.relations,
                )
            imported.append(work_rec.hid)
        lead.mark_written()

    return ImportAbsorbResult(
        imported_ids=imported,
        reminted=reminted,
        skipped=skipped,
        decision=decision,
        guard_skipped=guard_skipped,
    )


def import_slice(
    *,
    lead_session_id: str,
    source_session_id: str,
    anchors: list[str],
    id_policy: str = "keep",
    depth: int = DEFAULT_QUERY_DEPTH,
    max_rows: int = DEFAULT_QUERY_MAX_ROWS,
    view: str | None = None,
    guard: Callable[[WorkingMemorySlice], ImportGuardDecision] | None = None,
    enable_guard: bool = True,
    agent: str | None = None,
    caller: str | None = None,
    mission_id: str | None = None,
    lease: str | None = None,
    write_scope: str | None = None,
    require_bind: bool = True,
    source_caller: str | None = None,
) -> ImportAbsorbResult:
    """Export from member session + absorb into lead (path B convenience)."""
    if not source_session_id or not lead_session_id:
        raise MemNetError(
            "no_session",
            "import_slice requires lead and source session ids",
        )
    if lead_session_id == source_session_id:
        raise MemNetError(
            "same_session_import",
            "path B import requires distinct sessions; use re-pin_map for path A",
        )
    source = get_session(source_session_id)
    lead = get_session(lead_session_id)
    slice_ = export_working_memory_slice(
        source,
        anchors=anchors,
        depth=depth,
        max_rows=max_rows,
        view=view,
        caller=source_caller or caller,
        agent=agent,
    )
    return absorb_working_memory_slice(
        lead,
        slice_,
        id_policy=id_policy,
        guard=guard,
        enable_guard=enable_guard,
        agent=agent,
        caller=caller,
        mission_id=mission_id,
        lease=lease,
        write_scope=write_scope,
        require_bind=require_bind,
    )


# SysML-facing aliases
ImportAbsorb = absorb_working_memory_slice
ImportGuard = set_import_guard
