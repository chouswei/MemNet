# Case study: SSOT parts allocate to live code (one wheel, many hosts)

**Shelf:** product canon — implementation allocate (not a new engine cut)

Evidence walk of **SoftwareAllocate**: nested logical parts in `deploy.sysml` map to live Python modules in this checkout. One Hatch wheel (`memnet-llm`) instantiates on many hosts (droplet + devices). MemNet MCP stays **tip/ops** (`tipIsFace=false`). Cousin **sysmledge** is not in the wheel and is not allocated here (`mustNotInventUploadBind`).  
Companions: [device-fleet-one-mcp-case-study.md](device-fleet-one-mcp-case-study.md) (ops topology), [tcp-shared-multitask-case-study.md](tcp-shared-multitask-case-study.md) (one shared serve per host).  
Lock: allocate = **path record**, not a second product; Hatch stays **0.19.11** honesty `c`; [#47](https://github.com/chouswei/MemNet/issues/47) stays research.

**Wire:** unchanged. Agents still GQL / `pin_map` / `mutate`. This cut does not change engine or MCP behaviour.

## 1. Purpose

Show maintainers **which file realises which SSOT part**, and **track implementation** as allocate rows (live path + `track=true`). Do not invent a SysMLEdge product face in this repo and do not treat hosts as extra packages.

## 2. Model locus

| Concern | SysML |
|---------|-------|
| Requirement | **MN-REQ-06.7** (`ssotToCodeAllocateReq`) |
| Verify | **MN-VER-06-S04** |
| Package | `MemNetImplementation` (`models/implementation.sysml`) |
| Wheel | `MemNetLlmWheel` — `oneWheelManyHosts=true`; `sysmlEdgeInWheel=false` |
| Tip module | `McpServerMod` — `memnet_mcp.server:main`; `tipIsFace=false` |
| Absence | `CousinSysMLEdgeNotInRepo` — `inThisRepo=false`; `track=false`; no `SoftwareAllocate` |
| Tracker | `ImplementationTracker` — `trackAllocateRows`; `missingPathFailsCi`; map = [ssot-to-code-allocate-map.md](ssot-to-code-allocate-map.md) |
| Fleet bind | `opsFleet` / droplet `memnet.mcp` / device `service` → same wheel |

```text
MemNetLlmWheel                              // Hatch memnet-llm (one package)
├── CoreLibraryMod                          // parts/common/memnet/memnet
└── McpServerMod                            // memnet_mcp.server:main (tip/ops)
    // sysmledge NOT here (CousinSysMLEdgeNotInRepo)

SoftwareAllocate                            // logical → code
├── MemNetSystem.core        → wheel.core
├── MemNetSystem.mcp         → wheel.mcp     // tip≠face
├── MemNetOpsFleet           → wheel         // many hosts, one wheel
├── DropletHost.memnet.mcp   → wheel.mcp
├── MemNetDeviceHost.service → wheel.core
└── nested session / RecallCommit / durable / pin-map / host-search
    → named *Mod paths on disk
```

## 3. Scenario

**Title:** Droplet and Pi run the same wheel; allocate names the files; sysmledge stays cousin

**Premise:** `pyproject.toml` ships `memnet` (`memnet.cli:main`) and `memnet-mcp` (`memnet_mcp.server:main`) from one Hatch target. A droplet and a Pi both install that wheel. The SysML allocate package records the mapping. Product invent face remains cousin `sysmledge` (not a path in this repo).

**Actors:**

- Hatch wheel `memnet-llm` — one package, many hosts (`oneWheelManyHosts`)
- `McpServerMod` — MemNet tip/ops console (`tipIsFace=false`)
- `CousinSysMLEdgeNotInRepo` — must not invent upload/bind
- Honesty tests — every `path=` exists on disk

**Steps (model mandates):**

| Step | What happens | MUST NOT |
|------|----------------|----------|
| **1. Name the wheel** | `MemNetLlmWheel` matches Hatch `memnet-llm` + two console entries | Nest a SysMLEdge package in the wheel |
| **2. Allocate core** | `MemNetCoreLibrary` → `parts/common/memnet/memnet` | Treat droplet and Pi as extra Python packages |
| **3. Allocate tip MCP** | `MemNetMcpServer` → `memnet_mcp.server` (`tipIsFace=false`) | Teach MemNet MCP as the product invent face |
| **4. Allocate nested parts** | Session / GQL / RecallCommit / durable / pin-map / MCP façade → live `.py` | Allocate `sysmledge` / invent upload/bind |
| **5. Fleet uses the same wheel** | `opsFleet` / droplet / devices bind `wheel` | N-server federation pipe (#47) |
| **6. Honesty / track** | Tests assert every `path=` exists; map lists every allocate row | Change engine/MCP behaviour for this cut; drop a row without updating the map |

## 3a. How to track implementation

The allocate package **is** the tracker. Ledger: [ssot-to-code-allocate-map.md](ssot-to-code-allocate-map.md).

| Step | Do this |
|------|---------|
| **Look** | Read the map, or cue `kind=TSK` `locators=['goal=TSK_model_alloc']` then `pin_map` |
| **Locate** | Match the logical SSOT part to `path` / `pyName` |
| **Prove** | `track=true` ⇒ path exists (`pytest tests/test_sysml_ssot_to_code.py`) |
| **Update** | Ship or move a module → edit `implementation.sysml`, sync the map, re-run pytest |
| **Refuse** | MUST NOT add a `sysmledge` row (`sysmlEdgeTracked=false`) |

Companions: [device-fleet-one-mcp-case-study.md](device-fleet-one-mcp-case-study.md) (where processes live); this map (which file realises each part).

## 4. Contrast (soft-pass kills)

| Not this | Why |
|----------|-----|
| SysMLEdge code in this wheel | `sysmlEdgeInWheel=false`; `CousinSysMLEdgeNotInRepo.inThisRepo=false` |
| Invent upload/bind for sysmledge | `mustNotInventUploadBind`; cousin `thisRepoHasProductFace=false` |
| MemNet MCP as product invent face | `McpServerMod.tipIsFace=false` (tip≠face) |
| One package per host | `oneWheelManyHosts=true`; hosts instantiate the same wheel |
| N-server federation | `nServerFederation=false`; #47 research |
| Engine behaviour change | Allocate is a path **tracker**; Hatch stays 0.19.11 honesty `c` |
| SemVer `b` | Same goldfish loop (`cue → pin_map → mutate`) |

## 5. Honesty

SysML + this note lock SSOT → code **and** the implementation ledger. Every `attribute path` on an in-repo module is a live file or directory. The derived map must list every `SoftwareAllocate` row. Engine/MCP **code** is unchanged. Shared session across processes remains TCP / streamable-http on **one** serve. A pipe between two MemNet servers is still Later (#47). This MemNet repo still has no SysMLEdge product face to invent (`CousinSysMLEdge.thisRepoHasProductFace=false`).
