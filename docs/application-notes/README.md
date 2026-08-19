# Application notes

Domain patterns for **using** MemNet (not engine internals). Index: [`../README.md`](../README.md).

**Product shape:** [`../SHAPE.md`](../SHAPE.md).  
**Dialect teach:** openCypher-shaped **GQL** + shaped `pin_map` + gated mutate — [`../grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md). Product **0.8**; **1.0** = 0.5–0.8 claimed (no extra engine). PyPI `memnet-llm` is still **0.4.6**.  
**Worked GQL example:** [`examples/inverting-amplifier-gql-case-study.md`](examples/inverting-amplifier-gql-case-study.md).  
**Decision:** [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md). Versions: [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md).

Note **bodies teach GQL**. Historical Layer / Tier A ASCII lives under [`../grammar/archive/`](../grammar/archive/) only — not agent wire.

## Shared contract (every note)

MemNet is **mission working memory** — named session \(S\), bounded Recall Shape \(\tilde{X}\), gated \(\Delta\). Chat is never SSOT. Corpus RAG is **host Snap** (locators only), not the session.

| MUST | MUST NOT |
|------|----------|
| `session_open` with `SCHEMA` covering every kind you mutate (`map_file` / `map_lines`) | Game `schema.example.txt` unless that *is* the domain |
| Cue then `pin_map`; skip if the seed is empty | Dump \(S\); `query_warm` as primary; ANN / `rag_query` of \(S\) |
| `id:'NEW'` for goldfish creates; copy minted ids | Client `NEW` or invented ids on Path-B ingest / locator pins |
| MCP tool arg **`session`** | Tool arg `session_id` (JSON envelope may still *return* `session_id`) |
| In-process MCP for a single agent | In-process MCP under Multitask (use TCP / streamable-http) |

Kinds not in the open map fail `unknown_tag`. Bundled maps: `parts/common/memnet/memnet/examples/schema.*.example.txt`.

| Note | Role | Default map |
|------|------|-------------|
| [`examples/inverting-amplifier-gql-case-study.md`](examples/inverting-amplifier-gql-case-study.md) | InvAmp through **GQL-wire** (canonical `CST_*` ground ids) | `SCHEMA CST` + `TSK` in `map_lines` (no bundled circuit map) |
| [`examples/inverting-amplifier-memnet.md`](examples/inverting-amplifier-memnet.md) | InvAmp **math** SSOT + retired Layer encoding | — (not wire teach) |
| [`llm-circuit-schematic.md`](llm-circuit-schematic.md) | Schematic / s-domain (GQL) | same as GQL case study |
| [`llm-nodal-analysis-formulas.md`](llm-nodal-analysis-formulas.md) | Node method (GQL) | same as GQL case study |
| [`llm-sysml-v2-modeling.md`](llm-sysml-v2-modeling.md) | SysML v2 session goldfish | `schema.sysml.example.txt` **union** `schema.coding.example.txt` |
| [`llm-system-dev-multitask.md`](llm-system-dev-multitask.md) | Multitask in `modelbasedPrj-*` | sysml + coding (+ ingest maps as needed) |
| [`llm-software-development.md`](llm-software-development.md) | Multi-turn coding memory | `schema.coding.example.txt`; locators via `ingest_codebase` |
| [`llm-tech-docs-decomposition.md`](llm-tech-docs-decomposition.md) | Manual / SCPI atomisation | `schema.techdocs.example.txt` |
| [`llm-daily-news.md`](llm-daily-news.md) | RSS digest pipeline | project `memnet_schema.txt` (must list `KYWD` / `ENT` / …) |
| [`llm-mud.md`](llm-mud.md) | Multiplayer MUD | project world map (`ROM` / `CHR` / `OBJ` / …); shared serve |
| [`llm-build-on-memnet.md`](llm-build-on-memnet.md) | Custom MCP + skill pack | — (builder; in-process first) |
