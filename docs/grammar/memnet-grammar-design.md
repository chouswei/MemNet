# MemNet grammar design

> **Not agent teach.** Agent wire SSOT: [`gql-wire-profile.md`](gql-wire-profile.md) (**GQL only**).  
> This file documents the **as-is** line-codec / harness (`tier_a` package names). Default mutate **rejects** Layer/Tier A (**M2 done**). Do **not** teach Tier A / Layer as wire.

**Status:** as-is harness / historical design (not GQL teach SSOT)  
**Audience:** codec owners (archive/tests; product accept is GQL)  
**Aligns with:** MN-REQ-00, MN-REQ-02, MN-REQ-08, MN-REQ-09, MN-REQ-10, MN-REQ-11 (engine as-is)  
**Lineage:** legacy line dialect + `@TAG` pipe (import-once)  
**British English.** Paths ASCII.

**Naming:** package `memnet.tier_a` / `tools/tier_a.py` are **as-is engine** identifiers — not agent teach names.

---

## 1. Goals and non-goals

### Goals

| Goal | Requirement hooks |
|------|-------------------|
| One **LLM-facing** dialect for stdio + MCP memory payloads | MN-REQ-08.1–08.2, 08.5 |
| **Write = display** — same shapes in live **pin map** emit and agent mutate | MN-REQ-08.7, 08.6, 08.8 |
| Express exactly **NODE** and **EDGE** (tags realise node kinds only) | MN-REQ-02.* |
| **Prompt-rule** friendly: low noise, template-copyable, not hostile positional dumps | MN-REQ-08.3, 08.6, 10.5, 10.6 |
| **Canonical parser** recovers structure; reject invalid wire | MN-REQ-09.*, 02.6, 10.7 |
| Pin map / snapshot presentation = **map of pins**, not corpus dump | MN-REQ-11.13, 04.*, 10.2–10.3 |
| Store may keep a denser internal form if boundaries still show the friendly surface | MN-REQ-08.4 |

### Non-goals (this design)

- Rewriting `parts/common/memnet` parsers in this pass.
- Novel-writer / play-loop product grammar (novel-cut is **reference only**).
- Making ad-hoc compact encodings (e.g. former TOON/TRON) the durable graph language — handoffs use plain Markdown or domain wire only.
- JSON as the agent memory dialect (JSON stays at MCP/CLI **envelope** boundaries only).
- Embedding full SysML / source files in the live pin map (pin map only).

---

## 2. Thesis (one paragraph)

MemNet’s agent language is a **single shared dialect of NODE and EDGE lines** (Write = display) — English-keyed fields, explicit triple arrows, short pins — so the LLM copies what it reads; the internal store holds NODE|EDGE records without a second agent dialect; live pin maps and snapshots are **ego digests of pins**, not full copies; one canonical parser is the only supported structure-recovery path for humans and tools. Legacy `@TAG` pipe may be imported once from old session files, then discarded (not preferred agent I/O).

---

## 3. Layering

```text
┌─────────────────────────────────────────────────────────┐
│  Agent I/O — shared dialect (this grammar; aka Tier A)  │
│  Shared shapes. Pin map = bare present; mutate = +/~/-. │
│  NODE / EDGE lines + optional section headers + pins.   │
└───────────────────────────┬─────────────────────────────┘
                            │ project (parse / emit)
┌───────────────────────────▼─────────────────────────────┐
│  Internal graph store                                   │
│  In-memory NODE | EDGE records (not a second agent      │
│  dialect; not @TAG pipe as standing store wire).        │
└───────────────────────────┬─────────────────────────────┘
                            │ envelope only
┌───────────────────────────▼─────────────────────────────┐
│  Transport                                              │
│  MCP/CLI JSON {args, stdin, stdout, stderr}             │
│  (in-process primary; local IPC / TCP migration).       │
└─────────────────────────────────────────────────────────┘

Deprecated footnote (not a peer agent dialect):
  Legacy @TAG pipe session files MAY be imported once then gone.
  Pipe is not preferred agent I/O and not the target store codec.
  Import productions / migration modules may still exist — keep them
  specified; do not teach pipe as the agent write surface.

Handoff contrast (not MemNet grammar):
  Plain Markdown tables / short prose = serve-down scratch between LLM steps
  Prose Markdown = human operator deliverable
  (Do not use TOON/TRON — they do not meaningfully save tokens.)
```

**Identity rule:** conceptual kinds are always NODE | EDGE. Surface spellings (`CLM`, `TSK`, …) are **node kinds**, not extra conceptual kinds (MN-REQ-02.7).

**Law-on-node / stratified pin map (design only):** still NODE|EDGE — see [`memnet-multi-layer.md`](memnet-multi-layer.md). Law leaf prefers `CST` with `law=` + `ports=` fields; dual EDGE — port↔port **bind**/`pipe`, node↔node **relation**; first-class `PORT` only if needed; nesting is a pin-map view budget, not a kind zoo. Distinct from this §3 I/O / store / transport layering.

---

## 4. Abstract syntax

### 4.1 Core records

```text
Node  = { kind, id, fields: Map[Key → Value], recycle? }
Edge  = { id?, from: Id, rel: Rel, to: Id, fields: Map[Key → Value], recycle? }
```

- **kind** — short uppercase token realising a node type (`TSK`, `CLM`, `MOD`, `PRT`, …). Not a third conceptual kind.
- **id** — stable session-scoped identifier. The LLM **does not invent** ids: on create it writes mint token `NEW`; the **engine allocates** the real id; thereafter the LLM **copies** ids from warm / engine response (MN-REQ-10.4).
- **rel** — English verb / snake token (`owns`, `satisfies`, `contains`, `next`, …).
- **fields** — atomised attributes; one idea per field; values are atoms / short lists / short maps (no prose blobs).
- **recycle** — `persistent` | `delete_on_settle` | `delete_on_expire` (warm visibility policy).

### 4.2 Ops (mutate)

```text
CreateNode  = + kind [NEW|Id] ; fields*      // NEW mints; explicit Id for locator pins
PatchNode   = ~ [Id] ; fields*               // Id from warm / prior response only
              // re-id: ~ [OldId] ; id=NewId
              // occupied: reject (id_occupied) unless ; merge=true (nodes only)
CreateEdge  = + [NEW|Eid]? [Id] --(Rel)--> [Id] ; fields*
              // warm shows Eid; create uses NEW or omits eid (implicit mint)
PatchEdge   = ~ [Id] --(Rel)--> [Id] ; fields*   |   ~ Eid ; fields*
              // re-id edge record: ~ Eid ; id=NewEid  (no merge=true)
DropEdge    = - Eid
```

Strict mutate maps to MemNet commands (MN-REQ-03): `+` → add; `~` → update; silent upsert forbidden.

### 4.2.0 Re-id / rename (locked default)

Ground **id** is the Write=display copy key (stable locator doctrine). `~` field patches do **not** change the bracket id unless an explicit `id=` field is present.

| Case | Line | Behaviour |
|------|------|-----------|
| Free | `~ [A] ; id=B` | Re-key A→B; retarget all EDG `src`/`dist` that referenced A. |
| Occupied | `~ [A] ; id=B` | **Reject** `id_occupied` (safe default). |
| Merge | `~ [A] ; id=B ; merge=true` | Nodes only: retarget edges A→B, drop A, keep B fields (optional other fields patch B). Tag mismatch → `id_conflict`. EDG → `invalid_merge`. |
| Self | `~ [A] ; id=A` | No-op on key; other fields still apply. |
| Create | `+ KIND [X] ; id=Y` | Illegal (`invalid_field`) — id belongs in brackets. |

`id=` / `merge=` are mutate control fields: they do not persist as row attributes. Prefer merge when a mistaken mint must fold into an existing schematic/locator ground id.

**Not the same as** MCP tool rename `query_warm` → `pin_map` (transport naming only).

### 4.2.0b Numeric incremental update (`+=` / `-=`) — locked

On **patch** (`~`) only, a field may use **`key+=N`** or **`key-=N`** where `N` is a number literal (`NUMBER` in `MemNet.g4`). The engine reads the **current stored value** for `key`, applies the delta, and persists the **absolute** result. Create (`+`) and drop (`-`) are unchanged — create uses plain `key=value` only.

| Rule | Detail |
|------|--------|
| Ops | `+=` add delta; `-=` subtract delta |
| Scope | **Update (`~`) only** — reject on create (`invalid_field` / lint `numeric_op_on_create`) |
| Operand | RHS must parse as `NUMBER`; stored field must parse as int/float (`bad_numeric`) |
| Display | Pin map / warm show absolute values (`wealth=2`), never `wealth+=1` |
| Spacing | Canonical emit: `key+=N` / `key-=N` (no spaces around operator) |
| Mix | Same line may combine `=`, `+=`, and `-=` fields |

```text
~ [PLR01] ; wealth+=1 ; reputation-=0.5 ; status=active
```

### 4.2.0a Multi-agent same session (design — not yet enforced)

Today: per-session mutex serialises ops (no torn writes), but there is **no** neighbourhood lease. Two agents sharing one `session_id` can still **logically** race. Goldfish docs assume one writer loop; `--agent` is attribution only.

**Recommended default (next minor):** **session ACL** (modes + roles + `session_token`) then **neighbourhood reserve** with holder **`llm_id`** + **TTL**. Pin map may show `SES` / `ACL` / `RSV` present lines — **never** `@TAG|pipe` for these. MCP `session_acl` / grant / revoke + `reserve` / `extend` / `release`. Optimistic `rev` optional secondary. SSOT: `docs/grammar/memnet-security-multi-agent.md`, `docs/grammar/memnet-neighbourhood-reserve.md`, and §9a. Re-id / merge under the same holder rules (§4.2.0).

### 4.2.1 Id mint rule (`NEW`) — locked

**Two paths — do not conflate them.**

#### A) LLM goldfish mutate (memory facts not yet in the net)

**Surface form:** keyword **`NEW`** — node id as **`[NEW]`**; edge record id as leading **`NEW`** (or omit for implicit mint). Not a field `id=NEW`, not client-numbered `NEW1` / `NEW2`.

| Op | Id rule |
|----|---------|
| Create NODE (`+ KIND […]`) | Id slot **must** be `[NEW]` when the LLM does not already hold a ground id. Engine assigns the real id. |
| Create EDGE | Edge id: leading `NEW` or omitted (engine allocates). Endpoints are **known** ids from warm / prior create response. Preferred warm form shows the assigned eid: `+ E77 [from] --(rel)--> [to]`. |
| Update / settle (`~`) | **Require** known ids from warm / engine response. `NEW` / `[NEW]` is **illegal** on patch. |
| Drop (`-`) | Known edge id only. |

**After create:** engine response and/or warm re-read returns the assigned ids; the LLM **must copy** those ids on all later lines. Never invent ground-truth ids (e.g. `[C_rand_99]`, `[T_maybe]`).

**Contrast:** create mints with `NEW`; update/settle only patch rows whose ids already appear in warm.

#### B) Pin-map ingest (SysML, codebase, PCBA / `.ato`, skills) — no client `NEW`

Pin-map ingest **preserves stable locators** into the source so Write=display round-trips and warm still points at the artefact. Blind `NEW` mint would break traceability (e.g. refdes `R1`, net `GND`, pin `U2.3`, path into `.ato`).

**Chosen approach (locked):**

1. **Ingest engine** derives a **deterministic MemNet id** from a pin key / locator of the source (examples below), **or** assigns an opaque engine key while **requiring** locator fields (`loc=`, `path=`, `refdes=`, `net=`, `pin=`, `qname=`, …) on the node.
2. **Warm** emits that **ground id** plus locator fields — copyable; never shows schematic elements as `[NEW]`.
3. **Pin-map ingest SHALL NOT** accept client `[NEW]` / `NEW` for schematic / source elements (R1, U2, nets, SysML qnames, module paths, skill ids).
4. **LLM** updating PCBA-related memory: **copy** ids/pins from warm; use `[NEW]` only for *new MemNet annotations* (e.g. a `CLM` decision about the rail), **not** for re-creating components, nets, or pins that already exist as pins in the map.

| Source | Deterministic id / key examples (illustrative) | Required locator fields (illustrative) |
|--------|------------------------------------------------|----------------------------------------|
| PCBA `.ato` | `ATO_R1`, `NET_GND`, `PIN_U2_3` | `refdes=`, `net=`, `pin=`, `path=` into `.ato` |
| SysML | `PRT_PowerDistribution`, hash of qname | `name=`, `qname=`, `requirementId=` |
| Codebase | `MOD_wire`, `SYM_split_payload` | `path=`, `line=`, `signature=` |
| Skills | `SKL_memnet_format` | `skill_id=`, `phrase=` |

IdAllocator: **`NEW` path** for goldfish mutate only; **pin-key path** for PinMapIngest_* (deterministic assign / upsert by locator).

### 4.3 Pin map (presentation, not a third data kind)

**Emit form (locked):** live pin map lines are **bare present** — KIND [Id] ; fields… / Eid [from] --(rel)--> [to] ; fields… with **no** leading + / ~ / -. Those ops are **mutate-only**. PinMapComposer emits Op.PRESENT.

The LLM must **not** see the whole Net of Memory. Each turn it receives a **pin map**: a bounded, ego/anchor digest of pins in the same **shared dialect** grammar as mutate I/O (Write = display).

**Primary term (locked):** **pin map** — the turn-facing agent payload.  
**Disambiguation:** MN-REQ-11 export/snapshot pin maps are selective projections into SysML/codebase/PCBA/skills; the **live pin map** is the per-turn ego digest. Same NODE|EDGE shapes; different purpose.  
**Legacy:** CLI/MCP `query_warm` / `query warm` are **deprecated aliases** for `pin_map` / `query pin-map`.

```text
PinMap = {                 // live pin map (turn-facing)
  laws: Pin[],             // engine invariants prepended
  focus: Id[],             // MCP/CLI envelope only — not shared-dialect body lines
  nodes: Node[],           // ego-reachable, recycle-filtered
  edges: Edge[],           // emit bare: Eid [from] --(rel)--> [to]  (no +)
  caps: { depth, max_rows }  // envelope only
}
```

A pin map is a **selective projection**, analogous to novel-cut `compose_g_n_digest`: ego expand from focus, class/relation filters, budget cap — not “dump session”.

**focus / caps:** carried on the MCP/CLI **envelope** (tool args), not as body grammar lines (locked default).

### 4.4 Pin (MN-REQ-11)

A **pin** is a short accurate locator atom, usually a Node (or a thin Edge) that points into an external artefact without embedding the artefact:

| Pin family | Example kinds | Locator fields (illustrative) |
|------------|---------------|-------------------------------|
| SysML | `PRT`, `POR`, `REQ`, `PKG` | `name=`, `qname=`, `requirementId=` |
| Law leaf (design; multi-layer) | `CST` (ports as fields; optional later `PORT`) | `law=`, `ports=`, params — see `memnet-multi-layer.md` |
| Codebase | `MOD`, `SYM` | `path=`, `line=`, `signature=` |
| Skills / rules | `SKL`, `RUL`, `TRG` | `skill_id=`, `phrase=` |
| PCBA schematics (Atopile `.ato`) | `CMP`, `NET`, `PIN` (or domain kinds) | `refdes=`, `net=`, `pin=`, `path=` |

**Ids vs locators:** the live **pin map** shows a **stable ground id** (deterministic from ingest) **and** locator fields. The LLM copies those ids; it does not invent refdes/net/pin strings as MemNet ids and does not use `[NEW]` to re-materialise schematic elements (see §4.2.1 B).

Export / snapshot pin map = **graph of pins** (NODE+EDGE), never a full source copy (MN-REQ-11.13).

### 4.5 Session ops and session schema

Session open/load/save/close remain **tool/CLI verbs**. Seed lines at open may inject law/config **nodes** in the shared dialect.

**Session schema** (`session open --map-file`) declares which kinds exist and their **ordered field names** (MN-REQ-02.7). That declaration is now **in the shared dialect**:

```text
SCHEMA MOD ; fields=id path summary status recycle
```

| Piece | Rule |
|-------|------|
| Keyword | `SCHEMA` (lexer `KW_SCHEMA`) |
| Kind | Uppercase token (`MOD`, `CMP`, …) — user kinds only; do not redefine fixed `LAW` / `EDG` |
| `fields=` | Space-separated field names (R1 atom / `BARE_ATOM`); **`id` must be first** |
| Not | Graph `NODE`/`EDGE`; not mutate ops; not `@TAG: id\|…` pipe |

Legacy pipe TagMap (`@MOD: id|path|…`) remains **accepted on import** for old map files; **emit / examples prefer `SCHEMA`**. Pin map and mutate stay NODE|EDGE — schema lines are registry only.

---

## 5. Concrete syntax proposal

### 5.1 Spine (locked separators — md_triple lineage)

```text
1. LINE  = op + endpoints + optional fields
2. FIELD = key=value | key+=N | key-=N   joined by ;
3. VALUE = atom                         // R1 locked; list/map = R2 deferred
```

| Char | Role |
|------|------|
| `;` | Join **fields** only in R1 (list/map item join deferred to R2) |
| `=` | Only at `key=` / `key+=` / `key-=` field start |
| `:` | Reserved for R2 map pairs `token:label` — not used in R1 atoms |
| `[]` | Wrap node Id or mint token `NEW` |
| `--(Rel)-->` | Directed edge |

**R1 atoms-only (locked):** values are `STRING` | bare atom | `NUMBER` | `IDENT` | `NEW`. No list/map compounds until R2 (bracketed or schema-predicated `;` — undecided). Store `@SET` membership expands to **many EDGE** lines in R1 (e.g. `member_of` / `contains`); do not encode member lists in one field.

**No `|` as field separator on the agent surface** (avoids LAW04 escape traps that plague the pipe codec — GH #10).

### 5.2 Sections (required on agent-facing pin map)

```text
## Laws       // when laws are present
## Nodes      // or ## Pins for locator-heavy slices
## Edges
```

**Locked:** agent-facing **warm must** emit `## Nodes` (or `## Pins`) and `## Edges` (and `## Laws` when laws are present). Headerless streams remain legal for **mutate batches** only.

### 5.3 Examples — good

```text
## Laws
LAW01 kind=engine ; text=one_row_per_id_tag ; recycle=persistent

## Nodes
+ TSK [T42] ; goal=Clear warehouse ; phase=2 ; status=in_progress ; recycle=persistent
+ MOD [M_wh] ; path=parts/warehouse/store.py ; summary=stock ledger ; recycle=persistent
+ CLM [C10] ; type=fact ; code=24V rail feeds both modems ; recycle=persistent

## Edges
+ E77 [N03] --(helps)--> [T42] ; note=labour ; recycle=persistent
+ E78 [M_wh] --(documents)--> [C10] ; recycle=persistent
```

Compact mutate forms:

```text
+ CLM [NEW] ; type=decision ; code=bitrate cap 2000 bps ; recycle=persistent
+ NEW [S03] --(part_of)--> [ART_pdu] ; recycle=delete_on_settle
~ [T42] ; status=settled ; recycle=delete_on_settle
~ E77 ; recycle=delete_on_settle
- E77
```

Numeric incremental update (`~` only; create keeps plain `=`):

```text
~ [PLR01] ; wealth+=1 ; cashflow-=50
~ [NPC02] ; corruption-=0.25
```

Canonical spacing: `key+=N` / `key-=N` (no spaces around the operator). Pin map and warm emit **absolute** field values, never `+=` / `-=`.

Engine response / warm re-read (assigned ids — LLM copies thereafter):

```text
## Nodes
+ CLM [C11] ; type=decision ; code=bitrate cap 2000 bps ; recycle=persistent

## Edges
+ E20 [C11] --(belongs_to)--> [S03]
```

### 5.4 Examples — bad

```text
# Hostile positional dump (current pipe as agent-facing — brittle field counts)
@TSK: T42|Clear the warehouse|2|in_progress|persistent

# Prose blob node (parse OK; soft lint-reject)
+ NOTE [N01] ; text=The warehouse mission involves N03 helping T42 and also the lock…

# Embedded relation inside a node field (lint-reject; use EDGE / SET→EDGE)
+ TSK [T42] ; helpers=N03,N04 ; goal=Clear warehouse

# Invented create ids (lint-reject — use [NEW] instead)
+ CLM [C_rand_99] ; type=fact ; code=guessed id ; recycle=persistent

# [NEW] on update / settle (parse-reject)
~ [NEW] ; status=settled ; recycle=delete_on_settle

# Wrong edge template (first [] is from, not eid — do not copy)
+ [E77] --(helps)--> [T42] ; from=N03

# Second dialect in the same prompt (write ≠ display)
## Nodes
@CLM: C10|S03|fact|24V rail|active|persistent

# Map of pins violated — corpus dump (lint-reject)
+ ART [A1] ; body=<entire system-design.md pasted here>
```

Fixture classification (`parse-reject` vs `lint-reject`): see `docs/grammar/examples/README.md`.

### 5.5 Escape and lexical discipline

- Atoms: no unescaped `;` inside a value (R1). Prefer `STRING` for spaces, `\`, or `"`.
- `STRING` escapes: `\\` `\"` `\n` `\r` `\t` (Windows paths: `"C:\\Projects\\MemNet\\…"`).
- Bare atoms may include `/` `.` `+` `-` and spaces between tokens; use quotes when brittle.
- Ids: ground `[A-Za-z_][A-Za-z0-9_]*`; mint token **`NEW`**. Lexer: `KW_NEW` (see `memnet-grammar-antlr.md`).
- Rel: `[a-z][a-z0-9_]*`
- Keys: `IDENT` (`[A-Za-z_][A-Za-z0-9_]*`, camelCase allowed)
- Ban gluing display names into Ids (`[N03=helper]`). Names live in `name=` / gloss fields.
- Fat / prose fields: **soft lint** (`@WRN` / lint-error in harness) — parse still succeeds (locked R1 default).

---

## 6. Legacy `@TAG` pipe (deprecated — not a peer tier)

Pipe is **not** part of the target architecture. It exists only as a **one-shot import** of historical session files.

| Concern | Target (shared dialect + internal graph) | Legacy pipe (deprecated agent I/O) |
|---------|------------------------------------------|------------------------------------|
| Agent I/O | `+ KIND [id] ; k=v` / EDGE arrows | Must not appear on pin map or mutate |
| Store wire | In-memory NODE\|EDGE records | Old `@KIND: id\|…` blobs (import path) |
| Pin map | Same dialect as write (bare present) | N/A (import once then gone) |

**Design stance (locked):**

1. **One agent dialect** — shared dialect Write=display both directions (MN-REQ-08.7 / 08.9).
2. **No standing pipe store codec** — internal graph is not `@TAG` pipe.
3. **MAY** import old pipe snapshots once and convert; thereafter shared dialect only for agent I/O. Keep import rules documented where they exist.

Do not teach dual dialect as normal agent practice. See `examples/deprecated/` for historical sketches only (fixtures retained for clarity, not as preferred I/O).

Schema authority for which keys exist per kind remains the session schema registry (MN-REQ-02.7).

---

## 7. Prompt-rules checklist (dialect)

Agents and assemblers SHALL treat these as prompt rules for MemNet I/O (MN-REQ-08.6):

```text
@CHK: G01 | Write = display: mutate using the same line shapes as the pin map | pass|fail
@CHK: G02 | Only NODE and EDGE lines; no prose paragraphs as records | pass|fail
@CHK: G03 | One idea per field; short atoms; no sentences in values | pass|fail
@CHK: G04 | Relations only as EDGE arrows; never embedded id lists as fake relations | pass|fail
@CHK: G05 | Create with [NEW]; copy assigned ids from pin map/response; never invent ids | pass|fail
@CHK: G06 | Use + for create and ~ for replace; no silent upsert | pass|fail
@CHK: G07 | Prefer named key=value fields; do not invent positional columns | pass|fail
@CHK: G08 | Pin map: keep depth/max_rows; do not paste corpora | pass|fail
@CHK: G09 | English keys and templates; low noise; template-copy from few examples | pass|fail
@CHK: G10 | Recycle matches lifetime; settle finished work out of future pin maps | pass|fail
```

Contrast (from memnet-format): durable graph = this grammar (or its compile); serve-down scratch = plain Markdown; tool envelope = JSON. Do not use TOON/TRON.

---

## 8. Parser strategy

### Pain addressed (GH)

- **#10** naive `|` splits / escape bugs → agent surface drops `|`; store path must still use one unescape API.
- **#11** divergent consumer parsers → **one** public parse API.
- **#18** atomisation mostly prompt-only → grammar + optional lint caps (chars/tokens) on ingest; still prompt-first for “is this a sentence?”.

### SSOT plan

```text
1. Spec book (this doc + examples/)              — human + LLM normative shapes
2. MemNet.g4 (ANTLR 4)                           — lexer/parser of shared dialect (stub; keep)
3. docs/grammar/tools/tier_a.py                  — R1 Python twin: parse → AST → emit + soft lint
4. tests/grammar/test_tier_a_golden.py           — golden accept/reject/lint + round-trip
5. Forbidden                                     — ad-hoc str.split in consumers (MN-REQ-09.4)
```

(Harness / package names keep `tier_a` for continuity; they implement the shared dialect.)

- **Reject** invalid lines (MN-REQ-09.2); do not “best effort” mis-split.
- Inspect / `read` paths render via the same AST (parse-faithful, MN-REQ-09.3).
- Deprecated pipe import may live behind a migration module; it is **not** the agent SSOT and **not** a standing store tier — keep the module/docs if present; do not elevate pipe to preferred agent I/O.

### ANTLR roadmap

| Step | Deliverable |
|------|-------------|
| R0 | This design + example fixtures |
| R1 | `MemNet.g4` + `tier_a.py` twin + golden harness — **current** (preserve) |
| R2 | Optional: generate visitor from `.g4`; keep twin or replace |
| R3 | CLI `memnet parse --stdin` / MCP inspect hook |
| R4 | Pin map + mutate agent I/O fully shared dialect; deprecate pipe as agent ingest |
| R5 | Legacy pipe = import-once only (session upgrade; keep import rules) |

Reference tooling docs: `third_party/antlr4/` (pin 4.13.2).  
Coherence / gaps / next steps: **`docs/grammar/memnet-grammar-antlr.md`**.

---

## 9. Migration sketch

```text
Phase 0  Document Write=display shared dialect as sole agent dialect.
Phase 1  Accept shared dialect on add/update; emit shared dialect on pin map (Write=display).
Phase 2  Skills / LLM-GUIDE teach shared dialect only (not pipe).
Phase 3  Parser SSOT mandatory for all consumers; delete private splits.
Phase 4  Legacy pipe session files: import once → convert → gone (keep importer).
```

Compatibility: old pipe session blobs MAY load via a deprecated importer; they are not a standing store format and not preferred agent I/O.

**Done:** live MCP/CLI call-site naming (`pin_map` / `query pin-map`; `query_warm` alias kept). Remaining: pipe import path only for historical files. Formal grammar + golden harness remain the dialect authority.

---

## 9a. Multi-agent concurrency (design note)

**As-is (0.3.2):** each session has a mutex (`SessionStore.lock`) so concurrent `add`/`update` do not tear the store. There is **no** neighbourhood lease, session `rev` / etag, or mutate gate on writer identity. `modified_at` / `has_writes` exist on session meta but are not agent-facing CAS. `--agent` is attribution only. Logical lost-update is unmitigated when two agents share one `session_id`.

**Goldfish assumption:** docs teach one agent loop (`pin_map` → reason → mutate → `pin_map`). Shared-session multi-writer is out of that model (MUD note: last write wins on contended edges).

**Primary (locked for next minor):** **neighbourhood reservation** with holder **`llm_id`** + **TTL**. SSOT: [`memnet-neighbourhood-reserve.md`](memnet-neighbourhood-reserve.md).

| Rank | Option | Role |
|------|--------|------|
| 1 | **Reserve ego neighbourhood** (`llm_id` + `ttl_s`; MCP `reserve`/`extend`/`release`) | **Primary** — parallel agents on disjoint pin-map scopes |
| 2 | Optimistic `rev` on envelope | **Secondary** — stale-read / single-writer CAS; optional later |
| 3 | Session-per-agent + snapshot merge | Avoids races; merge UX heavy |
| 4 | Append-only ops log + conflict markers | Large dialect change |

**MCP sketch (ASCII) — shared dialect on pin map; MCP tools for lifecycle:**

```text
reserve(session, anchor, depth=2, llm_id, ttl_s=120)
extend(session, rid|anchor, llm_id, ttl_s=120)
release(session, rid|anchor, llm_id)   # match holder only; no force in v1

# pin_map body (bare present — Write=display). Never @RSV: pipe.
## Reserves
RSV [R7] ; llm_id=coder_a ; anchor=ATO_R1 ; depth=2 ; until=2026-07-24T08:15:00Z ; left_s=87

# errors (prose / codes — do not invent @RSV pipe)
reserved: id ATO_R1 held by llm_id=coder_a until=… (caller llm_id=coder_b)
reserve_conflict: overlapping neighbourhood held by other llm_id
reserve_mismatch: release llm_id does not match holder
```

Re-id (`id=` / `merge=true`) is a mutate: only the lease holder may run it on covered ids; merge requires both endpoints held by the same `llm_id` (or free).

---

## 10. Locked defaults and remaining edges

**Locked (this pass):**

| Decision | Default |
|----------|---------|
| Agent dialect | **Shared dialect only** (Write = display both directions; aka Tier A in code) |
| Session map | **`SCHEMA KIND ; fields=…`** preferred; legacy `@TAG:` pipe accepted on load |
| Pipe / dual agent dialect | **Not preferred** — legacy import-once footnote; keep import productions if present |
| Pin-map sections | **Require** `## Nodes`/`## Pins` + `## Edges` (+ `## Laws` if present) on agent-facing pin map |
| Fat / prose fields | **Soft lint** (parse OK; lint-reject in harness) |
| Compound values | **R1 atoms-only**; R2 list/map deferred |
| focus / caps | **Envelope only** (MCP/CLI args), not body grammar |
| Id mint | **`[NEW]`** / leading **`NEW`** on create; engine allocates; copy from pin map thereafter |

**Still open (id-mint behaviour):**

| Case | Stance |
|------|--------|
| `NEW` / `[NEW]` on `~` | **Reject** |
| `NEW` as EDGE **endpoint** (from/to) same batch as node creates | **Open** — prefer create → response ids → edge |
| Multiple `+ … [NEW]` in one mutate | Distinct engine ids per line; response lists in order |
| Create EDGE with known ends | `+ NEW [a] --(rel)--> [b]` or omit eid (implicit mint) |

---

## 11. Requirement cross-ref (thin)

| Leaf | How this design satisfies |
|------|---------------------------|
| MN-REQ-02.1–02.6 | AST = Node \| Edge only; grammar + parser express both |
| MN-REQ-02.7 | Kind tokens + TagMap/schema validation on ingest |
| MN-REQ-03.* | `+` create vs `~` update; create uses `NEW` (engine id); update needs existing id |
| MN-REQ-08.* | LLM-facing named fields; Write=display; prompt checklist; mint `NEW` not invented ids |
| MN-REQ-09.* | `tier_a.py` + `.g4` path; reject invalid; golden harness (**keep**) |
| MN-REQ-10.* | Learnable templates; pin-map caps in envelope; ground ids from pin map/response |
| MN-REQ-11.13 | Pins as short locator nodes/edges; no corpus dump |

No requirement text is edited in `requirements.sysml` by this task. Thin note: engine-allocated ids on `NEW` align with MN-REQ-03 / 08 / 10.4 — see `system-design-notes.md`.

---

## 12. Related paths

| Path | Role |
|------|------|
| `docs/grammar/MemNet.g4` | ANTLR stub (R1; atom values; `KW_NEW`; lawPin; edge ids) — **keep** |
| `docs/grammar/tools/tier_a.py` | Python parse / emit / soft lint twin — **keep** |
| `docs/grammar/memnet-grammar-antlr.md` | ANTLR coherence + locked defaults |
| `docs/grammar/memnet-field-formulas.md` | **Generic** formula-as-EDGE (`derives`/`feeds`; design; no engine): MVP = one EDGE, `src_fields` **list** + `expr`, one `tgt_field` — any domain; not circuit-specific |
| `docs/application-notes/llm-nodal-analysis-formulas.md` | **Application:** nodal circuit graph (NET/CMP/PIN + KCL/Ohm) *using* formula edges; does not define the formula grammar |
| `docs/grammar/memnet-multi-layer.md` | **Design:** slim 1.x — NODE\|EDGE; law on node (`CST` + `ports=`/`law=`); dual EDGE (port↔port bind/`pipe`; node↔node relation); nesting = pin-map view; distinct from §3 I/O/store/transport layering |
| `docs/grammar/memnet-neighbourhood-reserve.md` | Multi-agent neighbourhood reserve design (shared dialect) |
| `docs/grammar/memnet-security-multi-agent.md` | Session ACL / tokens + security + multi-agent coop (shared dialect) |
| `docs/grammar/examples/` | Good/bad fixtures + README classification — **keep** |
| `tests/grammar/test_tier_a_golden.py` | Golden harness — **keep** |
| `refs/novel-cut-grammar/specs/md_triple_grammar.md` | Write=display lineage |
| `docs/LLM-GUIDE.md` | Agent playbook (still largely pipe-centric — migrate prose; do not delete) |
| `sysml-models/outputs/system-design-notes.md` | Design notes pointer |
| Skill `memnet-format` / `mcp-memnet` | Agent wire + MCP tools (shared dialect; point here for formal rules) |
