# Layer ↔ GQL construct map

**Status:** map / durable-side vocabulary — **not** agent teach, **not** shipped sync.  
**Audience:** product developers, SysML / adapter authors.  
**Wire rule:** agent I/O stays **Layer** (Write = display; `pin_map`; dual EDGE; law on NODE). ISO GQL / Cypher belong on the **durable store / AgensGraph adapter** side.  
**SSOT for stance:** [`gql-consideration.md`](gql-consideration.md). This file is the **construct crosswalk** only.

---

## 1. Same family, different job

| Side | Job | Vocabulary |
|------|-----|------------|
| **Agent wire** | Bounded live pin map + mutate | Layer lines (`NODE` \| `EDGE`) |
| **Store / map** | Durable property graph + optional sync | GQL / openCypher / AgensGraph |

Both are **property graphs** (nodes, relationships, properties, labels, direction). MemNet does **not** teach `MATCH` / `RETURN` / `MERGE` as agent ops.

---

## 2. Construct map (Layer ↔ GQL)

| GQL / property-graph construct | MemNet Layer analogue | Adapter note |
|--------------------------------|----------------------|--------------|
| **Graph** (named property graph) | Session graph (`GraphStore`) | One mission session ↔ one working graph; durable graph optional behind sync |
| **Node** | **NODE** line: `KIND [Id] ; key=value ; …` | Kind ≈ primary label; id ≈ stable key |
| **Relationship / edge** | **EDGE** line: `Eid [src] --label--> [dst] ; …` | First-class row; dual grain (bind vs relation) is MemNet-only |
| **Node label(s)** | NODE **kind** (`CST`, …) + thin `role=` | Prefer single kind; avoid multi-label zoo on the wire |
| **Relationship type** | EDGE **label** (`bind`, `knows`, …) | Bind teach `bind` only; relation = open `IDENT` sense |
| **Property** | Field after `;` (`key=value`) | Omit defaults on wire; no nested graph-valued properties |
| **Directed edge** | `--label-->` | Primary teach |
| **Undirected edge** | `--label--` | Non-directed (no arrowheads) |
| **Bidirectional mark** | `<--label-->` | Accept; demote teach (≠ undirected) |
| **Endpoint / incident** | `[Id]` or `[Id.port]` inside brackets | Port grain = MemNet bind; bare id = relation |
| **Path** (pattern walk) | Bounded **`pin_map(anchor=…)`** ego slice | **Not** general GQL path patterns on the agent wire |
| **Variable-length / shortest path** | `query_walk` / depth caps (product ops) | Store-side path algebra OK; keep out of Layer teach |
| **Binding table + `RETURN`** | Live pin map = **same graph lines** as mutate | **Non-analogue** — no tabular RETURN as primary read |
| **`MATCH` / `OPTIONAL MATCH`** | Re-anchor + second `pin_map` | **Non-analogue** — no pattern matcher as agent dialect |
| **`INSERT` / `CREATE` / `MERGE`** | Mutate `+` / `~` / `-` (`NEW` mint) | Upsert spirit partial; **not** GQL MERGE syntax on wire |
| **Graph type / DDL / schema** | Session `SCHEMA` / TagMap registry | SCHEMA vocab freeze deferred; no GQL DDL teach in 0.5 |
| **Nested graph / graph-as-property** | Stratified **view** (`shell` / `interior`) | Both reject nesting-as-data; MemNet uses view budget |
| **Active graph / table / record** | Session + pin-map slice | No binding-table machine on the agent path |

---

## 3. Dual EDGE vs plain GQL relationships

GQL treats one relationship kind as typed directed/undirected links. MemNet keeps **one EDGE primitive** with **two endpoint grains**:

| Grain | Endpoints | GQL-ish reading | Layer teach |
|-------|-----------|-----------------|-------------|
| **Bind** | Both `[Node.port]` | Relationship whose ends are port-qualified incidences | Label **`bind`** only |
| **Relation** | Both bare `[NodeId]` | Ordinary node–node relationship | Label = sense (`knows`, …) |

Adapters **MUST** preserve grain (or encode port incidence in durable keys). **MUST NOT** flatten bind into chart labels on the agent wire.

---

## 4. ASCII conflict (do not harmonise)

| Family | Nodes | Relationships |
|--------|-------|---------------|
| GQL / Cypher | `(n:Label)` | `[r:TYPE]` |
| MemNet Layer | `KIND [Id]` | bare `--label-->` between `[…]` endpoints |

Layer puts **ids in `[…]`** and holds `()` free. **MUST NOT** retarget agent teach toward Cypher parentheses.

---

## 5. Law on NODE (MemNet-only overlay)

| Concern | Where it lives |
|---------|----------------|
| Constitutive / causal **law** | NODE field `law=` (LaTeX) — **never** on EDGE |
| Ideal continuity on bind | Implied by port↔port bind; not EDGE `law=` |
| GQL analogue | Property (or related node props) — **not** a GQL clause on the wire |

Property-graph stores may persist `law=` as a node property; agents still read/write Layer lines.

---

## 6. SysML / model alignment

Product SysML (`sysml-models/`) names internal records **NODE** \| **EDGE** and agent items as Layer/Tier A batches. Map stereotypes in `MemNetConnections` document the GQL-side reading (**Node**, **Edge**, **Property**, **Label**) for durable/adapter authors. **MUST NOT** model `MATCH`/`RETURN` as agent behaviour events.

---

## 7. Related

| Path | Role |
|------|------|
| [`gql-consideration.md`](gql-consideration.md) | Stance: map, not teach; risks; replacement rejected |
| [`agensgraph-buffer.md`](agensgraph-buffer.md) | Durable AgensGraph; GQL store-side only |
| [`memnet-multi-layer.md`](memnet-multi-layer.md) | Layer ontology SSOT |
| [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md) | One-path; model GQL-aligned (map); wire stays Layer |
| [`../../sysml-models/models/connections.sysml`](../../sysml-models/models/connections.sysml) | Property-graph map stereotypes |
