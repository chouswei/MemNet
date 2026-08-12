# ADR-001: GQL as agent wire (MemNet brand retained)

**Status:** Accepted

**Date:** 2026-08-12

**Context**

MemNet (Net of Memory) is an agent memory product: bounded live pin map, goldfish re-read, Multitask shared sessions. Through 0.4.x the agent teach/wire surface was a bespoke shared dialect (**Layer** / legacy Tier A alias), with ISO GQL / openCypher held to a **model map** and to the durable-store side (AgensGraph buffer sketch).

Three pressures reversed the prior “map only; MUST NOT teach GQL as wire” stance:

1. **Training priors.** LLMs already know Cypher-shaped ASCII (`MATCH` / `CREATE` / `(n)-[:R]->(m)`). Invent-syntax errors and teach cost for Layer remain higher than for openCypher-shaped GQL.
2. **AgensGraph buffer.** The durable thesis (MemNet as working-memory buffer in front of Postgres + property graph) is stronger when agent and store speak the **same family** of query language. Keeping a private Layer dialect forever forces a permanent translation tax and invites dual-dialect drift.
3. **Layer cost.** Maintaining Layer as 1.x teach (ANTLR, skills, application notes, codec paths) is real product cost. Prior docs already conceded “familiar ≠ fit”; the explicit product decision is that **training-prior + store alignment now outweigh Layer uniqueness** for agent wire — without abandoning the MemNet product name or the pin-map *mission*.

This ADR does **not** abandon MemNet. It replaces **Layer / MemNet Grammar as agent wire** with **GQL (openCypher-shaped, AgensGraph-compatible)**. Brand and product remain MemNet.

**Decision**

1. **Agent teach / wire = GQL (openCypher-shaped).** Primary agent read/write dialect for 1.x planning is ISO GQL / openCypher patterns compatible with AgensGraph — not Layer lines as the teach surface.
2. **MemNet remains the product name** for agent memory (engine, MCP, sessions, Multitask ops). “Net of Memory” / pin-map *concept* may be redefined around bounded GQL result shaping (see Open question below).
3. **Layer becomes legacy.** `MemNetLayer.g4`, Layer fixtures, and Layer-first application notes stay in-tree for migration; they are no longer the forward teach SSOT. Do not delete grammar sources in the first cut.
4. **Write = display must be redefined on GQL** (or the mission changes). Raw tabular `MATCH`/`RETURN` dumps are **not** an acceptable primary agent read. The product either (a) reshapes GQL results into a bounded, agent-stable graph view, or (b) honestly drops Write = display as a Layer-era slogan. This ADR chooses (a) — see recommendation under Open question.
5. **One dialect teach (updated):** GQL = 1.x teach; Layer / Tier A = legacy accept / migration path only. Do not invent a third peer dialect beside GQL + Layer-legacy.

**Alternatives Considered**

| Option | Why not chosen |
|--------|----------------|
| **Keep Layer as 1.x wire; GQL map/store-side only** | Prior stance. Rejected by explicit product decision — training prior + AgensGraph alignment outweigh Layer uniqueness. |
| **Dual teach (Layer + GQL peer surfaces)** | Breaks one-path / one dialect teach; doubles skills and error modes. |
| **Thin Cypher relay only (drop MemNet buffer)** | Collapses product value; loses session goldfish, Multitask shared graph owner, and token-shaped reads. Brand without buffer is not MemNet. |
| **Full ISO GQL DDL / graph-types on agent wire in first cut** | Schema/type bloat; deferred with other Open items. First cut = openCypher-shaped CRUD + bounded read. |

**Consequences**

**Easier**

- Agents reuse Cypher priors; teach docs and skills can cite openCypher patterns.
- AgensGraph sync / durable buffer needs less conceptual translation.
- Contributors stop defending a private ASCII dialect against industry defaults.

**Harder / honest costs**

- **Write = display is broken as Layer defined it.** Layer “same graph lines on read and write” does not transfer to raw GQL binding tables. Mission continuity requires a **redefinition**: bounded shaped subgraph (or equivalent) as the primary read contract — not free-form `RETURN` columns.
- Dual EDGE (bind vs relation), law-on-NODE, `view=` grains, and `NEW` mint must be **re-expressed** as GQL conventions (labels, properties, port-qualified endpoints) or intentionally narrowed.
- Skills (`memnet-format`, `mcp-memnet`), `LLM-GUIDE`, and application notes remain Layer-first until a migration pass — temporary doctrine drift is expected and must be labelled **legacy**.
- Engine / MCP mutate and `pin_map` paths need a GQL accept + shaped-emit plan; Layer codec becomes accept-only then retire.

**Non-goals for first cut**

- Delete `MemNetLayer.g4` / Layer ANTLR tree or golden Layer fixtures.
- Rewrite all `docs/application-notes/` to GQL in this pass — migration plan only.
- Ship AgensGraph sync adapter or dual-write.
- Teach full GQL schema/DDL, multi-label cardinality debates, or unbounded analytic `MATCH` as agent primary read.
- Rewrite user-pack skills in the same commit as this ADR (follow-on).
- Harmonise historical Layer `[Id]` ASCII into Cypher in stored 0.4.x snapshots without an explicit migrate tool.

**Migration plan (docs-only this pass)**

| Phase | Action |
|-------|--------|
| **M0 (this ADR)** | Reverse stance docs; Layer map becomes migration crosswalk; flag `pin_map` open question. |
| **M1** | Define GQL wire profile (allowed clauses, id/property conventions, dual-EDGE encoding) + shaped-read contract replacing Layer Write = display. |
| **M2** | Engine/MCP: accept openCypher-shaped mutate; emit shaped subgraph for pin-map-equivalent tool; Layer accept path retained. |
| **M3** | Update `LLM-GUIDE`, user-pack skills, then application notes; mark Layer examples deprecated. |
| **M4** | Optional: retire Layer teach from ROADMAP; keep `.g4` / fixtures until parity tests pass; then archive. |

**Open question (hard): what replaces `pin_map` Write = display under GQL?**

| Option | Sketch | Trade-off |
|--------|--------|-----------|
| **A. Shaped subgraph return** | Tool returns a bounded ego/view subgraph as openCypher-compatible graph text (nodes/rels), not a binding table | Closest to Write = display; agents still see graph shapes |
| **B. Runtime `view=` wrapper** | MemNet keeps `pin_map(anchor, view=…)` as the tool; internally compiles to GQL; emit stays shaped | Preserves goldfish UX; GQL is wire *inside* the envelope |
| **C. Raw `MATCH`/`RETURN` as primary** | Agent consumes tabular results | Lowest implement cost; **abandons** Write = display mission |
| **D. Hybrid** | `pin_map` shaped default; escape hatch `query_gql` for DBA/debug | Useful later; must not dual-teach in M1 |

**Recommendation (default):** **B with A’s emit shape** — keep a MemNet **`pin_map`-class tool** (anchor, depth, view budget) that **wraps GQL** internally and **returns a shaped subgraph** (openCypher-family graph lines / structured graph), never raw unbounded `RETURN` tables as the primary agent read. Mutate teaches openCypher-shaped writes under the same session/view gates. Option C is explicitly **out** unless a future ADR drops Write = display.

**References**

- [`../grammar/gql-consideration.md`](../grammar/gql-consideration.md) — stance (now: adopt GQL as agent wire)
- [`../grammar/layer-gql-map.md`](../grammar/layer-gql-map.md) — Layer ↔ GQL map (migration path)
- [`../grammar/agensgraph-buffer.md`](../grammar/agensgraph-buffer.md) — durable buffer; agent wire now GQL-aligned
- [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md) — one-path plan; dialect teach updated
- [ISO/IEC 39075:2024 GQL](https://www.iso.org/standard/76120.html)
- [AgensGraph](https://github.com/skaiworldwide-oss/agensgraph)
