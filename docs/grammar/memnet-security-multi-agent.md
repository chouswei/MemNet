# Security and multi-agent cooperation (design)

**Status:** design for next minor / follow-ons; **partial MVP in 0.3.6** (localhost bind default, remote opt-in, frame cap — not session token/ACL).  
**Builds on:** [`memnet-neighbourhood-reserve.md`](memnet-neighbourhood-reserve.md) (coop leases), re-id §4.2.0 in [`memnet-grammar-design.md`](memnet-grammar-design.md).  
**Dialect:** agent-facing I/O is **shared dialect only** (Write = display). No new `@TAG|pipe` surfaces. ASCII field values.  
**Product context:** ~0.3.6; primary read `pin_map`; transport **in-process first**, TCP `memnet serve` (default `127.0.0.1:18765`) as fallback.

## How the pieces fit

Authorisation is **two layers**. Session access control decides *who may use the session at all*. Neighbourhood reserve decides *which authorised writer holds which ego slice*.

| Layer | Job | Today (0.3.5) | Target |
|-------|-----|---------------|--------|
| **Transport trust** | Who may reach the engine | In-process = process trust; TCP = LAN/host trust | Bind defaults + optional serve token |
| **Session access (ACL)** | Who may open / join / read / mutate / reserve on a `session_id` | **Anyone who knows (or guesses) the id** | Modes + roles + **session token** (first-class) |
| **Identity** | Who is speaking | `--agent` optional — attribution only | Declared **`llm_id`**, bound by ACL + token |
| **Cooperation (reserve)** | Parallel writers without lost updates | Unmitigated same-session races | **Reserve → edit → release** inside an authorised session |
| **Audit** | Who did what | Weak / optional agent tag | Ops tagged with `llm_id` |

**One sentence:** limit the session first (ACL + token); then use neighbourhood reserve so authorised writers do not step on each other; TCP must not treat an obscure `session_id` as a secret.

```text
                    TCP / in-process
                           |
              serve reachability (bind / serve token)
                           |
              session_id + session_token + llm_id
                           |
              +------------+------------+
              |   Session ACL (gate)    |
              |  private | shared | open |
              |  roles: owner/writer/reader |
              +------------+------------+
                           |
         authorised?  --no-->  session_denied / session_auth
                           |
                          yes
                           |
              +------------v------------+
              | Neighbourhood reserve   |
              |  llm_id + TTL (coop)    |
              +-------------------------+
```

---

## 1. Session access control (first-class)

**MUST:** MemNet designs a way to **limit access of a session**. Knowing a `session_id` alone is **not** sufficient authorisation on a shared TCP serve.

### 1.1 Problem

Today any client that can reach serve and supplies a live `session_id` can `pin_map`, `add`, `update`, load/save. Multi-agent confusion is one failure mode; **unauthorised join** is another. Reserve without session ACL only coordinates *members who already got in*.

### 1.2 Modes (locked ranking)

| Mode | Who may join | MVP? | Use |
|------|--------------|------|-----|
| **`private`** | Owner `llm_id` only | **Yes** | Single trusted agent; no guests |
| **`shared`** | Explicit allow-list of `llm_id`s with roles | **Yes** | Multi-agent cooperation (primary multi-writer mode) |
| **`open`** | Any caller with valid `session_token` (id+token still required) | Compat only | Local single-process goldfish; **not** recommended on LAN TCP |

**Default when creating a multi-agent session:** `access=shared` with creator as `owner`.  
**Default for unbroken 0.3.5 single-agent UX (in-process):** `access=open` may remain until callers opt into ACL — document the risk if the same session is exposed over TCP.

### 1.3 Roles

| Role | open / join | pin_map / read_* | mutate (`add`/`update`) | reserve / extend / release | re-id / merge | grant / revoke ACL | session save/load / destroy |
|------|-------------|------------------|-------------------------|----------------------------|---------------|--------------------|-----------------------------|
| **owner** | yes | yes | yes | yes (own leases) | yes | yes | yes |
| **writer** | yes | yes | yes | yes (own leases) | yes | no (MVP) | no (MVP) |
| **reader** | yes | yes | **no** | **no** | **no** | no | no |

Reserve remains the coop mechanism **inside** an already-authorised session: a `writer` who is ACL-allowed still needs a lease to edit a neighbourhood another writer holds. A `reader` never obtains a lease.

### 1.4 Session token (capability per session)

| Item | Rule |
|------|------|
| **Mint** | Engine mints opaque ASCII **`session_token`** on successful `session_open` (and optionally on rotate) |
| **Present** | Every subsequent op that targets the session MUST supply `session` + `session_token` (+ `llm_id` when ACL ≠ ignore) |
| **Not the session id** | `session_id` remains the handle for routing; **token** is the capability. Do not treat id as a password |
| **Distribution** | Out of band (operator / orchestrator gives token to allowed agents). MemNet does not invent a public directory of tokens |
| **Rotate** | Owner may `session_token_rotate` → old token invalid (later if not MVP; MVP may mint once) |
| **Snapshot** | Saving a snapshot **does not** embed the live token in agent-facing dialect; restore mints a new token or requires owner re-auth (pick at implement time; prefer **mint new**) |

**TCP shared serve:** many agents, one host → ACL + token are mandatory for `private` / `shared`. Security through obscurity of `session_id` is **rejected** as a design.

**In-process:** still pass token in the tool envelope (MCP can hold it in process memory after `session_open`). Spoofing another `llm_id` inside the same process remains a trust-the-harness problem; ACL still prevents accidental cross-session mix-ups when multiple sessions exist.

### 1.5 Membership operations

Control plane (not graph mutate):

| Op | Who | Effect |
|----|-----|--------|
| `session_open(..., access, owner_llm_id, ...)` | creator | Create session; mint token; seed ACL (owner row) |
| `session_acl(session, session_token, llm_id)` | member | Return ACL present lines (caller’s view) |
| `session_grant(session, session_token, owner_llm_id, member_llm_id, role)` | owner | Add/update allow-list row (`shared` only) |
| `session_revoke(session, session_token, owner_llm_id, member_llm_id)` | owner | Remove member; drop their leases |
| `session_join` (optional alias) | listed member | Validate token + `llm_id` ∈ ACL; no-op success |

On `private`, `session_grant` → `session_forbidden` (switch mode only via owner `session_acl_set access=shared` if provided later; MVP: recreate session).

### 1.6 Gate order (every op)

```text
1. transport reachability (process / TCP bind / optional serve token)
2. session exists
3. session_token valid                          -> else session_auth
4. llm_id in ACL for this mode/role             -> else session_denied
5. role permits this op (read vs write vs acl)  -> else session_forbidden
6. if mutate/reserve: neighbourhood reserve rules (see reserve design)
7. if re-id: id_occupied / merge rules
```

Reserve is **step 6**, never a substitute for steps 3–5.

### 1.7 Pin-map / dialect: access and membership

Bare present (Write = display). Control-plane facts may appear in a pin-map preamble when the caller is authorised:

```text
## Session
SES [demo_sysml] ; access=shared ; role=writer ; llm_id=coder_a

## Members
ACL [A1] ; llm_id=coder_a ; role=owner
ACL [A2] ; llm_id=coder_b ; role=writer
ACL [A3] ; llm_id=reviewer ; role=reader

## Reserves
RSV [R7] ; llm_id=coder_a ; anchor=ATO_R1 ; depth=2 ; until=2026-07-24T08:15:00Z ; left_s=87

## Nodes
CMP [ATO_R1] ; refdes=R1 ; path=boards/pdu/pdu.ato ; recycle=persistent
...
```

| Kind | Meaning |
|------|---------|
| `SES` | This session’s access mode + **caller’s** `role` and `llm_id` (not a dump of the token) |
| `ACL` | Allow-list rows visible to members (MVP: all members see the list; later: owner-only detail) |
| `RSV` | Neighbourhood leases (coop; unchanged semantics) |

**MUST NOT** put `session_token` in pin-map lines.  
**MUST NOT** invent `@SES:` / `@ACL:` pipe.

Denials are envelope errors (prose / codes), not fake empty pin maps that look like success:

```text
session_auth: session_token missing or invalid
session_denied: llm_id=coder_c not a member of session demo_sysml
session_forbidden: role=reader cannot mutate
session_forbidden: role=writer cannot grant
session_mode: grant requires access=shared
```

### 1.8 MCP / CLI sketch (session ACL)

```text
session_open(
  session?,                 # optional client hint; engine may mint
  access=private|shared|open,
  owner_llm_id,             # required unless access=open
  members=[                 # optional seed for shared
    {llm_id=coder_b, role=writer},
    {llm_id=reviewer, role=reader}
  ],
  ...existing seed_lines / map_file...
) -> session_id, session_token, access, SES present line

session_acl(session, session_token, llm_id)
  -> ## Session / ## Members present lines

session_grant(session, session_token, llm_id, member_llm_id, role=writer|reader)
  -> ok + ACL present line    # caller llm_id must be owner

session_revoke(session, session_token, llm_id, member_llm_id)
  -> ok                       # drops member leases

# All graph ops gain session_token (+ llm_id when ACL enforced):
pin_map(session, session_token, llm_id, anchor, depth, ...)
add / update(session, session_token, llm_id, wire_lines)
reserve / extend / release(session, session_token, llm_id, ...)
```

CLI mirrors:

```text
memnet session open --access shared --owner-llm-id coder_a --grant coder_b=writer --grant reviewer=reader
memnet session acl  --session S --token TOKEN --llm-id coder_a
memnet session grant --session S --token TOKEN --llm-id coder_a --member coder_b --role writer
memnet session revoke --session S --token TOKEN --llm-id coder_a --member reviewer
```

### 1.9 Interaction with TCP shared serve

| Concern | Design |
|---------|--------|
| Many agents, one `memnet serve` | Each session has its own ACL + token; serve token (later) is host-level, session token is session-level |
| Guessable / leaked session id | Useless without token **and** ACL membership |
| Bind `0.0.0.0` | Still LAN-visible plaintext; ACL limits *session* damage, not wire sniffing — prefer localhost + later TLS |
| `access=open` on LAN | Discouraged; document as equivalent to “any holder of token may act as any llm_id” unless llm_id binding is still checked |

**MVP binding rule for `private` / `shared`:** ops must supply `llm_id` that matches an ACL row; client cannot act as another member by renaming alone **if** token is unguessable and not shared. If orchestrators share one token among agents, each agent still passes its own `llm_id` and is confined to that row’s role. (Stolen token ⇒ stolen session — same as any capability token.)

---

## 2. Authentication of agents (`llm_id` / tokens)

| Rank | Mechanism | Notes |
|------|-----------|--------|
| **MVP** | `session_token` (session capability) + ACL membership of ASCII **`llm_id`** | First-class session limit |
| **MVP** | Non-empty `llm_id` on reserve / reserved mutate | Lease key inside authorised session |
| **MVP (TCP)** | Default bind **`127.0.0.1`**; non-loopback (`0.0.0.0`, LAN IP) needs **`MEMNET_SERVE_ALLOW_REMOTE=1`** | `config.serve_host()` + `validate_serve_bind_host()` (**0.3.6**) |
| **MVP (TCP)** | Length-prefixed frame cap (default **4 MiB**); oversized frames get `@ERR: frame_too_large` | `MEMNET_SERVE_MAX_FRAME_BYTES` (**0.3.6**) |
| Later | Host **serve token** (`MEMNET_SERVE_TOKEN`) | Casual LAN gate before session layer |
| Later | Per-agent bearer / HMAC proving `llm_id` | Stops token-sharing impersonation |
| Out of scope (v1) | OAuth / mTLS / OS user mapping | Local engineer tooling |

**Locked:** bare client-supplied `llm_id` without session token is **not** enough for `private` / `shared` on TCP.

---

## 3. Authorisation inside a session (after ACL)

Once steps 1–5 in §1.6 pass, lease-centric rules apply (unchanged intent from reserve design):

| Action | Rule for `owner` / `writer` |
|--------|-----------------------------|
| `pin_map` / `read_*` | Allowed; reserved ids read-only for non-holders |
| `reserve` | Non-empty `llm_id`; reject foreign overlap (`reserve_conflict`) |
| `extend` / `release` | Caller `llm_id` == holder; **no force in MVP** |
| `add` / `update` on free ids | Allowed when no foreign lease covers the id |
| `add` / `update` on reserved ids | Holder + unexpired lease; else `reserved` |
| Re-id / merge | Same mutate gate; merge needs both ends free or same holder |

`reader` stops at pin_map/read — never reaches reserve success.

**Later capabilities (optional, envelope):** `cap_admin_release`, `cap_grant` for non-owners, finer merge/re-id caps. Prefer roles in MVP over a large cap matrix.

---

## 4. Session isolation vs shared session

| Pattern | ACL mode | Coop |
|---------|----------|------|
| One agent alone | `private` or in-process `open` | Reserve optional |
| Several agents, one graph | **`shared`** + allow-list | **Reserve required** for writers |
| Independent workstreams | Separate `session_id`s (each with own token) | No cross-session reserve in MVP |

---

## 5. TCP serve exposure risks

Default: `MEMNET_SERVE_HOST=127.0.0.1`, port `18765`.

| Risk | Mitigation |
|------|------------|
| Bind `0.0.0.0` | LAN trust; enable `private`/`shared` + tokens; later serve token / TLS |
| No TLS | Plaintext on wire — tokens visible to sniffers |
| Spoofed `llm_id` | Mitigated by ACL + unshared token discipline; later proof-of-id |
| Session id guessing | Insufficient alone; token required |
| Snapshot path abuse | Keep load/save owner-only (MVP role table) |

---

## 6. Audit / attribution

| Rank | What |
|------|------|
| **MVP** | Tag ops with `llm_id`; ACL grant/revoke recorded in serve log / meta |
| **MVP** | Pin-map `SES` / `ACL` / `RSV` present lines for live attribution |
| Later | Append-only ops log (`llm_id`, op, ids, time) — not agent `@TAG` pipe |

---

## 7. Multi-agent cooperation (inside authorised session)

### 7.1 Primary loop: reserve → edit → release

```text
0. session_open / join (token + llm_id + role=writer|owner)
1. pin_map(anchor=…)           # SES / ACL / RSV + nodes
2. reserve(..., llm_id=me, ttl_s=…)
3. update / add (same llm_id)
4. extend(...) if needed
5. release(..., llm_id=me)
6. pin_map again
```

Lease lifecycle stays MCP/CLI control plane — **not** `+ RSV` graph mutate.

### 7.2 Occupied id: reject vs merge

| Case | Result |
|------|--------|
| `~ [A] ; id=B`, B free | Re-id; lease follows B |
| `~ [A] ; id=B`, B occupied | **`id_occupied`** |
| `~ [A] ; id=B ; merge=true` | Fold if both ends free or same holder |

Foreign lease → `reserved` / `reserve_conflict`, not silent merge. Unauthorised caller → `session_denied` / `session_forbidden` before re-id runs.

### 7.3 Discovering holds and membership

Via pin map only (§1.7): `ACL` rows for who may write; `RSV` rows for who currently holds a neighbourhood.

### 7.4 Optional secondary: optimistic `rev`

Rank: (1) session ACL (2) neighbourhood reserve (3) `rev` CAS (4) session-per-agent merge (5) ops log. Do not block ACL+reserve MVP on `rev`.

### 7.5 Patterns

- **Single-writer lease:** one ACL writer reserves ego, edits, releases.
- **Collaborative subgraphs:** disjoint anchors for different writers on the same `shared` session.
- **Read-only guests:** `role=reader` on allow-list; see pin map + ACL/RSV; cannot mutate.

### 7.6 Failure modes

| Failure | Behaviour |
|---------|-----------|
| TTL expiry / crash | Auto-release lease; ACL membership unchanged |
| Overlap reserve | `reserve_conflict` (no wait → no deadlock) |
| Revoked mid-flight | Next op → `session_denied`; leases dropped on revoke |
| Token leak | Treat as session compromise → owner revoke members + rotate token (later) |
| Open mode on LAN | Any token holder may act — avoid |

---

## 8. MVP vs later (ranked)

### MVP (next minor)

1. **Session ACL:** modes `private` | `shared` | `open`; roles `owner` | `writer` | `reader`.
2. **Session token** minted on open; required on all session ops for `private` / `shared` (and recommended for `open`).
3. MCP: `session_open` fields + `session_acl` / `session_grant` / `session_revoke`; pass `session_token` + `llm_id` on graph tools.
4. Pin-map `## Session` / `## Members` with `SES` / `ACL` present lines (no token in body).
5. Neighbourhood reserve as in `memnet-neighbourhood-reserve.md` (**after** ACL gate).
6. MutateGate: ACL role check then lease check; re-id/merge under holder rules.
7. Document TCP bind risk; default `127.0.0.1`.
8. Align CLI `--agent` → `--llm-id` (alias ok).

### Later

1. Host serve token / TLS.
2. Token rotate; proof-of-`llm_id` (HMAC/bearer).
3. Optimistic `rev`; force-release; non-owner grant caps.
4. Durable ops audit log.
5. Cross-session reserve / merge tooling.
6. Snapshot policy for ACL restore (members yes / tokens no).

### Explicitly out of MVP

- Full enterprise RBAC product
- Agent-authored `+ SES` / `+ ACL` / `+ RSV` as ordinary graph mutates for lifecycle
- Any new `@TAG|pipe` agent dialect
- Half-enforced ACL or reserve (display without gate)

---

## 9. MCP / CLI sketch (cooperation tools)

```text
reserve(session, session_token, llm_id, anchor, depth=2, ttl_s=120)
  -> rid, until, held_count

extend(session, session_token, llm_id, rid|anchor, ttl_s=120)
  -> until

release(session, session_token, llm_id, rid|anchor)
  -> ok

pin_map(session, session_token, llm_id, anchor, depth, ...)
add / update(session, session_token, llm_id, wire_lines)
```

### Agent-facing errors (prose / codes — not pipe kinds)

```text
session_auth: session_token missing or invalid
session_denied: llm_id=coder_c not a member of session demo_sysml
session_forbidden: role=reader cannot mutate
reserved: id ATO_R1 held by llm_id=coder_a until=… (caller llm_id=coder_b)
reserve_conflict: id ATO_R1 already held by llm_id=coder_a
reserve_mismatch: release llm_id does not match holder
reserve_expired: R7 (lease cleared; treat as free)
no_llm_id: llm_id required
id_occupied: target id busy (use merge=true only when intentional)
auth_required: serve token missing or invalid   # later
```

Existing CLI may still use historical `@ERR:` **transport** envelopes — not a licence to invent `@SES:` / `@ACL:` / `@RSV:` for agents.

---

## 10. Pin-map present lines (summary)

```text
## Session
SES [demo_sysml] ; access=shared ; role=writer ; llm_id=coder_a

## Members
ACL [A1] ; llm_id=coder_a ; role=owner
ACL [A2] ; llm_id=coder_b ; role=writer

## Reserves
RSV [R7] ; llm_id=coder_a ; anchor=ATO_R1 ; depth=2 ; until=2026-07-24T08:15:00Z ; left_s=87

## Nodes
...
## Edges
...
```

| Kind | Required fields | Notes |
|------|-----------------|-------|
| `SES` | `access`, `role`, `llm_id` | Caller’s view; id = session id |
| `ACL` | `llm_id`, `role` | Allow-list row; engine-minted row id |
| `RSV` | `llm_id`, `anchor`, `depth`, `until`; optional `left_s` | Lease; see reserve design |

---

## 11. Engine fit (when implementing — not this design drop)

| Component | Change |
|-----------|--------|
| `SessionStore` / lifecycle | ACL table; `session_token` hash at rest; mode/roles |
| Op entry (CLI/MCP/serve) | Gate order §1.6 before mutate/reserve |
| `MutateGate` | Role ≥ writer; then lease checks |
| `PinMapComposer` | `## Session` / `## Members` / `## Reserves` |
| MCP `server.py` | open/acl/grant/revoke; thread token + `llm_id` |
| `serve.py` | Document bind; later host token |
| Snapshot | Restore members optional; **never** restore old token plaintext to pin map |

Do not ship pin-map `SES`/`ACL`/`RSV` display without enforcing the gates.

---

## 12. Grammar / doctrine constraints (preserve)

- Shared dialect Write = display for all new agent-visible lines (`SES`, `ACL`, `RSV`).
- Preserve formal grammar benefits (`MemNet.g4`, golden fixtures, `tier_a.py`) — present kinds follow existing KIND / field patterns; ACL/reserve lifecycle stays on MCP/CLI in MVP.
- British English in this doc and related notes.
- Novel-writer stays dropped.

---

## 13. Related paths

| Path | Role |
|------|------|
| [`memnet-neighbourhood-reserve.md`](memnet-neighbourhood-reserve.md) | SSOT for lease semantics (inside ACL) |
| [`memnet-grammar-design.md`](memnet-grammar-design.md) §4.2.0 / §9a | Re-id / merge; concurrency ranking |
| `README.md` | Doctrine / transport |
| `.cursor/skills/memnet-reference/SKILL.md` | Product development skill (repo) |
| `~/.cursor/skills/mcp-memnet/` | MCP application skill (user pack) |
| `parts/memnet-mcp/` | Tool SSOT when implementing |
| `parts/common/memnet/memnet/config.py` | `serve_host` / `serve_port` defaults |
