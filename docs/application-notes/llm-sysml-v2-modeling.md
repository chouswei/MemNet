# LLM SysML v2 modeling

> **Dialect (product 0.8):** **GQL only** — [`../grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md). Product shape: [`../SHAPE.md`](../SHAPE.md). Shared contract: [`README.md`](README.md). Do **not** teach Layer / Tier A. Wire shapes: [`examples/inverting-amplifier-gql-case-study.md`](examples/inverting-amplifier-gql-case-study.md). Map: `schema.sysml.example.txt` **union** `schema.coding.example.txt`.

**Single-file application example.** Drive a long-form SysML v2 textual modeling session where session memory lives in MemNet, following `sysml-memnet-documentation` (user pack) and its 6-step snap loop.

**Teach:** openCypher-shaped GQL + shaped `pin_map` + gated mutate.

MemNet holds the symbol index (`MOD`/`SYM`), design atoms (`PRT`/`CON`/`REQ`/`CLM`), locators, rationale and backlog; authoritative structure and satisfy links live in split `models/*.sysml` files.

British English. ASCII.

---

## 1. What lives in the graph

| Kind | Role |
|------|------|
| `TSK` | Modeling campaign or step |
| `PKG` | Logical source files / packages |
| `PRT` / `POR` / `CON` / `BEH` / `ITM` / `REQ` | Model element atoms |
| `MOD` / `SYM` | File modules and editable symbols (path + line hints) |
| `ART` / `SEC` / `CLM` | Outputs / claims |
| `USR` | Modeller preferences |
| Transient | `DEC` / `ISSUE` / short-lived `TSK` (`delete_on_settle`) |

A piece of background is pulled into context only when a relationship from the live focus reaches it. Cross-file: `:declaredIn` to `PKG`; `pin_map` + traversal — no "remember the other file."

---

## 2. The 6-step pipeline

Cue then `pin_map`. MCP arg is **`session`**. In-process only for a **single** agent; Multitask uses TCP/HTTP.

1. **`serve_status`** (if TCP/shared; skip under in-process default) — if down, edit `.sysml` only and note stale graph.
2. **Cue** the live `TSK_model_<short>` (or `find`); then **`pin_map(kind='TSK', locators=[…], depth=2)`**. Never rely on prior chat or full-file reads. leftover `anchor=` is leftover.
3. **Locate then edit** — from `SYM` → narrow Read/grep → edit `.sysml`.
4. **Validate** — `mcp-sysml-v2 validate` until clean.
5. **Doc sync (conditional)** — `sysml-view-doc-sync` if `outputs/` changed.
6. **Delta write + locator refresh** — gated GQL `mutate` affected atoms; refresh `SYM.line`; settle transients. leftover `add`/`update` named leftover.

After heavy settlement, optional `housekeep prune recyclable --apply`. Reference material is never settled away.

---

## 3. Schema (GQL labels / relationships)

Illustrative primary labels: `:ART`, `:SEC`, `:PKG`, `:PRT`, `:POR`, `:CON`, `:REQ`, `:MOD`, `:SYM`, `:TSK`, `:USR`, `:DEC`, `:CLM`.

```cypher
(:X {id:'SRC_ID'})-[:relation {id:'E99', note:'optional'}]->(:Y {id:'DST_ID'})
```

Teach `:declaredIn`, `:typedBy`, `:inFile`, `:about`, `:owns`. Do **not** invent ports on locator rows to force `:bind` unless the atom is a true electrical law leaf.

---

## 4. Seed sketch (PDU campaign)

```cypher
(:TSK {id:'TSK_model_pdu', goal:'Model 6U CubeSat PDU', phase:'model', status:'in_progress'})
(:PKG {id:'PKG_LIB', path:'library/power', kind:'library', status:'active'})
(:MOD {id:'MOD_pdu', path:'project/pdu-controller.sysml', summary:'PDU controller part', status:'active'})
(:SYM {id:'SYM_PDUController', name:'PDUController', kind:'partDef', path:'project/pdu-controller.sysml', line:12, status:'active'})
(:SYM {id:'SYM_PDUController'})-[:inFile {id:'E04'}]->(:MOD {id:'MOD_pdu'})
(:SYM {id:'SYM_PDUController'})-[:declaredIn {id:'E05'}]->(:PKG {id:'PKG_LIB'})
```

Delta after a validated edit:

```cypher
CREATE (d:DEC {id:'DEC01', task:'TSK_model_pdu', question:'Command channel', options:'UART / GPIO', recycle:'delete_on_settle'})
CREATE (c:CON {id:'CON_Cmd', name:'cmd_uart', status:'active'})
CREATE (s:SYM {id:'SYM_Cmd', name:'cmd_uart', kind:'portUsage', path:'project/pdu-controller.sysml', line:58, of:'CON_Cmd', status:'active'})
MATCH (c:CON {id:'CON_Cmd'}), (iface {id:'LibraryCmdIface'}) CREATE (c)-[:typedBy]->(iface)
```

---

## 5. Electrical vs SysML grains

| Grain | Shape | Doc |
|-------|-------|-----|
| SysML / locator | `PRT`/`POR`/`PKG` + bare-id relationships | this note |
| Electrical (GQL) | `:CST` + `ports` + `law` + `:bind` | [`llm-circuit-schematic.md`](llm-circuit-schematic.md) |

Same device may appear in both — keep ids stable; relate across grains with bare-id relationships. Do not put Ohm/KCL on SysML locator rows.

---

## 6. Snap **one** SysML model into multiple sessions

`ingest_sysml` remains 1 path → **current** session (Path-B as-is). **Model Snap (0.15)** is **one model** (root package / load tree) → a **stack** of sessions (catalog + interiors): `memnet snap model --root …`. Doctrine: [`../grammar/memnet-session-strata.md`](../grammar/memnet-session-strata.md).

Goldfish \(M\approx 50\); ingest `max_nodes` is Commit into **one interior**, not a Shape of the whole model. `.sysml` stays SSOT.

| Session in the Snap | Holds |
|---------------------|--------|
| Catalog \(S_{\mathrm{cat}}\) | `session=` + `qname=` of packages in **this** model |
| Interiors \(S_1\ldots S_k\) | Pins for one **package** (kind band if still over ~2\(M\)) |
| Lead mission (not in the Snap) | `TSK` / `USR`; locators into the catalog |

Worked grain for **this** product model: interiors follow `root.sysml` imports (`MemNetRequirements`, `MemNetVerification`, …), not “a session because a file exists.” Cue `qname=` then `pin_map` **one** interior. Cross-package `satisfy`: second look or Absorb a **slice**. Re-Snap that package after a validated edit. **MUST NOT** one session per requirement. **MUST NOT** Layer. **MUST NOT** `rag_query` textual SysML.

---

## 7. Multitask

Shared TCP/HTTP session + parent/worker doctrine: [`llm-system-dev-multitask.md`](llm-system-dev-multitask.md) and [`../multi-agent-sessions.md`](../multi-agent-sessions.md). Chat is never SSOT. Handoff = **session id**; prefer **import** for path-B member slices.

---

## 8. Pitfalls

| Mistake | Fix |
|---------|-----|
| Layer / `@TAG` / `query_warm` as primary | GQL + `pin_map` |
| Prose blobs in `CLM` / `USR` | Distilled codes / short values |
| Stale `SYM.line` after edit | Re-grep + `update` |
| Merging electrical `PIN` teach into SysML | Use GQL circuit note for circuits |
| One `ingest_sysml` per file as if each were a Snap | **One** model Snap → session stack; files are SSOT storage |

---

## 9. Related

- [`llm-circuit-schematic.md`](llm-circuit-schematic.md) — electrical GQL
- [`llm-system-dev-multitask.md`](llm-system-dev-multitask.md)
- [`../LLM-GUIDE.md`](../LLM-GUIDE.md)
- [`../grammar/memnet-session-strata.md`](../grammar/memnet-session-strata.md) — Snap one SysML model into many sessions
- `~/.cursor/skills/sysml-memnet-documentation/`

---

## 10. Retired dialects (pointer only)

Older `@PKG` / `@EDG` pipe or Layer ASCII seeds are **not** agent teach. Archive: [`../grammar/archive/`](../grammar/archive/). Prefer slim GQL seeds and the live `.sysml` tree.
