# AgensGraph buffer — durable graph behind shared LLM memory

**Status:** **planned M2.5** — architecture sketch; **not** shipped behaviour.  
**Audience:** product developers.  
**Promotion:** user direction 2026-08-13 — durable online GQL store adapter is the **next product notch after M2** (engine/MCP GQL). Order: M1 → M2 → **M2.5** → M3. See [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md).

**Product framing (2026-08-13):** MemNet is **shared working memory for LLMs** (multi-agent / Multitask sessions; goldfish re-read via shaped `pin_map`; gated mutate). A MemNet **session** can be SSOT for a mission / that shared memory (“SOMETHING”): handoff between LLMs = deliver **session id** (+ anchors / write scope); peers **re-pin_map** — do **not** receive a graph dump in chat. Chat is never SSOT ([`../multi-agent-sessions.md`](../multi-agent-sessions.md)). [AgensGraph](https://github.com/skaiworldwide-oss/agensgraph) (Postgres + property graph / openCypher / partial GQL) is the **durable / backing** graph **behind** sessions — it does **not** replace the session handle for agent handoff, and is not the default agent teach surface. **MUST NOT** reframe MemNet as a Cypher proxy to AgensGraph.

**Wire:** agent teach = **GQL only** ([`gql-wire-profile.md`](gql-wire-profile.md)). No Layer / Tier A path.

| Question | Answer |
|----------|--------|
| **Can** GQL be the LLM wire? | **Yes.** |
| **Should** it be the only agent dialect? | **Yes** (ADR-001 + supersession). |
| MemNet role | **Shared working memory** for LLMs (sessions, budgets, Multitask, mint/`NEW`, MutateGate). |
| Session role | Mission / shared-memory **SSOT handle**; handoff = session id (+ anchors / scope); peers re-`pin_map`. |
| AgensGraph role | **Durable backing** behind sessions; hydrate into / flush from MemNet (**M2.5**) — not the handoff handle. |

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
| **LLM ↔ MemNet** | Shared memory via **session**; goldfish `pin_map`; GQL teach; gated mutate |
| **LLM → LLM handoff** | Pass **session id** (+ anchors / write scope); peer re-`pin_map` — not a chat graph dump |
| **MemNet → AgensGraph** | Flush settled / durable subgraphs out of the session buffer |
| **AgensGraph → MemNet** | Hydrate into a session pin budget (ego-bounded) |
| **LLM ↔ AgensGraph (direct)** | **Out of default MemNet teach** (no agent Bolt / driver as goldfish or handoff path) |

---

## M2.5 scope (sketch)

| Concern | Plan |
|---------|------|
| **Hydrate** | Pull a durable subgraph into the live session under pin / depth / view budget |
| **Flush** | Push settled or explicitly durable pins from MemNet into AgensGraph |
| **Connection** | Store URL / credentials via env (e.g. `MEMNET_AGENSGRAPH_*` placeholders) — not hardcoded secrets |
| **Sync owner** | **One** owner process (MemNet serve / adapter) owns hydrate+flush — **MUST NOT** dual-write |
| **Dialect** | Same openCypher-family GQL as agent wire (CIP / oC9 family; MemNet-gated subset); no Layer revival |

### Out of M2.5 scope

| MUST NOT | Why |
|----------|-----|
| Teach **LLM ↔ AgensGraph direct** (agent Bolt / raw driver) as default | Breaks shared MemNet memory / goldfish / Multitask owner |
| Use durable store (or chat dump) as agent **handoff** instead of session id | Session is the SSOT handle; peers re-`pin_map` |
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
| [`../multi-agent-sessions.md`](../multi-agent-sessions.md) | Session SSOT; handoff by session id; chat never SSOT |
