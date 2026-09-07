# Application notes

How to **use** MemNet (not engine internals). Folders: **system** (repos / SysML / builder), **domains** (worked domains), **examples** (InvAmp). Index: [`../README.md`](../README.md).

**Product shape:** [`../SHAPE.md`](../SHAPE.md).  
**Dialect teach:** openCypher-shaped **GQL** + shaped `pin_map` + gated mutate — [`../grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md). Product **0.19.5.** Hatch **0.19.5**; published PyPI is **`memnet-llm==0.19.5`**. **1.0** = 0.5–0.8 claimed (unclaimed; no extra engine). Playbook: [`../LLM-GUIDE.md`](../LLM-GUIDE.md). Honesty `c` (`SHAPE_DROP_KEYS`): [`../operations/honesty-c-wire-audit.md`](../operations/honesty-c-wire-audit.md). Changelog: [`../../CHANGELOG.md`](../../CHANGELOG.md) **0.19.5**.  
**Worked GQL example:** [`examples/inverting-amplifier-gql-case-study.md`](examples/inverting-amplifier-gql-case-study.md).  
**Decision:** [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md). Versions: [`../ROADMAP.md`](../ROADMAP.md).

Note **bodies teach GQL**. Do **not** load Layer / Tier A / leftover line-codec as agent wire.

## Shared contract (every note)

MemNet is **mission working memory** — named session \(S\), bounded Recall Shape \(\tilde{X}\), gated \(\Delta\). Chat is never SSOT. Corpus RAG is **host Snap** (locators only), not the session.

| MUST | MUST NOT |
|------|----------|
| `session_open` with `SCHEMA` covering every kind you mutate (`map_file` / `map_lines`) | Game `schema.example.txt` unless that *is* the domain |
| Cue then `pin_map(q)` by labels + observable properties / keyword; skip if a *cued* seed is empty; CueConflict when \(|Q|>1\); **drop** prior maps from the prompt; empty \(q\) = outline (not `view=shell`) | Dump \(S\); stuff every map into `messages`; leftover `query_warm` as primary; ANN / `rag_query` of \(S\); Neo4j/Bolt as goldfish; leftover `--anchor` / leftover copy-id as law |
| Pattern Commit via `mutate` (`CREATE` / `MATCH…SET`); locators as properties; identity is the graph element, not a store key | leftover `id:'NEW'` mint; leftover `add`/`update` as TARGET; leftover copy-id `--anchor` as law; silent MERGE-by-name; treat nickname `id` / `hid` as identity |
| Shaped `pin_map` emit: labels + observable properties only (`SHAPE_DROP_KEYS` drops `hid` / `_memnet_hid` / `elementId`; nickname `id` stays off the wire) | Copy hid / `_memnet_hid` / `elementId` / nickname `id` from emit as identity; leftover `--anchor` as goldfish |
| MCP tool arg **`session`** | Tool arg `session_id` (JSON envelope may still *return* `session_id`) |
| In-process MCP for a single agent | In-process MCP under Multitask (use TCP / streamable-http) |
| Prefer **filter-out** (drop news / tighten cue / narrower scope) or **uncapped / high enough `max_rows`** so load-bearing kinds (`FND`, checklist, fundamentals) stay in \(\tilde{X}\). Engine \(M\) caps stay **hard rejects** — change cue/filter/scope, do not soften \(M\) | Hard-truncate a `pin_map` / Shape so FND / checklist / fundamentals drop; clip load-bearing kinds to fit \(M\); soften engine \(M\) |
| When `pin_map` / ShapeWalk hits a hard cap (`max_rows` / hop / budget) and the offer is **clipped**, the emit **MUST** carry an explicit **truncation signal** — same honesty family as **CueConflict** (visible on the wire, not silent). Treat that Shape as **incomplete**. Never claim a complete extract. Wire-flag honesty `c` MAY land in a sibling PR; this MUST holds even if the emit token follows | Silent clip; ignore a truncation mark; treat stderr `@WRN:` as the only signal; claim completeness under a truncating window |

Kinds not in the open map fail `unknown_tag`. Bundled maps: `parts/common/memnet/memnet/examples/schema.*.example.txt`.

| Note | Role | Default map |
|------|------|-------------|
| [`examples/inverting-amplifier-gql-case-study.md`](examples/inverting-amplifier-gql-case-study.md) | InvAmp through **GQL-wire** (canonical `CST_*` ground locators as properties) | `SCHEMA CST` + `TSK` in `map_lines` (no bundled circuit map) |
| [`examples/inverting-amplifier-memnet.md`](examples/inverting-amplifier-memnet.md) | InvAmp **math** SSOT (not wire teach) | — |
| [`llm-circuit-schematic.md`](domains/llm-circuit-schematic.md) | Schematic / s-domain (GQL) | same as GQL case study |
| [`llm-nodal-analysis-formulas.md`](domains/llm-nodal-analysis-formulas.md) | Node method (GQL) | same as GQL case study |
| [`llm-sysml-v2-modeling.md`](system/llm-sysml-v2-modeling.md) | SysML SSOT; relatives of one cue; sub-unit in a **separate session** | `schema.sysml.example.txt` **union** `schema.coding.example.txt` |
| [`llm-system-dev-multitask.md`](system/llm-system-dev-multitask.md) | Multitask in `modelbasedPrj-*` | sysml + coding (+ ingest maps as needed) |
| [`llm-software-development.md`](system/llm-software-development.md) | Multi-turn coding memory | `schema.coding.example.txt`; locators via `ingest_codebase` |
| [`llm-tech-docs-decomposition.md`](domains/llm-tech-docs-decomposition.md) | Manual / SCPI atomisation | `schema.techdocs.example.txt` |
| [`llm-daily-news.md`](domains/llm-daily-news.md) | RSS digest pipeline | project `memnet_schema.txt` (must list `KYWD` / `ENT` / …) |
| [`llm-mud.md`](domains/llm-mud.md) | Multiplayer MUD | project world map (`ROM` / `CHR` / `OBJ` / …); shared serve |
| [`llm-build-on-memnet.md`](system/llm-build-on-memnet.md) | Custom MCP + skill pack | — (builder; in-process first) |
