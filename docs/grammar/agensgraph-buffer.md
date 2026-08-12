# AgensGraph buffer — MemNet working memory in front of durable GQL

**Status:** consideration / architecture sketch — **not** shipped behaviour.  
**Audience:** product developers.  
**Buffer thesis:** [AgensGraph](https://github.com/skaiworldwide-oss/agensgraph) (Postgres + property graph / openCypher / partial GQL) is a natural **durable** graph store; MemNet stays the **working-memory buffer** (bounded shaped `pin_map`, redefined Write = display) between that store and the LLM.  
**Wire:** agent teach = **GQL only** ([`gql-wire-profile.md`](gql-wire-profile.md)). No Layer / Tier A path.

| Question | Answer |
|----------|--------|
| **Can** GQL be the LLM wire? | **Yes.** |
| **Should** it be the only agent dialect? | **Yes** (ADR-001 + supersession). |
| Buffer + AgensGraph (durable) | **Strong mission fit**; **deferred** past ROADMAP 0.5 one-path. |

---

## Architecture

```text
  LLM  ←→  MemNet (GQL wire: shaped pin_map-class read / mutate)
              │
              │  optional sync / hydrate / flush
              ▼
         AgensGraph (durable property graph)
```

| Path | Role |
|------|------|
| **LLM ↔ MemNet** | Goldfish loop; GQL teach; shaped bounded read |
| **MemNet → AgensGraph** | Optional flush of settled / durable subgraphs |
| **AgensGraph → MemNet** | Optional hydrate into a session pin budget |
| **LLM ↔ AgensGraph (direct)** | Out of default MemNet teach |

**MUST NOT:** raw tabular `MATCH`/`RETURN` as primary goldfish; revive Layer teach; drop the MemNet buffer; dual-write without a single sync owner.

## Related

| Path | Role |
|------|------|
| [`gql-wire-profile.md`](gql-wire-profile.md) | M1 wire SSOT |
| [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md) | Decision |
| [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md) | One-path plan |
