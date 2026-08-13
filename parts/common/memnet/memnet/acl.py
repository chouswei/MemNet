"""CapsPolicy ACL — who / pin_map-vs-mutate / WorkerWriteScope / optional bind.

Shipped engine gates (CapsPolicy.engineAclShipped). Session id is a secret
capability: MUST NOT appear in error ``example`` fields or casual dumps.

Privilege grain (analogy only — steal grain, do not become the product):
Neo4j / AgensGraph-class RBAC maps onto MemNet CapsPolicy ACL as:

  TRAVERSE / MATCH  ≈  pin_map   (read walk / shaped ego)
  WRITE (CREATE/SET/DELETE)  ≈  mutate
  label / id GRANT  ≈  WorkerWriteScope hard reject (cumulative OR)
  role / user  ≈  caller (who)
  optional bind  =  missionId + lease  (MemNet-only; not a Neo4j concept)

Agent wire remains gated GQL only. MUST NOT: Bolt as agent wire,
LLM↔Neo4j/AgensGraph teach, or MemNet-as-Cypher-proxy.
Canonical table: ``sysml-models/outputs/system-design-notes.md``
(CapsPolicy ACL — privilege grain).

In-process trusted path MAY skip bind match (MEMNET_SERVE_INTERNAL=1 or
MEMNET_ACL_SKIP_BIND=1). InvestorApi / TCP shared paths require who + bind
when bind is configured on the session.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal

from memnet.exceptions import MemNetError

# Public permission names (MemNet). Grain aliases are documentation only:
# pin_map ≈ TRAVERSE/MATCH; mutate ≈ WRITE.
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
    """Label / id / relation GRANT allowlist for mutate hard reject.

    Non-empty dimensions are cumulative OR grants (Neo4j-style additive GRANT
    grain): a node is in scope if it matches any configured id, label, or
    ego(anchor) grant. ``relations`` grants edge types the same way.
    ``anchors`` is MemNet ego extent (pin_map neighbourhood), not a Neo4j
    privilege name.
    """

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
    """Optional missionId + lease bind; when set, mutate must match.

    MemNet-only (not a Neo4j/AgensGraph privilege).
    """

    mission_id: str
    lease: str


@dataclass(frozen=True)
class CallerGrant:
    """Who grant: role/user ≈ caller; TRAVERSE≈pin_map; WRITE≈mutate."""

    caller: str
    can_pin_map: bool = True  # ≈ TRAVERSE / MATCH
    can_mutate: bool = True  # ≈ WRITE
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
    """Who + TRAVERSE/WRITE-grain gate (pin_map vs mutate).

    Returns resolved caller, or None when ACL is off.
    Raises MemNetError on deny.
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
            "caller lacks pin_map (TRAVERSE/MATCH read) permission",
        )
    if permission == "mutate" and not grant.can_mutate:
        raise MemNetError(
            "acl_forbidden",
            "caller lacks mutate (WRITE) permission",
        )
    return who


def check_bind(
    acl: SessionAcl | None,
    *,
    mission_id: str | None = None,
    lease: str | None = None,
    require: bool = True,
) -> None:
    """Optional MemNet bind match for mutate (missionId+lease).

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


def _node_granted(
    rid: str,
    tag: str,
    scope: WorkerWriteScope,
    ego: set[str] | None,
) -> bool:
    """True if any non-empty node GRANT dimension matches (cumulative OR)."""
    hits: list[bool] = []
    if scope.ids:
        hits.append(bool(rid) and rid in scope.ids)
    if scope.labels:
        hits.append(bool(tag) and tag.upper() in scope.labels)
    if scope.anchors:
        in_anchor = bool(rid) and (rid in scope.anchors or (ego is not None and rid in ego))
        hits.append(in_anchor)
    if not hits:
        # Only relation grants configured → node id/label unrestricted here
        return True
    # NEW mint: allow when a label GRANT covers the kind
    if (not rid or rid.upper() == "NEW" or rid.startswith("NEW")) and scope.labels:
        if tag.upper() in scope.labels:
            return True
    return any(hits)


def _edge_granted(
    *,
    rid: str,
    rel: str,
    src: str,
    dst: str,
    scope: WorkerWriteScope,
    ego: set[str] | None,
) -> bool:
    """True if relation GRANT or endpoint/id GRANT covers the edge."""
    hits: list[bool] = []
    if scope.relations:
        hits.append(bool(rel) and rel in scope.relations)
    if scope.ids:
        hits.append(bool(rid) and rid in scope.ids)
    # Endpoint coverage via id/anchor/label-less ego grants
    if scope.ids or scope.anchors:
        endpoints_ok = True
        for endpoint in (src, dst):
            if not endpoint:
                continue
            if scope.ids and endpoint in scope.ids:
                continue
            if scope.anchors and (
                endpoint in scope.anchors or (ego is not None and endpoint in ego)
            ):
                continue
            endpoints_ok = False
            break
        hits.append(endpoints_ok)
    if not hits:
        return True
    return any(hits)


def check_write_scope(
    acl: SessionAcl | None,
    *,
    caller: str | None,
    records: Iterable,
    store=None,
    agent: str | None = None,
    override_scope: WorkerWriteScope | None = None,
) -> None:
    """Hard-reject mutate records outside WorkerWriteScope (label/id GRANT).

    Scope source: override_scope, else caller's grant.write_scope.
    Empty / absent scope → no id-level gate (permission already checked).
    Non-empty grant dimensions are cumulative OR.
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
            src = fields.get("src") or fields.get("from") or ""
            dst = fields.get("dist") or fields.get("to") or ""
            if not _edge_granted(rid=rid, rel=rel, src=src, dst=dst, scope=scope, ego=ego):
                raise MemNetError(
                    "acl_scope",
                    "edge outside WorkerWriteScope (relation/id GRANT)",
                )
            continue

        if not _node_granted(rid, tag, scope, ego):
            raise MemNetError(
                "acl_scope",
                "id/label outside WorkerWriteScope (GRANT)",
            )


def redact_session_secret(message: str, session_id: str | None) -> str:
    """Strip a known session id from messages/examples (capability secret)."""
    if not session_id or not message:
        return message
    return message.replace(session_id, "<session>")
