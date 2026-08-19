---
name: sysml-memnet-documentation
description: >-
  MemNet MCP for SysML v2 design memory and model snap: atomised graph (parts, ports, connections, behaviour,
  locators, rationale), mandatory pin_map before edit, delta write after validate. Also outputs/*.md and
  system design reports. Triggers: memnet sysml, sysml memnet, model snap, goldfish sysml, memnet outputs,
  design memory sysml, TSK_model, AGENT-CONTEXT memnet, sysml knowledge graph, read sysml, memnet vs sysml, avoid re-read deploy.
metadata:
  pattern: pipeline
  secondary: tool-wrapper
  domain: sysml,memnet
  version: "1.10"
  pairs_with: [sysml-memnet-cache, sysml-modeling-workflow, mcp-memnet, memnet-codebase-snap, sysml-view-doc-sync, mcp-sysml-v2, mcp-sysmledgraph, memnet-format, sysml-gql]
token_guardrails: |
  - Follow the 6-step turn sequence in references/sysml-memnet-snap.md; pin_map before substantive edits.
  - MUST follow references/sysml-memnet-read-policy.md: topology from warm; ≤2 narrow Read windows per turn; no full deploy re-read.
  - MUST follow references/sysml-memnet-pipeline.md: pipeline step atoms via GQL/openCypher-shaped mutate when MemNet is up; plain Markdown when down (not TOON/TRON).
  - Use unified labels PRT/POR/BEH with kind prop; MUST NOT write PARTD/PORTD/BEHD/TASK aliases.
  - Atomise first: one fact per node/rel; short props; never store full .sysml or paragraph prose.
  - Copy stable ids from pin_map; refresh SYM.line after every validated edit.
  - satisfy/allocate -> relationships only (SATISFIES, ALLOCATES); SYM only for line locators.
  - AGENT-CONTEXT.md: agents read session+anchor only; topology/backlog live in MemNet.
  - If MemNet MCP is missing from the catalog, or serve_status false (TCP): skip MemNet read/write; plain Markdown only.
---

# SysML MemNet (design memory + model snap)

**Layout:** `SKILL.md` + references (load order below).

**Entry point for “use MemNet as cache”:** [sysml-memnet-cache](../sysml-memnet-cache/SKILL.md) — specialist `sysml-*` skills defer read/write there.

**Durable graph memory** for SysML v2 projects: symbol index with file/line locators, ports, connections, behaviour, design rationale, and documentation atoms. Complements `mcp-sysmledgraph` (structural impact) and `mcp-sysml-v2` (validate/parse).

MemNet stores **structure + atomic facts** (not full prose). **Do not re-read `deploy*.sysml` for topology** when pin_map has PRT/CON -- see [sysml-memnet-read-policy.md](references/sysml-memnet-read-policy.md). Tools: [mcp-memnet](../mcp-memnet/SKILL.md); GQL wire: [memnet-format](../memnet-format/SKILL.md). Thin SysML bridge: [sysml-gql](../sysml-gql/SKILL.md).

## Read policy (mandatory)

**Discovery:** `pin_map` -> PRT / CON / SYM / REQ. (`query_warm` is legacy alias.)  
**Edit:** `Read(path, offset=line-12, limit=35)` at SYM.line only.  
**Forbidden per turn:** full deploy read; re-grep names already in warm; multi-file read without warm miss.

Full rules: [sysml-memnet-read-policy.md](references/sysml-memnet-read-policy.md).

## Reference load order

1. [references/sysml-memnet-snap.md](references/sysml-memnet-snap.md) — **mandatory** 6-step sequence, grep, delta, `.snap`
2. [references/sysml-memnet-read-policy.md](references/sysml-memnet-read-policy.md) — **when to read `.sysml`** vs warm (anti-patterns, read budget)
3. [references/sysml-memnet-pipeline.md](references/sysml-memnet-pipeline.md) -- **pipeline handoffs** (GQL/shaped step atoms)
4. [references/sysml-memnet-patterns.md](references/sysml-memnet-patterns.md) -- canonical 19-kind map, construct table, closed rel list
5. [references/relatives-cache-map.md](references/relatives-cache-map.md) -- **which specialist skill writes which kinds**
6. [references/sysml-memnet-cookbook-bridge.md](references/sysml-memnet-cookbook-bridge.md) -- upstream cookbook pointer, unified-kind policy
7. [sysml-gql](../sysml-gql/SKILL.md) -- thin turn loop + construct abbrev
8. Upstream cookbook -- MemNet `docs/application-notes/llm-sysml-v2-modeling.md` (worked turns)

Pair with [sysml-modeling-workflow](../sysml-modeling-workflow/SKILL.md) and [memnet-codebase-snap](../memnet-codebase-snap/SKILL.md).

## Prerequisites

1. Repo install for **0.9**: `pip install -e ".[mcp]"` from MemNet (PyPI `memnet-llm` is still **0.4.6**). Extra cabinet client: `.[mcp,neo4j]` (live Neo4j unclaimed).
2. MemNet entry in `~/.cursor/mcp.json` (in-process preferred; see [mcp-policy.md](../mcp-memnet/references/mcp-policy.md)).
3. MemNet MCP tools visible in the session catalog. If absent: treat as serve down — no `pin_map` / mutate.
4. Under TCP only: `memnet serve` + optional `serve_status`. Skip that probe under in-process default.

## When to use

- Opening or resuming work on a SysML project root:
  - Multi-project pack: `sysml-v2-models/projects/<slug>/`
  - System repo (`modelbasedPrj-*`): `sysml-models/` (NCU-LEO anchor `TSK_model_leo_cubesat`)
- Recording design decisions, assumptions, backlog not fully expressed in `.sysml`
- Maintaining `outputs/*.md` / system-design-report atoms (ART/SEC/CLM)
- Multi-turn refactors, requirement audits, report updates

**Skip MemNet** when: one-shot question with no edit; comment-only `.sysml` change; MemNet MCP missing from catalog; or `serve_status` false (TCP).

## Atomisation (docs + model)

Model elements: PRT/POR/CON/BEH/ITM/REQ + SYM (path, line) + MOD per file. Conventions: CONV. Open forks: DEC. Backlog: ISSUE. Docs: ART/SEC/CLM. Campaign: TSK_model_<short>.

ITM is a **node** only (item definition / flow item); see [the ITM pattern](references/sysml-memnet-patterns.md#itm-is-a-node).

## Pairing

- **sysml-modeling-workflow** — encodes the 6-step sequence
- **system-design-report-generator** — full pack generate/maintain: pin_map before prose, ART/SEC/CLM after sync ([memnet-report-pipeline.md](../system-design-report-generator/references/memnet-report-pipeline.md))
- **sysml-view-doc-sync** — sync outputs, then atomise key claims as CLM
- **sysml-refactorer**, **sysml-traceability**, **sysml-requirements-audit** — persist findings after work
- **memnet-format** — MemNet GQL wire; thin SysML x MemNet kind/id pointer only
- **mcp-sysmledgraph** — impact/rename; record intent in MemNet
- **mcp-memnet** — base MCP mechanics

## Quick anchors

| Anchor | Use when |
|--------|----------|
| `TSK_model_<short>` | Start/resume project session (NCU-LEO: `TSK_model_leo_cubesat`) |
| `TSK_diagram_<figureId>` | Mermaid placement graph ([mermaid-placement-by-degree.md](../mermaid/references/mermaid-placement-by-degree.md)) |
| `SYM_<name>` | Jump to edit location (path + line) |
| `PRT_<name>` / `POR_<name>` | Part or port + linked claims/reqs |
| `BEH_<name>` | Behaviour under edit |
| `REQ_<requirementId>` | Requirement audit / satisfy |
| `DEC_<nn>` | Pending design choice |
| `CONV_<topic>` | Site convention |
| `ART_<project>-design` | Outputs / report pack |

## References

- [sysml-memnet-snap.md](references/sysml-memnet-snap.md)
- [sysml-memnet-read-policy.md](references/sysml-memnet-read-policy.md)
- [sysml-memnet-pipeline.md](references/sysml-memnet-pipeline.md)
- [sysml-memnet-patterns.md](references/sysml-memnet-patterns.md)
- [sysml-memnet-cookbook-bridge.md](references/sysml-memnet-cookbook-bridge.md)
- [mcp-memnet](../mcp-memnet/SKILL.md), [memnet-goldfish-loop.mdc](~/.cursor/rules/memnet-goldfish-loop.mdc)
- [sysml-modeling-workflow](../sysml-modeling-workflow/SKILL.md)
