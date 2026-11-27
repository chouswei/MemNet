"""PROXY nodes: a one-hop pointer from this session to a node in a session.

A PROXY is a fixed node tag (``memnet.fixed_tags``) with the fields
``id, target_session, target, target_backend``. ``target_session`` and
``target`` are opaque ids: a write checks their shape only, never that the
target exists. ``target_backend`` is a label; nothing routes by it.

Existing reads (pin_map, find, walks) show a PROXY as a plain node and never
follow it. ``memnet query follow`` (MCP ``follow_proxy``) resolves one hop:

- ``ok``: the target session is in this process and the caller may read it;
  the target node is returned. A target that is itself a PROXY is returned
  as is; there is no second hop.
- ``dangling`` (reason ``target_missing``): the target session is here but
  the node is not.
- ``not_reachable``: the target session is not in this process. A gateway
  may make the second hop (``product_gateway``); a single serve cannot tell
  a remote session from a deleted one, so this is never a confirmed delete.

No function here holds two session locks at once.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from memnet.config import ID_PATTERN, Caps
from memnet.exceptions import MemNetError
from memnet.models import Record

PROXY_TAG = "PROXY"  # fields: memnet.fixed_tags.PROXY_FIELDS
_REQUIRED = ("target_session", "target")
_ID_RE = re.compile(ID_PATTERN)

OK = "ok"
DANGLING = "dangling"
NOT_REACHABLE = "not_reachable"
TARGET_MISSING = "target_missing"
# The miss codes of a target session lookup; all of them read as not reachable.
_SESSION_MISS = frozenset({"session_not_found", "session_expired"})
EXAMPLE = "CREATE (:PROXY {target_session: 'sess_b', target: 'TSK01'})"


def check_proxy_fields(fields: Mapping[str, str]) -> None:
    """Refuse ``proxy_shape`` unless both pointer fields are set and well formed.

    Values are not echoed: a target session id is a capability.
    """
    for key in _REQUIRED:
        val = fields.get(key) or ""
        if not val.strip():
            raise MemNetError("proxy_shape", f"PROXY needs a non-empty {key}", example=EXAMPLE)
        if not _ID_RE.fullmatch(val):
            raise MemNetError("proxy_shape", f"PROXY {key} must match {ID_PATTERN}")
    backend = fields.get("target_backend") or ""
    if backend and not _ID_RE.fullmatch(backend):
        raise MemNetError("proxy_shape", f"PROXY target_backend must match {ID_PATTERN}")


def check_records(records: Iterable[Record]) -> None:
    """Shape check for every PROXY in a batch about to be written."""
    for rec in records:
        if rec.tag == PROXY_TAG:
            check_proxy_fields(rec.fields)


def check_stored(store, hids: Iterable[str]) -> None:
    """Shape check for the stored rows ``hids`` (after a SET / MERGE / rename merged them)."""
    by_hid = store._by_hid
    for hid in hids:
        rec = by_hid.get(hid)
        if rec is not None and rec.tag == PROXY_TAG:
            check_proxy_fields(rec.fields)


def pointer(rec: Record) -> tuple[str, str, str]:
    f = rec.fields
    return f.get("target_session", ""), f.get("target", ""), f.get("target_backend", "")


def find_node(store, session_id: str, token: str) -> Record | None:
    """A node by nickname, typed-walk handle or hid (same resolve as other reads).

    None when nothing matches; ``cue_conflict`` when a nickname names several nodes.
    """
    from memnet import typed_walk as tw

    if not token:
        return None
    hits = [r for r in store.match_nickname(token) if r.tag != "EDG"]
    if len(hits) > 1:
        raise MemNetError("cue_conflict", f"follow id matches {len(hits)} nodes")
    if hits:
        return hits[0]
    if tw.is_handle(token):
        try:
            return tw.resolve_handle(store, session_id, token)
        except MemNetError as exc:
            if exc.code == "stale_handle":
                return None
            raise
    rec = store._by_hid.get(token)
    if rec is not None and rec.tag != "EDG":
        return rec
    return None


@dataclass
class FollowResult:
    status: str
    node: Record | None = None
    store: object | None = None
    pointer: tuple[str, str, str] = ("", "", "")

    def lines(self) -> list[str]:
        """The reply. ``@FOLLOW:`` repeats the pointer so a gateway can hop."""
        from memnet.pin_map_composer import record_to_gql_line

        if self.status == OK and self.node is not None:
            return ["@STAT: follow|ok", record_to_gql_line(self.node, store=self.store)]
        if self.status == DANGLING:
            return [f"@STAT: follow|dangling|reason={TARGET_MISSING}"]
        ts, target, backend = self.pointer
        return [
            "@STAT: follow|not_reachable|target not reachable from here",
            f"@FOLLOW: {ts}|{target}|{backend}",
        ]


def _acl(holder, caller: str | None, agent: str | None) -> None:
    from memnet.acl import check_permission

    check_permission(
        holder.acl,
        caller=caller or os.environ.get("MEMNET_CALLER"),
        permission="pin_map",
        agent=agent or os.environ.get("MEMNET_AGENT"),
    )


def read_node(ss, token: str, *, caller: str | None = None, agent: str | None = None):
    """The node ``token`` in session ``ss`` (ACL pin_map on ``ss``): ok or dangling.

    Used for the target of a hop and for ``query follow --resolved-id``. Never
    follows a PROXY it finds.
    """
    _acl(ss, caller, agent)
    with ss.lock(exclusive=False):
        node = find_node(ss.store, ss.session_id, token)
        if node is None:
            return FollowResult(DANGLING)
        return FollowResult(OK, node=node, store=ss.store)


def follow(
    ss,
    proxy_token: str,
    *,
    caller: str | None = None,
    agent: str | None = None,
    caps: Caps | None = None,
) -> FollowResult:
    """Resolve the PROXY ``proxy_token`` in ``ss`` one hop.

    ACL pin_map on ``ss`` first, then on the target session before anything
    about the target is returned. The source lock is released before the
    target session is opened, so two follows never wait on each other.
    """
    from memnet.registry import get_entry
    from memnet.session import get_session

    _acl(ss, caller, agent)
    with ss.lock(exclusive=False):
        rec = find_node(ss.store, ss.session_id, proxy_token)
        if rec is None:
            raise MemNetError("not_found", "follow id not found")
        if rec.tag != PROXY_TAG:
            raise MemNetError("not_proxy", "follow id is not a PROXY node", example=EXAMPLE)
        ptr = pointer(rec)
    target_session, target, _backend = ptr
    if target_session == ss.session_id:
        target_ss = ss
    else:
        entry = get_entry(target_session)
        if entry is None:
            return FollowResult(NOT_REACHABLE, pointer=ptr)
        # ACL before any TTL renew: a denied caller must not keep the target alive.
        _acl(entry, caller, agent)
        try:
            target_ss = get_session(target_session, caps or ss.caps, touch=True)
        except MemNetError as exc:
            if exc.code in _SESSION_MISS:
                return FollowResult(NOT_REACHABLE, pointer=ptr)
            raise
    try:
        return read_node(target_ss, target, caller=caller, agent=agent)
    except MemNetError as exc:
        if exc.code in _SESSION_MISS:
            return FollowResult(NOT_REACHABLE, pointer=ptr)
        raise


def dangling_proxy_rows(
    ss, *, caller: str | None = None, agent: str | None = None
) -> list[tuple[Record, str]]:
    """PROXY nodes of ``ss`` whose target is missing or not reachable from here.

    ``(record, reason)`` with reason ``target_missing`` (the target session is
    in this process, the node is not) or ``not_reachable`` (the target session
    is not in this process, or the caller lacks pin_map on it). An
    ACL-protected target is ``not_reachable``: the scan never confirms that
    the node exists or is absent. Other sessions are read through the
    registry entry under their own lock, one at a time, with no touch and no
    TTL slide. Call it without holding the ``ss`` lock. Lists only; deletes
    nothing.
    """
    from memnet.registry import get_entry

    with ss.lock(exclusive=False):
        proxies = [
            Record(tag=r.tag, fields=dict(r.fields), hid=r.hid)
            for r in ss.store.list_records(PROXY_TAG)
        ]
        out: list[tuple[Record, str]] = []
        foreign: list[Record] = []
        for rec in proxies:
            ts, target, _ = pointer(rec)
            if ts == ss.session_id:
                if find_node(ss.store, ss.session_id, target) is None:
                    out.append((rec, TARGET_MISSING))
            else:
                foreign.append(rec)
    for rec in foreign:
        ts, target, _ = pointer(rec)
        entry = get_entry(ts)
        if entry is None:
            out.append((rec, NOT_REACHABLE))
            continue
        try:
            _acl(entry, caller, agent)
        except MemNetError:
            out.append((rec, NOT_REACHABLE))
            continue
        with entry.lock:
            try:
                found = find_node(entry.store, ts, target)
            except MemNetError:
                found = rec  # cue_conflict: the target is there, just not unique
            if found is None:
                out.append((rec, TARGET_MISSING))
    out.sort(key=lambda pair: (pair[0].id, pair[0].hid))
    return out
