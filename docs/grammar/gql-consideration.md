# GQL vs MemNet Layer — consideration (slim)

**Status:** consideration only — **not** a wire dialect, **not** shipped behaviour.  
**Audience:** product developers.  
**Verdict (0.5):** **map** — keep ISO GQL on the radar; map constructs to Layer analogues or deliberate non-analogues. **Do not teach GQL as agent wire.**  
**Later (post one-path):** selective **borrow** of naming / mental models where Layer already aligns; **partial adopt** only if a future export/interop path is justified. **MUST NOT** invent a third teach dialect.

**Mission constraints (unchanged):** agent memory graph; Write = display; bounded `pin_map`; NODE | EDGE only; Layer = 1.x teach; ROADMAP 0.5 one-path (one remote, one dialect teach, one graph owner); tokens + factual accuracy; LLM-consumed wire — not DBA tooling.

**Sources:** [ISO/IEC 39075:2024 GQL](https://www.iso.org/standard/76120.html) (property-graph query language); overview [Wikipedia — Graph Query Language](https://en.wikipedia.org/wiki/Graph_Query_Language). Cypher-like ASCII patterns are the industry prior LLMs already know.

---

## 1. Training prior vs mission fit

**Concede:** ISO GQL / Cypher-like syntax is heavily represented in LLM training data. If the agent spoke GQL, invent-syntax errors would likely fall and teach cost would drop versus a bespoke Layer dialect.

**Counter (mission):** MemNet optimises for Write = display, bounded `pin_map`, dual EDGE, and law-on-NODE — **not** for matching training priors. Familiar ≠ fit. Tabular `MATCH` / `RETURN` fights token budgets and factual accuracy on agent turns.

**Harvest the prior without replacing Layer:** keep GQL/Cypher **behind** the sync adapter (AgensGraph side). Optional later: LLM-assisted sync that translates Layer ↔ Cypher using that prior — the agent still only sees Layer / `pin_map`.

**MUST NOT:** treat “the LLM already knows GQL” as a reason to drop Layer as agent wire for 0.5 (or as the 1.x surface).

---

## 2. Why map (not ignore, not adopt)

| Option | Fit for MemNet |
|--------|----------------|
| **Watch** | Too thin — ISO + Cypher priors will keep reshaping tooling and LLM defaults |
| **Map** (chosen for 0.5) | Honest crosswalk; protects one-path teach; documents deliberate non-analogues |
| **Borrow** | Later — reuse *ideas* (direction marks, label-as-type) without GQL clauses on the wire |
| **Partial adopt** | Only with an explicit interop/export story; never as a second agent surface in 0.5 |

GQL is a **declarative database query language** (SQL’s cousin for property graphs). MemNet Layer is an **LLM shared dialect** for the same shapes on read and write. Same family of graphs; different job.

**Replacement rejected:** using GQL/Cypher **instead of** Layer as the LLM wire is **technically possible** but **wrong for MemNet’s mission**. GQL `RETURN` tables are not Write = display pin maps; a DBA query language is not an agent mutate dialect (dual EDGE, law-on-NODE, view budgets); and speaking store dialect directly **collapses** the MemNet-as-buffer thesis into a thin proxy. **MUST NOT** replace Layer teach with GQL for 0.5 (or as the 1.x agent surface). GQL belongs on the durable store / sync-adapter side — see [`agensgraph-buffer.md`](agensgraph-buffer.md).

---

## 3. Consideration matrix

| GQL / Cypher-family construct | MemNet analogue | Deliberate non-analogue? |
|-------------------------------|-----------------|---------------------------|
| Property graph (nodes + edges + properties) | NODE \| EDGE + `key=value` fields | No — same broad model |
| Multigraph (many edges between same pair) | Multiple EDGE rows / ids | No |
| Directed / undirected edges | `--label-->` / `--label--` (bi-directed `<--label-->` accept, demote teach) | No — already aligned in Layer |
| Node / edge labels (types / tags) | NODE kind (`CST`, …); EDGE label (`bind`, `knows`, …); thin `role=` | Partial — MemNet avoids label zoo; open `IDENT` on relations, not multi-label sets |
| Properties on elements | Fields after `;` | No — but MemNet omits defaults; no nested graph-valued properties |
| **Nested graphs / graph-as-property** (GQL forbids) | Stratified **view** (`shell` / `interior`), not nested store graphs | **Aligned non-analogue:** both reject nesting-as-data; MemNet uses view budget instead of chapter kinds |
| `MATCH` path patterns `(n:L)-[:R]->(m)` | Bounded **`pin_map(anchor=…)`** ego slice | **Yes** — no general pattern matcher on the agent wire |
| Variable-length / shortest / cheapest paths | `query_walk` / depth caps (product ops) | **Yes** — not GQL path algebra; keep out of teach dialect |
| Binding table + `RETURN` columns | Live pin map = **graph lines** (Write = display) | **Yes** — tabular RETURN fights the mission |
| `OPTIONAL MATCH` / joins across patterns | Re-anchor + second `pin_map`; edges for membership | **Yes** — no outer-join clause teach |
| Active graph / active table / active record | Session graph + pin-map slice (no binding table) | **Yes** |
| `INSERT` / `CREATE` / `MERGE` | Mutate `+` / `~` / `-` (mint `NEW`, known ids on patch) | Partial — upsert semantics exist; **not** GQL `MERGE` syntax |
| Schema / graph types / DDL | Session `SCHEMA` map (registry); SCHEMA vocab freeze deferred | **Yes for 0.5** — no GQL schema teach; avoid allow-list bloat |
| SQL/PGQ-style table projection | Out of mission | **Yes** |
| Procedural traversal (Gremlin-like) | Out of GQL *and* MemNet teach | **Yes** |

**ASCII conflict note:** GQL/Cypher puts nodes in `(…)` and relationships in `[…]`. MemNet Layer puts **ids in `[…]`** and keeps `()` free/held. Do **not** “harmonise” toward Cypher parentheses on the wire — that would break Layer and confuse Write = display.

---

## 4. Risks if we ignore GQL entirely

| Risk | Why it matters |
|------|----------------|
| **Interop gravity** | ISO GQL + SQL/PGQ become the default “graph query” story in industry docs and tools |
| **LLM / hiring priors** | Models and engineers default to `MATCH`/`RETURN` Cypher; unexplained divergence looks like ignorance |
| **Training-prior temptation** | “LLM already knows GQL” can be misread as licence to replace Layer — see §1 |
| **Silent drift** | Contributors may paste Cypher into fixtures or skills without a written non-analogue |
| **Missed free alignment** | Directed/undirected, no nested graphs, property-vs-topology split — we already rhyme; mapping records that on purpose |

Ignoring is not “staying pure”; it is leaving the crosswalk undocumented.

---

## 5. Risks if we adopt GQL naively

| Risk | Why it hurts MemNet |
|------|---------------------|
| **Third dialect** | ROADMAP 0.5 locks **one dialect teach** (Layer; Tier A = legacy alias). GQL-as-wire breaks that |
| **Tabular `RETURN`** | Binding tables are DBA/analytics I/O; they break Write = display and inflate tokens |
| **`MATCH` as primary read** | Unbounded pattern search fights bounded pin map and goldfish loop |
| **SCHEMA / type bloat** | GQL graph types + multi-label cardinality debates pull us into allow-lists we deferred |
| **Syntax collision** | `(node)` / `[rel]` vs MemNet `[Id]` / bare `--label-->` — dual ASCII art in one product |
| **Wrong audience** | GQL targets database applications; MemNet targets LLM turn I/O |
| **Prior ≠ mission** | Training familiarity does not deliver dual EDGE, law-on-NODE, or Write = display |

---

## 6. Stance for ROADMAP 0.5 / multi-layer Open

**GQL: consider / map, not teach as wire.**

- 0.5 delivery stays one-path (remote, dialect, graph owner) — unchanged.
- Layer remains the only 1.x teach surface.
- This doc is the SSOT crosswalk; refresh when ISO practice or Layer locks move.
- Optional later: **borrow** glossary phrases in contributor docs (“undirected edge”, “property graph”) without GQL keywords in agent skills; LLM-assisted Layer ↔ Cypher sync stays **adapter-side** ([`agensgraph-buffer.md`](agensgraph-buffer.md)).

---

## 7. Related

| Path | Role |
|------|------|
| [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md) | One-path plan; Open pointer |
| [`agensgraph-buffer.md`](agensgraph-buffer.md) | AgensGraph buffer; MUST NOT replace Layer with GQL as agent wire |
| [`memnet-multi-layer.md`](memnet-multi-layer.md) | Layer SSOT; §8 Open |
| [`memnet-grammar-design.md`](memnet-grammar-design.md) | Shared-dialect spine |
| [`../LLM-GUIDE.md`](../LLM-GUIDE.md) | Agent playbook (Layer teach) |
