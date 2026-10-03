# LAN MCP front (several MemNet serves)

Later invent ([#191](https://github.com/chouswei/MemNet/issues/191)): **one MemNet MCP** catalogues sessions across **N LAN `memnet serve` backends**. Named move: **ClusterRoute** — where the session lives. Engine/tip topology only (**tip≠face**). Not the SysMLEdge product face. Not AccountFace. Not InvenTree. Invent-only: no engine code, no SemVer.

**Two moves, do not conflate:** ClusterRoute (this note) is **not** SliceHandCarry. Contrast: [`cluster-route-vs-slice-hand-carry.md`](cluster-route-vs-slice-hand-carry.md).

Model: `MemNetLanMcpFront` outside `MemNetSystem` (`MN-REQ-06.9` / `MN-VER-06-S07`). Case study: [`sysml-models/outputs/lan-mcp-front-case-study.md`](../../sysml-models/outputs/lan-mcp-front-case-study.md).

**Cousin, not the same invent:** [#47](https://github.com/chouswei/MemNet/issues/47) / **SliceHandCarry** is a bounded copy into **another** session (handoff ≠ live hop; `import_slice` only on the same serve). This note is **one MCP catalogue + N backends** (where the session lives). Cross-host slice still uses export→file copy→import, or `session_save` / `session_load`. `import_slice(from_url=…)` is **not** shipped.

Distinct from **MN-REQ-06.6** (`MemNetOpsFleet`): one droplet MemNet MCP bound to **that host’s** serve; device registries stay independent.

## Placement and routing

`SessionOwnerRegistry` is the owner of a session (sid → `backendId`). **Explicit pin** of a new session to a live backend is allowed. Silent hash of sid is **not** the sole routing policy (hash MAY hint placement; the registry row is the owner).

| Call | Behaviour |
|------|-----------|
| `session_open` | Honour an explicit pin if that backend is live; else pick a live backend, **write** the registry, forward open to that serve |
| `session_list` | Union reachable backend catalogues; each row tagged with owner `backendId`. MUST NOT look complete if any backend clipped or was unreachable |
| `session_current` | One current sid for this MCP connection, owned by exactly one backend. Owner down → loud fail |

## One owner per session

A session lives on **exactly one** serve. No cross-backend graph merge. Commit / `mutate` stays the owning serve’s one gate.

## Recall across backends

`pin_map` / `find` MUST NOT span sessions on different backends in one call. Copying atoms into another session is **SliceHandCarry**, not this cluster route.

## Caps and truncation

Hard `max_rows` / hops and truncation flags (`## Truncation`) MUST survive routing. A multi-backend answer MUST NOT look complete if any backend clipped or was unreachable.

## Failure

`serve_status` is **per-backend**. Owner backend down **fails loudly** (no silent retry on another serve). Session move is optional save then load via the snapshot dir — **not** silent migrate.

## TTL / expire-save

Snapshot dir is **per-backend** by default (`MEMNET_EXPIRE_SNAPSHOT_DIR` on that serve). Shared NFS is an optional ops choice, not required. A shared graph DB under backends is retired ([#189](https://github.com/chouswei/MemNet/issues/189)).

## Auth and ACL

Session ACL follows the session to its backend. The LAN hop front↔backend needs its own auth (not an open port). **InkMirage CEO lock:** no unauthenticated MemNet MCP on the public internet.

## Rate cap

Per-session (unchanged; MN-REQ-13 rate cap \(R\)). Per-backend is an optional ops overlay.

## Worth building? (decision stub)

A **single serve already hosts many sessions** (projectId, then registry, then `mn_*` sid). This invent adds a registry, LAN auth, truncation honesty across hosts, and loud failure — complexity for capacity, not a second product.

**Decision stub:** keep one serve as the default. Do **not** ship this front, bump SemVer, or treat the invent as code-approved. Revisit only if a named InkMirage host hits one-serve RAM/CPU **and** ops can run N serves plus a registry plus LAN auth. Until then the trade-off stays visible on `MemNetLanMcpFront` (`inventOnly=true`, `implemented=false`, `codeApproved=false`, `singleServeHostsManySessions=true`, `worthBuildingVisible=true`).
