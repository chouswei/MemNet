# SysML MemNet snap -- canonical procedure (user pack)

**Wire:** agent mutate/read uses MemNet **GQL / shaped pin_map** ([memnet-format](../../memnet-format/SKILL.md)). Emit openCypher-shaped statements on the wire -- not pipe `@TAG` rows. Thin bridge: [sysml-gql](../../sysml-gql/SKILL.md).

Authoritative MemNet-first rules for SysML project roots. Pair with [sysml-memnet-patterns.md](sysml-memnet-patterns.md), [sysml-memnet-cookbook-bridge.md](sysml-memnet-cookbook-bridge.md), and [mcp-memnet](../../mcp-memnet/SKILL.md).

**Model root (pick one; do not mix):**

| Layout | Root | Snap dir |
|--------|------|----------|
| Multi-project pack | `sysml-v2-models/projects/<slug>/` | `…/projects/<slug>/.memnet/` |
| System repo (`modelbasedPrj-*`) | `sysml-models/` | `sysml-models/.memnet/` |

Copy the live root from repo `AGENTS.md` / `AGENT-CONTEXT.md`. NCU-LEO: `sysml-models/` + anchor `TSK_model_leo_cubesat`.

## Three stores -- one authority each

| Store | Authority for | Agent rule |
|-------|---------------|------------|
| `<model-root>/models/*.sysml` | Structure, syntax, satisfy links | Edit here first. Validate with `mcp-sysml-v2`. |
| MemNet (MCP) | Symbol index, locators, rationale, backlog | `pin_map` before edit; `add`/`update` after validate. |
| `AGENT-CONTEXT.md` | Human stub only | Session id + anchor only. Never duplicate topology/backlog. |

**Snap** = batch `add` of atomised GQL rows. Do **not** paste snap contents into chat.

## Mandatory turn sequence (6 steps)

| Step | Action | MemNet |
|------|--------|--------|
| **0** | MemNet MCP in catalog? If no -> edit `.sysml` only; skip 1-2 and 6. Plain Markdown (no TOON/TRON). | -- |
| **1** | `serve_status` only if TCP / unsure. If `running: false` -> edit `.sysml` only; skip 2 and 6. Under in-process default, skip this probe. | -- |
| **2** | `pin_map(anchor=TSK_model_<short>, depth=2, max_rows=50)`. | **READ** |
| **3** | Locate symbol (§Locate). Edit `models/*.sysml`. | -- |
| **4** | `mcp-sysml-v2 validate`. Fix until pass. | -- |
| **5** | `sysml-view-doc-sync` **iff** outputs exist and structure changed. For **`system-design-report/`** packs -> also MemNet report delta per [memnet-report-pipeline.md](../../system-design-report-generator/references/memnet-report-pipeline.md) when serve up. | -- |
| **6** | MemNet delta (§Delta write) + **pipeline settle** (§Pipeline wire). Required when step 4 changed symbols/traceability. | **WRITE** |

### Pipeline wire (steps 1-6)

After each step when MemNet is up, `add`/`update` one `:CLM` with `type='pipe'` and `code='sN:payload'` under `TSK_turn_*`; settle turn when done. Full template: [sysml-memnet-pipeline.md](sysml-memnet-pipeline.md). **Do not** keep pipeline step state only in chat when MemNet is up (use wire rows; plain Markdown only when down / MCP missing).

### Warm miss

- No `:TSK` for project anchor
- `:TSK` exists but zero `:PRT` / `:SYM` for non-greenfield project
- Wrong session / empty graph
- Snap/wire `path=` still cites a root that does not exist in the workspace (e.g. legacy `sysml-v2-models/…` under a `sysml-models/` system repo)

**On warm miss:** run §Initial snap once, then continue from step 3. If graph uses legacy `PARTD` / `PORTD` / `BEHD` / `TASK` kinds -> re-snap with unified labels.

### Step 6 skip (only)

| Case | Skip? |
|------|-------|
| Comment/whitespace only | Yes |
| MemNet MCP missing / `serve_status` false | Yes (note stale) |
| User question only; no `.sysml` edit | Yes |
| Any new/renamed symbol, port, connection, req, satisfy, allocate, behaviour | **No** |

## Identity and locators

### Stable keys

| Label | Pattern |
|-------|---------|
| `:TSK` | `TSK_model_<short>` |
| `:PRT` | `PRT_<name>` |
| `:POR` | `POR_<name>` |
| `:CON` | `CON_<linkName>` |
| `:BEH` | `BEH_<name>` |
| `:ITM` | `ITM_<name>` |
| `:REQ` | `REQ_<requirementId>` |
| `:MOD` | `MOD_<file_slug>` |
| `:SYM` | `SYM_<name>` |
| `:CONV` | `CONV_<topic>` |
| `:DEC` | `DEC_<nn>` |
| `:ISSUE` | `ISS_<nn>` |

### Ephemeral locator

- `:SYM` props: `path`, `line`, `kind`, `owner`
- **`line` is a hint.** Stable identity = **`name` + `path`**.

### `session_open` map

Use the **full canonical map** in [sysml-memnet-patterns.md](sysml-memnet-patterns.md) -- 19 kinds including `POR`, `BEH`, `ITM`, `CONV`, `DEC`, `ISSUE`.

### Example edges

```cypher
CREATE (:PRT {id: 'PRT_edgePc'})-[:DECLAREDIN {id: 'NEW', recycle: 'persistent'}]->(:PKG {id: 'PKG_FoamLiteVer2Deploy'})
CREATE (:SYM {id: 'SYM_edgePc'})-[:INFILE {id: 'NEW', note: 'loc', recycle: 'persistent'}]->(:MOD {id: 'MOD_deploy_vfdl2'})
CREATE (:PRT {id: 'PRT_edgePc'})-[:HASPORT {id: 'NEW', recycle: 'persistent'}]->(:POR {id: 'POR_ethernet'})
CREATE (:POR {id: 'POR_ethernet'})-[:TYPEDBY {id: 'NEW', recycle: 'persistent'}]->(:POR {id: 'POR_EthernetPort'})
CREATE (:PRT {id: 'PRT_edgePc'})-[:SATISFIES {id: 'NEW', recycle: 'persistent'}]->(:REQ {id: 'REQ_VFDL2-MQTT-RELAY'})
```

## Locate before edit (step 3)

**Read policy:** [sysml-memnet-read-policy.md](sysml-memnet-read-policy.md) -- per-turn budget, anti-patterns, decision tree.

1. `pin_map` on `PRT_*` / `POR_*` / `REQ_*` / `CON_*` / `SYM_*` -> `path`, `name`, `line`, link ends
2. **Only if editing:** `Read(path, offset=line-12, limit=35)` -- not full file
3. Window miss -> `Grep` exact name scoped to `path` from `:MOD`
4. Still ambiguous -> `mcp-sysml-v2` `getDefinition` or `getSymbols` (not bulk Read)
5. Grep/LSP line != stored line -> `update` `SYM.line` (self-heal)

**MUST NOT** open `deploy*.sysml` without `SYM.line` or validate error when MemNet is up and warm hit.

## Line drift (after edit)

| When | Action |
|------|--------|
| Before edit | Stored line as hint; grep if window miss |
| After validate (step 6) | Re-grep every `SYM.name` under touched `MOD`(s) -> batch `update` lines |
| Multi-file edit | Refresh locators per touched file only |
| Large refactor in one file | Re-grep whole file -> batch `update` all `:SYM` for that `:MOD` |

## Delta write (step 6)

| `.sysml` change | MemNet write |
|-----------------|--------------|
| New/changed part | `:PRT` + `:SYM` + rels (`declaredIn`, `inFile`) |
| New/changed port | `:POR` + `:SYM` + `hasPort` + optional `typedBy` |
| New/changed connection | `:CON` + `:SYM` + rels |
| New/changed requirement | `:REQ` + `:SYM` |
| satisfy / allocate in root or deploy | rel only `satisfies` / `allocates` |
| Behaviour edit | `:BEH` + `:SYM` |
| Item / flow | `:ITM` + rel `flowOf` |
| User chose between options | `update` `DEC.chosen`; settle `:DEC` |
| New convention | `:CONV` + `constrained_by` |
| Open backlog | `:ISSUE` or `:CLM` assumption |
| Any touched file | Re-grep all `SYM.name` under that `:MOD` -> batch `update` line |

**Batch rule:** new `:PRT` / `:POR` / `:CON` **MUST** include `declaredIn` + `inFile` in the **same** `add`/`update`.

Do **not** store full `.sysml` text or paragraph prose on any graph row.

## Initial snap (warm miss only)

1. `session_open` with full canonical map from [sysml-memnet-patterns.md](sysml-memnet-patterns.md)
2. `Glob` `<model-root>/models/*.sysml` (see layout table above)
3. Per file -- grep by role:

| File pattern | Grep / extract -> MemNet |
|--------------|-------------------------|
| `deploy*.sysml` | `part def`, `^\s*part\s+\w+`, `port def`, nested ports, top-level usages |
| `connections*.sysml` | `connection def`, `connect `, `link\w+` |
| `requirements*.sysml` | `requirement def`, `requirementId` |
| `behaviour*.sysml` | `state def`, `action def`, `perform action`, transitions |
| `root*.sysml` | imports -> `:PKG` kind=`root`; **`satisfy`** -> `:satisfies` |
| any file | `item def`, `flow of`, `allocate` |

4. Per file: one `:MOD` + N `:SYM` (with line) + semantic `:PRT` / `:POR` / `:CON` / `:REQ` / `:BEH` / `:ITM` + rels
5. One `add` batch 30-80 statements
6. `pin_map(anchor=TSK_model_<short>, depth=2)` to confirm
7. Write thin `AGENT-CONTEXT.md` if missing

## Session `.snap` file

Graph persistence **MUST** use MemNet server-side save/load:

```text
memnet session save --file <project>.snap
memnet session load --file <project>.snap
```

Agents **MUST NOT** paste `.snap` contents into chat. After load: `pin_map(TSK_model_*)` only.

Optional store path: `<model-root>/.memnet/<short>.snap` (not required in repo). For system repos this is typically `sysml-models/.memnet/`.

## AGENT-CONTEXT.md contract

Max 40 lines:

```markdown
# Agent context -- <slug>
**MemNet session:** `<mn_…>` · **Anchor:** `TSK_model_<short>`
## Summary
<5-10 lines human overview>
## MemNet
Query `TSK_model_<short>` -- do not duplicate topology/backlog here.
```

| Content | Store in |
|---------|----------|
| Session id, anchor, short summary | `AGENT-CONTEXT.md` |
| Topology, backlog, req trace | MemNet `:SEC` / `:CLM` / `:REQ` / `:ISSUE` |
| Symbol names, paths, line hints | MemNet `:SYM` / `:MOD` / `:POR` / `:BEH` |

## Incremental re-snap (after edits)

Same pattern as [memnet-codebase-snap](../../memnet-codebase-snap/SKILL.md): `update` affected `:SYM` rows; never duplicate ids.
