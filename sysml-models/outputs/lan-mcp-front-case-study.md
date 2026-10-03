# Case study: one MCP front, several LAN MemNet serves (#191)

**Shelf:** product canon — ops invent (not N-server peer pipe; not shipped)

Evidence walk of a **LAN MCP catalogue**: one MemNet MCP in front of N `memnet serve` backends, with `SessionOwnerRegistry` as owner.  
Companions: [device-fleet-one-mcp-case-study.md](device-fleet-one-mcp-case-study.md) (one droplet MCP bound to **that** host; independent device registries), [session-import-case-study.md](session-import-case-study.md) (Path-B slice, not live-server MERGE), [snapshot-passport-case-study.md](snapshot-passport-case-study.md) (save/load hand-carry).  
Lock: **tip≠face**; invent-only (`inventOnly=true`; `implemented=false`; `codeApproved=false`). [#47](https://github.com/chouswei/MemNet/issues/47) stays the **cousin** peer pipe. No SemVer. Wire: [`docs/operations/memnet-lan-mcp-front.md`](../../docs/operations/memnet-lan-mcp-front.md).

**Wire:** agents still GQL / `pin_map` / `mutate`. The front routes; it does not merge graphs. Chat is never SSOT.

## 1. Purpose

Let agents keep **one MCP endpoint** while sessions live on more than one LAN serve — only if one host’s RAM/CPU is the bottleneck. Make the **complexity versus capacity** trade-off visible. Do not ship.

## 2. Model locus

| Concern | SysML |
|---------|-------|
| Requirement | **MN-REQ-06.9** (`lanMcpFrontSeveralServesReq`) |
| Verify | **MN-VER-06-S07** |
| Part | `MemNetLanMcpFront` **outside** `MemNetSystem` |
| Load | Already on `ProjectMemNet` via `deploy.sysml` (`config.yaml` / `root.sysml` import `MemNet`) |
| Items | `MemNetLanMcpCluster`, `SessionOwnerRecord`, `RoutedMcpCall`, `TruncationHonestyMark`, `SnapshotHandCarryBlob`, `LanFrontAuthToken` |
| Parts | `ClusterRoute` (`SessionOpenRoute` / `SessionListUnion` / `SessionCurrentBind`), `SessionOwnerRegistry`, `ServeBackend[1..*]`, `FrontBackendAuth`, `SnapshotHandCarry` |

```text
MemNetSystem                                 // SharedLlmMemory product (unchanged)
MemNetLanMcpFront                            // OUTSIDE — inventOnly #191; ClusterRoute
├── ClusterRoute                             // named move A: where the session lives
│   └── SessionOpenRoute / SessionListUnion / SessionCurrentBind
├── SessionOwnerRegistry                     // sid → backendId; pin allowed; not silent hash
├── ServeBackend[1..*]                       // one serve; local Commit; per-backend snap dir
├── FrontBackendAuth                         // LAN hop auth; not an open port
└── SnapshotHandCarry                        // same-sid relocate; not SliceHandCarry
```

## 3. Scenario

**Title:** One catalogue; N backends; one owner; no spanning recall

**Premise:** InkMirage ops MAY run several `memnet serve` processes on a LAN. Agents bind **one** MemNet MCP. Product questions still go to cousin `sysmledge`. This nest is not that face.

**Actors:**

- `MemNetLanMcpFront` — one MCP tool surface (`inventOnly`; not shipped)
- `SessionOwnerRegistry` — owner of each sid
- `ServeBackend` — owning serve (Commit gate, ACL, expire-save dir)
- Cousin #47 — peer sid handoff between **independent** MemNets (no shared catalogue)

**Steps (model mandates):**

| Step | What happens | MUST NOT |
|------|----------------|----------|
| **1. Open** | Explicit pin or pick a live backend; write registry; forward `session_open` | Silent hash as the only policy |
| **2. List / current** | Union tagged with owner; one current sid | Look complete when a backend clipped or is down |
| **3. Recall** | `pin_map` / `find` on the owning serve only | Span sessions on different backends in one call |
| **4. Commit** | `mutate` on the owning serve’s one gate | Cross-backend graph MERGE |
| **5. Caps** | `max_rows` / hops / Truncation pass through | Drop the truncation mark |
| **6. Fail** | Per-backend `serve_status`; owner down is loud | Silent retry on another serve |
| **7. Move** | Optional `session_save` → copy file → `session_load`; update registry | Silent migrate; shipped `import_slice(from_url=…)` |
| **8. Cross-host slice** | Not this nest — see SliceHandCarry / MN-REQ-06.10 | Shared Neo4j / AgensGraph as the cluster store |

## 4. Contrast (soft-pass kills)

| Not this | Why |
|----------|-----|
| SysMLEdge / AccountFace / InvenTree | `tipIsFace=false`; `isSysmlEdgeProduct=false` |
| Nest under `MemNetSystem` | `lanMcpFrontInsideSystem=false` |
| Same invent as #47 | `nServerPeerHandoff=false`; `cousinIssue47=true` (#47 = peer sid / optional import, no shared catalogue) |
| Same as MN-REQ-06.6 fleet | Fleet = one droplet MCP bound to that host; this nest = one catalogue over N backends |
| Silent hash routing | `silentHashRouting=false`; `registryPreferred=true`; `explicitPinAllowed=true` |
| Span `pin_map` / `find` | `pinMapSpansBackends=false`; `findSpansBackends=false` |
| Cross-backend MERGE / shared graph DB | `sharedGraphDb=false`; Neo4j retired #189 |
| Complete-looking clipped / down answers | `incompleteIfAnyClippedOrUnreachable=true`; `loudFailOwnerDown=true` |
| Silent migrate | `silentMigrate=false`; `importSliceFromUrl=false` |
| Open LAN / public MCP | `lanAuthRequired=true`; `unauthenticatedPublicMcp=false` |
| Shipping / SemVer | `inventOnly=true`; `implemented=false`; `codeApproved=false`; `noSemVerBump=true` |

## 5. Worth building? (decision stub)

A single serve already hosts many sessions (`singleServeHostsManySessions=true`). Default: **keep one serve**. Do not ship. Revisit only if a named InkMirage host hits one-serve RAM/CPU and ops can run N serves plus a registry plus LAN auth. `worthBuildingVisible=true` so the trade-off stays on the model.

## 6. Honesty

SysML + the wire note lock the invent. Engine/MCP **code** is unchanged. Hatch `memnet-llm` is not bumped. `MemNetOpsFleet.nServerFederation` stays false (#47 research). This MemNet repo still has no SysMLEdge product face to invent.
