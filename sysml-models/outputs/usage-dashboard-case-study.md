# Case study: MemNet usage dashboard (human look only)

**Shelf:** product canon — ops visibility (not agent wire)

Evidence walk of a **read-only** human look at live serve usage against `sysml-models/models/`.  
Companions: [tcp-shared-multitask-case-study.md](tcp-shared-multitask-case-study.md) (shared store), [session-import-case-study.md](session-import-case-study.md) (ImportGuard nest).  
Lock: dashboard = **LOOK**; manage serve / MCP / roll / housekeep / ImportGuard env = **Memnetor + Devicor**.

**Wire:** agents still GQL / `pin_map` / `mutate` (CLI/MCP). The page is **not** a second agent API. tip is not face; not Foam product MCP.

## 1. Purpose

Show operators **load at a glance** without giving the page manage or mutate. HTTP/UI remains **parked** (`httpImplemented=false`) until Core GO.

## 2. Model locus

| Concern | SysML |
|---------|-------|
| Requirement | **MN-REQ-06.5** (`humanUsageLookReq`) |
| Verify | **MN-VER-06-S02** |
| Part | `MemNetUsageDashboard` **outside** `MemNetSystem` |
| Observe | `TcpServeBridge.usageLookOut`, `CmdSessionList.usageLookOut`, `HousekeepSettle.usageLookOut`, `CheapLlmImportGuard.armedLookOut` |
| Shared registry | `MultitaskSharedStoreBinding` (observe; dashboard does not own `SessionLifecycle`) |
| Items | `ServeUsageLook`, `ImportGuardArmedLook`, `HumanUsagePage` |
| Nested looks | `ServeStatusLook`, `SessionCensusLook`, `HousekeepLook`, `ImportGuardArmedDisplay` |

```text
MemNetSystem                                 // SharedLlmMemory product
├── TransportBoundary / TcpServeBridge       // usageLookOut = serve_status
├── McpFacade.sessionList                    // usageLookOut = sessions|n/max
├── SessionLifecycle.housekeep               // usageLookOut = housekeep_stats
└── ImportGuard.cheapLlm                     // armedLookOut = env presence
MemNetUsageDashboard                         // OUTSIDE — look only
├── ServeStatusLook
├── SessionCensusLook                        // no session_close
├── HousekeepLook                            // no prune
└── ImportGuardArmedDisplay                  // no key, no enable
```

## 3. Scenario

**Title:** Human glances at localhost usage while Memnetor owns serve

**Premise:** A shared TCP serve is up (`127.0.0.1:18765`). Sessions sit at `n/max`. Housekeep reports caps. ImportGuard is armed or not from env presence. An operator opens the look surface (when implemented) or reads the same facts from CLI/MCP today.

**Actors:**

- Human — look actor (`lookActor=human`)
- Memnetor + Devicor — manage owners (CLI/MCP only)
- `MemNetUsageDashboard` — display; `ownsSessionLifecycle=false`

**Steps (model mandates):**

| Step | What happens | MUST NOT |
|------|----------------|----------|
| **1. Observe serve** | `serve_status` → up/host/port | Send `ServeCommand`; restart serve |
| **2. Session census** | `@STAT: sessions\|n/max` + id table | `session_close`; open; dump \(S\) |
| **3. Housekeep** | caps / row counts | prune / settle / housekeep apply |
| **4. ImportGuard armed** | env presence on/off | key on page; enable toggle; reproject |
| **5. Manage stays CLI** | Memnetor/Devicor use MCP/CLI | Humans operating serve via the page |

## 4. Contrast (soft-pass kills)

| Not this | Why |
|----------|-----|
| Manage console | Ownership lock: Memnetor + Devicor |
| `session_close` / `mutate` / `import_slice` ports on the dashboard | MN-REQ-06.5; `sessionClosePort`/`mutatePort`/`importSlicePort`=false |
| ImportGuard key entry / write toggles | `keyOnPage=false`; `writable=false` |
| Agent wire / Foam product MCP | `agentWire=false`; `foamProductMcp=false`; `tipIsFace=false` |
| Nest under `MemNetSystem` | `usageDashboardInsideSystem=false` (same honesty as HostSearch) |
| HTTP server in this cut | `httpImplemented=false` until Core GO |
| Teaching goldfish to read the page | SemVer **c** only; agents stay CLI/MCP |

## 5. Honesty

SysML + this note lock the look/manage split. Webpage v0 is **parked**. CLI/MCP `serve_status`, `session_list`, `housekeep_stats` remain the live read path until Core GO.
