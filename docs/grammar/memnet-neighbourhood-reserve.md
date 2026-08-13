# Neighbourhood reservation (design)

**Status:** implemented (MN-REQ-12.13 / `memnet.neighbourhood_reserve`).  
**Primary concurrency fix** for multi-agent same-session confusion **inside an already-authorised session**.  
**Related:** re-id §4.2.0 in `memnet-grammar-design.md`; optimistic `rev` is secondary only.  
**Security + session ACL:** [`memnet-security-multi-agent.md`](memnet-security-multi-agent.md) — first-class session access (`private` / `shared` / `open`, roles, `session_token`); this reserve design is the coop layer **after** that gate.  
**Dialect:** agent-facing I/O is **GQL only** ([`gql-wire-profile.md`](gql-wire-profile.md)). Do **not** invent `@RSV:` pipe forms or revive Layer.

## Problem

Per-session mutex prevents torn writes but not **logical** races: two agents share one `session_id`, both `pin_map`, both `update` — last commit wins. Goldfish docs assume one writer loop; `--agent` today is attribution only.

## Decision

**Reserve an ego neighbourhood** (same expand as `pin_map`) for holder **`llm_id`** until **release** or **TTL expiry**.

| Rule | Locked default |
|------|----------------|
| Holder | Required **`llm_id`** (agent/LLM identity; ASCII token) |
| Lease | Required **TTL** (`ttl_s`); wall-clock `until`; auto-release on expiry |
| Scope | Anchor node + ego neighbourhood at `depth` (same as `pin_map`) |
| Mutate | Only if caller `llm_id` == holder **and** lease not expired |
| Read | Others **may** `pin_map` / read (read-only on reserved ids) |
| Release | Caller `llm_id` must match holder; mismatch rejected. **No force in v1** |
| Overlap | Reject if any id held by another `llm_id` (no wait → no deadlock) |
| Heartbeat | Optional `extend(..., llm_id, ttl_s)`; same holder only |

Leases are **session control plane**, not durable product graph rows. Pin map may **display** intersecting leases as bare present lines (below). MCP `reserve` / `extend` / `release` manage lifecycle — do **not** teach `+ RSV` / `- RSV` as graph mutate in v1.

## Rank vs optimistic `rev`

| Rank | Option | Role |
|------|--------|------|
| 1 | Neighbourhood reserve (`llm_id` + TTL) | **Primary** |
| 2 | Session/subgraph `rev` CAS | **Secondary** (optional later) |
| 3 | Session-per-agent + merge | Heavy |
| 4 | Append-only ops log | Large dialect change |

## Canonical pin-map display (shared dialect)

When a lease intersects the current ego view, pin map shows it as **bare present** (no leading `+`/`~`/`-`), same Write=display rule as other pins:

```text
## Reserves
RSV [R7] ; llm_id=coder_a ; anchor=ATO_R1 ; depth=2 ; until=2026-07-24T08:15:00Z ; left_s=87

## Nodes
CMP [ATO_R1] ; refdes=R1 ; path=boards/pdu/pdu.ato ; recycle=persistent
...
## Edges
...
```

Field names (locked for display): `llm_id`, `anchor`, `depth`, `until`, optional `left_s`. Copy ids from this line; do not invent reserve ids.

**Wrong (forbidden — legacy pipe pollution):**

```text
@RSV: R7|holder=coder_a|anchor=ATO_R1|depth=2|until=...|ids=12
```

## MCP / CLI surface

```text
reserve(session, anchor, depth=2, llm_id, ttl_s=120)
  -> rid, until, held_count   # ack may also echo RSV present line

extend(session, rid|anchor, llm_id, ttl_s=120)
  -> until

release(session, rid|anchor, llm_id)
  -> ok

pin_map(session, anchor, depth, ...)   # primary read; includes ## Reserves when relevant
```

CLI mirror: `memnet reserve --anchor ATO_R1 --depth 2 --llm-id coder_a --ttl 120`.

Mutate (`add` / `update`) must pass the same `llm_id` as the holder when touching reserved ids.

### Errors (agent-facing text — not new `@TAG` pipe)

```text
reserved: id ATO_R1 held by llm_id=coder_a until=2026-07-24T08:15:00Z (caller llm_id=coder_b)
reserve_conflict: id ATO_R1 already held by llm_id=coder_a
reserve_mismatch: release llm_id does not match holder
reserve_expired: R7 (lease cleared; treat as free)
no_llm_id: llm_id required to reserve or mutate a reserved id
```

Existing CLI stderr may still use historical `@ERR:` **transport** for any MemNet error code — that is store/CLI envelope, not a licence to invent `@RSV:` or teach pipe as the agent dialect.

## Semantics (detail)

### Who can reserve

Non-empty `llm_id`. Engine matches strings only in v1. Empty → `no_llm_id`.

### Scope

Held set = nodes and incident edge ids reachable from `anchor` within `depth` (same expand as `pin_map`). Prefer **exempt LAW** from reserve checks in v1.

### Mutate gate

For every touched id (re-id: old and new; merge: source and target):

1. No active lease on id → allow (single-writer goldfish path).
2. Lease active, `caller.llm_id == holder`, not expired → allow; optional soft-extend.
3. Else → `reserved` (or clear expired lease then re-check).

### Nested / expand

Same `llm_id` may deepen or add an anchor: **union** if no foreign overlap; refresh TTL. Other `llm_id` on overlap → `reserve_conflict` (immediate fail).

### Timeout / crash

Expiry checked on reserve / mutate / pin_map. Expired → auto-release. `extend` for long edits.

### Release

Matching `llm_id` only. No force/admin in v1.

## Interaction with re-id / locators

| Case | Rule under reserve |
|------|--------------------|
| Free `~ [A] ; id=B` | Caller holds A; lease follows B; expand if retargeted edges fall outside |
| Occupied | Still `id_occupied` without `merge=true` |
| `~ [A] ; id=B ; merge=true` | A and B free or held by **same** `llm_id` |
| Stable locators | Reserve by ground id; locator fields unchanged |

Re-id shape (shared dialect, already in engine):

```text
~ [PLR_BAD] ; id=PLR01
~ [PLR_BAD] ; id=PLR01 ; merge=true
```

## Fit with 0.3.2 engine (when implementing)

| Component | Change |
|-----------|--------|
| `SessionStore` | Lease table: rid → {llm_id, until, anchor, depth, ids} |
| `MutateGate` | Check caller `llm_id` vs leases |
| `PinMapComposer` | Emit `## Reserves` + `RSV […] ; …` present lines |
| MCP | `reserve` / `extend` / `release`; `llm_id` on mutate |
| Snapshot | v1: do not restore leases (or short TTL) |

## Out of scope (v1)

- Force release  
- Cross-session reserves  
- `+ RSV` / `- RSV` graph mutate  
- Shipping optimistic `rev` in the same drop  
- Any new agent-facing `@TAG|pipe` feature  

Session ACL, roles, and `session_token` are specified in [`memnet-security-multi-agent.md`](memnet-security-multi-agent.md) (not deferred as vague “auth later” here).

## Implementation note

Shipped as `memnet.neighbourhood_reserve` + CLI/MCP `reserve` / `extend` / `release`.
Snapshot v1 does not restore leases.