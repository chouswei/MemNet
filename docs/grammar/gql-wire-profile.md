# GQL wire profile (MemNet agent teach)

**Status:** **M2 shipped** (engine/MCP GQL accept + shaped `pin_map` emit). **M1 SSOT** for conventions remains this file.  
**Audience:** product developers; M2.5 durable-store authors; M3 in-repo playbook / app-note authors. (User-pack skill migration is separate — see §6.)  
**Brand:** MemNet (Net of Memory). **Dialect:** **GQL only** (openCypher-shaped, AgensGraph-compatible).  
**Decision:** [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md) — **superseded on Layer:** user directed **no Layer / Tier A** as agent wire or accept path; see ADR supersession note.  
**British English.** ASCII ids.

**Pointer chain:** product shape [`../SHAPE.md`](../SHAPE.md) → ADR-001 → **this file** → AgensGraph / durable store [`agensgraph-buffer.md`](agensgraph-buffer.md) (**M2.5**, live path **0.7**).

---

## 0. Product locks (M1)

| Lock | Rule |
|------|------|
| **One dialect** | Agent teach and wire = **GQL (openCypher-shaped)** only. |
| **Three GQL elements** | ISO/IEC 39075 names: **node** (synonym **vertex**), **edge** (synonym **relationship**), **property**. Labels name kinds; they are not a fourth element. Ports, law, `id`, locators are **property** values — not a fourth graph-element kind. |
| **No Layer** | Do **not** teach, accept, or dual-path MemNet Layer / Tier A as agent wire. Historical grammar sources live under [`archive/`](archive/) only — not product doctrine. |
| **Write = display (redefined)** | Primary agent read = **bounded shaped subgraph** in the same openCypher-family graph shapes used for mutate — not raw tabular `RETURN`. |
| **Shaped-read option** | **B with A’s emit shape:** keep a `pin_map`-class tool (anchor, depth, view budget) that wraps GQL internally and emits a shaped subgraph. |
| **MemNet buffer** | Sessions, budgets, Multitask graph owner stay MemNet. Thin Cypher-relay-only is out. |
| **Not the corpus** | MemNet is working memory, not RAG / GraphRAG. Host search MAY propose locators; in-session recall is serial cue then `pin_map`. |

### External dialect authority

MemNet’s agent wire is **openCypher-shaped** (GQL family). Cypher syntax and semantics are defined **externally** by openCypher CIP materials — MemNet does **not** re-specify the full language here.

| Authority | Role for MemNet |
|-----------|-----------------|
| [openCypher CIP tree](https://github.com/opencypher/openCypher/tree/main/cip) | Normative **family** home for openCypher Improvement Proposals |
| [oC9 baseline](https://github.com/opencypher/openCypher/tree/main/cip/0.baseline) (`openCypher9.pdf`) | Baseline Cypher 9 dialect |
| [Adopted CIPs](https://github.com/opencypher/openCypher/tree/main/cip/1.adopted) / [testable CIPs](https://github.com/opencypher/openCypher/tree/main/cip/2.testable) | Incremental openCypher features in the same family |
| [ISO/IEC 39075 GQL](https://www.iso.org/standard/76120.html) | Normative for **GQL-native** features; a CIP for those may be informational only (per CIP README) |
| Optional: [CIP process](https://opencypher.org/cips/) | Process / site overview |

**Gated subset wins:** MemNet agent surface = `pin_map`-class read + gated mutate (§1) — **not** full openCypher / every CIP. Unbounded `MATCH` as primary goldfish read remains out. SysML pointer: [`../../sysml-models/outputs/system-design-notes.md`](../../sysml-models/outputs/system-design-notes.md) (`GqlCodec`).

---

## 1. Allowed agent-facing clauses

Subset of openCypher-shaped GQL for **agent** I/O. Full ISO GQL DDL / analytic Cypher is **not** the agent surface.

### 1.1 Primary read — `pin_map` envelope (not free `MATCH`)

Agents **MUST** read via the MemNet **`pin_map`-class** tool (MCP `pin_map` / CLI `query pin-map`) when an ego/anchor id is known:

| Input | Meaning | Default / notes |
|-------|---------|-----------------|
| `anchor` | Ego node `id` (required for goldfish) | Stable id string |
| `depth` | Hop budget from anchor | Typical `2` |
| `view` | Grain budget | Omit → shell-safe default; teach `shell` / `interior` first |
| `max_rows` | Hard row / element cap | Engine default (e.g. 50) |

Runtime **MAY** compile the envelope to internal `MATCH` / path patterns. Agents **MUST NOT** be taught unbounded `MATCH … RETURN` as the primary goldfish read.

**Emit:** shaped subgraph (§5) — openCypher-family **node / edge / property** patterns (or equivalent structured graph), ego-bounded and view-filtered.

**Honesty:** SysML nests `BoundedMatchFind` beside `PinMapShapedRead` under `Recall` / `AgentShapedRead` (parent `RecallCommit`). Same Recall operator; seed rule differs (known id vs bounded MATCH + hard `LIMIT`). Find emits **hit nodes only** (`query find` / MCP `find`); then `pin_map` walks. Do **not** teach MATCH…RETURN as goldfish. Product math: [`math-skeleton.md`](math-skeleton.md).

### 1.2 Mutate — openCypher-shaped writes (gated)

Allowed **agent mutate** clause shapes (session-scoped; MutateGate / MCP `add`/`update` envelope in M2):

| Intent | Allowed shape (sketch) | Notes |
|--------|------------------------|-------|
| Create node | `CREATE (n:Label { id: 'NEW', … })` or mint token per §2 | Engine allocates real `id` |
| Create relationship | `MATCH` ends by `id`, then `CREATE (a)-[:TYPE {…}]->(b)` | Ends must be known ids |
| Merge / upsert | `MERGE (n:Label {id: $id}) SET n += {…}` | Prefer when ground id known |
| Patch properties | `MATCH (n {id: $id}) SET n.key = value` | No mint on patch |
| Delete | `MATCH (n {id: $id}) DETACH DELETE n` or delete one rel by `id` | Settle / recycle policy elsewhere |

**Batch:** one mutate payload = ordered list of such clauses (or structured equivalents). Response **MUST** list minted ids in order.

### 1.3 Forbidden on the agent teach surface

| MUST NOT | Why |
|----------|-----|
| Unbounded `MATCH` without anchor/depth/view envelope as primary read | Breaks goldfish / token budget |
| Primary tabular `RETURN` columns / binding tables as goldfish read | Breaks redefined Write = display |
| Full GQL **DDL** / graph-type / schema teach in first cut | SCHEMA deferred |
| Variable-length / shortest-path as default agent read | Store/DBA only |
| Dual-teach Layer ASCII / Tier A lines as peer or accept wire | User: **no Layer** |
| Invent a third peer dialect | One dialect = GQL |
| Put constitutive **law** on a relationship | Law lives on the **node** (`law` property) |

---

## 2. Id / property / label conventions

### 2.1 Stable ids

| Rule | Detail |
|------|--------|
| **Canonical key** | Every node and relationship durable for agent copy has property **`id`** (string). |
| **House prefixes** | Prefer `TSK_*`, `USR_*`, `MOD_*`, `SYM_*`, `CST_*`, `E_*`, … — ASCII `[A-Za-z_][A-Za-z0-9_]*`. |
| **Copy, don’t invent** | After mint, agents copy `id` from shaped `pin_map` / mutate response. |

### 2.2 `NEW` mint policy (sketch for M2)

| Case | Rule |
|------|------|
| **Create (LLM goldfish)** | Client sets `id: 'NEW'` (node) or omits / `id: 'NEW'` (relationship). Engine **IdAllocator** replaces with a real id. |
| **Update / settle** | `NEW` **illegal** — known ids only. |
| **External locators** (SysML, `.ato`, paths) | Deterministic ground ids from locators — **no** client `NEW` for those pins. |
| **Multiple `NEW` in one batch** | Distinct engine ids per create; response lists in order. |
| **Relationship ends** | Must be known ids (prior pin map or earlier create in batch after mint resolution). Prefer create nodes → response → create rels when unsure. |

Surface spelling of the mint token is the string **`NEW`** in property `id` (not `NEW1` / client-numbered). M2 may also accept a structured mint flag equivalent — one behaviour, documented in emit.

### 2.3 Labels vs kinds

| Concern | Convention |
|---------|------------|
| **Primary label** | One primary GQL label per node ≈ former “kind” (`:TSK`, `:CST`, `:MOD`, …). |
| **Avoid label zoo** | Prefer properties (`role`, `status`, …) over many labels. |
| **Relationship type** | Upper/lower openCypher type name = sense (`:bind`, `:about`, `:helps`, …). |
| **Law** | Node property `law` (LaTeX string). **Never** on a relationship. |
| **Ports** | Node property `ports` (map / structured bag). See §3. |
| **Omit defaults** | Do not emit session-default noise (e.g. default recycle) on shaped read when product policy says omit. |

---

## 3. Dual-EDGE encoding (bind vs relation)

GQL has one relationship primitive. MemNet preserves **two endpoint grains** via **type + endpoint properties**:

| Grain | Rel type | Endpoints | Encoding (**locked for M1 → M2**) |
|-------|----------|-----------|-----------------------------------|
| **Bind** (ideal pipe / copper / continuity) | `:bind` | Port↔port | Rel properties **`fromPort`** / **`toPort`** (port names on the incident nodes). Optional `carries`. Nodes hold `ports` bags. |
| **Relation** (chart / semantic) | Other types (`:about`, `:helps`, `:derives_result`, …) | Bare node↔node | **No** `fromPort`/`toPort`. Both ends are node `id`s only. |

**MUST:**

- Preserve grain: bind stays port-qualified; relation stays bare-id.
- Keep continuity implied by `:bind` (no Ohm/KCL/gain on the relationship).

**MUST NOT:**

- Silently flatten bind into a chart label without ports.
- Mix grains on one relationship (one end port-qualified, other bare) — reject in soft-validate / MutateGate.
- Introduce first-class `PORT` nodes in M1 (deferred); ports are **property** values, not a fourth graph-element kind.

**Alternate encodings** (synthetic port nodes, etc.) are **out** unless a later ADR revises this freeze. Case study: [`../application-notes/examples/inverting-amplifier-gql-case-study.md`](../application-notes/examples/inverting-amplifier-gql-case-study.md).

---

## 4. Explicit MUST / MUST NOT (summary)

**MUST**

- Teach **GQL only** as the agent wire: **node** (vertex), **edge** (relationship), **property**.
- Use **`pin_map`-class** reads with anchor (+ depth / view / max_rows).
- Emit **shaped subgraph** for primary agent read (same family as mutate).
- Mint with **`NEW`**; copy assigned ids thereafter.
- Encode bind as `:bind` + `fromPort`/`toPort`; law on node.

**MUST NOT**

- Unbounded `MATCH` as primary agent read.
- Primary tabular `RETURN` / binding-table goldfish.
- Layer / Tier A / MemNet Layer as agent wire, peer teach, or product accept path.
- Dual-teach two agent dialects.
- Delete mission budgets (sessions, view, Multitask owner) in favour of raw store access.
- Require the durable cabinet for goldfish / M1–M2 wire (sync is **M2.5 / 0.7**; optional; Fake + URL skip in CI).
- Teach full GQL DDL as agent surface in first cut.

---

## 5. Shaped-read contract

### 5.1 Relation to `pin_map`

| Item | Contract |
|------|----------|
| **Tool** | Keep MCP `pin_map` / CLI `query pin-map` (aliases `query_warm` / `query warm` = legacy **tool** names only, not a dialect). |
| **Internal** | Composer wraps GQL / graph walk; agents do not author the internal query. |
| **Primary emit** | Shaped subgraph (§5.2). |
| **Non-goal** | Raw `RETURN n, r, m` tables as the default tool result. |

Option **C** (raw tables as primary) is **out**. Option **D** (`query_gql` escape hatch) may exist later for DBA/debug — **MUST NOT** be dual-taught as the goldfish path in M1–M3.

### 5.2 Emit shape

Shaped subgraph = ordered openCypher-family lines (or isomorphic structured graph) such as:

```cypher
(:Label {id:'…', …})
(:Label {id:'…'})-[:TYPE {id:'…', …}]->(:Label {id:'…'})
```

**Rules:**

- Include anchor and in-budget neighbours only (depth / view / max_rows).
- Prefer copyable property maps (ids, law, ports, params) agents need for the next mutate.
- Hide recyclable / out-of-budget neighbours (MN-REQ-04).
- Engine-law / control preamble rows **MAY** prepend when authorised — still not a binding table.

### 5.3 Write = display (redefined)

| Era | Meaning |
|-----|---------|
| **This profile (0.8 teach)** | Agent **reads** shaped openCypher-family graph lines and **writes** the same family under gates. |
| **Out** | “Whatever `RETURN` produced” as the teach surface. |

---

## 6. Boundary vs M2 / M2.5 / M3 / archive

**Order (done):** M1 → M2 → **M2.5** → M3. Next SemVer is **1.0 = claim** of 0.5–0.8, not a new M-phase.

| Phase | Owns | This file does **not** |
|-------|------|-------------------------|
| **M1 (done)** | Conventions, MUST/MUST NOT, shaped-read contract, GQL-only teach | Engine code, app-note marathon, store adapter |
| **M2 (done)** | `GqlCodec` accept; `PinMapShapedRead` emit; MutateGate GQL path; Layer/Tier A **retired** from product accept | — |
| **M2.5 (done, 0.7)** | Durable online GQL store adapter (MemNet ↔ AgensGraph hydrate/flush; one sync owner) — [`agensgraph-buffer.md`](agensgraph-buffer.md) | Agent Bolt / LLM↔store direct teach; hosted cabinet |
| **M3 (done, 0.8 docs)** | In-repo `LLM-GUIDE` + application-notes GQL examples | User-pack skill rewrite (sibling repo) |
| **User-pack (parallel)** | `memnet-format` / `mcp-memnet` / … → GQL-only in `chouswei/cursor-user-skills` | **In flight separately** — not this repo’s M1–M3 gate |
| **Archive** | Historical Layer `.g4` / fixtures under [`archive/`](archive/) | Not an accept path; not CI teach |

**As-is note:** Engine/MCP product path is **GQL** (`memnet.gql_codec.GqlCodec`, `PinMapComposer` shaped emit). Layer/Tier A modules may remain on disk for archive/tests but are **rejected** on default mutate accept (`legacy_dialect_retired`). **M2.5** client + 0.7 live hydrate/flush are shipped; Fake + URL skip remain the CI seam.

---

## 7. Related

| Path | Role |
|------|------|
| [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md) | Decision + supersession (no Layer) |
| [`../SHAPE.md`](../SHAPE.md) | Product shape from the problem |
| [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md) | SemVer map SSOT |
| [`gql-model-exam.md`](gql-model-exam.md) | GQL-wire paradox (historical filename; nest SSOT is SysML README) |
| [`math-skeleton.md`](math-skeleton.md) | 0.5 Recall/Commit math SSOT |
| [`agensgraph-buffer.md`](agensgraph-buffer.md) | Durable GQL store adapter sketch (**M2.5**) |
| [`../application-notes/examples/inverting-amplifier-gql-case-study.md`](../application-notes/examples/inverting-amplifier-gql-case-study.md) | Worked GQL encoding |
| [`archive/README.md`](archive/README.md) | Quarantined historical Layer sources |
| [`../../sysml-models/README.md`](../../sysml-models/README.md) | Nested `GqlCodec` / `PinMapShapedRead` |
