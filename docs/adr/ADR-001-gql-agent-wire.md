# ADR-001: GQL as agent wire (MemNet brand retained)

**Status:** Accepted — **superseded on Layer** (see below)

**Date:** 2026-08-12

**Supersession (user direction, 2026-08-12):** **No Layer / Tier A** as agent wire, peer teach, or product accept path. One dialect only: **GQL (openCypher-shaped)**. Layer grammar sources are **dropped** from `docs/` — not doctrine. Wire profile SSOT: [`../grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md). The original migration table’s “Layer accept until M4” schedule is **withdrawn**.

**Context**

MemNet (Net of Memory) is **mission working memory for LLMs** — not the search corpus, not GraphRAG: multi-agent / Multitask sessions, goldfish re-read via shaped `pin_map`, gated mutate. A MemNet **session** can be SSOT for a mission / that shared memory — LLM handoff = **session id** (+ anchors / write scope); peers re-`pin_map`; chat is never SSOT ([`../multi-agent-sessions.md`](../multi-agent-sessions.md)). A durable online GQL store may sit **behind** sessions; it does not replace MemNet or the session handle for handoff, and is not the default agent teach surface. Through 0.4.x the agent teach/wire surface was a bespoke shared dialect (**Layer** / Tier A alias), with ISO GQL / openCypher held to a map and to the durable-store side (AgensGraph buffer sketch).

Three pressures reversed the prior “map only; MUST NOT teach GQL as wire” stance:

1. **Training priors.** LLMs already know Cypher-shaped ASCII (`MATCH` / `CREATE` / `(n)-[:R]->(m)`). Invent-syntax errors and teach cost for Layer remain higher than for openCypher-shaped GQL.
2. **Durable backing alignment.** Shared LLM memory plus optional AgensGraph backing is stronger when agent wire and store speak the **same family** of query language — without collapsing MemNet into a store proxy.
3. **Layer cost.** Maintaining Layer as teach (ANTLR, skills, application notes, codec paths) is real product cost — now **retired from doctrine**, not kept as a soft accept story.

This ADR does **not** abandon MemNet. It replaces **Layer / MemNet Grammar as agent wire** with **GQL (openCypher-shaped, AgensGraph-compatible)**. Brand and product remain MemNet — mission working memory, not a Cypher proxy and not a RAG corpus.

**Decision**

1. **Agent teach / wire = GQL (openCypher-shaped) only.**
2. **MemNet remains the product** — mission working memory for LLMs (engine, MCP, sessions, Multitask), not a RAG corpus. Pin-map *concept* = bounded shaped GQL subgraph via `pin_map`-class tool. A **session** is the SSOT handle for a mission: handoff = session id (+ anchors / scope); peers re-`pin_map`; chat is never SSOT.
3. **Layer / Tier A = dropped from docs** — not 1.x teach, not legacy-accept dual path. Leftover codecs remain in `memnet.layer` / `memnet.tier_a` and are rejected on mutate.
4. **Write = display redefined on GQL:** shaped subgraph emit — not raw tabular `RETURN`. Locked: **B with A’s emit shape** ([`gql-wire-profile.md`](../grammar/gql-wire-profile.md)).
5. **Do not invent a third peer dialect.**
6. **Durable store (M2.5) backs sessions** — hydrate/flush with one sync owner; **MUST NOT** replace the session handle for agent handoff, teach LLM↔store direct, or MemNet-as-Cypher-proxy as the goldfish path.

**Alternatives Considered**

| Option | Why not chosen |
|--------|----------------|
| **Keep Layer as 1.x wire; GQL map/store-side only** | Rejected — training prior + AgensGraph alignment. |
| **Dual teach / long Layer-accept era** | Rejected by supersession — doubles skills and error modes; user directed **no Layer**. |
| **Thin Cypher relay only (drop MemNet / “just a proxy”)** | Collapses shared LLM working memory — product value gone. |
| **Full ISO GQL DDL on agent wire in first cut** | Deferred. First cut = openCypher-shaped CRUD + bounded shaped read. |

**Consequences**

**Easier**

- Agents reuse Cypher priors; one teach surface.
- AgensGraph sync needs less conceptual translation.

**Harder / honest costs**

- Layer / Tier A leftover codecs remain on disk (`memnet.layer` / `memnet.tier_a`); default mutate **rejects** them (`legacy_dialect_retired`) — **M2 done**.
- In-repo playbook / application-notes teach GQL (**M3 / 0.8 done**). **User-pack** MemNet skills (`memnet-format`, `mcp-memnet`, …) may still migrate in `chouswei/cursor-user-skills` **in flight separately**.
- Dual EDGE, law-on-node, `view=`, `NEW` mint are frozen in [`gql-wire-profile.md`](../grammar/gql-wire-profile.md).

**Non-goals for first cut (M1–M2 wire)**

- Treat user-pack skill rewrite as this repo’s M3 gate (sibling repo; in flight separately).
- Teach full GQL schema/DDL or unbounded analytic `MATCH` as primary read.
- Implement or teach **every** openCypher CIP — family authority only; agent surface stays MemNet-gated (`pin_map` + mutate subset).
- Revive Layer as accept path.
- Ship AgensGraph sync as required for **M1/M2** wire (adapter is **M2.5**, not M1/M2).

**Migration plan (updated 2026-08-13)**

User promotion (2026-08-13): durable adapter named **M2.5** so M3 (playbook) did not block it. **All M-phases are done** (M2.5 = 0.7 live path; M3 = 0.8 GQL docs). **1.0** = claim, not a new M-phase.

| Phase | Action |
|-------|--------|
| **M0** | ADR accept; reverse “map only” stance. |
| **M1 (done)** | [`gql-wire-profile.md`](../grammar/gql-wire-profile.md); purge Layer from forward docs. |
| **M2 (done)** | Engine/MCP: GQL accept + shaped `pin_map` emit; remove Layer/Tier A from product codec path. |
| **M2.5 (done, 0.7)** | Durable online GQL store adapter **behind** shared LLM memory (MemNet ↔ AgensGraph hydrate/flush; one sync owner). Sketch: [`agensgraph-buffer.md`](../grammar/agensgraph-buffer.md). Live hydrate/flush proven (external cabinet; not vendored). **MUST NOT** reframe MemNet as a Cypher proxy. |
| **M3 (done, 0.8 docs)** | In-repo `LLM-GUIDE` body + application-notes examples → GQL. User-pack skill rewrite remains **in flight separately** (`chouswei/cursor-user-skills`). |

**Order (historical):** M1 → M2 → **M2.5** → M3. All done. **MUST NOT** treat the adapter as deferred, or hold **1.0** for Later items.

**Open question — locked in M1:** **B with A’s emit shape** (`pin_map`-class wrapper; shaped subgraph emit). Option C out. See wire profile.

**References**

- [`../grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md) — **M1 SSOT** (incl. external dialect authority)
- [`../grammar/agensgraph-buffer.md`](../grammar/agensgraph-buffer.md) — durable backing graph behind shared LLM memory (**M2.5**)
- [`../ROADMAP.md`](../ROADMAP.md) — one-path plan; phase order M2 → M2.5 → M3
- [openCypher CIP tree](https://github.com/opencypher/openCypher/tree/main/cip) — external dialect family home
- [oC9 baseline](https://github.com/opencypher/openCypher/tree/main/cip/0.baseline) (`openCypher9.pdf`) — Cypher 9 baseline
- [Adopted CIPs](https://github.com/opencypher/openCypher/tree/main/cip/1.adopted) / [testable CIPs](https://github.com/opencypher/openCypher/tree/main/cip/2.testable)
- [ISO/IEC 39075:2024 GQL](https://www.iso.org/standard/76120.html) — normative for GQL-native features (CIP may be informational only)
- [AgensGraph](https://github.com/skaiworldwide-oss/agensgraph)
- Optional: [CIP process](https://opencypher.org/cips/)
