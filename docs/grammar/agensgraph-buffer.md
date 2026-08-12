# AgensGraph buffer — MemNet working memory in front of durable GQL

**Status:** consideration / architecture sketch — **not** shipped behaviour. Wire stance updated by [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md).  
**Audience:** product developers.  
**Buffer thesis:** [AgensGraph](https://github.com/skaiworldwide-oss/agensgraph) (Postgres + property graph / openCypher / partial GQL) is a natural **durable** graph store; MemNet stays the **working-memory buffer** (bounded live pin-map *concept*, redefined Write = display) between that store and the LLM. Neither replaces the other.  
**Wire decision:** agent teach/wire = **GQL (openCypher-shaped)**. Layer is **legacy**, not the forward surface.

| Question | Answer |
|----------|--------|
| **Can** GQL be the LLM wire? | **Yes.** |
| **Should** it replace Layer for MemNet’s mission? | **Yes (product decision).** Brand stays MemNet; Layer → legacy migration. |
| Buffer + AgensGraph (durable) | **Strong mission fit**; **deferred** past ROADMAP 0.5 one-path. |

Mission constraints (updated): agent memory; Write = display **redefined** as bounded shaped GQL subgraph / `pin_map`-class wrapper; one dialect teach = GQL in 0.5+.

---

## 1. Adopt GQL as agent wire (reversal)

**Concede:** ISO GQL / Cypher-like syntax is in LLM training data — fewer invent-syntax errors and less teach cost when the agent speaks GQL.

**Can:** yes. LLMs already know Cypher-shaped ASCII; AgensGraph accepts openCypher (+ partial GQL).

**Should (for MemNet):** **yes as replacement of Layer teach** — explicit ADR-001. Reasons now decisive:

1. **Training prior + store alignment** outweigh maintaining a private Layer dialect.
2. **Same language family** on agent path and durable path reduces permanent translation tax.
3. **MemNet product value remains the buffer** — sessions, budgets, Multitask graph owner, shaped reads — not a thin anonymous Cypher relay.

**Still MUST NOT:**

- Treat raw tabular `MATCH`/`RETURN` as the primary agent goldfish read.
- Dual-teach Layer and GQL as peer 1.x surfaces.
- Drop the MemNet buffer and point agents straight at AgensGraph as the only story.
- Delete `MemNetLayer.g4` in the first cut (migration only).

**Where Layer still belongs:** legacy accept, fixtures, application notes until M3/M4; construct map [`layer-gql-map.md`](layer-gql-map.md).

---

## 2. Correct architecture (updated)

```text
  LLM  ←→  MemNet (GQL wire: shaped pin_map-class read / mutate; Layer legacy accept)
              │
              │  optional sync / hydrate / flush
              │  (openCypher / GQL; same family as agent wire)
              ▼
         AgensGraph (durable property graph)
```

| Path | Role |
|------|------|
| **LLM ↔ MemNet** | Always: goldfish loop; **GQL teach**; shaped bounded read (not raw dumps) |
| **MemNet → AgensGraph** | Optional **flush** of settled / durable subgraphs |
| **AgensGraph → MemNet** | Optional **hydrate** / re-anchor into a session pin budget |
| **LLM ↔ AgensGraph (direct)** | Out of default MemNet teach — DBA / app / escape hatch only |

Sync is an **engine or sidecar adapter**. Agent and store sharing GQL family is intentional; MemNet still owns budgets and session semantics.

---

## 3. Why the buffer still fits

| Surface | Job |
|---------|-----|
| **LLM** | Turn reasoning from bounded shaped graph text; mutate in openCypher-shaped GQL |
| **MemNet** | Agent working memory — session graph; redefined Write = display |
| **AgensGraph** | Durable multi-model DB — ACID, SQL + openCypher (+ partial GQL) |

MemNet’s mission remains “between LLM call pipelines and data search.” AgensGraph is a concrete persistence/search backend. GQL on the LLM side **does not** remove the need for pin budgets.

---

## 4. What stays where

| Stays in **MemNet** | Stays in **AgensGraph** |
|---------------------|-------------------------|
| Live pin-map-class slice (anchor, depth, view budget) | Full graph history and large neighbourhoods |
| Session / mission working set (`TSK_*`, turn state) | Cross-session durable domain graph |
| Shaped subgraph emit + gated mutate | Unconstrained analytics Cypher, SQL, triggers |
| Multitask shared session on one MemNet owner | Multi-client ACID writes, backups, PostGIS, etc. |
| Token-shaped ego reads | Multi-hop search, unlabelled scans |

**MUST NOT** dump AgensGraph `RETURN` tables into the agent as primary read.

---

## 5. GQL map stance (agent + store)

Construct crosswalk (migration): [`layer-gql-map.md`](layer-gql-map.md). Stance: [`gql-consideration.md`](gql-consideration.md). Decision: ADR-001.

| Construct | Where it lives |
|-----------|----------------|
| Property graph NODE \| EDGE | Both — same family |
| openCypher-shaped agent mutate | **MemNet** agent wire (1.x teach) |
| Bounded `pin_map`-class shaped read | **MemNet** (wraps GQL; see ADR-001 recommendation) |
| Unbounded path algebra / analytic `RETURN` | **AgensGraph** / tooling |
| Layer ASCII `[Id]` / `--label-->` | **Legacy** accept / migration only |

---

## 6. Risks

| Risk | Mitigation |
|------|------------|
| **Naive tabular wire** | ADR-001: shaped subgraph / `pin_map` wrapper default |
| **Two writers** | LLM mutates MemNet; durable flush single-writer. Aligns with ROADMAP one MemNet graph owner. |
| **Sync lag / identity drift** | Stable external keys; adapter locator map; settle before flush. |
| **Token blow-up** | Hydrate into pin budget only; never paste full query tables. |
| **Scope creep into 0.5** | Buffer adapter = Open / post one-path. Ship one remote + GQL teach direction first. |

---

## 7. Stance for ROADMAP / Open

- **Replacement:** **yes** — GQL **replaces Layer as agent teach/wire** (ADR-001).  
- **Buffer:** strong mission fit; AgensGraph optional durable store behind MemNet.  
- **0.5:** one dialect teach = GQL; Layer = legacy; no AgensGraph sync required to ship one-path.  
- **Later:** optional adapter (hydrate / flush); same GQL family end-to-end.

---

## 8. Related

| Path | Role |
|------|------|
| [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md) | Accepted wire decision + migration |
| [`gql-consideration.md`](gql-consideration.md) | Stance narrative (adopt GQL; Layer legacy) |
| [`layer-gql-map.md`](layer-gql-map.md) | Layer ↔ GQL map (migration) |
| [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md) | One-path plan |
| [`memnet-multi-layer.md`](memnet-multi-layer.md) | Layer ontology (legacy until GQL profile) |
| [`../LLM-GUIDE.md`](../LLM-GUIDE.md) | Agent playbook (Layer until M3) |
| [AgensGraph](https://github.com/skaiworldwide-oss/agensgraph) | Durable Postgres + property/openCypher graph |
