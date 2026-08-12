# LLM SysML v2 modeling

> **Dialect (1.x):** **GQL only** — [`../grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md). Do **not** teach Layer / Tier A. Note body may still show historical seeds until **M3**; prefer [`examples/inverting-amplifier-gql-case-study.md`](examples/inverting-amplifier-gql-case-study.md) for wire shapes.

**Single-file application example.** Drive a long-form SysML v2 textual modeling session where session memory lives in MemNet, following `sysml-memnet-documentation` (user pack) and its 6-step snap loop.

**Teach:** GQL wire profile + shaped `pin_map`. Historical body examples below are M3-bound.

MemNet holds the symbol index (`MOD`/`SYM`), design atoms (`PRT`/`CON`/`REQ`/`CLM`), locators, rationale and backlog; authoritative structure and satisfy links live in split `models/*.sysml` files.

British English. ASCII. No `|` pipe on the agent surface.

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

A piece of background is pulled into context only when an EDGE from the live focus reaches it. Cross-file: `--declaredIn-->` to `PKG`; `pin_map` + traversal — no “remember the other file.”

---

## 2. The 6-step pipeline

1. **`serve_status`** (if TCP/shared; skip under in-process default) — if down, edit `.sysml` only and note stale graph.
2. **`pin_map(anchor=TSK_model_<short>, depth=2)`** — smallest useful anchor. Never rely on prior chat or full-file reads.
3. **Locate then edit** — from warm/`SYM` → narrow Read/grep → edit `.sysml`.
4. **Validate** — `mcp-sysml-v2 validate` until clean.
5. **Doc sync (conditional)** — `sysml-view-doc-sync` if `outputs/` changed.
6. **Delta write + locator refresh** — `add`/`update` affected atoms; refresh `SYM.line`; settle transients.

After heavy settlement, optional `housekeep prune recyclable --apply`. Reference material is never settled away.

---

## 3. Schema (Write = display)

```text
SCHEMA ART ; fields=id title source kind status
SCHEMA SEC ; fields=id art heading order status
SCHEMA PKG ; fields=id path kind status
SCHEMA PRT ; fields=id name kind status
SCHEMA POR ; fields=id name kind direc status
SCHEMA CON ; fields=id name kind status
SCHEMA REQ ; fields=id name requirementId status
SCHEMA MOD ; fields=id path summary status
SCHEMA SYM ; fields=id name kind path line of status
SCHEMA TSK ; fields=id goal phase status
SCHEMA USR ; fields=id topic value status
SCHEMA DEC ; fields=id task question options chosen
SCHEMA CLM ; fields=id type code status
```

Edge present form (relation grain):

```text
E99 [SRC_ID] --relation--> [DST_ID] ; note=optional
```

Teach bare `--declaredIn-->`, `--typedBy-->`, `--inFile-->`, `--about-->`, `--owns-->`. Do **not** invent ports on locator rows to force bind unless the atom is a true Layer law leaf.

---

## 4. Seed sketch (PDU campaign)

```text
TSK [TSK_model_pdu] ; goal="Model 6U CubeSat PDU" ; phase=model ; status=in_progress
PKG [PKG_LIB] ; path=library/power ; kind=library ; status=active
MOD [MOD_pdu] ; path=project/pdu-controller.sysml ; summary=PDU controller part ; status=active
SYM [SYM_PDUController] ; name=PDUController ; kind=partDef ; path=project/pdu-controller.sysml ; line=12 ; status=active
E04 [SYM_PDUController] --inFile--> [MOD_pdu]
E05 [SYM_PDUController] --declaredIn--> [PKG_LIB]
```

Delta after a validated edit:

```text
DEC [DEC01] ; task=TSK_model_pdu ; question="Command channel" ; options="UART / GPIO" ; recycle=delete_on_settle
CON [CON_Cmd] ; name=cmd_uart ; status=active
SYM [SYM_Cmd] ; name=cmd_uart ; kind=portUsage ; path=project/pdu-controller.sysml ; line=58 ; of=CON_Cmd ; status=active
E10 [CON_Cmd] --typedBy--> [LibraryCmdIface]
```

---

## 5. Electrical vs SysML grains

| Grain | Shape | Doc |
|-------|-------|-----|
| SysML / locator | `PRT`/`POR`/`PKG` + bare-id relations | this note |
| Electrical Layer | `CST` + `ports=` + `law=` + `--bind-->` | [`llm-circuit-schematic.md`](llm-circuit-schematic.md) |

Same device may appear in both — keep ids stable; relate across grains with bare-id edges. Do not put Ohm/KCL on SysML locator rows.

---

## 6. Multitask

Shared TCP/HTTP session + parent/worker doctrine: [`llm-system-dev-multitask.md`](llm-system-dev-multitask.md) and [`../multi-agent-sessions.md`](../multi-agent-sessions.md). Chat is never SSOT.

---

## 7. Pitfalls

| Mistake | Fix |
|---------|-----|
| Pipe `@TAG` / `query_warm` as primary | Write = display + `pin_map` |
| Prose blobs in `CLM` / `USR` | Distilled codes / short values |
| Stale `SYM.line` after edit | Re-grep + `update` |
| Merging electrical `PIN` teach into SysML | Use Layer bind note for circuits |
| Dual-teaching Tier A paren arrows | Bare `--rel_name-->` |

---

## 8. Related

- [`llm-circuit-schematic.md`](llm-circuit-schematic.md) — Layer electrical
- [`llm-system-dev-multitask.md`](llm-system-dev-multitask.md)
- [`../LLM-GUIDE.md`](../LLM-GUIDE.md)
- `~/.cursor/skills/sysml-memnet-documentation/`
- [`../grammar/memnet-multi-layer.md`](../grammar/memnet-multi-layer.md)

---

## 9. Legacy pipe (pointer only)

Older seeds used `@PKG: id|path|…` and `@EDG: id|from|rel|to|…`. Accept on load; **do not** dual-teach. Full historical “complete model as rows” dumps are omitted here — prefer slim Write = display seeds and the live `.sysml` tree.
