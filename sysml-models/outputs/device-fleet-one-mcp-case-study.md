# Case study: device MemNet services, one MemNet MCP at the droplet (tip≠face)

**Shelf:** product canon — ops fleet (not N-server federation)

Evidence walk of a **droplet-centred fleet**: MemNet engine/serve on device hosts, **one** fleet `MemNetMcpServer` on the droplet as the **MemNet tip/ops** engine face. Product invent face is cousin **SysMLEdge** (`sysmledge`; `mustNotInventUploadBind`).  
Companions: [tcp-shared-multitask-case-study.md](tcp-shared-multitask-case-study.md) (one shared serve **per host**), [session-import-case-study.md](session-import-case-study.md) (Path-B slice, not live-server MERGE), [usage-dashboard-case-study.md](usage-dashboard-case-study.md) (ops look).  
Lock: devices = **MemNet service** (tip MemNet MCP on Pi for ops is allowed); droplet MemNet MCP = **tip/ops**, not invent face; product Q → **sysmledge**. [#47](https://github.com/chouswei/MemNet/issues/47) stays research.

**Wire:** MemNet agents still GQL / `pin_map` / `mutate` on the session they hold. Chat is never the handoff. Two handles stay two handles. Dual-MCP remeter: product agents bind `sysmledge`; MemNet tip/ops bind droplet MemNet MCP and/or Pi tip.

## 1. Purpose

Show operators and agents **where processes live** without inventing a mesh of MemNet servers and without selling the MemNet tip as the product face. Local notepads (Pi OpenClaw digest) stay on device serve; a Pi **MAY** run tip `memnet-mcp` for engine ops (still tip≠face). Product questions go to **sysmledge** only.

## 2. Model locus

| Concern | SysML |
|---------|-------|
| Requirement | **MN-REQ-06.6** (`deviceServicesOneDropletMcpReq`) |
| Verify | **MN-VER-06-S03** |
| Fleet | `MemNetOpsFleet` **outside** `MemNetSystem` |
| Droplet | `DropletHost` — `part memnet : MemNetSystem` (`mcpCount=1` = one MemNet MCP) |
| Devices | `MemNetDeviceHost[1..*]` — `part service : MemNetCoreLibrary` (`mcpNested=false` = no **product** MCP; `tipMcpLegal=true`) |
| Product face | cousin `sysmledge` (`productInventFace`; `mustNotInventUploadBind`) — not nested under `MemNetSystem` |
| Item | `DeviceMemNetFleet` (`connections.sysml`) |

```text
MemNetOpsFleet                               // OUTSIDE MemNetSystem
├── DropletHost                              // DigitalOcean
│   ├── MemNetSystem                         // includes the ONE fleet MemNetMcpServer
│   │   ├── MemNetCoreLibrary                // CompanyMemory / droplet serve
│   │   └── MemNetMcpServer                  // MemNet tip/ops MCP (fleetSingleton; tip≠face)
│   └── sysmledge (cousin; not nested here)  // product invent face; mustNotInventUploadBind
└── MemNetDeviceHost[1..*]                   // Pi / workstation / SBC
    └── MemNetCoreLibrary                    // local notepad; no product MCP
        // tip memnet-mcp MAY run for ops; still tip≠face; not sold as product
```

## 3. Scenario

**Title:** rpi5-syson notepad plus droplet CompanyMemory; MemNet tip≠face; sysmledge is product

**Premise:** The droplet runs CompanyMemory behind `memnet-mcp` (MemNet **tip/ops**). The same droplet runs cousin `sysmledge` as the **product invent face**. A Pi (`rpi5-syson`) runs `memnet serve` (or in-process library) as OpenClaw’s local digest notepad and **MAY** run tip `memnet-mcp` for engine ops. Product agents bind **sysmledge**; MemNet tip/ops bind the droplet MemNet MCP and/or the Pi tip. MUST NOT answer product questions on the MemNet tip path.

**Actors:**

- Droplet MemNet MCP — the fleet’s one MemNet tip/ops engine face (`fleetMcpHost=droplet`, `mcpCount=1`, `tipIsFace=false`)
- Droplet `sysmledge` — product invent face (cousin; `mustNotInventUploadBind`; not a MemNet nest)
- Device MemNet service — engine + TCP/IPC/CLI; optional tip `memnet-mcp` for ops; `mcpNested=false` / `productMcpNested=false`; `tipMcpLegal=true`
- Human / Memnetor+Devicor — manage serve on each host via CLI, not a second **product** MCP

**Steps (model mandates):**

| Step | What happens | MUST NOT |
|------|----------------|----------|
| **1. Product bind** | Product agents use `sysmledge` only (dual-MCP remeter) | Bind droplet MemNet MCP for a product question; tip path answering product Q |
| **2. MemNet tip/ops** | MemNet tip/ops use droplet `MemNetMcpServer` (`session_open` / `pin_map` / `mutate`) and/or Pi tip | Treat MemNet MCP as the invent/product face |
| **3. Device service** | Pi runs `MemNetCoreLibrary` for the local notepad; tip `memnet-mcp` MAY run for ops | Nest a second **product** MCP / nest SysMLEdge-as-product on the Pi; teach “device must never run any MCP” as a ban on ops tip |
| **4. Handles** | Droplet `companySessionId` and Pi digest session stay distinct | Mash ids; one global MemNet by accident |
| **5. Handoff** | Pass session id; peer re-`pin_map` | Graph dump in chat; Cypher MERGE of two live servers |
| **6. Optional join** | Path-B `import_slice` / ImportAbsorb into a mission session | N-server federation pipe (#47); shared cabinet required |

## 4. Contrast (soft-pass kills)

| Not this | Why |
|----------|-----|
| MemNet MCP as product invent face | `tipIsFace=false`; product face is `sysmledge`; `mustNotInventUploadBind` |
| Tip path answering a product question | Dual-MCP remeter: product Q → `sysmledge` only |
| Teach “Cursor/cloud agents bind the droplet MemNet MCP only” for product work | Product agents → `sysmledge`; MemNet tip/ops → droplet MemNet MCP and/or Pi tip |
| Teach “device must never run any MCP” as a ban on ops tip | `tipMcpLegal=true`; `mcpNested=false` means no **product** MCP nested |
| A second product MCP / SysMLEdge-as-product on a device | `mcpCount=1`; `productMcpNested=false` |
| N fleet MemNet MCP servers as product faces | MN-REQ-06.6; `mcpCount=1`; `fleetSingleton=true` (one MemNet tip/ops at droplet) |
| Nest fleet under `MemNetSystem` | `opsFleetInsideSystem=false` (same honesty as dashboard / HostSearch) |
| N-server federation | `nServerFederation=false`; #47 research |
| Shared DB as the pipe | No requirement that hosts share a cabinet |
| Multitask across two servers | MN-REQ-12.2 is one shared serve **on one host** (TCP / streamable-http) |

## 5. Honesty

SysML + this note lock the ops topology and tip≠face remeter. Engine/MCP **code** is unchanged. Shared session across processes remains TCP / streamable-http on **one** serve. A pipe between two MemNet servers is still Later (#47). This MemNet repo still has no SysMLEdge product face to invent (`CousinSysMLEdge.thisRepoHasProductFace=false`).
