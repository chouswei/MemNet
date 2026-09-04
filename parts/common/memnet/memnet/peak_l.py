"""Peak_L — last-resort residual local-max cue inside one session S.

Not a third operator. Recall stays RelativeSeed MATCH_L then ShapeWalk.
Peak_L fires only on a non-empty codebook miss (tokens present, MATCH_L
empty). Empty q remains 0.11 session outline. MUST NOT be default goldfish.
MUST NOT density-peak cluster assignment, Leiden from peaks, or global
top-k degree.

ρ*(v) = incident edges except hierarchical ``contains`` (hide recycled).
"""

from __future__ import annotations

from memnet.models import Record
from memnet.observable_rank import node_rank_key

CONTAINS_REL = "contains"
_SKIP_TAGS = frozenset({"LAW", "EDG"})


def _relation(edge: Record) -> str:
    return str(edge.fields.get("relation") or "")


def _other_end(edge: Record, hid: str) -> str:
    src = edge.fields.get("src", "")
    dist = edge.fields.get("dist", "")
    if src == hid:
        return dist
    return src


def _incident_edges(store, hid: str) -> list[Record]:
    return list(store._edges_from(hid)) + list(store._edges_to(hid))


def residual_degree(store, hid: str, *, active_only: bool = True) -> int:
    """ρ*(v): incident non-``contains`` edges; hide recycled."""
    seen: set[str] = set()
    n = 0
    rec = store.get(hid) if hasattr(store, "get") else None
    if rec is None or rec.tag in _SKIP_TAGS:
        return 0
    if active_only and rec.is_recyclable():
        return 0
    for edge in _incident_edges(store, hid):
        if edge.hid in seen:
            continue
        seen.add(edge.hid)
        if active_only and edge.is_recyclable():
            continue
        if _relation(edge) == CONTAINS_REL:
            continue
        other = _other_end(edge, hid)
        orec = store.get(other) if other else None
        if orec is None or orec.tag == "EDG":
            continue
        if active_only and orec.is_recyclable():
            continue
        n += 1
    return n


def residual_neighbours(store, hid: str, *, active_only: bool = True) -> list[str]:
    """Nodes joined to *hid* by a residual (non-``contains``) edge."""
    out: list[str] = []
    seen: set[str] = set()
    for edge in _incident_edges(store, hid):
        if active_only and edge.is_recyclable():
            continue
        if _relation(edge) == CONTAINS_REL:
            continue
        other = _other_end(edge, hid)
        if not other or other in seen:
            continue
        orec = store.get(other)
        if orec is None or orec.tag in _SKIP_TAGS:
            continue
        if active_only and orec.is_recyclable():
            continue
        seen.add(other)
        out.append(other)
    return out


def peak_l(
    store,
    *,
    limit: int,
    active_only: bool = True,
) -> tuple[list[Record], int]:
    """Typed residual local max of ρ* inside one S. Hard LIMIT L.

    A node is a peak iff ρ*(v) > 0 and ρ*(v) ≥ ρ*(u) for every residual
    neighbour u. Two peaks stay two (CueConflict). Empty peaks → skip.
    Does not assign the rest of S to a peak.
    """
    if limit < 1:
        from memnet.exceptions import MemNetError

        raise MemNetError("bad_limit", "Peak_L --limit must be >= 1")
    nodes = [r for r in store.list_records(active_only=active_only) if r.tag not in _SKIP_TAGS]
    rho: dict[str, int] = {
        r.hid: residual_degree(store, r.hid, active_only=active_only) for r in nodes
    }
    peaks: list[Record] = []
    for rec in nodes:
        val = rho[rec.hid]
        if val <= 0:
            continue
        nbrs = residual_neighbours(store, rec.hid, active_only=active_only)
        if any(rho.get(n, 0) > val for n in nbrs):
            continue
        peaks.append(rec)
    peaks.sort(key=lambda r: (-rho[r.hid], node_rank_key(r)))
    return peaks[:limit], len(peaks)


# SysML-facing alias (last-resort cue under RelativeSeed, not a third operator)
Peak_L = peak_l
