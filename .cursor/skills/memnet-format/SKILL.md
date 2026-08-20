---
name: memnet-format
description: >-
  MemNet GQL wire for shaped pin_map reads and openCypher-shaped mutate.
  Triggers: memnet format, GQL wire, pin map, pin_map, mutate NEW, shaped subgraph,
  openCypher mutate, view budget, bind vs relation.
metadata:
  pattern: tool-wrapper
  version: "4.2"
  domain: data-formats,memnet
  product: memnet-llm==0.9.0
token_guardrails: |
  - General GQL / paths: MemNet `docs/grammar/gql-wire-profile.md`; keep this skill MemNet-specific.
  - Prefer pin_map with a tight anchor + view/max_rows budget; do not dump the whole graph.
  - Mint creates with NEW; copy assigned ids from pin_map / mutate response — never invent colliding ids.
  - Port-port links use BIND; node-node links use typed relation labels.
---

# MemNet formats (LLM-facing)

**Audience:** model. Pair with [mcp-memnet](../mcp-memnet/SKILL.md) for tools.

**GQL wire only.** ISO/IEC 39075 elements: **node** (vertex), **edge** (relationship), **property**. Labels name kinds; ports / law / `id` / locators are property values. Agents read a bounded **shaped subgraph** from `pin_map` and write with **openCypher-shaped** mutate in the MCP envelope. Do **not** use TOON/TRON. Do **not** teach pipe `@TAG:…` as agent I/O. Do **not** teach Layer / Tier A. leftover `id:'NEW'` / leftover `--anchor` are leftover; product Commit is GraphElement `CREATE` / MCP **`mutate`**. Formal SSOT: `docs/grammar/gql-wire-profile.md`.

General GQL / path patterns live in the optional user pack (`graph-query-language`, `gql-path-patterns`). This skill keeps **MemNet-specific** conventions only.

Product notes: MemNet `README.md`, `docs/grammar/`, `docs/SHAPE.md`. Package **0.9.0** (PyPI still 0.4.6). Field notes: [references/memnet-wire-format.md](references/memnet-wire-format.md).

---

## Shaped pin_map (primary read)

MCP `pin_map` / CLI `query pin-map` returns a **shaped subgraph** (nodes + relationships around an anchor), not a session dump. Parse the tool envelope **`stdout`**.

| Control | Use |
|---------|-----|
| `anchor` | Ego id (`TSK_*`, `SYM_*`, `PRT_*`, …) — required unless `anchors` is set |
| `anchors` | Optional extra egos (0.5); one `max_rows`, one LAW prepend — prefer one live `TSK` |
| `depth` / `max_rows` | Bound fan-out; raise depth only when the slice is too thin |
| `view` | Optional budget: `shell` (tight) or `interior` (richer); omit for depth/max_rows only |

(`query_warm` is a deprecated alias for `pin_map`.)

**Cue then pin_map:** if the ego is unknown, MCP `find` / CLI `query find` (`limit` required) returns seed nodes only — copy an id, then `pin_map`. Do not treat `find` as goldfish read. Do not dump `MATCH … RETURN`.

Agent loop: cue -> `pin_map` -> reason -> mutate -> `pin_map`.

---

## openCypher-shaped mutate

Mutate via MCP `add` / `update` with **openCypher-shaped** statements in `wire_lines`. Sketch:

```cypher
CREATE (c:CLM {id: 'NEW', type: 'decision', code: 'bitrate cap 2000 bps', recycle: 'persistent'})
MATCH (t {id: $tid}) SET t.status = 'in_progress', t.phase = coalesce(t.phase, 0) + 1, t.recycle = 'persistent'
CREATE (n03)-[:HELPS {id: 'NEW', note: 'labour', recycle: 'persistent'}]->(t42)
MATCH ()-[e {id: $eid}]->() SET e.recycle = 'delete_on_settle'
MATCH ()-[e {id: $eid}]->() DELETE e
```

| Intent | Shape |
|--------|-------|
| Create node | `CREATE (n:Kind {id: 'NEW' \| knownId, …})` |
| Patch node | `MATCH (n {id: $id}) SET n.prop = …` — no relabel on patch |
| Create rel | `CREATE (a)-[:TYPE {id: 'NEW' \| …, …}]->(b)` |
| Patch rel | `MATCH ()-[r {id: $eid}]->() SET r.…` or match by endpoints + type |
| Drop rel | `MATCH ()-[r {id: $eid}]->() DELETE r` |
| Session schema | `SCHEMA Kind ; fields=id …` — registry only (`session_open` map) |

- **Create:** `id: 'NEW'` (or engine-accepted NEW mint) — copy assigned ids afterwards.
- **Update:** known ids only — NEW illegal on patch.
- **Properties:** short atoms (ids, paths, codes, numbers). Membership = relationships, not comma id-lists.
- **Quotes / params:** prefer `$param` binds; quote paths that need `\` or spaces.
- **Ingest pins:** stable locators (`path`, `qname`, …); no client NEW for those.

---

## Bind vs relation (MemNet encoding)

| Link | Encoding |
|------|----------|
| Port <-> port | Relationship type **`BIND`** (endpoint refs such as `Node.port`) |
| Node <-> node | Typed relation label (`HELPS`, `OWNS`, `SATISFIES`, `DEFINES`, …) |

Copy exact type spellings from the live pin_map. Do not invent a second spelling for the same link. Law / `ports` props may appear on structural nodes when the session schema carries them.

---

## When to use which label

| Need | Label |
|------|-------|
| Fact / claim | `:CLM` (+ relationships) |
| Directed relation | typed relationship |
| Flat membership | many rels (`MEMBER_OF`, `CONTAINS`, …) — not id lists in props |
| Work unit | `:TSK` |
| User constraint | `:USR` |
| File / symbol | `:MOD` / `:SYM` |
| Rule / policy | `:RUL` |
| SysML model atoms | see **SysML x MemNet** — do not invent kinds here |

**`rel` style (engine):** English verb / snake or upper type token per MemNet `docs/grammar/` and the live pin_map.

User-pack engine: Cursor HTTP **`10.0.0.10:18766/mcp`** bridging TCP serve **`:18765`** — see [mcp-memnet](../mcp-memnet/SKILL.md). Optional Neo4j extra is not live-claimed.

---

## SysML x MemNet

**SysML construct map, kind enums, closed rel list, and batch rules** are SSOT in [sysml-memnet-documentation](../sysml-memnet-documentation/SKILL.md) -> [sysml-memnet-patterns.md](../sysml-memnet-documentation/references/sysml-memnet-patterns.md). Thin turn loop: [sysml-gql](../sysml-gql/SKILL.md). Cache loop: [sysml-memnet-cache](../sysml-memnet-cache/SKILL.md).

| SysML v2 textual (grammar) | MemNet | Stable id |
|----------------------------|--------|-----------|
| `package` | `:PKG` | `PKG_<suffix>` |
| `part def` / part usage | `:PRT` (+ `:SYM` locator) | `PRT_<name>` |
| `port def` / port usage | `:POR` (+ `:SYM`) | `POR_<name>` |
| `connection` / `connect` / link | `:CON` (+ `:SYM`) | `CON_<name>` |
| `requirement` def/usage | `:REQ` (+ `:SYM`) | `REQ_<requirementId>` |
| `item def` / flow item | `:ITM` **node** (see [ITM pattern](../sysml-memnet-documentation/references/sysml-memnet-patterns.md#itm-is-a-node)) | `ITM_<name>` |
| `state def` / action / calc | `:BEH` (+ `:SYM`) | `BEH_<name>` |
| `assert` … `satisfy` | **rel only** `:SATISFIES` | — |
| `allocate` / `allocation` | **rel only** `:ALLOCATES` | — |
| `.sysml` file / edit locus | `:MOD` / `:SYM` | `MOD_<slug>` / `SYM_<name>` |

House anchors (copy, do not mint colliding prefixes): `TSK_model_<short>`, `TSK_diagram_<figureId>`, `USR_*`, plus the `PRT_` / `POR_` / `REQ_` / `BEH_` / `SYM_` / `MOD_` rows above. `satisfy` / `allocate` are never structure nodes — relationships only (`:SYM` only if a line locator is needed).

---

## Handoff tiers

| Priority | When | Format |
|----------|------|--------|
| 1 | Durable / multi-step with MemNet up | GQL / openCypher-shaped mutate |
| 2 | No session / same-turn scratch | Plain Markdown |
| 3 | Tool / MCP / CLI boundary | JSON envelope |
| 4 | Human deliverable | Prose Markdown |

---

## Atomisation (before every mutate)

1. Split fat rows into multiple nodes + relationships when possible.
2. Property values = short ids, paths, codes, numbers — no sentences.
3. Stable id from prior pin_map or mutate response.
4. No prose paragraphs on the wire.

Full discipline: [mcp-memnet/references/atomisation.md](../mcp-memnet/references/atomisation.md).

---

## Pre-write checklist

- [ ] pin_map on a tight anchor (view / max_rows budgeted); `find` first if ego unknown
- [ ] Values short and structured
- [ ] Relations are relationships (BIND for port-port)
- [ ] Recycle matches lifetime
- [ ] Atom reachable from a useful anchor

---

## Further reading

- [references/memnet-wire-format.md](references/memnet-wire-format.md) -- MemNet GQL field notes
- [mcp-memnet](../mcp-memnet/SKILL.md) -- tools and session loop
- [sysml-gql](../sysml-gql/SKILL.md) -- thin SysML x MemNet GQL bridge
- [sysml-memnet-documentation](../sysml-memnet-documentation/SKILL.md) -- SysML atomisation SSOT
- MemNet `docs/grammar/gql-wire-profile.md` -- wire SSOT
