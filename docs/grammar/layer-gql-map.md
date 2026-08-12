# Layer ↔ GQL construct map (migration)

**Status:** **migration crosswalk** — Layer is legacy agent wire; GQL (openCypher-shaped) is 1.x teach per [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md).  
**Audience:** product developers, SysML / adapter authors, migrators.  
**Wire rule:** agent I/O **adopts GQL**; Layer lines remain **accept / fixtures** until M4. ISO GQL / Cypher also remain the durable store vocabulary (AgensGraph).  
**SSOT for stance:** [`gql-consideration.md`](gql-consideration.md) + ADR-001. This file is the **construct crosswalk** for migration — not a licence to dual-teach.

---

## 1. Same family; teach side flipped

| Side | Job | Vocabulary |
|------|-----|------------|
| **Agent wire (1.x)** | Bounded shaped read + mutate | **GQL / openCypher-shaped** |
| **Agent wire (legacy)** | Prior Write = display lines | **Layer** (`NODE` \| `EDGE`) — migration only |
| **Store / map** | Durable property graph + optional sync | GQL / openCypher / AgensGraph |

Both are **property graphs**. MemNet **does** teach openCypher-shaped patterns as agent ops; it **MUST NOT** teach unbounded tabular `RETURN` as the primary goldfish read (ADR-001: shaped subgraph / `pin_map`-class wrapper).

---

## 2. Construct map (Layer → GQL migration)

| GQL / property-graph construct | MemNet Layer (legacy) | Migration note |
|--------------------------------|----------------------|----------------|
| **Graph** (named property graph) | Session graph (`GraphStore`) | One mission session ↔ one working graph |
| **Node** | **NODE** line: `KIND [Id] ; key=value ; …` | Kind → primary label; id → stable key / property |
| **Relationship / edge** | **EDGE** line: `Eid [src] --label--> [dst] ; …` | Rel type = former label; preserve dual grain in properties or endpoint encoding |
| **Node label(s)** | NODE **kind** + thin `role=` | Prefer single primary label; avoid label zoo |
| **Relationship type** | EDGE **label** (`bind`, `knows`, …) | `bind` vs open relation sense — encode explicitly |
| **Property** | Field after `;` | GQL property map; omit defaults on wire |
| **Directed edge** | `--label-->` | `(a)-[:label]->(b)` |
| **Undirected edge** | `--label--` | Cypher undirected form |
| **Bidirectional mark** | `<--label-->` | Prefer two directed edges or documented convention |
| **Endpoint / incident** | `[Id]` or `[Id.port]` | Port grain → qualified property / synthetic node — **open in GQL profile (M1)** |
| **Path** (pattern walk) | Bounded **`pin_map(anchor=…)`** | Re-home as shaped ego tool wrapping GQL |
| **Variable-length / shortest path** | `query_walk` / depth caps | Store-side OK; keep out of default agent teach |
| **Binding table + `RETURN`** | Live pin map = **same graph lines** | **Do not** use raw tables as primary read — shaped subgraph emit |
| **`MATCH` / `OPTIONAL MATCH`** | Re-anchor + second `pin_map` | Allowed inside runtime; agents use pin-map-class / gated patterns |
| **`INSERT` / `CREATE` / `MERGE`** | Mutate `+` / `~` / `-` (`NEW` mint) | Teach openCypher-shaped writes; mint policy in M1 |
| **Graph type / DDL / schema** | Session `SCHEMA` / TagMap | Deferred — no GQL DDL teach in first cut |
| **Nested graph / graph-as-property** | Stratified **view** (`shell` / `interior`) | Keep view budget in MemNet runtime |
| **Active graph / table / record** | Session + pin-map slice | No binding-table machine as primary agent UX |

---

## 3. Dual EDGE vs plain GQL relationships

GQL treats one relationship kind as typed directed/undirected links. Legacy MemNet keeps **one EDGE primitive** with **two endpoint grains**:

| Grain | Layer endpoints | GQL-ish migration |
|-------|-----------------|-------------------|
| **Bind** | Both `[Node.port]` | Rel type `bind` (or equivalent) + port-qualified ends |
| **Relation** | Both bare `[NodeId]` | Ordinary node–node relationship type = sense |

Adapters / GQL profile **MUST** preserve grain (or encode port incidence in durable keys). **MUST NOT** silently flatten bind into chart labels without a documented rule.

---

## 4. ASCII (new teach vs legacy)

| Family | Nodes | Relationships |
|--------|-------|---------------|
| **GQL / Cypher (1.x teach)** | `(n:Label)` | `[r:TYPE]` |
| **MemNet Layer (legacy)** | `KIND [Id]` | bare `--label-->` between `[…]` endpoints |

**MUST** teach Cypher-family ASCII for new agents. **MUST NOT** dual-teach Layer ASCII as peer 1.x. Legacy fixtures may keep Layer form until M4.

---

## 5. Law on NODE (overlay to re-express)

| Concern | Legacy Layer | GQL migration |
|---------|--------------|---------------|
| Constitutive / causal **law** | NODE field `law=` (LaTeX) — never on EDGE | Node property `law` (or related) — **not** a GQL clause |
| Ideal continuity on bind | Implied by port↔port bind | Preserve via bind encoding |
| Runtime | Agents read/write Layer lines | Agents read/write GQL + properties under MemNet gates |

---

## 6. SysML / model alignment

Product SysML (`sysml-models/`) still names internal records **NODE** \| **EDGE**. Map stereotypes in `MemNetConnections` document **Node**, **Edge**, **Property**, **Label**. Agent behaviour events should move toward GQL mutate + shaped pin-map-class read (follow-on model edits — not this pass).

---

## 7. Related

| Path | Role |
|------|------|
| [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md) | Adopt GQL wire; Layer legacy; `pin_map` open question |
| [`gql-consideration.md`](gql-consideration.md) | Stance narrative |
| [`agensgraph-buffer.md`](agensgraph-buffer.md) | Durable AgensGraph; agent wire GQL-aligned |
| [`memnet-multi-layer.md`](memnet-multi-layer.md) | Layer ontology (legacy SSOT) |
| [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md) | One-path; dialect teach = GQL |
| [`../../sysml-models/models/connections.sysml`](../../sysml-models/models/connections.sysml) | Property-graph map stereotypes |
