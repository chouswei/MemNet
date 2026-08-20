# LLM SysML v2 modeling

> **Dialect (product 0.8):** **GQL only** — [`../grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md). Product shape: [`../SHAPE.md`](../SHAPE.md). Shared contract: [`README.md`](README.md). Do **not** teach Layer / Tier A. Map: `schema.sysml.example.txt` **union** `schema.coding.example.txt`.

**Teach:** the `.sysml` load tree is structural **SSOT** (and the SSOT of the codebase it specifies). MemNet is **mission working memory**: a coding or modelling agent `pin_map`s **relatives of one cut**, then narrow-Reads that brace. Doctrine: [`../grammar/memnet-session-strata.md`](../grammar/memnet-session-strata.md). Case study: [`../../sysml-models/outputs/sysml-session-nest-cuts-case-study.md`](../../sysml-models/outputs/sysml-session-nest-cuts-case-study.md).

British English. ASCII.

---

## 1. Why MemNet (token law)

Dumping the model into chat is the expensive path. Relatives of the live cue are the cheap one. Counts \(\approx 3.5\) characters/token (this product tree and the OMG vehicle examples):

| Prompt contents | ~tokens |
|-----------------|--------:|
| Whole `sysml-models/models/` load tree | **113k** |
| `deploy.sysml` alone | **38k** |
| OMG Annex A `SimpleVehicleModel.sysml` | **21k** |
| leftover `pin_map` \(M=50\) with `doc` blobs on every node | **~25k** (alarm) |
| leftover clipped depth-2 \(M=50\), short locators | **1.5–4k** (same cost, **wrong** rows) |
| Catalog look (a few `session=` + `qname=` rows) | **~0.2k** |
| Complete shell of **one part** (direct children) | **0.2–0.8k** |
| Narrow Read of that part’s brace (e.g. `MutateGate`, 34 lines) | **~0.5k** |
| OMG `VehicleUsages.sysml` **whole file** | **0.7k** (too small to be a budget example) |

**TARGET turn:** catalog **~200** + complete relatives of **one** interior **~400–800** + brace Read **~500** \(\approx\) **1.3–2.5k** on the model side, then one code window at `SYM.line`. That is about **20–100×** less than pasting `deploy.sysml` or the load tree. Goldfish bound: \(\lesssim 4\,\mathrm{k}\) in; \(\gtrsim 8\,\mathrm{k}\) from one `pin_map` is alarm ([`../grammar/math-skeleton.md`](../grammar/math-skeleton.md)).

The saving holds only if the Shape is **complete and the right relatives**. Truncation spends the budget on the wrong 50 rows.

---

## 2. Two stores

| Store | SSOT for | In the prompt |
|-------|----------|----------------|
| `models/*.sysml` | Nest, `satisfy`, ports, code mapping | **One brace** at `SYM.line` |
| MemNet sessions | Relatives, locators, `TSK`/`USR` | **One** `pin_map` (drop the last map next turn) |
| Source tree | Implementation | One code window after `SYM.path` |

MemNet is not a second copy of every brace. Chat is never SSOT.

| Kind | Role |
|------|------|
| `TSK` / `USR` | Campaign and constraints (mission session) |
| `PKG` / `PRT` / `POR` / `CON` / `BEH` / `ITM` / `REQ` | Projected model atoms (interiors) |
| `MOD` / `SYM` | File + line locators into `.sysml` and code |
| `ART` / `SEC` / `CLM` | Outputs / claims |
| Transient | `DEC` / `ISSUE` / short `TSK` (`delete_on_settle`) |

Teach `:declaredIn`, `:typedBy`, `:inFile`, `:about`, `:owns`, `:contains` (membership), `:satisfies`. Electrical `:CST` / `:bind` / `law` is [`llm-circuit-schematic.md`](llm-circuit-schematic.md) — do not put Ohm on SysML locator rows. leftover `id:'NEW'` is leftover; product is GraphElement `CREATE`.

---

## 3. Session stack (one model Snap)

`ingest_sysml` is Path-B **1 path → current session** (as-is). **Model Snap** is one load tree → catalog + interiors: `memnet snap model --root …` / MCP `snap_model`.

SysML can nest **everything** in everything. Sessions cut that **containment tree** so each interior **fits** goldfish \(M\approx 50\) **whole**. Construct name is not a layer taxonomy. Package imports (`root.sysml`) are a convenient **first** cut, not the law. Recurse at a part / requirement group / nested package when that subtree still will not fit. Defs vs usages (OMG vehicle) are two interiors of **the same** Snap — `import ::*` is not a dump of the def nest into every usage.

| Session | Holds |
|---------|--------|
| Catalog \(S_{\mathrm{cat}}\) | `session=` + `qname=` of cuts |
| Interiors \(S_i\) | Relatives of **one** subtree that fits \(M\) whole |
| Mission \(S\) | `TSK` / `USR` / `SYM` locators — **not** the nest |

This product: first interiors follow `MemNetRequirements`, `MemNetVerification`, `MemNet`, … `package MemNet` in `deploy.sysml` still needs **part-root** cuts (`AgentMemory`, …). Goldfish: **one** \(S\) per generate. Cross-cut `satisfy`: second look or Absorb a **slice**.

**Shape law.** \(M\) is a **fit test**, not a slicer. TARGET: reconstruct **fits whole** or Recall **refuses** (sibling of CueConflict). Parent **shell** = complete **direct** children (names + `session=` if a child was cut away). Shell is not a clipped depth-2 walk. `MATCH_L` hard LIMIT stays (lists \(Q\); CueConflict when \(|hits|>L\)).

**As-is leftover:** `snap_model` package / kind-band / two-segment child package; `context_pack[:max_rows]` still clips; ingest `_DEF_HEAD` misses `interface` usages, `subsets`/`redefines`, `connect`/`flow`, multiplicity, attributes. Do not teach those caps as law. Do not invent `:contains` walks to fake missing edges — `.sysml` stays SSOT.

---

## 4. One turn (coding or modelling)

MCP arg is **`session`**. In-process only for a single agent; Multitask uses TCP/HTTP ([`llm-system-dev-multitask.md`](llm-system-dev-multitask.md)).

1. **`serve_status`** if TCP; if down, edit `.sysml` only (stale graph).
2. **Mission** — cue `TSK_model_<short>` → `pin_map` **that** session. Copy `SYM.path` / `line`. leftover `anchor=` is leftover.
3. **Catalog** — `pin_map` \(S_{\mathrm{cat}}\) on the parent `qname=` / `requirementId=`. Complete row: `session=` of the cut.
4. **Relatives** — `pin_map` **that one interior** on the parent cue. Shape = parent + **direct** children **whole**. Re-anchor to a child cut; do not depth-2 the package.
5. **Edit SSOT** — narrow Read at `SYM.line`; write the nest in `.sysml`. Optional: one code window at the same locator.
6. **Validate** — `mcp-sysml-v2 validate`.
7. **Re-Snap this subtree** — `memnet snap model --root …`. If it no longer fits \(M\), Snap **cuts** the child; parent shell keeps the **name** + `typedBy`/`session=`, not the child’s interior.
8. **Mission Δ** — sparse `mutate`: refresh `SYM.line`; optional `:about`. Do not CREATE the nest into the mission. Drop the prior `pin_map` before the next generate.

Conditional: `sysml-view-doc-sync` if `outputs/` changed. Settle transients; `housekeep prune recyclable --apply` after heavy settlement.

---

## 5. Relatives (every nest is the same loop)

The **element is made in `.sysml`**. MemNet shows **relatives** of the parent cut. New interior only when that subtree no longer fits \(M\). Never one session per leaf.

| Nest | Parent cue | Relatives in the Shape | Cut away when |
|------|------------|------------------------|----------------|
| `part` / `part def` | parent `qname=` | usage names; def via `typedBy` | child subtree over \(M\) |
| `requirement def` | parent `requirementId=` | direct child ids | child **group** over \(M\) |
| `package` | parent `qname=` | child package + `session=` | nested package over \(M\) (not per file) |
| `port` / `connection` / `action` / `item` | owning part | those **direct** children | owning part over \(M\) (not `S_port`) |
| `satisfy` / `allocate` | source interior | — | never; second look or Absorb slice |
| `view def` | owning package/part | view name | that def’s subtree over \(M\); not `pin_map view=` |
| `subsets` / `redefines` | specialised usage | **delta** + locator to ancestor | never paste the ancestor nest |
| `interface` / `connect` / `flow` | owning part | interface name | nested port ends: second look or slice |
| multiplicity `[n]` / `[n..m]` | the **one** usage | property | never explode n pins |

### Worked: nested part (PDU)

Mission holds locators only (`TSK_model_pdu`, `SYM` on `PduController`). Interior `mn_pdu` cues `qname:'PkgPdu::PduController'`. Relatives: `pwr_in`. Write:

```sysml
part def PduController {
  port pwr_in : PowerIn;
  part sense : SenseAmp;
}
part def SenseAmp {
  port vin : AnalogIn;
  port vout : AnalogOut;
}
```

After Snap, `sense` is `:contains` + `:typedBy`. If `mn_pdu` no longer fits \(M\), cut `SenseAmp` to `mn_sense`; the `PduController` shell keeps the usage **name**, not `vin`/`vout`.

Mission seed (not the nest):

```cypher
(:TSK {id:'TSK_model_pdu', goal:'Model 6U CubeSat PDU', phase:'model', status:'in_progress'})
(:MOD {id:'MOD_pdu', path:'project/pdu-controller.sysml'})
(:SYM {id:'SYM_PDUController', name:'PDUController', kind:'partDef', path:'project/pdu-controller.sysml', line:12})
(:SYM {id:'SYM_PDUController'})-[:inFile]->(:MOD {id:'MOD_pdu'})
```

### Official: Vehicle definitions vs usages

[VehicleUsages.sysml](https://github.com/Systems-Modeling/SysML-v2-Release/blob/master/sysml/src/examples/Vehicle%20Example/VehicleUsages.sysml) + [VehicleDefinitions.sysml](https://github.com/Systems-Modeling/SysML-v2-Release/blob/master/sysml/src/examples/Vehicle%20Example/VehicleDefinitions.sysml). One Snap, two interiors. `part narrowRimWheel: Wheel { part lugbolt: Lugbolt[4..5]; }` — `typedBy` Wheel (`hub` stays in the def interior) plus nested `lugbolt`; **`[4..5]` is one pin**.

`vehicle_C1` relatives are **only** `frontAxleAssembly` and `rearAxleAssembly`. Lugbolts are depth 3. Re-anchor; do not clip depth 2.

`vehicle_C2 subsets vehicle_C1` — Shape is **redefines + new `interface` connect** and a locator to C1, not a paste of C1.

`vehicle_C3` connects to nested `rearAxleAssembly.rearAxle.drive`. C3 relatives: `transmission`, redefined axle assembly, `driveShaft`. Port `drive` is on `rearAxle` — second look or Absorb slice.

The whole usages file is \(\approx 0.7\,\mathrm{k}\) tokens (cheap to dump, **misleading**). Annex A in the same folder is \(\approx 21\,\mathrm{k}\); `deploy.sysml` is \(\approx 38\,\mathrm{k}\).

---

## 6. Pitfalls

| Mistake | Fix |
|---------|-----|
| Paste the load tree / `deploy.sysml` so the agent “sees the model” | Catalog + relatives of **one** cut + brace Read (\(\approx 1\)–\(2\,\mathrm{k}\)) |
| Clip `max_rows` / shell 8+12 / ingest mid-brace | Refuse; cut sessions; complete Shape |
| Kind zoo (`S_part`, `S_req`, `S_port`) | Cuts are **fit** on the nest |
| One `ingest_sysml` per file as Snap | One model Snap → session stack |
| One session per leaf / exploded `[4..5]` | One usage pin; recurse only over \(\sim 2M\) |
| Paste `vehicle_C1` into C2 because it `subsets` | Delta + locator |
| Depth-2 from C3 to `rearAxle.drive` | C3 shell, then re-anchor |
| `Peak_L` as default goldfish | Cue `qname=`; Peak last-resort (`contains` parents look like peaks) |
| Layer / `query_warm` / `rag_query` `.sysml` | GQL + `pin_map` |
| Electrical `PIN` teach on SysML rows | Circuit note for `:CST` / `:bind` |
| leftover `id:'NEW'` / `anchor=` as law | Pattern `mutate`; cue `pin_map` |
| Stuff every interior into `messages` | Drop prior maps (`stuffed_maps`) |

---

## 7. Related

- [`../../sysml-models/outputs/sysml-session-nest-cuts-case-study.md`](../../sysml-models/outputs/sysml-session-nest-cuts-case-study.md) — nest-cut case study (Turns A–F)
- [`../grammar/memnet-session-strata.md`](../grammar/memnet-session-strata.md) — sessions as strata
- [`llm-system-dev-multitask.md`](llm-system-dev-multitask.md) — shared TCP/HTTP
- [`llm-circuit-schematic.md`](llm-circuit-schematic.md) — electrical GQL
- [`../LLM-GUIDE.md`](../LLM-GUIDE.md)
- `~/.cursor/skills/sysml-memnet-documentation/`
- Archive (not teach): [`../grammar/archive/`](../grammar/archive/)
