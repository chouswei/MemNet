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

A piece of background is pulled into context only from the **chosen** session’s complete Shape. Cross-cut: catalog look or Absorb a **slice** — no "remember the other file" and no depth-2 walk of a fat `:contains` tree.

---

## 2. The 6-step pipeline

Cue then `pin_map`. MCP arg is **`session`**. In-process only for a **single** agent; Multitask uses TCP/HTTP.

1. **`serve_status`** (if TCP/shared; skip under in-process default) — if down, edit `.sysml` only and note stale graph.
2. **Cue** the live `TSK_model_<short>` (or `find`); then **`pin_map` that one session**. Mission `TSK` ego is not a dump of the SysML nest — model interiors are separate sessions (section 6). Never rely on prior chat or full-file reads. leftover `anchor=` is leftover.
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

Mission locators only (not the SysML nest). Making nests (part, requirement, package, port, …): section 6 worked examples.

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

`.sysml` stays structural SSOT. MemNet holds **cut locators** and a complete Shape of **one** interior — not a second copy of every brace.

### Nest is unbounded

SysML can nest **everything** in everything: `package`, `part` / `part def`, `requirement`, `port`, `action`, `view`, `connection`, leftover leaves. That is **one containment tree** of mixed kinds. Sessions cut **that** tree so each interior **fits** goldfish \(M\approx 50\). Construct name is not a layer taxonomy.

A convenient **first** cut is the load-tree packages (`root.sysml` imports). It is **not** the law. Kind-band (REQ vs PRT) is the same special case: the nest does not stay in bands. `requirement def` inside `requirement def` and `part` inside `part` are the same `:contains` problem.

When a subtree is still over ~2\(M\) after that first cut, **cut again at that root** (composition part, nested requirement group, child package). Recurse. Nested **usage** (`part mutate : MutateGate`) is a locator (`typedBy` + `qname=` / `session=` of the **def** interior) — do not copy MutateGate’s nest into Commit’s map.

| Session in the Snap | Holds |
|---------------------|--------|
| Catalog \(S_{\mathrm{cat}}\) | `session=` + `qname=` of **cuts** in **this** model (package roots first; part-roots when the deploy nest still will not fit) |
| Interiors \(S_1\ldots S_k\) | The projected pins of **one** subtree that **fits \(M\) whole** |
| Lead mission (not in the Snap) | `TSK` / `USR`; locators into the catalog |

Worked **first** grain for **this** product model: interiors follow `root.sysml` imports (`MemNetRequirements`, `MemNetVerification`, `MemNet`, …), not “a session because a file exists.” `package MemNet` in `deploy.sysml` is still a fat part nest — that interior **must** recurse (composition roots such as `AgentMemory`, not one session per nested usage). Cue `qname=` then `pin_map` **one** interior. Cross-cut `satisfy`: second look or Absorb a **slice**. Re-Snap **that subtree** after a validated edit.

### Truncation is not Shape

Goldfish \(M\) is a **fit test**, not a slicer. A `pin_map` that walks `:contains` and keeps `max_rows` (as-is `context_pack`), a shell cap of 8 NODE / 12 EDGE, or ingest `max_nodes` mid-brace, still **looks** complete. Children, `satisfy`, and nested usages past the cut vanish with no CueConflict. That is the same class of lie as silently picking one root.

**TARGET Shape:** the chosen interior’s reconstruct either **fits \(M\) whole**, or Recall **refuses** (cardinality / over-budget — sibling of CueConflict). Do not emit a clipped neighbourhood. Do not raise \(M\). Do not use `Peak_L` as default (parents of `:contains` look like peaks).

A parent **shell** is a **grain**: the **complete** list of **direct** children of this cut (names + `session=` when a child lives in another interior). If that child list does not fit \(M\), cut again. Shell is **not** a truncated depth-2 walk of a fat \(S\). Hard `LIMIT` on seed `MATCH_L` stays: that lists \(Q\) and CueConflict when \(|hits|>L\).

**As-is leftover:** `snap_model` still prefers package / kind-band / two-segment child package; `PinMapComposer` still silently caps the walk. Do not teach those caps as product law. Path-B `ingest_sysml` 1→1 is not this Snap.

**MUST NOT** one session per `requirement def` / nested `part` / port. **MUST NOT** dump the nest into the mission. **MUST NOT** Layer / `layer=`. **MUST NOT** `rag_query` textual SysML. **MUST NOT** Absorb a whole subtree.

### Worked examples: making nests

The **element is made in `.sysml`**. MemNet records locators and a **complete** Shape of the interior that owns that subtree. The loop is the same for every nest kind (section 2). Construct name does not pick a session type.

| Step | Where | What you do |
|------|--------|-------------|
| 1 | Mission \(S\) | Cue `TSK_model_*` → `pin_map` **that session only**. Copy `SYM.line` / `path`. Drop the map next turn. |
| 2 | Catalog | `pin_map` \(S_{\mathrm{cat}}\) on the parent `qname=`. Complete row: `session:` of that cut. If the catalog itself is over \(M\), cut it — do not clip. |
| 3 | One interior | `pin_map` that `session=` on the **parent** `qname=`. Shape is the parent and its **direct** children **whole**. Not depth 2 across the package. |
| 4 | `.sysml` SSOT | Narrow Read at `SYM.line`. Write the nested construct (and a sibling `def` when the nest is a typed usage). |
| 5 | Validate | `mcp-sysml-v2 validate` until clean. |
| 6 | Re-Snap **this subtree** | `memnet snap model --root …`. If the interior **no longer fits \(M\)**, Snap **cuts** the new child to its own `session=`; the parent shell lists the child **name** + `session=` / `typedBy` — it does **not** copy the child’s interior. |
| 7 | Mission Δ | Sparse `mutate`: refresh `SYM.line`; optional `:about` the parent `qname=`. Do **not** CREATE the nest into the mission. leftover `id:'NEW'` is leftover. |

**Wrong (every nest):** `ingest_sysml` into the mission; clip `max_rows`; mint `mn_` per leaf.

#### Part in part

PDU campaign (section 4). Before: `PduController` has only `pwr_in`. Add nested **usage** `sense` and sibling **def** `SenseAmp`:

```sysml
package PkgPdu {
  part def PduController {
    port pwr_in : PowerIn;
    part sense : SenseAmp;
  }
  part def SenseAmp {
    port vin : AnalogIn;
    port vout : AnalogOut;
  }
}
```

Catalog: `PkgPdu` → `mn_pdu`. Interior cue: `qname:'PkgPdu::PduController'`. After Snap, `sense` is `:contains` + `:typedBy` `SenseAmp`. If `mn_pdu` no longer fits \(M\), cut `SenseAmp` to `mn_sense`; the `PduController` shell keeps the usage **name**, not `vin`/`vout`.

#### Requirement in requirement

Same loop. Parent cut is the group, not each leaf (MN-REQ-11.17). Product tree already does this: `MN_REQ_00` contains `MN_REQ_01`, which contains `MN_REQ_01_1`.

```sysml
requirement def MN_REQ_01_SessionLifecycle {
  attribute requirementId : String = "MN-REQ-01";
  requirement def MN_REQ_01_1_NamedSessions {
    attribute requirementId : String = "MN-REQ-01.1";
  }
}
```

Interior cue: `requirementId='MN-REQ-01'`. Shape lists **direct** children (`MN-REQ-01.1`, …) whole. Adding `MN-REQ-01.9` is an edit under that brace, then re-Snap **that group**. If `MN-REQ-01`’s children no longer fit \(M\), cut a **child group** (e.g. a nested `requirement def` that still has children) — not one session per `MN-REQ-01.1`.

#### Package in package

```sysml
package PkgLib {
  package PkgPower {
    part def PowerRail { }
  }
}
```

First Snap cut is often the **import** root (`PkgLib`), not the file. Nested `PkgPower` stays in that interior while it fits; when it does not, catalog grows a row `qname:'PkgLib::PkgPower'` → `mn_power`. Parent shell lists `PkgPower` + `session=`. Do **not** mint a session because a `.sysml` file exists.

#### Port, connection, action, item (inside a part)

These are still **children of the part cut**, not their own session kinds.

```sysml
part def PduController {
  port pwr_in : PowerIn;
  item fuel : Charge;
  action boot { }
  connection pwrLink : PowerFlow {
    end port source ::> pwr_in;
    end port sink ::> sense.vin;
  }
}
```

Cue the **part** `qname=`. Shape lists those direct children whole. A typed `port pwr_in : PowerIn` is `:hasPort` + `:typedBy`; do not copy `PowerIn`’s nest into `PduController` if `PowerIn` was cut away. `connection` / `action` / `item` stay in the part interior until **that part’s** reconstruct exceeds \(M\) — then cut the **part** (or a nested part usage), not a `S_port` / `S_action`.

#### Satisfy / allocate across cuts

```sysml
part def PduController {
  satisfy PkgReq::ReqAlpha;
}
```

`satisfies` is an **edge**. If `ReqAlpha` lives in another interior, the part interior **must not** grow a dangling same-store node. Second `pin_map` on the requirements cut, or Absorb a **slice** of `ReqAlpha` into the mission — not merge sessions, not one `pin_map` across stores.

#### View / viewpoint

SysML `view def` / `viewpoint def` ingest as `PRT` (as-is). They stay in the **package** (or part) interior that owns the brace. `pin_map view=shell` is **grain inside one session**, not a SysML view and not a second session. If a `view def` body is over \(M\), cut **that def’s subtree** like any other root.

| Nest | Parent cue | Child in parent shell | New interior only when |
|------|------------|------------------------|-------------------------|
| `part` / `part def` | parent `PRT` `qname=` | usage name; def `typedBy` | child subtree over \(M\) |
| `requirement def` | parent `REQ` `requirementId=` | child `requirementId=` | child **group** over \(M\) |
| `package` | parent `PKG` `qname=` | child package `qname=` | nested package over \(M\) |
| `port` / `connection` / `action` / `item` | owning `PRT` | child name | owning part over \(M\) (not per port) |
| `satisfy` / `allocate` | source interior | — | never; second look or Absorb slice |
| `view def` | owning `PKG`/`PRT` | view name | that def’s subtree over \(M\) |

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
| One `MemNet` (or other fat package) session for all nested parts | Recurse containment cuts until each interior **fits \(M\)** |
| Kind zoo of layer sessions (`S_part`, `S_req`, `S_port`) | Cuts are budget on the nest, not construct names |
| Silent `max_rows` / shell drop / ingest mid-brace | Refuse; partition; complete Shape of the chosen \(S\) |
| `pin_map` depth 2 on a parent nest | Shell of **direct** children, then one child interior |
| `Peak_L` as default goldfish on a `:contains` tree | Cue `qname=`; Peak is last-resort residual only |

---

## 9. Related

- [`llm-circuit-schematic.md`](llm-circuit-schematic.md) — electrical GQL
- [`llm-system-dev-multitask.md`](llm-system-dev-multitask.md)
- [`../LLM-GUIDE.md`](../LLM-GUIDE.md)
- [`../grammar/memnet-session-strata.md`](../grammar/memnet-session-strata.md) — sessions as strata; containment cuts; truncation is not Shape
- [`../../sysml-models/outputs/sysml-session-nest-cuts-case-study.md`](../../sysml-models/outputs/sysml-session-nest-cuts-case-study.md) — case study (requirement / part / package / satisfy / view)
- `~/.cursor/skills/sysml-memnet-documentation/`

---

## 10. Retired dialects (pointer only)

Older `@PKG` / `@EDG` pipe or Layer ASCII seeds are **not** agent teach. Archive: [`../grammar/archive/`](../grammar/archive/). Prefer slim GQL seeds and the live `.sysml` tree.
