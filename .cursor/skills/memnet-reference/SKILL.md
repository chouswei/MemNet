---
name: memnet-reference
description: >-
  Load when working in this MemNet (Net of Memory) repository on the agent
  memory graph, MCP sessions, live pin-map reads, or graph mutates (including
  minting ids with NEW) — triggers: MemNet, pin map, MCP session, mutate NEW,
  pin_map, memnet-mcp, Net of Memory, MutateGate, shared dialect,
  Write=display. Explains the shared agent read/write dialect (Write=display —
  same NODE|EDGE shapes for display and mutate), parts layout, and doctrine
  SSOT pointers. Use before inventing a wire dialect or restoring novel-writer.
metadata:
  pattern: pipeline
  version: "1.10"
  domain: memnet
  product: "0.3.5"
---

# MemNet project reference

Repo skill for agents using MemNet in **this** repository. Doctrine SSOT lives in docs below — do not duplicate or invent features here.

**Product version:** `project.toml` / PyPI **`memnet-llm==0.3.5`** (CLI command remains `memnet`).

## Mission

**MemNet** (Net of Memory) is an **agent memory graph** (NODE | EDGE) between LLM call pipelines and data search. Agents read a bounded **live pin map** each turn and write with the **same shapes** — that **shared dialect** (Write = display). Code/harness may still say "Tier A" for the same dialect; prefer **shared dialect** in agent text. Aims (MN-REQ-00): save wall-clock time and tokens while keeping factual accuracy. Aids **system**, **programme**, **software**, **firmware**, **hardware**, and **documentation**. Transport: **in-process first**. This repo is **engine + generic memnet-mcp** only — novel-writer dropped.

## Agent I/O (shared dialect)

- **Shared dialect only** for agent I/O: **Write = display** means shared NODE | EDGE field shapes for live read and mutate (copy what you see).
- **Mutate** uses ops: `+` create, `~` update, `-` drop. May use `[NEW]` / leading `NEW` so the engine mints ids. On `~` only, numeric fields may use `key+=N` / `key-=N` (absolute values on pin map).
- **Live pin map** output is **bare present** (assigned ids, **no** leading `+`/`~`/`-`). Ops are mutate-only.
- **Session map** (`session open --map-file`): shared-dialect `SCHEMA KIND ; fields=id …` (legacy `@TAG: id|…` still loads).
- LLM creates: mint with `NEW`. Pin-map ingest (SysML, codebase, PCBA, skills): **stable locators** (`refdes=`, `path=`, `qname=`, ...); reject client `NEW` for those pins. PCBA schematics use Atopile **`.ato`**.

Formal shapes / validation: `docs/grammar/` (`MemNet.g4`, golden fixtures, `tools/tier_a.py`) — **keep** that precision; do not invent a thinner dialect. `docs/LLM-GUIDE.md` remains operational (still largely pipe-centric) until migrated.

## Transport

**In-process first**; TCP localhost (`MEMNET_MCP_TRANSPORT=tcp` / `memnet serve`) as migration fallback.

## Agent loop

```text
pin map → reason → mutate → pin map
```

Primary read: live **pin map** (bounded ego/anchor digest). MCP `pin_map` / CLI `query pin-map`. Legacy aliases: `query_warm` / `query warm`.

## Canonical paths

| Need | Path |
|------|------|
| Doctrine / quick start | `README.md` |
| Shared-dialect grammar design | `docs/grammar/` |
| Field formulas (generic design) | `docs/grammar/memnet-field-formulas.md` (formula as EDGE / `derives` — any domain) |
| Multi-layer (design) | `docs/grammar/memnet-multi-layer.md` (law on node `CST`+`ports=`/`law=`; dual EDGE bind/relation; nesting = pin-map view; no FN) |
| Nodal circuitry (app note) | `docs/application-notes/llm-nodal-analysis-formulas.md` (*uses* formula edges; does not define them) |
| Neighbourhood reserve (design) | `docs/grammar/memnet-neighbourhood-reserve.md` |
| Security / session ACL / multi-agent (design) | `docs/grammar/memnet-security-multi-agent.md` |
| Agent playbook (as-is pipe) | `docs/LLM-GUIDE.md` |
| Core library | `parts/common/memnet/` |
| Generic MCP | `parts/memnet-mcp/` |
| SysML models | `sysml-models/` |
| Layout / hub | `LAYOUT.md`, `AGENTS.md` |
| Novel-writer drop | `DROP-NOVEL-WRITER.md` |

Part-based folders only — do not recreate top-level `src/` or `applications/`.

## MCP (generic memnet)

Implementation: `parts/memnet-mcp/` (`server.py` = tool SSOT). Transport defaults to **in-process**. Register MemNet MCP **once** (prefer project `.cursor/mcp.json`; do not also enable user-level `memnet`). Always pass the same `session` id.

### Tool <-> grammar

| Tool | Grammar role |
|------|----------------|
| `session_*` | Lifecycle / snapshot — not NODE/EDGE body |
| `pin_map` | **Live pin map** — bare present in `stdout` (`query_warm` is legacy alias) |
| `query_walk` | Hop debug |
| `add` / `update` | Mutate — shared dialect in `wire_lines` (`+`/`~`/`-`, `NEW`) |
| `read_get` / `read_list` | Lookup / enumerate |
| `housekeep_stats` / `serve_status` | Caps / transport probe |

Wire shapes: shared dialect for agent I/O (`docs/grammar/`). Legacy `@TAG` pipe may still be accepted on mutate/import — do not teach it as preferred agent format. User-pack map detail: skill `mcp-memnet` → `references/tool-grammar.md`.

## MUSTNOT

- Invent ids when a pin map already shows them — copy assigned ids.
- Feed `@TAG` pipe as the agent-facing dialect (store/legacy only; shared dialect for LLM I/O). Includes `@RSV:` / `@SES:` / `@ACL:` — use bare present `RSV` / `SES` / `ACL` lines instead (design).
- Recommend TOON/TRON for handoffs — shared dialect or plain Markdown.
- Restore `parts/novel-writer/` or novel MCP extras.
- Route agents to personal Cursor / user-pack skills from this repo.

## When ids must match model / schematic

**Decision rule:** if the row is a **pin into an external artefact** (SysML qname, `.ato` refdes/net/pin, codebase path, skill id) → **stable locator path**. If it is a **new MemNet-only fact** (decision, task, note) with no external id → **`[NEW]`**.

| Path | Use when | Id rule |
|------|----------|---------|
| **B — pin / ingest** | Must align with model or schematic | Deterministic ground id + locator fields; **no** client `NEW` |
| **A — goldfish** | Annotation / memory fact only | `+ KIND [NEW]`; engine mints; copy thereafter |

**Form ground ids from the source** (illustrative; keep ASCII):

| Source | Ground id examples | Locator fields |
|--------|--------------------|----------------|
| PCBA `.ato` | `ATO_R1`, `NET_GND`, `PIN_U2_3` | `refdes=`, `net=`, `pin=`, `path=` |
| SysML | `PRT_PowerDistribution`, `REQ_MN_REQ_02_1` | `name=`, `qname=`, `requirementId=` |
| Codebase | `MOD_wire`, `SYM_split_payload` | `path=`, `line=`, `signature=` |
| Skills | `SKL_memnet_format` | `skill_id=`, `phrase=` |

**`NEW` is forbidden** for: schematic/model pins on ingest; re-creating an element that already has a pin; any `~` / `-` line.

**Re-id (wrong ground id):** `~ [OldId] ; id=NewId` on `update`. If `NewId` exists → `id_occupied` unless `; merge=true` (fold mistaken mint into locator id; retarget edges; drop OldId). Self `id=OldId` is a no-op. Not the MCP tool rename `query_warm`→`pin_map`.

**Multi-agent / session access (design):** limit the session first — ACL modes (`private` / `shared` / `open`), roles (`owner` / `writer` / `reader`), engine-minted **`session_token`** (not obscurity of `session_id`). Then neighbourhood **reserve** (`llm_id` + TTL) for coop inside an authorised session. Pin map may show `SES` / `ACL` / `RSV` present lines. SSOT: `docs/grammar/memnet-security-multi-agent.md` + `docs/grammar/memnet-neighbourhood-reserve.md`. Not implemented in 0.3.5.

**Lookup before write** (same session):

1. Know ground id → `read_get(id=ATO_R1)` or pin map `pin_map(anchor=ATO_R1, …)`.
2. Know only schematic field → `read_list(tag=CMP, where=["refdes=R1"])` (or `net=`, `qname=`, …) → then warm on the returned id.
3. If missing and alignment is required → create once with **explicit id + locators** (seed / bootstrap), not `NEW`:

```text
+ CMP [ATO_R1] ; refdes=R1 ; value=10k ; path=boards/pdu/pdu.ato ; recycle=persistent
+ CLM [NEW] ; type=decision ; code=R1 stays 10k ; recycle=persistent
```

(After create, copy the minted `CLM…` id from ack/re-warm, then `+ NEW [CLM…] --(about)--> [ATO_R1]`. Prefer create → assigned ids → edge. `add` fails if the id already exists — look up first.)

**0.3.5:** Path A vs B remains valid. PinMapIngest_* may still be stubs; agents may seed pins via `session_open` `seed_lines` or `add` with explicit locator ids. Prefer ingest when available. SSOT: `docs/grammar/memnet-grammar-design.md` §4.2.1.

## Pre-write checklist

1. Pin map first (`pin_map`) before inventing structure.
2. External artefact → locator ground id; goldfish fact → `NEW`; known id for update/settle.
3. Atomise: one fact per row; relations as edges; short field values (no prose blobs).

## Related (in-repo only)

| Path | Role |
|------|------|
| `.cursor/skills/memnet-reference/` (this) | Repo doctrine + routing |
| `README.md`, `docs/grammar/` | SSOT doctrine / shared dialect |
| `parts/memnet-mcp/` | Generic MCP |
| `sysml-models/` | SysML models |
| `AGENTS.md` | Hub / policy |
