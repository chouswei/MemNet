# AgensGraph as durable store — MemNet as pin-map buffer

**Status:** consideration / architecture sketch — **not** shipped behaviour.  
**Audience:** product developers.  
**Thesis:** [AgensGraph](https://github.com/skaiworldwide-oss/agensgraph) (Postgres + property graph / openCypher / partial GQL) is a natural **durable** graph store; MemNet stays the **working-memory buffer** (bounded live pin map, Write = display) between that store and the LLM. Neither replaces the other.  
**Verdict (mission):** **strong fit.**  
**Verdict (0.5 product):** **conditional / deferred** — optional sync adapter only after ROADMAP one-path (one remote, one dialect teach, one MemNet graph owner). **MUST NOT** teach Cypher/GQL as agent wire.

---

## 1. Why strong fit

| Layer | Job | Surface |
|-------|-----|---------|
| **LLM** | Turn reasoning | Reads bounded pin-map text; writes mutate lines |
| **MemNet** | Agent working memory | Session graph; `pin_map` / `add` / `update`; Layer dialect |
| **AgensGraph** | Durable multi-model DB | ACID Postgres + graph labels; SQL + openCypher (+ partial GQL) |

MemNet’s mission is already “between LLM call pipelines and data search.” AgensGraph is a concrete **search / persistence** backend: enterprise transactions, relational+graph coexistence, indexes, bulk load — not an LLM turn dialect. Putting MemNet in the middle preserves Write = display and token-bounded ego slices while leaving long-lived topology and analytics where they belong.

---

## 2. Architecture sketch

```text
  LLM  ←→  MemNet MCP (pin_map / mutate / session)
              │
              │  optional sync / hydrate / flush
              │  (adapter owns mapping; not agent wire)
              ▼
         AgensGraph (durable property graph)
```

| Path | Role |
|------|------|
| **LLM ↔ MemNet** | Always: goldfish loop; Layer lines only |
| **MemNet → AgensGraph** | Optional **flush** of settled / durable subgraphs |
| **AgensGraph → MemNet** | Optional **hydrate** / re-anchor into a session pin budget |
| **LLM ↔ AgensGraph direct** | Out of MemNet teach — DBA / app / AgensGraph-AI tooling |

Sync is an **engine or sidecar adapter**, not a third teach dialect and not a second MCP story for agents.

---

## 3. What stays where

| Stays in **MemNet** | Stays in **AgensGraph** |
|---------------------|-------------------------|
| Live pin-map slice (anchor, depth, view budget) | Full graph history and large neighbourhoods |
| Session / mission working set (`TSK_*`, turn state) | Cross-session durable domain graph |
| Write = display mutate (`+` / `~` / `-`, `NEW` mint) | Cypher/`MERGE`, SQL, constraints, triggers |
| Multitask shared session on one MemNet owner | Multi-client ACID writes, backups, PostGIS, etc. |
| Token-shaped ego reads | Analytics, multi-hop search, unlabelled scans (planner) |

**MUST NOT** dump AgensGraph query result tables into the agent as primary read — that fights Write = display (same non-analogue as GQL `RETURN`).

---

## 4. GQL **map** stance (not teach as wire)

This buffer story **uses** the GQL map stance in [`gql-consideration.md`](gql-consideration.md):

| Construct | Where it lives |
|-----------|----------------|
| Property graph NODE \| EDGE | Both — same family |
| `MATCH` / path algebra / binding `RETURN` | **AgensGraph** (and tooling) only |
| Bounded `pin_map(anchor=…)` | **MemNet** agent wire only |
| Label / property crosswalk | Adapter map (ids, kinds, edge labels) — documented, not taught as Layer syntax |
| ASCII `(n)-[:R]->(m)` vs MemNet `[Id]` / `--label-->` | **Do not harmonise** agent wire toward Cypher parentheses |

AgensGraph (and ISO GQL / openCypher) remain the **durable query language** story. Layer remains the **only 1.x agent teach surface.** Mapping happens in the sync adapter.

---

## 5. Risks

| Risk | Mitigation |
|------|------------|
| **Two writers** | One **authoritative write path per concern**: LLM mutates MemNet; durable flush is single-writer (or explicit conflict policy). Do not dual-write the same mission from HTTP MCP *and* TCP serve *and* AgensGraph clients without an owner. Aligns with ROADMAP “one graph owner” for the MemNet side. |
| **Sync lag / identity drift** | Stable external keys in AgensGraph; MemNet session ids may be ephemeral. Adapter records locator map; settle before flush. |
| **Token blow-up** | Hydrate only into pin budget; never “SELECT * then paste.” Prefer re-anchor + bounded `pin_map`. |
| **Third dialect** | Agents never see Cypher/GQL in skills as wire. ROADMAP 0.5 one-path unchanged. |
| **Scope creep into 0.5** | Buffer + AgensGraph adapter = **Open / post one-path**. Ship one-path (remote, Layer teach, MemNet store owner) first. |

---

## 6. Stance for ROADMAP / Open

- **Mission:** strong fit — MemNet as working-memory buffer; AgensGraph as optional durable graph DB.  
- **0.5:** do not implement or teach AgensGraph sync as part of one-path.  
- **Later:** optional adapter (hydrate / flush) under grammar Open; keep GQL/Cypher off agent wire.

---

## 7. Related

| Path | Role |
|------|------|
| [`gql-consideration.md`](gql-consideration.md) | GQL vs Layer: map, not teach as wire |
| [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md) | One-path plan; Open pointer |
| [`memnet-multi-layer.md`](memnet-multi-layer.md) | Layer / stratified pin maps |
| [`../LLM-GUIDE.md`](../LLM-GUIDE.md) | Agent playbook (MemNet-only surface) |
| [AgensGraph](https://github.com/skaiworldwide-oss/agensgraph) | Durable Postgres + property/openCypher graph |
