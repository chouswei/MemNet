# GQL vs MemNet Layer — consideration (slim)

**Status:** **superseded stance** — agent wire decision locked in [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md). This file keeps the risk narrative and points the migration path.  
**Audience:** product developers.  
**Verdict (post ADR-001):** **adopt GQL as agent teach/wire** (openCypher-shaped, AgensGraph-compatible). **MemNet** remains the product name. **Layer** is **legacy** — map = migration crosswalk, not the 1.x teach surface.  
**Construct crosswalk SSOT:** [`layer-gql-map.md`](layer-gql-map.md) (Layer ↔ Node / Edge / Property / Label — now a **migration** map).  
**MUST NOT** invent a third peer dialect beside GQL (1.x) and Layer (legacy accept).

**Mission constraints (updated):** agent memory graph; **Write = display redefined on GQL** (bounded shaped subgraph / `pin_map`-class wrapper — not raw `MATCH` dumps); NODE | EDGE family retained in the store; ROADMAP 0.5 one-path (one remote, **one dialect teach = GQL**, one graph owner); tokens + factual accuracy; LLM-consumed wire.

**Sources:** [ISO/IEC 39075:2024 GQL](https://www.iso.org/standard/76120.html); [Wikipedia — Graph Query Language](https://en.wikipedia.org/wiki/Graph_Query_Language). Cypher-like ASCII is the industry prior LLMs already know.

---

## 1. Training prior vs mission fit

**Concede (now decisive):** ISO GQL / Cypher-like syntax is heavily represented in LLM training data. Teaching openCypher-shaped GQL as agent wire lowers invent-syntax errors and teach cost versus bespoke Layer.

**Mission continuity:** MemNet still optimises for bounded agent reads, Multitask shared sessions, and factual accuracy — **not** for unbounded DBA `RETURN` tables. Adopting GQL **does not** licence raw tabular dumps as the primary goldfish read. Write = display must be **redefined** (shaped subgraph / runtime view wrapper) — see ADR-001 Open question (recommended default: `pin_map`-class tool wrapping GQL with shaped emit).

**Prior “harvest without replacing Layer”** is **withdrawn** as the wire rule. GQL is now the agent surface; Layer stays only for migration / accept.

---

## 2. Why adopt (reversal)

| Option | Fit for MemNet (now) |
|--------|----------------------|
| **Watch** | Too thin |
| **Map only** | **Superseded** — was the 0.5 interim; insufficient once product chose GQL wire |
| **Borrow** | Absorbed into GQL teach conventions |
| **Adopt GQL as agent wire** (**chosen**) | Aligns training priors + AgensGraph buffer; Layer demoted to legacy |

GQL remains a **declarative property-graph query language**. MemNet remains the **agent memory product** (sessions, pin-map *concept*, MCP). Same family of graphs; agent job now speaks GQL under MemNet budgets.

**Replacement accepted (product decision):** use openCypher-shaped GQL **instead of** Layer as the LLM teach/wire. Layer grammar sources (`MemNetLayer.g4`) are **not** deleted in the first cut — see migration in ADR-001.

**Model alignment:** ontology and map stereotypes still speak **Node / Edge / Property / Label**. Agent events and MCP move toward GQL mutate + shaped pin-map-equivalent read. Detail: [`layer-gql-map.md`](layer-gql-map.md).

---

## 3. Layer ↔ GQL construct map (summary)

Full table: [`layer-gql-map.md`](layer-gql-map.md). Summary for **migration**:

| GQL / Cypher-family construct | Former Layer analogue | Migration note |
|-------------------------------|----------------------|----------------|
| Property graph (nodes + edges + properties) | NODE \| EDGE + `key=value` fields | Same broad model — keep |
| Directed / undirected edges | `--label-->` / `--label--` | Prefer Cypher ASCII on new teach |
| Node / edge labels | NODE kind; EDGE label | Encode as GQL labels / rel types |
| Properties | Fields after `;` | GQL property maps |
| Nested graphs (GQL forbids) | Stratified **view** budget | Keep view budget in MemNet runtime |
| `MATCH` path patterns | Bounded **`pin_map(anchor=…)`** | **Re-home:** shaped ego read, not free `MATCH` |
| Binding table + `RETURN` | Live pin map = graph lines | **Non-goal as primary read** — shaped subgraph instead |
| `CREATE` / `MERGE` | Mutate `+` / `~` / `-` | Teach openCypher-shaped writes |

**ASCII note:** new teach uses GQL/Cypher `(n:L)-[:R]->(m)`. Layer `[Id]` / bare `--label-->` remains **legacy accept** until M4.

---

## 4. Risks if we ignore GQL entirely

| Risk | Why it matters |
|------|----------------|
| **Interop gravity** | ISO GQL + SQL/PGQ dominate industry graph docs |
| **LLM / hiring priors** | Models default to Cypher; private dialect looks accidental |
| **Silent drift** | Contributors paste Cypher into fixtures without a written wire rule |

Adoption addresses these; **ignoring is closed**.

---

## 5. Risks if we adopt GQL naively (still live)

| Risk | Why it hurts MemNet |
|------|---------------------|
| **Tabular `RETURN` as primary** | Breaks redefined Write = display; inflates tokens |
| **Unbounded `MATCH`** | Fights goldfish / pin-map budget |
| **SCHEMA / type bloat** | Pulls first cut into DDL debates — deferred |
| **Dropping the buffer** | Thin Cypher relay ≠ MemNet product |
| **Dual teach Layer + GQL** | Breaks one dialect teach |

Mitigations: ADR-001 shaped-read recommendation; Layer legacy-only; AgensGraph still optional durable behind MemNet.

---

## 6. Stance for ROADMAP 0.5 / multi-layer Open

**GQL: agent wire adopted; Layer = legacy migration.**

- 0.5 delivery stays one-path (remote, dialect, graph owner) — **dialect teach = GQL**.
- Layer remains in-tree for accept / fixtures; not 1.x teach.
- Crosswalk [`layer-gql-map.md`](layer-gql-map.md) is the **migration map**.
- AgensGraph buffer stays deferred past one-path; agent and store now share GQL family — see [`agensgraph-buffer.md`](agensgraph-buffer.md).
- Decision SSOT: [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md).

---

## 7. Related

| Path | Role |
|------|------|
| [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md) | Accepted decision + migration + `pin_map` open question |
| [`layer-gql-map.md`](layer-gql-map.md) | Layer ↔ GQL construct map (**migration**) |
| [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md) | One-path plan; dialect teach = GQL |
| [`agensgraph-buffer.md`](agensgraph-buffer.md) | AgensGraph buffer; agent wire GQL-aligned |
| [`memnet-multi-layer.md`](memnet-multi-layer.md) | Layer ontology (legacy SSOT until GQL profile lands) |
| [`memnet-grammar-design.md`](memnet-grammar-design.md) | Shared-dialect spine (legacy) |
| [`../LLM-GUIDE.md`](../LLM-GUIDE.md) | Agent playbook (still Layer until M3) |
| [`../../sysml-models/models/connections.sysml`](../../sysml-models/models/connections.sysml) | Property-graph map stereotypes |
