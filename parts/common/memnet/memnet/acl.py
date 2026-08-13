"""CapsPolicy ACL — who / pin_map-vs-mutate / WorkerWriteScope / optional bind.

Shipped engine gates (CapsPolicy.engineAclShipped). Session id is a secret
capability: MUST NOT appear in error ``example`` fields or casual dumps.

In-process trusted path MAY skip bind match (MEMNET_SERVE_INTERNAL=1 or
MEMNET_ACL_SKIP_BIND=1). InvestorApi / TCP shared paths require who + bind
when bind is configured on the session.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Iterable, Literal

from memnet.exceptions import MemNetError

Permission = Literal["pin_map", "mutate"]

_SCOPE_KV = re.compile(
    r"^(anchors|ids|labels|relations)=(.+)$",
    re.IGNORECASE,
)


def _env_truthy(name: str) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def acl_globally_enabled() -> bool:
    """Host may force ACL on via MEMNET_ACL=1 (new sessions inherit enabled)."""
    return _env_truthy("MEMNET_ACL")


def in_process_trusted() -> bool:
    """True when running the in-process / serve-internal trusted path."""
    return _env_truthy("MEMNET_SERVE_INTERNAL") or _env_truthy("MEMNET_TEST_INLINE")


def skip_bind_allowed() -> bool:
    """In-process MAY skip bind; explicit MEMNET_ACL_SKIP_BIND also opts in."""
    if _env_truthy("MEMNET_ACL_SKIP_BIND"):
        return True
    return in_process_trusted()


@dataclass(frozen=True)
class WorkerWriteScope:
    """Ego / label / id / relation allowlist for mutate hard reject."""

    anchors: frozenset[str] = frozenset()
    ids: frozenset[str] = frozenset()
    labels: frozenset[str] = frozenset()
    relations: frozenset[str] = frozenset()

    def is_empty(self) -> bool:
        return not (self.anchors or self.ids or self.labels or self.relations)

    def to_wire(self) -> str:
        parts: list[str] = []
        if self.anchors:
            parts.append("anchors=" + ",".join(sorted(self.anchors)))
        if self.ids:
            parts.append("ids=" + ",".join(sorted(self.ids)))
        if self.labels:
            parts.append("labels=" + ",".join(sorted(self.labels)))
        if self.relations:
            parts.append("relations=" + ",".join(sorted(self.relations)))
        return ";".join(parts)


@dataclass(frozen=True)
class SessionBind:
    """Optional missionId + lease bind; when set, mutate must match."""

    mission_id: str
    lease: str


@dataclass(frozen=True)
class CallerGrant:
    caller: str
    can_pin_map: bool = True
    can_mutate: bool = True
    write_scope: WorkerWriteScope | None = None


@dataclass
class SessionAcl:
    """Per-session ACL state consulted by MutateGate / PinMapComposer."""

    enabled: bool = False
    callers: dict[str, CallerGrant] = field(default_factory=dict)
    bind: SessionBind | None = None

    def enable(self) -> None:
        self.enabled = True

    def grant(
        self,
        caller: str,
        *,
        can_pin_map: bool = True,
        can_mutate: bool = True,
        write_scope: WorkerWriteScope | None = None,
    ) -> None:
        key = caller.strip()
        if not key:
            raise MemNetError("acl_bad_caller", "caller id required for grant")
        self.callers[key] = CallerGrant(
            caller=key,
            can_pin_map=can_pin_map,
            can_mutate=can_mutate,
            write_scope=write_scope,
        )
        self.enabled = True

    def set_bind(self, mission_id: str, lease: str) -> None:
        mid = mission_id.strip()
        lid = lease.strip()
        if not mid or not lid:
            raise MemNetError(
                "acl_bad_bind",
                "mission_id and lease required together",
            )
        self.bind = SessionBind(mission_id=mid, lease=lid)
        self.enabled = True

    def clear_bind(self) -> None:
        self.bind = None


def parse_write_scope(raw: str | None) -> WorkerWriteScope | None:
    """Parse ``anchors=a,b;ids=x;labels=TSK;relations=about,owns``."""
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    anchors: set[str] = set()
    ids: set[str] = set()
    labels: set[str] = set()
    relations: set[str] = set()
    for chunk in text.split(";"):
        piece = chunk.strip()
        if not piece:
            continue
        m = _SCOPE_KV.match(piece)
        if not m:
            raise MemNetError(
                "acl_bad_scope",
                "write_scope expects anchors=|ids=|labels=|relations= segments",
            )
        key = m.group(1).lower()
        values = {v.strip() for v in m.group(2).split(",") if v.strip()}
        if key == "anchors":
            anchors |= values
        elif key == "ids":
            ids |= values
        elif key == "labels":
            labels |= {v.upper() for v in values}
        elif key == "relations":
            relations |= {v.lower() for v in values}
    scope = WorkerWriteScope(
        anchors=frozenset(anchors),
        ids=frozenset(ids),
        labels=frozenset(labels),
        relations=frozenset(relations),
    )
    return None if scope.is_empty() else scope


def resolve_caller(
    caller: str | None,
    *,
    agent: str | None = None,
) -> str | None:
    """Resolve who: explicit caller, else MEMNET_CALLER, else agent fallback."""
    if caller and caller.strip():
        return caller.strip()
    env = os.environ.get("MEMNET_CALLER", "").strip()
    if env:
        return env
    if agent and agent.strip():
        return agent.strip()
    return None


def check_permission(
    acl: SessionAcl | None,
    *,
    caller: str | None,
    permission: Permission,
    agent: str | None = None,
) -> str | None:
    """Who + pin_map-vs-mutate gate. Returns resolved caller or None if ACL off.

    Raises MemNetError on deny. No-op when ACL disabled.
    """
    if acl is None or not acl.enabled:
        return resolve_caller(caller, agent=agent)

    who = resolve_caller(caller, agent=agent)
    if not who:
        raise MemNetError(
            "acl_who",
            "caller id required when session ACL is enabled",
            # session id is a capability — never put it in example
            example="pass --caller or MEMNET_CALLER",
        )
    grant = acl.callers.get(who)
    if grant is None:
        raise MemNetError(
            "acl_denied",
            "unknown caller for this session",
            example="grant caller via session acl-grant",
        )
    if permission == "pin_map" and not grant.can_pin_map:
        raise MemNetError(
            "acl_forbidden",
            "caller lacks pin_map (read) permission",
        )
    if permission == "mutate" and not grant.can_mutate:
        raise MemNetError(
            "acl_forbidden",
            "caller lacks mutate (write) permission",
        )
    return who


def check_bind(
    acl: SessionAcl | None,
    *,
    mission_id: str | None = None,
    lease: str | None = None,
    require: bool = True,
) -> None:
    """Optional bind match for mutate.

    If session has no bind configured, no-op.
    When ``require`` is False and the in-process trusted path is active,
    bind match is skipped (documented). InvestorApi / TCP shared paths
    pass ``require=True`` so who+bind are enforced when bind is set.
    """
    if acl is None or not acl.enabled or acl.bind is None:
        return

    mid = (mission_id or os.environ.get("MEMNET_MISSION_ID") or "").strip()
    lid = (lease or os.environ.get("MEMNET_LEASE") or "").strip()
    if mid == acl.bind.mission_id and lid == acl.bind.lease:
        return

    if not require and skip_bind_allowed():
        return

    raise MemNetError(
        "acl_bind",
        "mission_id and lease must match session bind",
        example="pass --mission-id and --lease matching session acl-bind",
    )


def _ego_ids(store, anchors: Iterable[str], *, depth: int = 2) -> set[str]:
    """Ids reachable from anchors (including anchors themselves)."""
    allowed: set[str] = set()
    for anchor in anchors:
        allowed.add(anchor)
        try:
            rows = store.context_pack(
                anchor_id=anchor,
                depth=depth,
                max_rows=500,
                active_only=False,
            )
        except Exception:
            continue
        for rec in rows:
            if rec.id:
                allowed.add(rec.id)
            if rec.tag == "EDG" or getattr(rec, "kind", None) == "edge":
                src = rec.fields.get("src") or rec.fields.get("from")
                dst = rec.fields.get("dist") or rec.fields.get("to")
                if src:
                    allowed.add(src)
                if dst:
                    allowed.add(dst)
    return allowed


def check_write_scope(
    acl: SessionAcl | None,
    *,
    caller: str | None,
    records: Iterable,
    store=None,
    agent: str | None = None,
    override_scope: WorkerWriteScope | None = None,
) -> None:
    """Hard-reject mutate records outside WorkerWriteScope.

    Scope source: override_scope, else caller's grant.write_scope.
    Empty / absent scope → no id-level gate (permission already checked).
    """
    if acl is None or not acl.enabled:
        return
    who = resolve_caller(caller, agent=agent)
    if not who:
        return
    grant = acl.callers.get(who)
    if grant is None:
        return
    scope = override_scope if override_scope is not None else grant.write_scope
    if scope is None or scope.is_empty():
        return

    ego: set[str] | None = None
    if scope.anchors and store is not None:
        ego = _ego_ids(store, scope.anchors)

    for rec in records:
        tag = getattr(rec, "tag", "") or ""
        rid = getattr(rec, "id", None) or ""
        if not rid and hasattr(rec, "fields"):
            rid = rec.fields.get("id", "")
        fields = getattr(rec, "fields", {}) or {}
        is_edge = tag == "EDG" or getattr(rec, "kind", None) == "edge"

        if is_edge:
            rel = (fields.get("relation") or fields.get("type") or "").lower()
            if scope.relations and rel and rel not in scope.relations:
                raise MemNetError(
                    "acl_scope",
                    f"relation {rel!r} outside WorkerWriteScope",
                )
            src = fields.get("src") or fields.get("from") or ""
            dst = fields.get("dist") or fields.get("to") or ""
            for endpoint in (src, dst):
                if endpoint and not _id_in_scope(endpoint, scope, ego):
                    # endpoints may be new; allow if labels gate only and no ids/anchors
                    if scope.ids or scope.anchors:
                        raise MemNetError(
                            "acl_scope",
                            "edge endpoint outside WorkerWriteScope",
                        )
            continue

        # Node
        if scope.labels and tag.upper() not in scope.labels:
            # label gate only applies when labels list is non-empty
            if not _id_in_scope(rid, scope, ego):
                raise MemNetError(
                    "acl_scope",
                    f"label {tag!r} / id outside WorkerWriteScope",
                )
            continue
        if not _id_in_scope(rid, scope, ego):
            # NEW mint: allow when label allowed or only relation scope set
            if rid.upper() == "NEW" or rid.startswith("NEW"):
                if scope.labels and tag.upper() in scope.labels:
                    continue
                if not scope.ids and not scope.anchors:
                    continue
            raise MemNetError(
                "acl_scope",
                "id outside WorkerWriteScope",
            )


def _id_in_scope(
    rid: str,
    scope: WorkerWriteScope,
    ego: set[str] | None,
) -> bool:
    if not rid:
        return False
    if scope.ids and rid in scope.ids:
        return True
    if ego is not None and rid in ego:
        return True
    if scope.anchors and rid in scope.anchors:
        return True
    # If only labels/relations configured (no ids/anchors), id gate is open
    if not scope.ids and not scope.anchors:
        return True
    return False


def redact_session_secret(message: str, session_id: str | None) -> str:
    """Strip a known session id from messages/examples (capability secret)."""
    if not session_id or not message:
        return message
    return message.replace(session_id, "<session>")
