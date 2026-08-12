# ADR-001: GQL as agent wire (MemNet brand retained)

**Status:** Accepted — **superseded on Layer** (see below)

**Date:** 2026-08-12

**Supersession (user direction, 2026-08-12):** **No Layer / Tier A** as agent wire, peer teach, or product accept path. One dialect only: **GQL (openCypher-shaped)**. Historical Layer grammar is **quarantined** under [`../grammar/archive/`](../grammar/archive/) — not doctrine. Wire profile SSOT: [`../grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md). The original migration table’s “Layer accept until M4” schedule is **withdrawn**.

**Context**

MemNet (Net of Memory) is an agent memory product: bounded live pin map, goldfish re-read, Multitask shared sessions. Through 0.4.x the agent teach/wire surface was a bespoke shared dialect (**Layer** / Tier A alias), with ISO GQL / openCypher held to a map and to the durable-store side (AgensGraph buffer sketch).

Three pressures reversed the prior “map only; MUST NOT teach GQL as wire” stance:

1. **Training priors.** LLMs already know Cypher-shaped ASCII (`MATCH` / `CREATE` / `(n)-[:R]->(m)`). Invent-syntax errors and teach cost for Layer remain higher than for openCypher-shaped GQL.
2. **AgensGraph buffer.** The durable thesis (MemNet as working-memory buffer in front of Postgres + property graph) is stronger when agent and store speak the **same family** of query language.
3. **Layer cost.** Maintaining Layer as teach (ANTLR, skills, application notes, codec paths) is real product cost — now **retired from doctrine**, not kept as a soft accept story.

This ADR does **not** abandon MemNet. It replaces **Layer / MemNet Grammar as agent wire** with **GQL (openCypher-shaped, AgensGraph-compatible)**. Brand and product remain MemNet.

**Decision**

1. **Agent teach / wire = GQL (openCypher-shaped) only.**
2. **MemNet remains the product name** (engine, MCP, sessions, Multitask ops). Pin-map *concept* = bounded shaped GQL subgraph via `pin_map`-class tool.
3. **Layer / Tier A = archived historical only** — not 1.x teach, not legacy-accept dual path. Sources under `docs/grammar/archive/`.
4. **Write = display redefined on GQL:** shaped subgraph emit — not raw tabular `RETURN`. Locked: **B with A’s emit shape** ([`gql-wire-profile.md`](../grammar/gql-wire-profile.md)).
5. **Do not invent a third peer dialect.**

**Alternatives Considered**

| Option | Why not chosen |
|--------|----------------|
| **Keep Layer as 1.x wire; GQL map/store-side only** | Rejected — training prior + AgensGraph alignment. |
| **Dual teach / long Layer-accept era** | Rejected by supersession — doubles skills and error modes; user directed **no Layer**. |
| **Thin Cypher relay only (drop MemNet buffer)** | Collapses product value. |
| **Full ISO GQL DDL on agent wire in first cut** | Deferred. First cut = openCypher-shaped CRUD + bounded shaped read. |

**Consequences**

**Easier**

- Agents reuse Cypher priors; one teach surface.
- AgensGraph sync needs less conceptual translation.

**Harder / honest costs**

- As-is 0.4.x Python may still parse old line dialects until **M2** removes them — implementation lag, not doctrine.
- Skills and application-notes bodies still need **M3** GQL rewrite; doctrine headers already point at GQL.
- Dual EDGE, law-on-node, `view=`, `NEW` mint are frozen in [`gql-wire-profile.md`](../grammar/gql-wire-profile.md).

**Non-goals for first cut**

- Full application-notes body rewrite (M3).
- Ship AgensGraph sync adapter.
- Teach full GQL schema/DDL or unbounded analytic `MATCH` as primary read.
- Revive Layer as accept path.

**Migration plan (updated)**

| Phase | Action |
|-------|--------|
| **M0** | ADR accept; reverse “map only” stance. |
| **M1 (this)** | [`gql-wire-profile.md`](../grammar/gql-wire-profile.md); purge Layer from forward docs; archive Layer grammar. |
| **M2** | Engine/MCP: GQL accept + shaped `pin_map` emit; remove Layer/Tier A from product codec path. |
| **M3** | `LLM-GUIDE` body, user-pack skills, application-notes examples → GQL. |

**Open question — locked in M1:** **B with A’s emit shape** (`pin_map`-class wrapper; shaped subgraph emit). Option C out. See wire profile.

**References**

- [`../grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md) — **M1 SSOT**
- [`../grammar/archive/README.md`](../grammar/archive/README.md) — quarantined Layer sources
- [`../grammar/agensgraph-buffer.md`](../grammar/agensgraph-buffer.md) — durable buffer sketch
- [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md) — one-path plan
- [ISO/IEC 39075:2024 GQL](https://www.iso.org/standard/76120.html)
- [AgensGraph](https://github.com/skaiworldwide-oss/agensgraph)
