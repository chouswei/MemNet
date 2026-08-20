# LLM SysML v2 modeling

> **Dialect (product 0.8):** **GQL only** — [`../grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md). Product shape: [`../SHAPE.md`](../SHAPE.md). Shared contract: [`README.md`](README.md). Do **not** teach Layer / Tier A. Map: `schema.sysml.example.txt` **union** `schema.coding.example.txt`.

**Teach:** `.sysml` is structural **SSOT** (and of the code and docs it specifies). MemNet is mission working memory. Token saving is two laws together: **relatives of one cue**, and each over-budget **sub-unit in a separate session**. Doctrine: [`../grammar/memnet-session-strata.md`](../grammar/memnet-session-strata.md). Evidence: [`../../sysml-models/outputs/sysml-session-nest-cuts-case-study.md`](../../sysml-models/outputs/sysml-session-nest-cuts-case-study.md).

British English. ASCII.

---

## 1. Two laws (MN-REQ-00)

Dumping the load tree, a fat `.sysml`, or a whole architecture file is the expensive path. Modelling, coding, and documentation that use this SysML SSOT share the same pair:

| # | Law | In the prompt |
|---|-----|----------------|
| 1 | **Relatives of one cue** | Complete Shape of **this** parent (direct children, `typedBy`, incident edges that live here). Then **one** brace Read at `SYM.line` (model, then optional code or doc). |
| 2 | **Sub-unit in a separate session** | Nested part / package / requirement group that will not fit \(M\), or that **already has** an interior, is cut away. Parent shell: **name** + `session=`. Goldfish does **not** walk that other \(S\). Look = `pin_map` that session. Join = Absorb a **slice**. |

Without (1) the agent still pastes `deploy.sysml`. Without (2) relatives of `WebShopSystem` or `package MemNet` still include every nested tree.

Counts \(\approx 3.5\) characters/token:

| Prompt contents | ~tokens |
|-----------------|--------:|
| Whole `sysml-models/models/` load tree | **113k** |
| `deploy.sysml` | **38k** |
| OMG Annex A `SimpleVehicleModel.sysml` | **21k** |
| leftover `pin_map` \(M=50\) with `doc` blobs | **~25k** (alarm) |
| elan8 `WebShopArchitecture.sysml` | **~3.2k** (most of goldfish \(4\,\mathrm{k}\)) |
| leftover clipped depth-2 \(M=50\) | **1.5–4k** (wrong rows) |
| Catalog (`session=` + `qname=`) | **~0.2k** |
| Relatives of one part + brace Read | **~0.5–1k** then code at `SYM.line` |
| OMG `VehicleUsages.sysml` **whole file** | **0.7k** (cheap to dump, **misleading**) |

**TARGET turn:** catalog **~200** + complete relatives of **one** interior **~400–800** + brace **~500** \(\approx\) **1.3–2.5k**, then one code window. About **20–100×** less than pasting `deploy.sysml`. Goldfish: \(\lesssim 4\,\mathrm{k}\) in; \(\gtrsim 8\,\mathrm{k}\) from one `pin_map` is alarm ([`../grammar/math-skeleton.md`](../grammar/math-skeleton.md)).

The Shape must be **complete and the right relatives**, and the child nest must stay in **its** session. Truncation spends the budget on the wrong 50 rows. Copying an already-built sub-unit spends it twice.

---

## 2. Two stores

| Store | SSOT for | In the prompt |
|-------|----------|----------------|
| `models/*.sysml` | Nest, `satisfy`, ports, mapping | **One brace** at `SYM.line` |
| MemNet sessions | Relatives, locators, `TSK`/`USR` | **One** `pin_map` (drop it next turn) |
| Source / docs tree | Implementation | One window after `SYM.path` |

MemNet is not a second copy of every brace. Chat is never SSOT.

| Kind | Role |
|------|------|
| `TSK` / `USR` | Campaign (mission session) |
| `PKG` / `PRT` / `POR` / `CON` / `BEH` / `ITM` / `REQ` | Projected atoms (interiors) |
| `MOD` / `SYM` | Locators into `.sysml` and code |
| `ART` / `SEC` / `CLM` | Outputs / claims |
| Transient | `DEC` / `ISSUE` / short `TSK` (`delete_on_settle`) |

Teach `:declaredIn`, `:typedBy`, `:inFile`, `:about`, `:owns`, `:contains`, `:satisfies`. Electrical `:CST` / `:bind` / `law` is [`llm-circuit-schematic.md`](llm-circuit-schematic.md). leftover `id:'NEW'` is leftover; product is GraphElement `CREATE`.

---

## 3. Session stack (one model Snap)

`ingest_sysml` is Path-B **1 path → current session**. **Model Snap** is one load tree → catalog + interiors: `memnet snap model --root …` / MCP `snap_model`.

SysML can nest everything. Sessions cut the **containment tree** so each interior **fits** \(M\approx 50\) **whole**. Construct name is not a layer taxonomy. Package imports are a convenient **first** cut; recurse at a part / requirement group / nested package when that subtree still will not fit. Defs vs usages are two interiors of **the same** Snap — `import ::*` is not a dump of the def nest into every usage.

| Session | Holds |
|---------|--------|
| Catalog \(S_{\mathrm{cat}}\) | `session=` + `qname=` of cuts |
| Interiors \(S_i\) | Relatives of **one** subtree that fits \(M\) whole |
| Mission \(S\) | `TSK` / `USR` / `SYM` — **not** the nest |

Goldfish: **one** \(S\) per generate. Cross-cut `satisfy` / `allocate`: second look or Absorb a **slice**.

**Shape.** \(M\) is a **fit test**, not a slicer. Reconstruct **fits whole** or Recall **refuses**. Parent shell = complete **direct** children (names + `session=` if cut away **or already built**). Not a clipped depth-2 walk.

**Already built.** If the nested type already presents in another minted session, do **not** Snap it again. Shell = usage **name** + `:typedBy` + that `session=`. Configuration **delta** (`subsets`, extra nested `lugbolt`) stays on the usage pin.

**Look loop (session in session).** Catalog → interior → child interior is the **same** goldfish, repeated. Each generate holds **one** `pin_map`. If the Shape shows a child `session=` you need, **drop** the parent map and `pin_map` that child on the **next** generate. Recurse until the cue’s brace. Not \(N\) maps stacked in one prompt (V5).

```text
pin_map(S_cat)     → pick session=
pin_map(S_i)       → child has session=?  yes → drop map, pin_map(S_child)
                   → … until this brace fits M whole
edit .sysml of THAT cut → re-Snap THAT interior
```

**Parallel sub-units.** When the **parent shell is already clear in `.sysml`** (children named, ports typed, `session=` assigned), sibling interiors are **disjoint**. Parent mints one `TSK_*` per sub-unit, passes that interior session id, **ends the turn**. Workers goldfish **only** their interior (TCP or streamable-http; [`llm-system-dev-multitask.md`](llm-system-dev-multitask.md)). If the parent nest is still being invented, stay **serial**: write the shell first. Cross-cut `satisfy` / `allocate` waits until both interiors exist (second look / slice). MUST NOT two workers on the same interior, the same brace, or overlapping `MOD_*` without RSV.

**As-is leftover:** `snap_model` still package / kind-band / two-segment child package; `context_pack[:max_rows]` still clips; ingest `_DEF_HEAD` misses `interface` usages, `subsets`/`redefines`, `connect`/`flow`, multiplicity, attributes; Snap may re-project the same `qname=`. Do not teach those caps as law. `.sysml` stays SSOT.

---

## 4. One turn

MCP arg is **`session`**. In-process for a single agent; Multitask uses TCP/HTTP ([`llm-system-dev-multitask.md`](llm-system-dev-multitask.md)).

1. **`serve_status`** if TCP; if down, edit `.sysml` only.
2. **Mission** — cue `TSK_model_<short>` → `pin_map` **that** session. Copy `SYM.path` / `line`. leftover `anchor=` is leftover.
3. **Catalog** — `pin_map` \(S_{\mathrm{cat}}\) on the parent `qname=` / `requirementId=`. Row carries `session=` of the cut.
4. **Relatives** — `pin_map` **that one interior**. Shape = parent + **direct** children **whole**. If a child `session=` is the cue, **re-anchor** next generate (look loop). Do not depth-2 the package and do not stack maps.
5. **Edit SSOT** — narrow Read at `SYM.line`; write the nest in `.sysml`. Optional: one code or doc window at the same locator.
6. **Validate** — `mcp-sysml-v2 validate`.
7. **Re-Snap this subtree.** If it no longer fits \(M\), cut the child. If that `qname=` already has `session=`, **reuse** it. Parent keeps name + `typedBy`/`session=`, not the child’s interior.
8. **Mission Δ** — sparse `mutate`: refresh `SYM.line`; optional `:about`. Do not CREATE the nest into the mission. Drop the prior `pin_map`.

Conditional: `sysml-view-doc-sync` if `outputs/` changed. Settle transients; `housekeep prune recyclable --apply` after heavy settlement.

---

## 5. Relatives

The **element is made in `.sysml`**. MemNet shows **relatives** of the parent cut. New interior only when that subtree no longer fits \(M\) **and** no catalog row exists for that `qname=`. Never one session per leaf.

| Nest | Parent cue | Relatives | Cut away when |
|------|------------|-----------|----------------|
| `part` / `part def` | parent `qname=` | usage names; def via `typedBy` + `session=` if already built | child over \(M\) and no existing interior |
| `requirement def` | parent `requirementId=` | direct child ids | child **group** over \(M\) |
| `package` | parent `qname=` | child package + `session=` | nested package over \(M\) (not per file) |
| `port` / `connection` / `action` / `item` | owning part | those **direct** children | owning part over \(M\) (not `S_port`) |
| `satisfy` / `allocate` | source interior | — | never; second look or slice |
| `view def` | owning package/part | view name | that def over \(M\); not `pin_map view=` |
| `subsets` / `redefines` | specialised usage | **delta** + locator to ancestor | never paste the ancestor |
| `interface` / `connect` / `flow` | owning part | interface name | nested port ends: second look |
| multiplicity `[n]` / `[n..m]` | the **one** usage | property | never explode n pins |

Sketch — mission holds locators only; interior cues `qname:'PkgPdu::PduController'`:

```sysml
part def PduController {
  port pwr_in : PowerIn;
  part sense : SenseAmp;
}
part def SenseAmp { port vin : AnalogIn; port vout : AnalogOut; }
```

`sense` is `:contains` + `:typedBy`. If `SenseAmp` already has a session, present it. Else if this interior will not fit \(M\), mint `mn_sense`. Parent shell keeps the usage **name**, not `vin`/`vout`.

```cypher
(:TSK {id:'TSK_model_pdu', goal:'Model 6U CubeSat PDU', phase:'model', status:'in_progress'})
(:SYM {id:'SYM_PDUController', name:'PDUController', kind:'partDef', path:'project/pdu-controller.sysml', line:12})
```

**Official examples** (detail in the case study, not here): Wheel already built (Turn F); `CheckoutService` relatives (Turn G); `MutateGate` reuse (Turn H); look loop and parallel `TSK_*` when the shell is already clear (Turn I).

---

## 6. Pitfalls

| Mistake | Fix |
|---------|-----|
| Paste the load tree so the agent “sees the model” | Laws 1 and 2 together (\(\approx 1\)–\(2\,\mathrm{k}\)) |
| Paste `WebShopArchitecture.sysml` to “see checkout” | Relatives of `CheckoutService`, then `SYM.line` |
| Clip `max_rows` / shell 8+12 / ingest mid-brace | Refuse; cut sessions; complete Shape |
| Kind zoo (`S_part`, `S_req`, `S_port`) | Cuts are **fit** on the nest |
| One `ingest_sysml` per file as Snap | One model Snap → session stack |
| One session per leaf / exploded `[4..5]` | One usage pin |
| Paste C1 into C2 because it `subsets` | Delta + locator |
| Re-Snap a type that already has a session | Present existing `session=` |
| Depth-2 to a nested port | Parent shell, then re-anchor |
| `Peak_L` as default goldfish | Cue `qname=` |
| Layer / `query_warm` / `rag_query` `.sysml` | GQL + `pin_map` |
| leftover `id:'NEW'` / `anchor=` as law | Pattern `mutate`; cue `pin_map` |
| Stuff every interior into `messages` | Drop prior maps |
| \(N\) nested `pin_map`s in one generate | Look loop: one \(S\) per generate |
| Parallel workers before the parent names children | Serial until the shell is in `.sysml` |
| Two workers on the same interior / brace | One `TSK_*` per disjoint `session=` |

---

## 7. Related

- [`.cursor/skills/memnet-nested-sessions/`](../../.cursor/skills/memnet-nested-sessions/) — look loop / already-built `session=`
- [`../../sysml-models/outputs/sysml-session-nest-cuts-case-study.md`](../../sysml-models/outputs/sysml-session-nest-cuts-case-study.md) — Turns A–I
- [`../grammar/memnet-session-strata.md`](../grammar/memnet-session-strata.md)
- [`llm-system-dev-multitask.md`](llm-system-dev-multitask.md) — shared TCP/HTTP
- [`llm-software-development.md`](llm-software-development.md) — coding when SysML is SSOT
- [`llm-circuit-schematic.md`](llm-circuit-schematic.md)
- [`../LLM-GUIDE.md`](../LLM-GUIDE.md)
