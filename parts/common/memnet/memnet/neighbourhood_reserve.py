"""Neighbourhood reserve (RSV) — ego leases with llm_id + TTL (MN-REQ-12.13).

Control-plane leases inside an authorised session. Not durable graph rows.
Design SSOT: docs/extras/memnet-neighbourhood-reserve.md.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from memnet.exceptions import MemNetError
from memnet.models import Record

IMPLEMENTED = True


def _now(now: datetime | None = None) -> datetime:
    if now is not None:
        return now
    from memnet.session import utc_now

    return utc_now()


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ReserveLease:
    rid: str
    llm_id: str
    anchor: str
    depth: int
    until: datetime
    ids: frozenset[str]

    def left_s(self, now: datetime | None = None) -> int:
        when = _now(now)
        return max(0, int((self.until - when).total_seconds()))

    def present_line(self, now: datetime | None = None) -> str:
        when = _now(now)
        return (
            f"RSV [{self.rid}] ; llm_id={self.llm_id} ; anchor={self.anchor} ; "
            f"depth={self.depth} ; until={_iso(self.until)} ; left_s={self.left_s(when)}"
        )


@dataclass
class NeighbourhoodReserveTable:
    """Per-session lease table (SessionEntry.reserves)."""

    leases: dict[str, ReserveLease] = field(default_factory=dict)
    _next_n: int = 1

    def purge_expired(self, now: datetime | None = None) -> list[str]:
        when = _now(now)
        gone: list[str] = []
        for rid, lease in list(self.leases.items()):
            if lease.until <= when:
                del self.leases[rid]
                gone.append(rid)
        return gone

    def _mint_rid(self) -> str:
        while True:
            rid = f"R{self._next_n}"
            self._next_n += 1
            if rid not in self.leases:
                return rid

    def ids_held_by_others(self, llm_id: str, ids: Iterable[str]) -> dict[str, ReserveLease]:
        hit: dict[str, ReserveLease] = {}
        wanted = set(ids)
        for lease in self.leases.values():
            if lease.llm_id == llm_id:
                continue
            for iid in lease.ids:
                if iid in wanted:
                    hit[iid] = lease
        return hit

    def lease_for_id(self, node_or_edge_id: str) -> ReserveLease | None:
        for lease in self.leases.values():
            if node_or_edge_id in lease.ids:
                return lease
        return None

    def get(self, rid: str) -> ReserveLease | None:
        return self.leases.get(rid)

    def find_by_anchor(self, anchor: str, llm_id: str | None = None) -> ReserveLease | None:
        for lease in self.leases.values():
            if lease.anchor != anchor:
                continue
            if llm_id is not None and lease.llm_id != llm_id:
                continue
            return lease
        return None


def collect_neighbourhood_ids(store, anchor: str, depth: int) -> frozenset[str]:
    """Same expand as pin_map; LAW ids exempt from the held set."""
    rec0 = store.resolve_one(anchor) if hasattr(store, "resolve_one") else store.get(anchor)
    if rec0 is None:
        raise MemNetError("no_anchor", f"reserve requires existing anchor {anchor!r}")
    depth = max(0, int(depth))
    fanout: list[str] = []
    subgraph = store.neighbors(rec0.hid, depth, fanout_warnings=fanout)
    held: set[str] = {rec0.hid}
    for rec in subgraph:
        if getattr(rec, "tag", None) == "LAW":
            continue
        held.add(rec.hid)
    return frozenset(held)


def reserve(
    table: NeighbourhoodReserveTable,
    store,
    *,
    anchor: str,
    llm_id: str,
    depth: int = 2,
    ttl_s: int = 120,
    now: datetime | None = None,
) -> ReserveLease:
    """Acquire or deepen a neighbourhood lease for llm_id."""
    when = _now(now)
    table.purge_expired(when)
    holder = (llm_id or "").strip()
    if not holder:
        raise MemNetError("no_llm_id", "llm_id required to reserve")
    if ttl_s < 1 or ttl_s > 86400:
        raise MemNetError("bad_ttl", "ttl_s must be 1..86400")

    new_ids = collect_neighbourhood_ids(store, anchor, depth)
    conflict = table.ids_held_by_others(holder, new_ids)
    if conflict:
        iid, lease = next(iter(conflict.items()))
        raise MemNetError(
            "reserve_conflict",
            f"id {iid} already held by llm_id={lease.llm_id}",
        )

    # Same llm_id: union existing leases that overlap / deepen, refresh TTL.
    until = when + timedelta(seconds=ttl_s)
    owned = [L for L in table.leases.values() if L.llm_id == holder]
    union_ids = set(new_ids)
    keep_rid: str | None = None
    for L in owned:
        if L.ids & union_ids or L.anchor == anchor:
            union_ids |= set(L.ids)
            if keep_rid is None:
                keep_rid = L.rid
            elif L.rid != keep_rid:
                del table.leases[L.rid]

    rid = keep_rid or table._mint_rid()
    # Drop other owned leases absorbed into this one
    for L in list(owned):
        if L.rid != rid and L.rid in table.leases:
            if table.leases[L.rid].ids <= union_ids:
                del table.leases[L.rid]

    lease = ReserveLease(
        rid=rid,
        llm_id=holder,
        anchor=anchor,
        depth=depth,
        until=until,
        ids=frozenset(union_ids),
    )
    table.leases[rid] = lease
    return lease


def extend(
    table: NeighbourhoodReserveTable,
    *,
    rid: str | None = None,
    anchor: str | None = None,
    llm_id: str,
    ttl_s: int = 120,
    now: datetime | None = None,
) -> ReserveLease:
    when = _now(now)
    table.purge_expired(when)
    holder = (llm_id or "").strip()
    if not holder:
        raise MemNetError("no_llm_id", "llm_id required to extend")
    if ttl_s < 1 or ttl_s > 86400:
        raise MemNetError("bad_ttl", "ttl_s must be 1..86400")

    lease = table.get(rid) if rid else None
    if lease is None and anchor:
        lease = table.find_by_anchor(anchor, llm_id=holder)
    if lease is None:
        raise MemNetError("reserve_expired", f"{rid or anchor} (lease cleared; treat as free)")
    if lease.llm_id != holder:
        raise MemNetError("reserve_mismatch", "extend llm_id does not match holder")

    refreshed = ReserveLease(
        rid=lease.rid,
        llm_id=lease.llm_id,
        anchor=lease.anchor,
        depth=lease.depth,
        until=when + timedelta(seconds=ttl_s),
        ids=lease.ids,
    )
    table.leases[refreshed.rid] = refreshed
    return refreshed


def release(
    table: NeighbourhoodReserveTable,
    *,
    rid: str | None = None,
    anchor: str | None = None,
    llm_id: str,
    now: datetime | None = None,
) -> str:
    when = _now(now)
    table.purge_expired(when)
    holder = (llm_id or "").strip()
    if not holder:
        raise MemNetError("no_llm_id", "llm_id required to release")

    lease = table.get(rid) if rid else None
    if lease is None and anchor:
        lease = table.find_by_anchor(anchor, llm_id=None)
    if lease is None:
        raise MemNetError("reserve_expired", f"{rid or anchor} (lease cleared; treat as free)")
    if lease.llm_id != holder:
        raise MemNetError("reserve_mismatch", "release llm_id does not match holder")
    del table.leases[lease.rid]
    return lease.rid


def check_mutate_ids(
    table: NeighbourhoodReserveTable,
    *,
    touched_ids: Iterable[str],
    llm_id: str | None,
    store=None,
    now: datetime | None = None,
) -> None:
    """Reject mutate that touches ids held by another llm_id (or missing llm_id)."""
    when = _now(now)
    table.purge_expired(when)
    if not table.leases:
        return

    for iid in touched_ids:
        if store is not None:
            rec = store.get(iid)
            if rec is not None and rec.tag == "LAW":
                continue
        lease = table.lease_for_id(iid)
        if lease is None:
            continue
        holder = (llm_id or "").strip()
        if not holder:
            raise MemNetError(
                "no_llm_id",
                f"llm_id required to mutate reserved id {iid}",
            )
        if holder != lease.llm_id:
            raise MemNetError(
                "reserved",
                f"id {iid} held by llm_id={lease.llm_id} until={_iso(lease.until)} "
                f"(caller llm_id={holder})",
            )


def intersecting_leases(
    table: NeighbourhoodReserveTable,
    view_ids: Iterable[str],
    *,
    now: datetime | None = None,
) -> list[ReserveLease]:
    when = _now(now)
    table.purge_expired(when)
    wanted = set(view_ids)
    out = [L for L in table.leases.values() if L.ids & wanted]
    out.sort(key=lambda L: L.rid)
    return out


def emit_reserves_section(leases: list[ReserveLease], *, now: datetime | None = None) -> str:
    if not leases:
        return ""
    when = _now(now)
    lines = ["## Reserves"]
    for lease in leases:
        lines.append(lease.present_line(when))
    return "\n".join(lines) + "\n"


def touched_ids_from_records(records: Iterable[Record]) -> set[str]:
    ids: set[str] = set()
    for rec in records:
        if rec.tag == "LAW":
            continue
        ids.add(rec.hid)
    return ids
