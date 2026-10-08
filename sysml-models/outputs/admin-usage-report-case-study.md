# Case study: admin serve usage report

**Shelf:** product canon — ops visibility for a product-gate admin MCP (not agent wire)

Evidence walk of a **read-only, admin-only** usage snapshot on `memnet-serve` against `sysml-models/models/`.  
Companion: [usage-dashboard-case-study.md](usage-dashboard-case-study.md) (MN-REQ-06.5 human look may list live ids; HTTP parked). This cut is **MN-REQ-06.11**: counts and caps, opaque aliases, separate admin credential.

**Wire:** agents still GQL / `pin_map` / `mutate` (CLI/MCP). The report is **not** a second agent API and **MUST NOT** appear on the generic MCP tool list. InkMirage admin MCP / face is the later caller; not nested in this repo.

## 1. Purpose

Let an owner see **per serve**: live sessions against `MEMNET_MAX_SESSIONS`, per-session row/relation pressure, process RSS / uptime / version / caps, and refuse/clip tallies since start — without graph content or real session ids.

## 2. Model locus

| Concern | SysML |
|---------|-------|
| Requirement | **MN-REQ-06.11** (`adminServeUsageReportReq`) |
| Verify | **MN-VER-06-S09** |
| Part | `AdminUsageReport` on `TcpServeBridge` (inside transport) |
| Command | `CmdAdminUsageReport` on `CliFacade`; **not** on `McpFacade` |
| Credential | `AdminCredentialGate` (`MEMNET_ADMIN_TOKEN`; not agent ACL) |
| Tally | `CapPressureTally` (since serve start) |
| Items | `AdminUsageReportSnapshot`, `AdminSessionUsageRow`, `CapPressureCounts` |
| Open | `mcpProductLabelOpen` — in-process MCP-only product label unbuilt |

```text
MemNetSystem
└── core.transport.tcp : TcpServeBridge
    ├── usageLookOut                 // 06.5 serve_status (may list ids elsewhere)
    └── adminUsage : AdminUsageReport
        ├── cred : AdminCredentialGate
        └── tally : CapPressureTally
CliFacade.adminUsageReport           // memnet admin usage-report
McpFacade.adminUsageToolNested=false
```

## 3. Scenario

**Title:** InkMirage admin MCP asks memnet-serve for load; agents never see the tool

**Premise:** A product gate runs `memnet serve` with `MEMNET_ADMIN_TOKEN` set. Agents use generic MCP (`pin_map` / `mutate`). The owner looks at usage from an admin face that is **not** this repo.

**Actors:**

- Admin MCP (InkMirage; later caller)
- `memnet-serve` / `TcpServeBridge.adminUsage`
- Agents — MUST NOT receive this tool

**Steps (model mandates):**

| Step | What happens | MUST NOT |
|------|----------------|----------|
| **1. Auth** | Compare caller token to env secret | Use CapsPolicy `MEMNET_CALLER`; return empty JSON when unset |
| **2. Peek** | Registry occupancy n/max; per-session rows/relations/TTL | `session_open` / close / load / save / mutate / purge / slide TTL |
| **3. Alias** | HMAC sid with admin token → `s_…` | Emit `mn_*`, node text, locators |
| **4. Process** | RSS, uptime, version, caps | Invent zeros for unmeasured fields |
| **5. Pressure** | Hard `@ERR` counts + Truncation reasons | Count leftover silent clips as Truncation |

## 4. Contrast (soft-pass kills)

| Not this | Why |
|----------|-----|
| MN-REQ-06.5 listed ids | `emitsRealSessionId=false` |
| Agent MCP tool | `onAgentMcp=false`; `adminUsageToolNested=false` |
| Unconfigured token → blank report | `@ERR: admin_unconfigured` |
| Product label on MCP `session_open` | `productLabelOnMcpSessionOpen=false`; open question `mcpProductLabelOpen` |
| SemVer bump | `noSemVerBump=true` |

## 5. Honesty

SysML locks admin vs agent split. CLI `--product` on `session open` is an optional gate-side hint. How an in-process MCP-only gate attaches a label without growing `session_open` remains **open** and unbuilt.
