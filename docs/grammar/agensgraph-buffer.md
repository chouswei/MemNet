# AgensGraph buffer — durable graph behind shared LLM memory

**Status:** **planned M2.5** — architecture sketch; **not** shipped behaviour.  
**Audience:** product developers.  
**Promotion:** user direction 2026-08-13 — durable online GQL store adapter is the **next product notch after M2** (engine/MCP GQL). Order: M1 → M2 → **M2.5** → M3. See [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md).

**Product framing (2026-08-13):** MemNet is **shared working memory for LLMs** (multi-agent / Multitask sessions; goldfish re-read via shaped `pin_map`; gated mutate). [AgensGraph](https://github.com/skaiworldwide-oss/agensgraph) (Postgres + property graph / openCypher / partial GQL) is the **durable / backing** graph **behind** that shared memory — not a replacement for MemNet and not the default agent teach surface. **MUST NOT** reframe MemNet as a Cypher proxy to AgensGraph.

**Wire:** agent teach = **GQL only** ([`gql-wire-profile.md`](gql-wire-profile.md)). No Layer / Tier A path.

| Question | Answer |
|----------|--------|
| **Can** GQL be the LLM wire? | **Yes.** |
| **Should** it be the only agent dialect? | **Yes** (ADR-001 + supersession). |
| MemNet role | **Shared working memory** for LLMs (sessions, budgets, Multitask, mint/`NEW`, MutateGate). |
| AgensGraph role | **Durable backing** store; hydrate into / flush from MemNet (**M2.5**). |

---

## Architecture

```text
  LLM(s)  <-->  MemNet = shared working memory
                  (GQL wire: shaped pin_map / gated mutate)
                    |
                    |  hydrate / flush (one sync owner)
                    v
               AgensGraph = durable backing graph
```

| Path | Role |
|------|------|
| **LLM ↔ MemNet** | Shared memory; goldfish loop; GQL teach; shaped bounded read; mint / MutateGate |
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
| Teach **LLM ↔ AgensGraph direct** (agent Bolt / raw driver) as default | Breaks shared MemNet memory / goldfish / Multitask owner |
| Thin Cypher-relay-only (drop MemNet; “just a proxy”) | Collapses product value — MemNet is the shared memory |
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
