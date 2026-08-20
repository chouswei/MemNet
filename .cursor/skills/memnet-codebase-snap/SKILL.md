---
name: memnet-codebase-snap
description: >-
  MemNet-powered snapshot and durable index of a C (or C-like) codebase.
  Files/modules as :MOD nodes; functions, variables (gvar/var), defines, structs,
  enums as :SYM nodes; relations (defines, calls, includes, owns, uses/reads/writes,
  constrained_by, etc.) as typed relationships. Supports full initial snap plus
  incremental re-snap. Enables low-token queries such as "where is X defined",
  "who calls Y", "what touches this ring buffer". Use for firmware/embedded work
  when the user asks for snap, memnet index, symbol graph, or "remember the
  functions and call structure". Primary example: weftTree Pico 2 + SIM7600 + IIS2ICLX.
metadata:
  pattern: pipeline
  version: "0.5"
  domain: memnet,codebase
token_guardrails: |
  - Verify on disk (Grep/Read) before mutate; never invent paths, symbols, or call edges.
  - Use pin_map + openCypher-shaped add/update (memnet-format); no pipe @TAG agent I/O.
  - Keep snap batches bounded; settle delete_on_settle TSK work so pin maps stay lean.
---

# MemNet Codebase Snap

**GQL wire** for `add`/`update` via shaped `pin_map`. See [memnet-format](../memnet-format/SKILL.md) and [coding-memory](../mcp-memnet/references/coding-memory.md). Product wire: `docs/grammar/gql-wire-profile.md`.

**Role:** Repeatable procedure to atomise a source tree (or delta) into MemNet:
- `:MOD` nodes for files
- `:SYM` nodes for functions and variables (and other symbols)
- Typed relationships for defines, calls, includes, uses, ownership, …

This gives fast, low-token navigation ("where is this fn/variable defined?", "who calls it?", "what state does this path touch?").

**Always pair with truth on disk:** Grep (ripgrep), Glob, Read, SemanticSearch first -- then `add`/`update` only confirmed facts.

## Before acting

1. Read the authoritative project guide if present: `AGENTS.md` (PAT) or equivalent.
2. Ensure the MemNet MCP is usable: `serve_status`; start `memnet serve` only if using TCP.
3. Read the tool schema for every MemNet tool before first `CallMcpTool` in a session.
4. Read once per significant snap session: `mcp-memnet` (coding-memory, atomisation) and `memnet-format`.
5. Open (or reuse) a session via `session_open`. For a bulk first pass, `ingest_codebase` (shipped Path-B) then `pin_map` — still **verify on disk** before trusting call/use edges.
6. Never invent ids -- copy from prior pin_map or the first `add` response.

## Core labels (coding memory)

MOD and SYM are **nodes**. Directed **relationships** connect them (and TSK/USR).

| Label | Typical props | Notes |
|-------|---------------|-------|
| MOD | path, lang, role, loc, recycle | one per `.c`/`.h`; lang=c\|cpp\|h; role=driver\|app\|hal\|calc\|uart\|mqtt\|platform |
| SYM | name, kind, path, line, sig, vis, recycle | kind=fn\|isr\|var\|gvar\|define\|macro\|struct\|enum\|typedef\|const |
| TSK | goal, phase, status, recycle | owning task; hang atoms via OWNS rels |
| Rel | TYPE + note, recycle | DEFINES, DECLARES, INCLUDES, CALLS, IMPLEMENTS, OWNS, USES, READS, WRITES, CONSTRAINED_BY, RELATED |

Mutate sketch:

```cypher
CREATE (m:MOD {id: 'NEW', path: 'src/i2c/iis2iclx_data_calc.c', lang: 'c', role: 'calc', loc: '~870', recycle: 'persistent'})
CREATE (s:SYM {id: 'NEW', name: 'iis2iclx_calc_push_sample', kind: 'fn', path: 'src/i2c/iis2iclx_data_calc.c', line: 108, recycle: 'persistent'})
CREATE (t:TSK {id: 'NEW', goal: 'Full structural index', status: 'in_progress', recycle: 'persistent'})
CREATE (m)-[:DEFINES {id: 'NEW', note: 'impl', recycle: 'persistent'}]->(s)
```

Stable id rules:
- Module: `MOD_` + path with `/` and `.` -> `_`
- Symbol: `SYM_` + short unique slug
- Rel: `E` + slug; copy ids from pin_map / add response
- Task: `TSK_` + short descriptive

Recycle: `persistent` for structural facts; `delete_on_settle` for investigation scratch.

## Snap workflow (initial full or targeted)

1. `serve_status` -> confirm OK.
2. `session_open` (once) supplying the label map above (plus any project USR seeds). Capture returned session id if given.
3. `pin_map` on a broad but useful anchor (e.g. an existing `TSK_codebase_snap_*` or a top-level `MOD_`) to see what is already known. Never assume the graph is empty. (`query_warm` is a legacy alias.)
4. Enumerate targets with `Glob`:
   - C/H focus: `src/**/*.c`, `src/**/*.h`, `include/**/*.h`, `lib/**/ads127*.h`
   - Supporting: `scripts/**/*`, `tools/**/*`, `docs/**/*.md`, `examples/**/README.md`, `.cursor/skills/**/*.md`, `.cursor/rules/**/*.mdc`
5. For each file (batch in mind; do not flood one turn):
   - `Read` the file (or sections via offset/limit for large ones).
   - Extract **nodes** with `Grep` (path-scoped):
     - Function definitions (kind=fn)
     - ISRs / weak handlers
     - Important variables (kind=gvar|var)
     - Public #defines / macros (kind=define)
     - Struct/enum/typedef at file scope
   - Note `#include` lines -> candidate INCLUDES relationships.
   - Derive one `:MOD` + N `:SYM` rows. Keep `sig` short (prototype head or `...`).
   - Verify on disk before emitting.
6. `add` (preferred) or `update` with a large `wire_lines` array (openCypher-shaped CREATE/MATCH-SET). 30-80 atoms comfortably.
7. After the batch: `pin_map(anchor="TSK_...", depth=1 or 2, max_rows=80)` to confirm and obtain ids.
8. **Mark relations** (core to the snap, not optional afterthought):
   - From the same file: DEFINES (MOD -> SYM, or SYM -> SYM for nested), OWNS, DECLARES.
   - Cross-file: INCLUDES, CALLS (verified call sites).
   - Data: USES, READS, WRITES, TOUCHES for important gvar access.
   - Architecture: BINDS, CONSTRAINED_BY where relevant.
   - Always emit at least ownership (`TSK OWNS MOD`, `MOD DEFINES SYM`) and the main control-flow / data-flow edges.
   - Full exhaustive call-graph is expensive; focus on primary execution paths and shared state first.
   - Use `query_walk` or narrow `pin_map` on a SYM to discover existing neighbours before adding duplicate edges.
9. `housekeep_stats` periodically; settle finished TSK phases with `update` + `delete_on_settle` so warm slices stay small.
10. Record any project conventions discovered as `:USR` atoms.

## Capturing the symbol relation graph

Functions and variables are **:SYM nodes**. Relations are **typed relationships** that make the graph queryable.

During the main snap:
- For every significant function SYM, record the DEFINES rel from its MOD.
- For the main execution skeleton, add CALLS edges (and reverse hints when helpful for warm slices).
- For shared state (rings, flags, thresholds as gvar SYM), add USES / READS / WRITES / TOUCHES.
- Record INCLUDES for the import structure.
- Use BINDS for registration / hook patterns.
- Keep edges sparse but architecturally meaningful. Answer "what calls this", "what touches this buffer", "what is the control flow" via `pin_map(anchor=SYM_..., depth=1..2)` or `query_walk`.

Discovery tips (always verify on disk):
- After you have a list of public function names, `Grep` for call sites excluding the definition line.
- For variables, `Grep` the bare name in other translation units.
- For each candidate edge, do a narrow `Read` of the call site or use site before writing the relationship.

## Incremental / edit-time snap

When the user edits a file (or you propose an edit):
- `pin_map` anchored on the `MOD_<that_file>` (or the owning `TSK`).
- Re-`Grep` + `Read` only the changed file (or the diff hunks).
- `update` the affected `:SYM` rows (line numbers, signatures) and any new/deleted symbols.
- Emit or update relationships for changed or new relations. Verify first.
- Never duplicate ids; `update` mutates in place.

After a multi-file refactor: re-snap the modified MODs + their SYM nodes, then walk INCLUDES / CALLS / USES and spot-check / repair them.

## PAT Nucleo firmware examples (same pattern everywhere)

| intent | anchor | action | notes |
|--------|--------|--------|-------|
| First time full index of quartet path | `TSK_codebase_snap_pat` (create if absent) | Glob + Grep; add MOD + SYM nodes; DEFINES + main CALLS | also capture important compile-time knobs as SYM (`kind=define`) or USR |
| Locate the blocking quartet read after context reset | `pin_map(anchor=SYM_ads127_read_quartet_blocking, depth=2)` | returns defining MOD, callers via CALLS, related TSK | if absent, Grep -> add SYM then call edges |
| Track a pin role change on 86ex5v90x HAT | `pin_map(anchor=MOD_...)` then Grep pins | update SYM for pins/config; add or repair CONSTRAINED_BY or USES | cross-ref project docs |
| Remember control flow that touches a shared ring | add SYM for ring + push/pop/service fns; connect with CALLS + USES | `pin_map` on the gvar or service fn | exactly what SYM nodes + typed rels enable |

## Verification and quality rules (non-negotiable)

- Every atom (MOD, SYM, or relationship) must be reproducible from a `Grep` or `Read` performed in the same or immediate prior turn.
- `sig` and `note` are short. No prose blobs.
- One fact / one node / one directed relationship per statement.
- After any substantial `add`/`update`, run a narrow `pin_map` and spot-check a few SYM signatures + a couple of relationships against source.
- Prefer `update` for existing ids.
- Run `housekeep_stats` when warned; settle transient TSK work.
- Only persist facts that affect runtime or build behaviour.

## Common anchors during development

- `TSK_*` — owns the MOD and SYM nodes for the current mission
- `MOD_<file>` — the file node + its defined SYM nodes
- `SYM_<name>` — a function or variable **node**; warm read gives its MOD plus connected neighbours

Increase `depth` only when you need the extra hop; always cap with `max_rows`. Use `query_walk` when you want the hop list instead of full rows.

## Related skills and references

- `mcp-memnet` (tool usage, goldfish loop, coding-memory.md, atomisation.md)
- `memnet-format` (GQL wire, leftover NEW named leftover, view budget, BIND vs relation)
- `docs/grammar/gql-wire-profile.md` for product wire
- Plain Markdown tables for in-turn handoffs before/after MCP calls (not TOON/TRON)

## Quick start checklist for a new snap session

- [ ] `serve_status` OK
- [ ] `session_open` with label map (once); MOD/SYM are nodes; typed rels are edges
- [ ] `pin_map` on TSK or a root MOD to see prior state
- [ ] Glob + Grep plan (functions + variables as SYM; calls/uses/includes as rels)
- [ ] Verify on disk -> emit nodes + rels in `add`/`update`
- [ ] `pin_map` + spot `Read` to confirm SYM signatures and relationships
- [ ] `housekeep_stats`; settle finished TSK phases

Use this skill when you need a durable, queryable index of **functions and variables (as nodes)** and their **call / data / ownership relations (as relationships)** across context resets.
