# AgensGraph buffer — MemNet working memory in front of durable GQL

**Status:** **planned M2.5** — architecture sketch; **not** shipped behaviour.  
**Audience:** product developers.  
**Promotion:** user direction 2026-08-13 — durable online GQL store adapter is the **next product notch after M2** (engine/MCP GQL). Order: M1 → M2 → **M2.5** → M3. See [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md).  
**Buffer thesis:** [AgensGraph](https://github.com/skaiworldwide-oss/agensgraph) (Postgres + property graph / openCypher / partial GQL) is a natural **durable** graph store; MemNet stays the **working-memory buffer** (sessions, pin budgets, Multitask, mint/`NEW`, MutateGate; bounded shaped `pin_map`; redefined Write = display) between that store and the LLM.  
**Wire:** agent teach = **GQL only** ([`gql-wire-profile.md`](gql-wire-profile.md)). No Layer / Tier A path.

| Question | Answer |
|----------|--------|
| **Can** GQL be the LLM wire? | **Yes.** |
| **Should** it be the only agent dialect? | **Yes** (ADR-001 + supersession). |
| Buffer + AgensGraph (durable) | **Strong mission fit**; scheduled **M2.5** (right after M2). |

---

## Architecture

```text
  LLM  <-->  MemNet (GQL wire: shaped pin_map-class read / mutate)
               |
               |  hydrate / flush (one sync owner)
               v
          AgensGraph (durable property graph)
```

| Path | Role |
|------|------|
| **LLM ↔ MemNet** | Goldfish loop; GQL teach; shaped bounded read; mint / MutateGate |
| **MemNet → AgensGraph** | Flush settled / durable subgraphs out of the session buffer |
| **AgensGraph → MemNet** | Hydrate into a session pin budget (ego-bounded) |
| **LLM ↔ AgensGraph (direct)** | **Out of default MemNet teach** (no agent Bolt / driver as goldfish path) |

---

## M2.5 scope (sketch)

| Concern | Plan |
|---------|------|
| **Hydrate** | Pull a durable subgraph into the live session under pin / depth / view budget |
| **Flush** | Push settled or explicitly durable pins from MemNet into AgensGraph |
| **Connection** | Store URL / credentials via env (e.g. `MEMNET_AGENSGRAPH_*` placeholders) — not hardcoded secrets |
| **Sync owner** | **One** owner process (MemNet serve / adapter) owns hydrate+flush — **MUST NOT** dual-write |
| **Dialect** | Same openCypher-family GQL as agent wire; no Layer revival |

### Out of M2.5 scope

| MUST NOT | Why |
|----------|-----|
| Teach **LLM ↔ AgensGraph direct** (agent Bolt / raw driver) as default | Breaks MemNet buffer / goldfish / Multitask owner |
| Thin Cypher-relay-only (drop MemNet) | Collapses product value |
| Dual-write without a single sync owner | Two writers → split brain |
| Claim adapter shipped before M2.5 lands | Plan only until implemented |
| Revive Layer / Tier A | ADR-001 supersession |

---

## Related

| Path | Role |
|------|------|
| [`gql-wire-profile.md`](gql-wire-profile.md) | M1 wire SSOT; M2.5 boundary in §6 |
| [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md) | Decision; M2.5 in migration plan |
| [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md) | Phase order: M2 → M2.5 → M3 |
