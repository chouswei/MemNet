# GQL-wire model exam (post ADR-001 nesting)

**Status:** model exam after SysML / grammar nesting pass.  
**Audience:** product developers.  
**Date:** 2026-08-12.  
**Scope:** conceptual + SysML model — not engine/MCP implementation.

**Decision SSOT:** [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md).  
**Wire profile SSOT:** [`gql-wire-profile.md`](gql-wire-profile.md).  
**Nesting:** [`../../sysml-models/README.md`](../../sysml-models/README.md).  
**Worked domain:** [`../application-notes/examples/inverting-amplifier-gql-case-study.md`](../application-notes/examples/inverting-amplifier-gql-case-study.md).

---

## Nesting outline (examined)

```text
MemNetSystem
├── MemNetCoreLibrary
│   ├── TransportBoundary
│   │   ├── InProcessEngine → AgentMemory → SessionLifecycle
│   │   │     ├── GraphStore
│   │   │     ├── GqlCodec                 ← 1.x primary wire
│   │   │     ├── PinMapShapedRead         ← shaped pin_map
│   │   │     ├── MutateGate
│   │   │     └── (legacy codecs → remove in M2)
│   │   ├── LocalIpcGateway
│   │   └── TcpServeBridge
│   └── CliFacade
├── MemNetMcpServer
├── DurableBuffer → AgensGraphAdapter      ← roadmap
├── PinMapRoadmap
└── MultitaskOperatingModel
```

---

## Exam checklist

| Question | Verdict | Notes |
|----------|---------|-------|
| **GQL-only wire unambiguous?** | **Pass** | Profile + ADR supersession: no Layer teach/accept. |
| **Write=display / shaped pin_map?** | **Pass** | `PinMapShapedRead` + shaped subgraph; no raw `RETURN` primary. |
| **Dual EDGE / law / ports frozen?** | **Pass** | `:bind` + `fromPort`/`toPort`; `law` on node — [`gql-wire-profile.md`](gql-wire-profile.md). |
| **Gaps?** | **M2** | As-is Python still old codec until M2; skills/app-note bodies until M3. |

---

## Overall verdict

**Pass** for model + M1 profile clarity: GQL is the only agent wire; shaped `pin_map` owns redefined Write = display.

**Next:** **M2** (engine/MCP GQL accept + shaped emit).

## Related

| Path | Role |
|------|------|
| [`gql-wire-profile.md`](gql-wire-profile.md) | M1 SSOT |
| [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md) | Decision |
| [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md) | Next: M2 |
| [`archive/README.md`](archive/README.md) | Quarantined Layer sources |
