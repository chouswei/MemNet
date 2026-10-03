# Case study: ClusterRoute vs SliceHandCarry

**Shelf:** product canon — ops invent (two named moves; not shipped)

One nest so a reader can pin `MemNetTwoMoves` and see **two** children: **ClusterRoute** (where the session lives) and **SliceHandCarry** (explicit copy into another session).  
Companions: [lan-mcp-front-case-study.md](lan-mcp-front-case-study.md) (move A detail), [session-import-case-study.md](session-import-case-study.md) (same-serve Path-B `import_slice`), [snapshot-passport-case-study.md](snapshot-passport-case-study.md) (`session_save` / `session_load`).  
Lock: **tip≠face**; invent-only (`inventOnly=true`; `implemented=false`; `codeApproved=false`). No SemVer. Public operator: InkMirage. Wire: [`docs/operations/cluster-route-vs-slice-hand-carry.md`](../../docs/operations/cluster-route-vs-slice-hand-carry.md).

**Wire:** cluster forwards `pin_map` / `mutate` to the **owning** serve. Slice copies a file, then dest absorbs. Chat is never SSOT.

## 1. Purpose

Stop agents treating LAN cluster routing as a live hop, and stop treating `import_slice` as a cross-host pipe. Make the split pin-able.

## 2. Model locus

| Concern | SysML |
|---------|-------|
| Requirements | **MN-REQ-06.9** (`lanMcpFrontSeveralServesReq`) + **MN-REQ-06.10** (`sliceHandCarryAcrossServesReq`) |
| Verify | **MN-VER-06-S07** + **MN-VER-06-S08** |
| Contrast part | `MemNetTwoMoves` **outside** `MemNetSystem` |
| Move A | `ClusterRoute` — realised by `MemNetLanMcpFront` (do not duplicate ServeBackend) |
| Move B | `SliceHandCarry` — `SliceExportCarry` / `LanFileCopy` / `DestSessionAbsorb` |
| Load | Already on `ProjectMemNet` via `deploy.sysml` |
| Items | `MemNetTwoMovesContrast`, `SliceHandCarryFile`, `MemNetLanMcpCluster` |

```text
MemNetSystem                                 // SharedLlmMemory product (unchanged)
MemNetTwoMoves                               // OUTSIDE — inventOnly; one diagram
├── ClusterRoute                             // A: where the session lives
│   └── realised by MemNetLanMcpFront        // existing nest; not copied here
└── SliceHandCarry                           // B: explicit copy into another session
    ├── SliceExportCarry                     // export_pin_map | session_save
    ├── LanFileCopy                          // operator file copy on the LAN
    └── DestSessionAbsorb                    // import_slice SAME serve | session_load dest
```

## 3. Scenario

**Title:** Cluster = owner; slice = copy

**Premise:** InkMirage ops MAY run several `memnet serve` processes. Agents still GQL. Product questions still go to cousin `sysmledge`.

**Steps (model mandates):**

| Step | ClusterRoute | SliceHandCarry |
|------|----------------|----------------|
| **1. Intent** | Bind / route to the session’s owner | Copy a bounded slice into a **different** session |
| **2. Same host** | One owner on that serve | `import_slice` only if **both** sessions are on that serve |
| **3. Other host** | Optional same-sid save+load + registry update | `export_pin_map` or `session_save` → LAN file copy → dest load/absorb |
| **4. Recall** | `pin_map` / `find` MUST NOT span backends | After absorb, dest session only |
| **5. Caps** | Truncation survives routing; loud if a backend is down or clipped | Truncation rides the file; MUST NOT look complete if clipped |
| **6. Commit** | Owning serve’s one gate | Dest session’s owning serve after absorb |

## 4. Contrast (soft-pass kills)

| Not this | Why |
|----------|-----|
| Same invent as each other | `clusterIsWhereSessionLives=true`; `sliceIsExplicitCopy=true` |
| Live hop / spanning `pin_map` | `liveHop=false`; `pinMapSpansBackends=false` |
| `import_slice` across hosts | `importSliceAcrossHosts=false`; `importSliceSameServeOnly=true` |
| `import_slice(from_url)` | `importSliceFromUrl=false` |
| Shared graph DB | `sharedGraphDb=false`; Neo4j retired #189 |
| Complete-looking clipped extract | `clippedMustNotLookComplete=true`; `truncationFlagsSurviveBothMoves=true` |
| Nest under `MemNetSystem` | `twoMovesInsideSystem=false` |
| SysMLEdge / AccountFace / InvenTree | `tipIsFace=false`; `isSysmlEdgeProduct=false` |
| Shipping / SemVer | `inventOnly=true`; `implemented=false`; `codeApproved=false`; `noSemVerBump=true` |

## 5. Honesty

SysML + the wire note lock the split. Engine/MCP **code** is unchanged. Hatch `memnet-llm` is not bumped. `MemNetLanMcpFront` stays the ClusterRoute realisation (PR #192 / `1f4b3b9` on master). This MemNet repo still has no SysMLEdge product face to invent.
