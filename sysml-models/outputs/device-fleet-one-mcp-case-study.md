# Case study: device MemNet services, one MCP at the droplet

**Shelf:** product canon — ops fleet (not N-server federation)

Evidence walk of a **droplet-centred fleet**: MemNet engine/serve on device hosts, **one** `MemNetMcpServer` on the droplet.  
Companions: [tcp-shared-multitask-case-study.md](tcp-shared-multitask-case-study.md) (one shared serve **per host**), [session-import-case-study.md](session-import-case-study.md) (Path-B slice, not live-server MERGE), [usage-dashboard-case-study.md](usage-dashboard-case-study.md) (ops look).  
Lock: devices = **MemNet service**; droplet = **the MCP face**. [#47](https://github.com/chouswei/MemNet/issues/47) stays research.

**Wire:** agents still GQL / `pin_map` / `mutate` on the session they hold. Chat is never the handoff. Two handles stay two handles.

## 1. Purpose

Show operators and agents **where processes live** without inventing a mesh of MemNet servers. Local notepads (Pi OpenClaw digest) stay on device serve. Cloud/LLM tools talk to **one** MCP at the droplet.

## 2. Model locus

| Concern | SysML |
|---------|-------|
| Requirement | **MN-REQ-06.6** (`deviceServicesOneDropletMcpReq`) |
| Verify | **MN-VER-06-S03** |
| Fleet | `MemNetOpsFleet` **outside** `MemNetSystem` |
| Droplet | `DropletHost` — `part memnet : MemNetSystem` (`mcpCount=1`) |
| Devices | `MemNetDeviceHost[1..*]` — `part service : MemNetCoreLibrary` (`mcpNested=false`) |
| Item | `DeviceMemNetFleet` (`connections.sysml`) |

```text
MemNetOpsFleet                               // OUTSIDE MemNetSystem
├── DropletHost                              // DigitalOcean
│   └── MemNetSystem                         // includes the ONE MemNetMcpServer
│       ├── MemNetCoreLibrary                // CompanyMemory / droplet serve
│       └── MemNetMcpServer                  // LLM tool face (fleetSingleton)
└── MemNetDeviceHost[1..*]                   // Pi / workstation / SBC
    └── MemNetCoreLibrary                    // local notepad; no MCP
```

## 3. Scenario

**Title:** rpi5-syson notepad plus droplet CompanyMemory, one MCP face

**Premise:** The droplet runs CompanyMemory behind `memnet-mcp`. A Pi (`rpi5-syson`) runs `memnet serve` (or in-process library) as OpenClaw’s local digest notepad. Cursor/cloud agents bind the droplet MCP only.

**Actors:**

- Droplet MCP — the fleet’s one LLM tool face (`fleetMcpHost=droplet`, `mcpCount=1`)
- Device MemNet service — engine + TCP/IPC/CLI; `mcpNested=false`
- Human / Memnetor+Devicor — manage serve on each host via CLI, not a second MCP

**Steps (model mandates):**

| Step | What happens | MUST NOT |
|------|----------------|----------|
| **1. Droplet MCP** | Agents `session_open` / `pin_map` / `mutate` at the droplet | Stand up a second product MCP on a device |
| **2. Device service** | Pi runs `MemNetCoreLibrary` for the local notepad | Nest `MemNetMcpServer` on the Pi |
| **3. Handles** | Droplet `companySessionId` and Pi digest session stay distinct | Mash ids; one global MemNet by accident |
| **4. Handoff** | Pass session id; peer re-`pin_map` | Graph dump in chat; Cypher MERGE of two live servers |
| **5. Optional join** | Path-B `import_slice` / ImportAbsorb into a mission session | N-server federation pipe (#47); shared cabinet required |

## 4. Contrast (soft-pass kills)

| Not this | Why |
|----------|-----|
| N MemNet MCP servers | MN-REQ-06.6; `mcpCount=1`; `fleetSingleton=true` |
| Device MCP face | `mcpNested=false`; LLM face is droplet only |
| Nest fleet under `MemNetSystem` | `opsFleetInsideSystem=false` (same honesty as dashboard / HostSearch) |
| N-server federation | `nServerFederation=false`; #47 research |
| Shared DB as the pipe | No requirement that hosts share a cabinet |
| Multitask across two servers | MN-REQ-12.2 is one shared serve **on one host** (TCP / streamable-http) |

## 5. Honesty

SysML + this note lock the ops topology. Engine/MCP **code** is unchanged. Shared session across processes remains TCP / streamable-http on **one** serve. A pipe between two MemNet servers is still Later (#47).
