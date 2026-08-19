# GQL wire profile (MemNet agent teach)

**Status:** **M2 shipped** (engine/MCP GQL accept + shaped `pin_map` emit). **M1 SSOT** for conventions remains this file.  
**Teach cut (2026-08-19):** GraphElement is identity. `CREATE ()` is legal; `properties()` MAY be empty. Later MATCH/MERGE = labels + properties; an edge is type + end elements. Optional property `id` = nickname only. Hidden store handle (`elementId`-style) is **not** a property, **not** on the wire, **not** a business key. **MUST NOT** invent a replacement application store key. Breaking teach, not a 0.9 Python patch, not a 1.0 SemVer gate. **0.9 leftover invented store:** `leftover_by_id` / `leftover_id_first` / `leftover_NEW_mint` / `leftover_MERGE_by_id` / `leftover_allocate_from_locator` / `leftover_ingestIsIdRule`.  
**Grammar SSOT:** vendored official [`openCypher.bnf`](openCypher.bnf) (Apache-2.0; [`NOTICE-openCypher.md`](NOTICE-openCypher.md)). Spelling/identity only — not TCK compliance, not a second accept path.  
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
| **No store key** | GraphElement is the identity. `CREATE ()` is legal; properties MAY be empty. MATCH/MERGE = labels + properties; edge = type + ends. **MUST NOT** invent an application store key. Optional `id` = nickname only. Hidden store handle stays in the store, off the wire — not a property, not a business key. Official BNF has no store-key production. |
| **No Layer** | Do **not** teach, accept, or dual-path MemNet Layer / Tier A as agent wire. Historical grammar sources live under [`archive/`](archive/) only — not product doctrine. |
| **Write = display (redefined)** | Primary agent read = **bounded shaped subgraph** in the same openCypher-family graph shapes used for mutate — not raw tabular `RETURN`. |
| **Shaped-read option** | **B with A’s emit shape:** keep a `pin_map`-class tool (optional nickname, depth, view budget) that wraps GQL internally and emits a shaped subgraph. Goldfish seeds from cue/pattern (`find`) first. |
| **MemNet buffer** | Sessions, budgets, Multitask graph owner stay MemNet. Thin Cypher-relay-only is out. |
| **Not the corpus** | MemNet is working memory, not RAG / GraphRAG. Host search MAY propose locators; in-session recall is serial cue then `pin_map`. |

### External dialect authority

MemNet’s agent wire is **openCypher-shaped** (GQL family). Pattern spelling and identity (node / relationship / property; no store key) use the **vendored official BNF**. Cypher family evolution is defined **externally** by openCypher CIP materials — MemNet does **not** re-specify the full language here, and does **not** claim TCK compliance or the Cypher® / “openCypher” names.

| Authority | Role for MemNet |
|-----------|-----------------|
| **Vendored official BNF** [`openCypher.bnf`](openCypher.bnf) | **Spelling / identity SSOT** (Apache-2.0; [`NOTICE-openCypher.md`](NOTICE-openCypher.md); [`LICENSE-Apache-2.0.txt`](LICENSE-Apache-2.0.txt)). One file only. |
| [openCypher CIP tree](https://github.com/opencypher/openCypher/tree/main/cip) | Family home for Improvement Proposals — **not** vendored |
| [oC9 baseline](https://github.com/opencypher/openCypher/tree/main/cip/0.baseline) (`openCypher9.pdf`) | Baseline Cypher 9 dialect — **not** vendored |
| [Adopted CIPs](https://github.com/opencypher/openCypher/tree/main/cip/1.adopted) / [testable CIPs](https://github.com/opencypher/openCypher/tree/main/cip/2.testable) | Incremental family features — **not** vendored |
| [ISO/IEC 39075 GQL](https://www.iso.org/standard/76120.html) | Normative for **GQL-native** features |
| Optional: [CIP process](https://opencypher.org/cips/) | Process / site overview |

**Productions locked for MemNet identity teach** (cite the BNF; do not rewrite it):

```
<node pattern> ::=
  <left paren> [ <node pattern filler> ] <right paren>

<property key value pair> ::=
  <property name> <colon> <value expression>

<create statement> ::=
  CREATE <create graph pattern>

<merge statement> ::=
  MERGE <merge graph pattern> [ <merge action> ]
```

Filler and property maps are optional. Property is any `<property name> : <value expression>` — `id` is not a required production. CREATE / MERGE have **no store-key production**.

**Behaviour cite (not a vendored suite, not a compliance claim):** upstream TCK `tck/features/clauses/create/Create1.feature` scenario `[1] Create a single node` (`CREATE ()`). Empty node pattern is legal.

**Gated subset wins:** MemNet agent surface = `pin_map`-class read + gated mutate (§1) — **not** full language / every CIP / WITH / UNWIND / CALL / unbounded `MATCH` as goldfish. Vendoring the BNF is spelling/identity SSOT, **not** a promise to accept the whole language, **not** a second Python accept path (do **not** generate a parser/visitor from this BNF). SysML pointer: [`../../sysml-models/outputs/system-design-notes.md`](../../sysml-models/outputs/system-design-notes.md) (`GqlCodec`).

---

## 1. Allowed agent-facing clauses

Subset of openCypher-shaped GQL for **agent** I/O. Full ISO GQL DDL / analytic Cypher is **not** the agent surface.

### 1.1 Primary read — `pin_map` envelope (not free `MATCH`)

Agents **MUST** read via the MemNet **`pin_map`-class** tool (MCP `pin_map` / CLI `query pin-map`) after a cue/pattern seed, or when a nickname is already in hand:

| Input | Meaning | Default / notes |
|-------|---------|-----------------|
| cue / `find` | Recall seed: label + properties (bounded MATCH) | Primary goldfish entry; not `--anchor` as law |
| `anchor` | Optional nickname `id` when one exists | Omit when no nickname; 0.9 leftover still requires it in Python |
| `depth` | Hop budget from the seed | Typical `2` |
| `view` | Grain budget **inside one session** | Omit → shell-safe default; teach `shell` / `interior` first **on a seed**. Not session outline (0.11). Not a second session ([`memnet-session-strata.md`](memnet-session-strata.md)) |
| `max_rows` | Hard row / element cap | Engine default (e.g. 50) |

Runtime **MAY** compile the envelope to internal `MATCH` / path patterns. Agents **MUST NOT** be taught unbounded `MATCH … RETURN` as the primary goldfish read.

**Caller (0.13).** Each generate packs **at most one** live `pin_map` (or skip). Drop prior map rows from the chat list. Sparse Commit Δ. Env blobs (test logs, screenshots) stay in the outer harness. `view=shell` is grain on a seed — **not** session outline (0.11). Empty cue still skips. leftover `--anchor` is not law. Pytest fail code: `stuffed_maps`. Sibling user-pack may absorb caller text; this repo owns the fail.

**Emit:** shaped subgraph (§5) — openCypher-family **node / edge / property** patterns (or equivalent structured graph), neighbourhood-bounded and view-filtered. Emit **MAY** omit `{id:'…'}`.

**Honesty:** SysML nests `BoundedMatchFind` beside `PinMapShapedRead` under `Recall` / `AgentShapedRead` (parent `RecallCommit`). Same Recall operator; seed rule is cue/pattern first, optional nickname for a later walk. Find emits **hit nodes only** (`query find` / MCP `find`); then `pin_map` walks. Do **not** teach MATCH…RETURN as goldfish. Product math: [`math-skeleton.md`](math-skeleton.md). **0.9 leftover:** `PinMapComposer` still `require_anchor` / `by_id` — leftoverIssue, not TARGET.

### 1.2 Mutate — openCypher-shaped writes (gated)

Allowed **agent mutate** clause shapes (session-scoped; MutateGate / MCP `add`/`update` envelope in M2):

| Intent | Allowed shape (sketch) | Notes |
|--------|------------------------|-------|
| Create node | `CREATE ()` or `CREATE (:TSK {goal:'…'})` | GraphElement identity. Empty properties legal. No required `id`. Optional nickname if you will point again |
| Create relationship | `MATCH` ends by label + properties, then `CREATE (a)-[:TYPE {…}]->(b)` | Ends by type + properties; leftover 0.9 still MATCH `{id}` |
| Merge / upsert | `MERGE (n:TSK {goal:$g}) SET n += {…}` | Per-write lookup of labels+props — **not** a primary key. `{id}` MERGE is leftover nickname. When \|Q\|>1, CueConflict (do not absorb) |
| SameThingAbsorb (Commit rule) | `MATCH (a:Label {…}), (b:Label {…}) SET a += b` | After CueConflict: agent-gated collapse of two patterns into one GraphElement (`aka` on the survivor). Not a product verb. Not MERGE-by-id / MERGE-by-name. Distinct from ImportAbsorb |
| Patch properties | `MATCH (n:Label {goal:'…'}) SET n.key = value` | No mint on patch |
| Delete | `MATCH (n:Label {…}) DETACH DELETE n` or delete one rel by type+ends | Settle / recycle policy elsewhere |

**Leftover invented store (not TARGET):** leftover_by_id / leftover_NEW_mint / leftover_id_first / leftover_MERGE_by_id / leftover_allocate_from_locator / leftover_ingestIsIdRule. **0.9 engine still does this.** Do not teach it as identity. Do not replace it with another application PK.

**Batch:** one mutate payload = ordered list of such clauses (or structured equivalents). Response **MAY** list nicknames if any were assigned; it **MUST NOT** teach hidden storage handles (`elementId` style).

### 1.3 Forbidden on the agent teach surface

| MUST NOT | Why |
|----------|-----|
| Unbounded `MATCH` without anchor/depth/view envelope as primary read | Breaks goldfish / token budget |
| Primary tabular `RETURN` columns / binding tables as goldfish read | Breaks redefined Write = display |
| Full GQL **DDL** / graph-type / schema teach in first cut | SCHEMA deferred |
| Variable-length / shortest-path as default agent read | Store/DBA only |
| Dual-teach Layer ASCII / Tier A lines as peer or accept wire | User: **no Layer** |
| Invent a replacement application store key | Grammar has none; locators/`id` are properties, not PK |
| Invent a third peer dialect | One dialect = GQL |
| Put constitutive **law** on a relationship | Law lives on the **node** (`law` property) |

---

## 2. No store key (optional nickname)

### 2.1 GraphElement is the identity

GraphElement (node or edge) **is** the identity. `CREATE ()` is legal. `properties()` MAY be empty. Three GQL elements: node, edge, property. Later MATCH/MERGE looks up **labels + properties**; an edge is **type + end elements**. That lookup is per-write, not a primary key.

Hidden store handle (`elementId`-style) stays **inside the store**. It is **not** a property, **not** on the wire, **not** a business key.

MemNet `leftover_by_id` / `leftover_id_first` / required property `id` / `leftover_NEW_mint` / `leftover_MERGE_by_id` / `leftover_allocate_from_locator` / `leftover_ingestIsIdRule` are a **store we invented**. That is the TARGET-vs-leftover split. **MUST NOT** invent a replacement application store key (locator-as-PK, qname-as-PK, minted string-as-PK). Optional property `id` = **nickname only**.

| Rule | Detail |
|------|--------|
| **No grammar PK** | Identity = GraphElement. Lookup = labels + properties (or rel type + ends) on that write. |
| **Empty create** | `CREATE ()` is legal. Properties MAY be empty. |
| **Nickname** | Property `id` MAY exist so an agent can point at a row again. House prefixes `TSK_*`, `USR_*`, … when present. |
| **Hidden handle** | Cabinet-internal. **MUST NOT** teach on the wire. **MUST NOT** treat as a property or business key. |
| **SCHEMA** | **MUST NOT** put `id` first as a required field. **0.9 leftover:** `leftover_id_first` / `validate_id`. |
| **Id-exists / not-found** | Valid **only when** an optional nickname is present (MN-REQ-03.1 / 03.2). |

**Struck law:** “every durable node and relationship has property `id`.” That over-fitted GQL by treating `id` as a store key. **0.9 leftover:** `leftover_by_id` still keys the Python store — leftoverIssue, not TARGET. This cut does **not** rewrite MutateGate / pin_map / store.

### 2.2 leftover_NEW_mint (not a product MUST)

`NEW` is leftover mint sugar from the invented `leftover_by_id` store, **not** a product rule. TARGET create is `CREATE ()` or `CREATE (:TSK {goal:'…'})`.

| Case | TARGET | 0.9 leftover (invented store) |
|------|--------|------------------------------|
| **Create (LLM goldfish)** | Omit `id`; empty properties legal | Client `id: 'NEW'`; IdAllocator keys a string in `leftover_by_id` |
| **Update / settle** | MATCH label + properties | `NEW` illegal; known nickname only |
| **External locators** (SysML, `.ato`, paths) | Locator **properties** on GraphElement — not a replacement PK | leftover_allocate_from_locator into leftover_by_id |
| **Relationship ends** | Type + end elements | Known ids after mint |
| **Cabinet MERGE** | Per-write lookup of labels + properties | leftover_MERGE_by_id when a nickname exists |

Surface spelling of leftover mint is the string **`NEW`** in property `id`. Do **not** teach `NEW` as identity. Hidden `elementId` stays off-wire.

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
| **Relation** (chart / semantic) | Other types (`:about`, `:helps`, `:derives_result`, …) | Bare node↔node | **No** `fromPort`/`toPort`. Ends are nodes (optional nickname `id` if present). |

**MUST:**

- Preserve grain: bind stays port-qualified; relation stays bare-node.
- Keep continuity implied by `:bind` (no Ohm/KCL/gain on the relationship).

**MUST NOT:**

- Silently flatten bind into a chart label without ports.
- Mix grains on one relationship (one end port-qualified, other bare) — reject in soft-validate / MutateGate.
- Introduce first-class `PORT` nodes in M1 (deferred); ports are **property** values, not a fourth graph-element kind.

**Alternate encodings** (synthetic port nodes, etc.) are **out** unless a later ADR revises this freeze. Case study: [`../application-notes/examples/inverting-amplifier-gql-case-study.md`](../application-notes/examples/inverting-amplifier-gql-case-study.md).

---

## 4. Explicit MUST / MUST NOT (summary)

**MUST**

- Teach **GQL only** as the agent wire: **node** (vertex), **edge** (relationship), **property**. GraphElement is the identity; grammar has no store key. `CREATE ()` is legal.
- Seed goldfish from cue/pattern (`find`); use **`pin_map`-class** walks (depth / view / max_rows). Nickname `anchor` is optional.
- Emit **shaped subgraph** for primary agent read (same family as mutate). Emit **MAY** omit `{id:'…'}`.
- Treat MATCH/MERGE as labels + properties (edge = type + ends), not a PK. Optional `id` = nickname. leftover_NEW_mint is leftover sugar.
- Encode bind as `:bind` + `fromPort`/`toPort`; law on node.

**MUST NOT**

- Require property `id` on every node or relationship; invent a replacement application store key; teach HiddenStoreHandle on the wire or as a property/business key; put `id` first as a required SCHEMA field.
- Treat `--anchor TSK1` as law for goldfish (cue/pattern first).
- Unbounded `MATCH` as primary agent read.
- Primary tabular `RETURN` / binding-table goldfish.
- Layer / Tier A / MemNet Layer as agent wire, peer teach, or product accept path.
- Dual-teach two agent dialects.
- Delete mission budgets (sessions, view, Multitask owner) in favour of raw store access.
- Require the durable cabinet for goldfish / M1–M2 wire (sync is **M2.5 / 0.7**; optional; Fake + URL skip in CI). Do **not** vendor a cabinet. Do **not** flip `liveNeo4jClaimed`.
- Teach full GQL DDL as agent surface in first cut.
- Pretend the 0.9 Python already dropped `by_id` / `validate_id` / `id_first`.
- Vendor the whole openCypher repo, TCK, CIP tree, or ANTLR tools; generate a parser/visitor from [`openCypher.bnf`](openCypher.bnf) as a second accept path; claim TCK compliance; describe MemNet as “Cypher” or “openCypher”.

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

```gql
(:Label {goal:'…'})
(:Label {goal:'…'})-[:TYPE {note:'…'}]->(:Label {status:'…'})
(:Label {id:'TSK_optional_nickname', goal:'…'})
```

**Rules:**

- Include the seed neighbourhood and in-budget neighbours only (depth / view / max_rows).
- **MAY** omit `{id:'…'}`. Prefer copyable property maps (law, ports, params, optional nickname) agents need for the next mutate.
- Hide recyclable / out-of-budget neighbours (MN-REQ-04).
- Engine-law / control preamble rows **MAY** prepend when authorised — still not a binding table.
- **0.9 leftover emit** still prints `id` because the store keys `by_id` — leftoverIssue, not TARGET.

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
| **M2.5 (done, 0.7)** | Durable online GQL store adapter (MemNet ↔ AgensGraph hydrate/flush; one sync owner; optional Neo4j client not live-claimed) — [`agensgraph-buffer.md`](agensgraph-buffer.md), [`neo4j-buffer.md`](neo4j-buffer.md) | Agent Bolt / LLM↔store direct teach; hosted cabinet |
| **M3 (done, 0.8 docs)** | In-repo `LLM-GUIDE` + application-notes GQL examples | User-pack skill rewrite (sibling repo) |
| **User-pack (parallel)** | `memnet-format` / `mcp-memnet` / … → GQL-only in `chouswei/cursor-user-skills` | **In flight separately** — not this repo’s M1–M3 gate |
| **Archive** | Historical Layer + unused `MemNet.g4` stub under [`archive/`](archive/) | Not an accept path; not CI teach |

**As-is note:** Engine/MCP product path is **GQL** (`memnet.gql_codec.GqlCodec`, `PinMapComposer` shaped emit). Layer/Tier A modules may remain on disk for archive/tests but are **rejected** on default mutate accept (`legacy_dialect_retired`). **M2.5** client + 0.7 live hydrate/flush are shipped; Fake + URL skip remain the CI seam.

---

## 7. Related

| Path | Role |
|------|------|
| [`openCypher.bnf`](openCypher.bnf) | Official grammar BNF (spelling/identity SSOT; Apache-2.0) |
| [`NOTICE-openCypher.md`](NOTICE-openCypher.md) | Attribution; MIT product vs Apache vendored file |
| [`LICENSE-Apache-2.0.txt`](LICENSE-Apache-2.0.txt) | Apache License 2.0 text (upstream `LICENSE`) |
| [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md) | Decision + supersession (no Layer) |
| [`../SHAPE.md`](../SHAPE.md) | Product shape from the problem |
| [`../ROADMAP.md`](../ROADMAP.md) | SemVer map SSOT |
| [`gql-model-exam.md`](gql-model-exam.md) | GQL-wire paradox (historical filename; nest SSOT is SysML README) |
| [`math-skeleton.md`](math-skeleton.md) | 0.5 Recall/Commit math SSOT (operator domains; one \(S\) per generate) |
| [`agensgraph-buffer.md`](agensgraph-buffer.md) | Durable GQL store adapter sketch (**M2.5**) |
| [`neo4j-buffer.md`](neo4j-buffer.md) | Second cabinet client (not live-claimed) |
| [`../application-notes/examples/inverting-amplifier-gql-case-study.md`](../application-notes/examples/inverting-amplifier-gql-case-study.md) | Worked GQL encoding |
| [`archive/README.md`](archive/README.md) | Quarantined historical Layer sources |
| [`memnet-session-strata.md`](memnet-session-strata.md) | Named sessions as strata (not Layer wire) |
| [`../../sysml-models/README.md`](../../sysml-models/README.md) | Nested `GqlCodec` / `PinMapShapedRead` |
