# GQL-wire model exam (post ADR-001 nesting)

**Status:** model exam after SysML / grammar nesting pass.  
**Audience:** product developers.  
**Date:** 2026-08-12.  
**Scope:** conceptual + SysML model only — not engine/MCP implementation.

**Decision SSOT:** [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md).  
**Nesting SSOT:** [`../../sysml-models/README.md`](../../sysml-models/README.md), [`../../sysml-models/outputs/system-design-notes.md`](../../sysml-models/outputs/system-design-notes.md).  
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
│   │   │     └── TierACodec               ← LEGACY Layer accept
│   │   ├── LocalIpcGateway
│   │   └── TcpServeBridge
│   └── CliFacade
├── MemNetMcpServer
├── DurableBuffer → AgensGraphAdapter      ← roadmap
├── PinMapRoadmap
└── MultitaskOperatingModel
```

Ontology items (first-class in `MemNetConnections`): Node, Edge, Property, Label, BindRelationship, RelationRelationship, LawOnNode, PortIncidence; wire items GqlWireBatch, ShapedSubgraph, LegacyLayerBatch.

---

## Exam checklist

| Question | Verdict | Notes |
|----------|---------|-------|
| **GQL-as-wire vs Layer-legacy unambiguous?** | **Pass** | `GqlCodec` + `GqlWireBatch` are primary; `TierACodec` / `LegacyLayerBatch` / `TierAFlow` labelled LEGACY; ADR-001 + ROADMAP + connections header agree. |
| **Write=display / shaped pin_map located correctly?** | **Pass** | `PinMapShapedRead` + `ShapedSubgraph` / `LivePinMap`; docs forbid raw `RETURN` as primary read; MN-REQ-08.9 updated. |
| **Dual EDGE / law / ports without smuggling Layer teach?** | **Pass with caveat** | Model uses `BindRelationship` / `RelationRelationship`, `LawOnNode`, `PortIncidence` as GQL-compatible items. Caveat: M1 wire profile must still freeze endpoint encoding (port properties vs synthetic nodes); until then Layer fixtures remain the richest *examples*, but not 1.x teach. |
| **Gaps / contradictions / over-nesting?** | **Issues (non-blocking)** | See below. |

---

## Issues (track, do not block M1)

1. **As-is Python still Layer-primary** — expected until M2; model/docs labelled target vs as-is. Skills / `LLM-GUIDE` still Layer-first (M3).
2. **AgentMemory nested only under InProcessEngine** — CLI/TCP paths conceptually share the same registry; SysML does not yet show a single shared `AgentMemory` instance across transport modes (doctrine says one graph owner; composite wiring is approximate).
3. **PortIncidence encoding open** — intentional M1 open; case study shows a concrete property-bag convention, not a frozen profile.
4. **HousekeepSettle `statsOut` typed as GqlWireOutPort** — may be too strong; stats could stay envelope/structured. Minor.
5. **Slight double conceptual layer** — `AgentMemory` → `SessionLifecycle` → leaves is clear; `MemNetCoreLibrary` + `TransportBoundary` adds one more hop — acceptable for transport vs memory separation, not over-nested.

---

## Overall verdict

**Pass** for model clarity after nesting: GQL is the primary agent wire in the SysML/conceptual model; Layer is unambiguously legacy; shaped `pin_map` owns redefined Write = display; dual EDGE and law/ports are relocated into GQL-compatible constructs without deleting the need.

**Next:** implement **M1** (GQL wire profile + shaped-read contract), then M2 engine/MCP.

---

## Related

| Path | Role |
|------|------|
| [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md) | Wire decision |
| [`layer-gql-map.md`](layer-gql-map.md) | Migration crosswalk |
| [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md) | One-path; M1 next |
| [`../application-notes/examples/inverting-amplifier-gql-case-study.md`](../application-notes/examples/inverting-amplifier-gql-case-study.md) | Domain case study |
| [`../../sysml-models/models/deploy.sysml`](../../sysml-models/models/deploy.sysml) | Nested parts |
| [`../../sysml-models/models/connections.sysml`](../../sysml-models/models/connections.sysml) | Ontology + ports |
