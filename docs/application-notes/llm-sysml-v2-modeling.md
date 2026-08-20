# LLM SysML v2 modeling

> **Dialect (product 0.8):** **GQL only** — [`../grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md). Product shape: [`../SHAPE.md`](../SHAPE.md). Shared contract: [`README.md`](README.md). Do **not** teach Layer / Tier A. Map: `schema.sysml.example.txt` **union** `schema.coding.example.txt`.

**Teach:** `.sysml` is structural **SSOT** (and of the code and docs it specifies). MemNet saves tokens with two moves: **(1)** `pin_map` **relatives of one cue**, then narrow-Read that brace; **(2)** each over-budget **sub-unit lives in a separate session** — the parent presents `session=`, it does not dump the child nest. Doctrine: [`../grammar/memnet-session-strata.md`](../grammar/memnet-session-strata.md). Case study: [`../../sysml-models/outputs/sysml-session-nest-cuts-case-study.md`](../../sysml-models/outputs/sysml-session-nest-cuts-case-study.md).

British English. ASCII.

---

## 1. Why MemNet (token law)

Dumping the load tree, a fat `.sysml`, or a whole architecture file into chat is the expensive path. MemNet saves tokens because of **two** facts together (MN-REQ-00):

| # | Law | In the prompt |
|---|-----|----------------|
| 1 | **Relatives of one cue** | Complete Shape of **this** parent: direct children, `typedBy`, incident `connect` / `satisfy` ends that live here. Then **one** brace Read at `SYM.line` (model or code). |
| 2 | **Sub-unit in a separate session** | Nested part / package / requirement group that will not fit \(M\), or that **already has** an interior, is **cut away**. Parent shell keeps the **name** + `session=`. Goldfish does **not** walk that other \(S\). |

Without (1), the agent still pastes `deploy.sysml`. Without (2), relatives of `WebShopSystem` or `package MemNet` still include every nested tree — same dump, smaller font. Modelling, coding, and documentation that use this SysML SSOT share the same two laws: design memory is relatives; implementation is one code or doc window after `SYM.path`.

Counts \(\approx 3.5\) characters/token (this product tree, OMG vehicle, [elan8/sysml-examples](https://github.com/elan8/sysml-examples)):

| Prompt contents | ~tokens |
|-----------------|--------:|
| Whole `sysml-models/models/` load tree | **113k** |
| `deploy.sysml` alone | **38k** |
| OMG Annex A `SimpleVehicleModel.sysml` | **21k** |
| leftover `pin_map` \(M=50\) with `doc` blobs on every node | **~25k** (alarm) |
| elan8 `drone/` tree (~24 kiB SysML) | **~7k** |
| elan8 `webshop/` tree (~17 kiB SysML) | **~5k** |
| `WebShopArchitecture.sysml` alone | **~3.2k** (already most of goldfish \(4\,\mathrm{k}\)) |
| leftover clipped depth-2 \(M=50\), short locators | **1.5–4k** (same cost, **wrong** rows) |
| elan8 `timer/` tree | **~2.9k** |
| elan8 `office/office.sysml` | **~1.4k** |
| Catalog look (a few `session=` + `qname=` rows) | **~0.2k** |
| Complete shell of **one part** (direct children) | **0.2–0.8k** |
| Relatives of `CheckoutService` + brace Read | **~0.5–1k** then code at `SYM.line` |
| Narrow Read of `MutateGate` brace (34 lines) | **~0.5k** |
| OMG `VehicleUsages.sysml` **whole file** | **0.7k** (too small to be a budget example) |

**TARGET turn:** catalog **~200** + complete relatives of **one** interior **~400–800** + brace Read **~500** \(\approx\) **1.3–2.5k** on the model side, then one code window at `SYM.line`. That is about **20–100×** less than pasting `deploy.sysml` or the load tree. Goldfish bound: \(\lesssim 4\,\mathrm{k}\) in; \(\gtrsim 8\,\mathrm{k}\) from one `pin_map` is alarm ([`../grammar/math-skeleton.md`](../grammar/math-skeleton.md)).

The saving holds only if the Shape is **complete and the right relatives**, and the child nest stays in **its** session. Truncation spends the budget on the wrong 50 rows. Copying an already-built sub-unit into the parent spends it twice.

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

**Shape law.** \(M\) is a **fit test**, not a slicer. TARGET: reconstruct **fits whole** or Recall **refuses** (sibling of CueConflict). Parent **shell** = complete **direct** children (names + `session=` if a child was cut away **or already has an interior**). Shell is not a clipped depth-2 walk. `MATCH_L` hard LIMIT stays (lists \(Q\); CueConflict when \(|hits|>L\)).

**Already-built interior.** If a nested usage’s type (or a cut-away child) **already presents in another session that Snap has minted**, the parent does **not** rebuild that tree. The shell row is the usage **name** + `:typedBy` + `session=` of the **existing** interior. Goldfish of the parent **does not walk** that other \(S\). Look = `pin_map(session=` that id`)`. Join = Absorb a **slice**, not a second Snap and not a paste of the nested brace. Same as coding: `part mutate : MutateGate` locates the MutateGate session; it does not copy MutateGate’s nest into Commit. A configuration **delta** (`subsets` / extra nested `lugbolt`) stays on the usage pin; the ancestor nest stays in the already-built session.

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
7. **Re-Snap this subtree** — `memnet snap model --root …`. If it no longer fits \(M\), Snap **cuts** the child. If the nested **type already has** a catalog `session=`, **reuse** that id — do not mint a second interior of the same `qname=`. Parent shell keeps the **name** + `typedBy`/`session=`, not the child’s interior.
8. **Mission Δ** — sparse `mutate`: refresh `SYM.line`; optional `:about`. Do not CREATE the nest into the mission. Drop the prior `pin_map` before the next generate.

Conditional: `sysml-view-doc-sync` if `outputs/` changed. Settle transients; `housekeep prune recyclable --apply` after heavy settlement.

---

## 5. Relatives (every nest is the same loop)

The **element is made in `.sysml`**. MemNet shows **relatives** of the parent cut. New interior only when that subtree no longer fits \(M\). Never one session per leaf.

| Nest | Parent cue | Relatives in the Shape | Cut away when |
|------|------------|------------------------|----------------|
| `part` / `part def` | parent `qname=` | usage names; def via `typedBy` + `session=` if the type is **already built** elsewhere | child subtree over \(M\) **and** no existing interior for that `qname=` |
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

After Snap, `sense` is `:contains` + `:typedBy`. If `SenseAmp` **already** has `mn_sense` (library Snap, earlier cut, or same catalog), `PduController` only **presents** that session — no second Snap of `vin`/`vout`. If this is the first time the subtree will not fit \(M\), **then** cut `SenseAmp` to `mn_sense`; the parent shell still keeps the usage **name**, not `vin`/`vout`.

Mission seed (not the nest):

```cypher
(:TSK {id:'TSK_model_pdu', goal:'Model 6U CubeSat PDU', phase:'model', status:'in_progress'})
(:MOD {id:'MOD_pdu', path:'project/pdu-controller.sysml'})
(:SYM {id:'SYM_PDUController', name:'PDUController', kind:'partDef', path:'project/pdu-controller.sysml', line:12})
(:SYM {id:'SYM_PDUController'})-[:inFile]->(:MOD {id:'MOD_pdu'})
```

### Official: Vehicle definitions vs usages

[VehicleUsages.sysml](https://github.com/Systems-Modeling/SysML-v2-Release/blob/master/sysml/src/examples/Vehicle%20Example/VehicleUsages.sysml) + [VehicleDefinitions.sysml](https://github.com/Systems-Modeling/SysML-v2-Release/blob/master/sysml/src/examples/Vehicle%20Example/VehicleDefinitions.sysml). One Snap, two interiors. The **Wheel** interior is **already built** in the definitions session. `part narrowRimWheel: Wheel { part lugbolt: Lugbolt[4..5]; }` **presents** that session (`typedBy` + `session=`); `hub` is not copied. Nested `lugbolt` is the usage **delta**; **`[4..5]` is one pin**.

`vehicle_C1` relatives are **only** `frontAxleAssembly` and `rearAxleAssembly`. Lugbolts are depth 3. Re-anchor; do not clip depth 2.

`vehicle_C2 subsets vehicle_C1` — Shape is **redefines + new `interface` connect** and a locator to C1, not a paste of C1.

`vehicle_C3` connects to nested `rearAxleAssembly.rearAxle.drive`. C3 relatives: `transmission`, redefined axle assembly, `driveShaft`. Port `drive` is on `rearAxle` — second look or Absorb slice.

The whole usages file is \(\approx 0.7\,\mathrm{k}\) tokens (cheap to dump, **misleading**). Annex A in the same folder is \(\approx 21\,\mathrm{k}\); `deploy.sysml` is \(\approx 38\,\mathrm{k}\).

### Official: elan8 teaching load trees (software SSOT)

[elan8/sysml-examples](https://github.com/elan8/sysml-examples) — office → timer → intersection → drone → **webshop**. Each example is **one model**: root package imports Structure / Behavior / Requirements / Ports / Views. That **is** the first Snap cut (not one session per file). `Views.sysml` is SysML `view`/`viewpoint`, not `pin_map view=`.

**Webshop** is the coding-agent case: `HttpService`, `KafkaTopic`, `SqlDatabase`, `KubernetesCluster`; `allocate webshopSystem.checkoutService to commerceCluster`. The architecture file alone is \(\approx 3.2\,\mathrm{k}\) tokens — dump it and the goldfish budget is gone before code. Relatives of `CheckoutService`: its ports and the **incident** `connect` rows (orders DB, payments, inventory, order-events). Then one code window. If `CheckoutService` already has its own interior, `WebShopSystem` / `CheckoutProcess` only **present** `session=` — they do not dump the service nest. Do not `pin_map` all of `WebShopSystem` (fourteen children plus every `connect`) unless that reconstruct still fits \(M\) whole.

Root `satisfy checkoutLatency by webshopSystem.checkoutService` is a **cross-cut** (requirements interior → architecture interior): second look or Absorb a slice — same as Turn D.

**Drone / timer** use nested satisfy paths (`satisfy FailsafeReq by droneInstance.flightControl.flightController`, `satisfy TimerRangeReq by timerInstance.pcb.mcu`). Same as Vehicle `vehicle_C3` nested port: shell of the instance, then re-anchor `flightControl` / `pcb`. `Propulsion` with four named `propulsionUnit*` is four usage pins in **one** interior if they fit \(M\), not four sessions.

These trees are **teaching-small** (\(\approx 1.4\,\mathrm{k}\) office … \(\approx 7\,\mathrm{k}\) drone). They prove the **folder = package cut** and the software `allocate`. They do not replace `deploy.sysml` as the fat budget example.

---

## 6. Pitfalls

| Mistake | Fix |
|---------|-----|
| Paste the load tree / `deploy.sysml` so the agent “sees the model” | Relatives of **one** cue + brace Read; child nests stay in **other** sessions (\(\approx 1\)–\(2\,\mathrm{k}\)) |
| Paste elan8 `WebShopArchitecture.sysml` (~3.2k) to “see checkout” | Relatives of `CheckoutService` (~0.5–1k) then `SYM.line` |
| Clip `max_rows` / shell 8+12 / ingest mid-brace | Refuse; cut sessions; complete Shape |
| Kind zoo (`S_part`, `S_req`, `S_port`) | Cuts are **fit** on the nest |
| One `ingest_sysml` per file as Snap | One model Snap → session stack |
| One session per leaf / exploded `[4..5]` | One usage pin; recurse only over \(\sim 2M\) |
| Paste `vehicle_C1` into C2 because it `subsets` | Delta + locator |
| Re-Snap / copy a nested type that already has a session | Parent shell: name + `typedBy` + existing `session=`; look = `pin_map` that \(S\) |
| Depth-2 from C3 to `rearAxle.drive` | C3 shell, then re-anchor |
| `Peak_L` as default goldfish | Cue `qname=`; Peak last-resort (`contains` parents look like peaks) |
| Layer / `query_warm` / `rag_query` `.sysml` | GQL + `pin_map` |
| Electrical `PIN` teach on SysML rows | Circuit note for `:CST` / `:bind` |
| leftover `id:'NEW'` / `anchor=` as law | Pattern `mutate`; cue `pin_map` |
| Stuff every interior into `messages` | Drop prior maps (`stuffed_maps`) |

---

## 7. Related

- [`../../sysml-models/outputs/sysml-session-nest-cuts-case-study.md`](../../sysml-models/outputs/sysml-session-nest-cuts-case-study.md) — nest-cut case study (Turns A–H)
- [elan8/sysml-examples](https://github.com/elan8/sysml-examples) — teaching load trees (webshop = software SSOT)
- [`../grammar/memnet-session-strata.md`](../grammar/memnet-session-strata.md) — sessions as strata
- [`llm-system-dev-multitask.md`](llm-system-dev-multitask.md) — shared TCP/HTTP
- [`llm-circuit-schematic.md`](llm-circuit-schematic.md) — electrical GQL
- [`../LLM-GUIDE.md`](../LLM-GUIDE.md)
- `~/.cursor/skills/sysml-memnet-documentation/`
- Archive (not teach): [`../grammar/archive/`](../grammar/archive/)
