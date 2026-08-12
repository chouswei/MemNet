# AgensGraph buffer — and why GQL must not replace Layer

**Status:** consideration / architecture sketch — **not** shipped behaviour.  
**Audience:** product developers.  
**Buffer thesis:** [AgensGraph](https://github.com/skaiworldwide-oss/agensgraph) (Postgres + property graph / openCypher / partial GQL) is a natural **durable** graph store; MemNet stays the **working-memory buffer** (bounded live pin map, Write = display) between that store and the LLM. Neither replaces the other.  
**Replacement proposal:** use GQL/Cypher as the LLM wire **instead of** MemNet Layer.  
**Verdicts:**

| Question | Answer |
|----------|--------|
| **Can** GQL be the LLM wire? | **Technically yes** — an agent can emit Cypher/GQL straight at AgensGraph. |
| **Should** it replace Layer for MemNet’s mission? | **No.** **MUST NOT** replace Layer teach with GQL as agent wire. |
| Buffer + AgensGraph (store-side only) | **Strong mission fit**; **deferred** past ROADMAP 0.5 one-path. |

Mission constraints (unchanged): agent memory; Write = display; bounded `pin_map`; Layer NODE \| EDGE as 1.x teach; one dialect teach in 0.5.

---

## 1. MUST NOT replace Layer with GQL as agent wire

**Concede:** ISO GQL / Cypher-like syntax is in LLM training data — fewer invent-syntax errors and less teach cost *if* the agent spoke GQL.

**Can:** yes. LLMs already know Cypher-shaped ASCII; AgensGraph accepts openCypher (+ partial GQL). Nothing stops a thin “run this query” MCP.

**Should (for MemNet):** **no as replacement.** Crisp reasons:

1. **Familiar ≠ fit.** MemNet optimises Write = display + bounded `pin_map` + dual EDGE + law-on-NODE — not training priors. Tabular `MATCH`/`RETURN` fights turn token budgets and accuracy.
2. **GQL `RETURN` tables ≠ Write = display.** Binding tables are DBA/analytics I/O. MemNet’s primary read is **graph lines** in the same shapes agents write — a bounded pin map, not columnar result sets.
3. **DBA query language ≠ agent mutate dialect.** Layer carries dual EDGE (bind / relation), law-on-NODE, view budgets (`shell` / `interior`), `NEW` mint, and goldfish re-read. GQL/`MATCH`/`MERGE` do not teach that contract; forcing them onto the agent collapses mission semantics into general graph SQL.
4. **Replacement collapses the buffer thesis.** If the LLM speaks store dialect directly, MemNet becomes a thin proxy — or disappears. The product value is the **working-memory buffer**, not a Cypher relay.
5. **ROADMAP 0.5 one dialect teach.** Layer is the 1.x surface; Tier A is legacy alias only. GQL-as-wire is a third dialect (or a hostile overwrite of Layer).

**Harvest the prior:** GQL/Cypher stay **behind** the adapter. Optional later: LLM-assisted Layer ↔ Cypher sync that uses the training prior — agent still only sees Layer / `pin_map`.

**MUST NOT:** use “LLM already knows GQL” as a reason to drop Layer as agent wire for 0.5.

**Where GQL does belong:** AgensGraph / durable store side; optional sync adapter that **maps** Layer ↔ property-graph rows; contributor crosswalk in [`gql-consideration.md`](gql-consideration.md). **Never** primary agent teach for 0.5.

---

## 2. Correct architecture (keep)

```text
  LLM  ←→  MemNet (Layer: pin_map / mutate / session)
              │
              │  optional sync / hydrate / flush
              │  (adapter owns GQL/Cypher; not agent wire)
              ▼
         AgensGraph (durable property graph)
```

| Path | Role |
|------|------|
| **LLM ↔ MemNet** | Always: goldfish loop; **Layer lines only** |
| **MemNet → AgensGraph** | Optional **flush** of settled / durable subgraphs |
| **AgensGraph → MemNet** | Optional **hydrate** / re-anchor into a session pin budget |
| **LLM ↔ AgensGraph (GQL direct)** | Out of MemNet teach — DBA / app / AgensGraph-AI tooling |

Sync is an **engine or sidecar adapter**, not a second teach dialect and not “GQL skills for agents.” Optional later: LLM-assisted translate Layer ↔ Cypher inside the adapter — harvest the training prior without putting GQL on the agent wire.

---

## 3. Why the buffer still fits (when Layer stays)

| Surface | Job |
|---------|-----|
| **LLM** | Turn reasoning from bounded pin-map text; mutate in Layer |
| **MemNet** | Agent working memory — session graph; Write = display |
| **AgensGraph** | Durable multi-model DB — ACID, SQL + openCypher (+ partial GQL) |

MemNet’s mission is already “between LLM call pipelines and data search.” AgensGraph is a concrete persistence/search backend. Keeping Layer on the LLM side preserves tokens and Write = display; GQL stays where it earns its keep.

---

## 4. What stays where

| Stays in **MemNet** | Stays in **AgensGraph** |
|---------------------|-------------------------|
| Live pin-map slice (anchor, depth, view budget) | Full graph history and large neighbourhoods |
| Session / mission working set (`TSK_*`, turn state) | Cross-session durable domain graph |
| Write = display mutate (`+` / `~` / `-`, `NEW` mint) | Cypher/`MERGE`, SQL, constraints, triggers |
| Multitask shared session on one MemNet owner | Multi-client ACID writes, backups, PostGIS, etc. |
| Token-shaped ego reads | Analytics, multi-hop search, unlabelled scans |

**MUST NOT** dump AgensGraph `RETURN` tables into the agent as primary read.

---

## 5. GQL map stance (store-side only)

Uses [`gql-consideration.md`](gql-consideration.md):

| Construct | Where it lives |
|-----------|----------------|
| Property graph NODE \| EDGE | Both — same family |
| `MATCH` / path algebra / binding `RETURN` | **AgensGraph** (and tooling) only |
| Bounded `pin_map(anchor=…)` | **MemNet** agent wire only |
| Label / property crosswalk | Adapter map — not Layer teach syntax |
| ASCII `(n)-[:R]->(m)` vs MemNet `[Id]` / `--label-->` | **Do not harmonise** agent wire toward Cypher parentheses |

---

## 6. Risks

| Risk | Mitigation |
|------|------------|
| **Replace Layer with GQL** | Rejected — see §1. Map only. |
| **Two writers** | LLM mutates MemNet; durable flush single-writer (or explicit conflict policy). Aligns with ROADMAP one MemNet graph owner. |
| **Sync lag / identity drift** | Stable external keys in AgensGraph; adapter locator map; settle before flush. |
| **Token blow-up** | Hydrate into pin budget only; never paste full query tables. |
| **Scope creep into 0.5** | Buffer adapter = Open / post one-path. Ship Layer teach + one remote first. |

---

## 7. Stance for ROADMAP / Open

- **Replacement:** **no** — GQL/Cypher **MUST NOT** replace Layer as agent wire.  
- **Buffer:** strong mission fit; AgensGraph optional durable store behind MemNet.  
- **0.5:** one dialect teach = Layer; no AgensGraph sync required to ship one-path.  
- **Later:** optional adapter (hydrate / flush); GQL remains store-side / map-doc only.

---

## 8. Related

| Path | Role |
|------|------|
| [`gql-consideration.md`](gql-consideration.md) | GQL vs Layer: map, not teach; replacement rejected |
| [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md) | One-path plan; Open pointer |
| [`memnet-multi-layer.md`](memnet-multi-layer.md) | Layer / stratified pin maps |
| [`../LLM-GUIDE.md`](../LLM-GUIDE.md) | Agent playbook (Layer teach) |
| [AgensGraph](https://github.com/skaiworldwide-oss/agensgraph) | Durable Postgres + property/openCypher graph |
