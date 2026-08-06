# Multi-layer MemNet and capsules (design)

**Status:** design only — **not implemented** in 0.3.x (`project.toml` **0.3.6**).  
**Target:** **MemNet 1.x** shared dialect (breaking vs 0.3.x `RES`/`VAR` stamp teaching). Ship path: design → SCHEMA/engine → **1.0**.  
**Store:** still **NODE | EDGE** only. Capsules and layers are patterns and pin-map projections — not a third AST primitive.  
**Dialect:** shared dialect (ASCII; Write = display). British English.  
**Aims:** MN-REQ-00 — bounded live pin map each turn; save wall-clock and tokens while keeping factual accuracy.

**Disambiguation:** [`memnet-grammar-design.md`](memnet-grammar-design.md) §3 *Layering* is I/O / store / transport. This document is **stratified product graph** (abstraction strata + capsule shell/interior). App-note “Layer A / B” means circuitry vs formula relations — not capsule strata.

| Label | Meaning |
|-------|---------|
| **Proposed 1.x** | Target agent surface in this doc |
| **Today (0.3.x)** | Current engine / transitional teaching |
| **Transitional** | Migrate then demote — not the long-term teachable surface |

---

## Contents

1. [Purpose](#1-purpose) · [Careful rethink (mission-first)](#11-careful-rethink-mission-first)
2. [Atoms](#2-atoms)
3. [Ports and carriers](#3-ports-and-carriers)
4. [Capsules (shell and interior)](#4-capsules-shell-and-interior)
5. [Worked examples](#5-worked-examples)
6. [Migration and demotions](#6-migration-and-demotions)
7. [Pin map, layers, and workflow](#7-pin-map-layers-and-workflow)
8. [MVP vs later](#8-mvp-vs-later)
9. [Open decisions](#9-open-decisions)
10. [Related docs](#10-related-docs)

---

## 1. Purpose

A flat ego expand (`depth` / `max_rows`) cannot scale to system → board → net → equation without blowing the pin-map budget or forcing agents to reason at the wrong grain.

Agents need to **reason at layer L**, then **descend only when needed**. The 1.x dialect must fix concrete agent failures (§1.1) — not grow into a modelling language because the shape looks familiar.

Transport and MCP tool *names* may stay; payloads and kinds change where earned.

### 1.1 Careful rethink (mission-first)

**Mission anchor:** MemNet is an **agent memory graph** (NODE\|EDGE) between LLM pipelines and search. MN-REQ-00: save wall-clock and tokens while keeping factual accuracy. **Write = display**; bounded live **`pin_map`**; in-process first. Not a full MBSE language, not SysML/KerML wire, not a circuit simulator.

#### What the agent must read/write each turn

| Need | Shape |
|------|--------|
| Bounded ego | Bare-present NODE\|EDGE lines under `depth` / `max_rows` — copyable for mutate |
| Right grain | Shell first (few rows); descend one step when blocked |
| Mutate | Same shapes with `+`/`~`/`-` (and `NEW` only for MemNet-native facts) |
| Facts, not essays | Short fields; laws as owned fields; wiring as edges — no prose blobs |

Token budget is the product constraint. Extra kinds only earn a place if they shrink wrong reasoning or pin-map waste.

#### What broke in the old dialect

| Failure | Symptom |
|---------|---------|
| Orphan stamp fields | `RES`/`VAR` mirrors (`Vinp`, `Vdiff`, …) that are not graph endpoints |
| Binary EDGE as device | `derives` + `expr` on a two-endpoint EDGE — lies about BJT / multi-port topology |
| Edge-as-function | Law / gain / β on the EDGE — EDGE ceases to be incidence |
| Flat expand | Wrong grain or budget blow-up at system → board → net → equation |

Those are **agent-graph** bugs. They do not require a SysML clone to fix.

#### Necessary vs comfort

| Piece | Verdict | Why |
|-------|---------|-----|
| **Law on the NODE** | **Necessary** | Owns constitutive / behavioural claim; fixes edge-as-function |
| **`PORT` endpoints** | **Necessary** | Multi-terminal honesty; quantities live on endpoints; wiring has somewhere to land |
| **EDGE = carrier** (`connects`, …) | **Necessary** | Incidence / membership / boundary only — never the law |
| **`CAP` shell nesting** | **Necessary for scale** | Pin-map **view** (shell \| interior) — budget, not a part metamodel |
| **Separate `FN` kind** | **Deferred** | Causality is useful; a second leaf tag is not required for MVP — use `CST` + port `side=` (+ optional `form=causal`) |
| **`FN ⊂ CST` as wire hierarchy** | **Teaching note only** | Maths is fine in prose; do not force two locked leaf kinds for 1.0 |
| SysML packages / def·usage / KerML | **Analogy + optional ingest** | Locator kinds (`PRT`/`POR`, …); not dialect-native |

Shape may *rhyme* with parts/ports/constraints. That rhyme is **not** a reason to import SysML product scope.

#### Verdict — minimal 1.x ontology

**Keep:** one law-bearing leaf **`CST`** + **`PORT`** + carrier / membership EDGEs + **`CAP`** for pin-map nesting only.

**Drop / defer from 1.0 lock:** distinct wire kind **`FN`** (optional later sugar ≈ `CST; form=causal`); SysML semantics / libraries / tool chain; constraint solvers; automatic SysML→capsule ingest.

**Dialect-native forever:** recycle, mutate ops, session/MCP, ACL/RSV, Write=display, live pin map.

---

## 2. Atoms

Store atoms remain only **NODE | EDGE** — never a third AST primitive.

| Atom | Role |
|------|------|
| **NODE** | Kinded fact. Law leaf: **`CST`**. Nesting shell: **`CAP`**. Endpoint: **`PORT`**. Also locator / session kinds (`CMP`, `NET`, `PIN`, `TSK`, `LAW`, …) |
| **EDGE** | **Carrier / incidence** — `connects` moves something in/out; `contains` / `exposes` / `refines` / `summarises` for membership / boundary. **Not** the law |

**Lock — kinds, not new atoms:** **`CST`**, **`CAP`**, **`PORT`** (and demoted `RES` / `VAR`; optional later `FN` sugar) are **NODE kinds**. Not a third atom class. Carriers are EDGEs.

### 2.1 One law leaf: `CST` (causality without a second kind)

**1.0 lock:** one constitutive / behavioural leaf tag — **`CST`**. Law and params live **on that node**.

| Need | How (MVP) | Not required |
|------|-----------|--------------|
| Own the equation | `law=` / params on **`CST`** | Law on EDGE |
| Multi-terminal honesty | **`PORT`** + `exposes` | Binary EDGE-as-device |
| Causality hint | Port `side=in\|out\|inout` + optional `form=causal\|acausal` on the **same** `CST` | Separate locked kind **`FN`** |
| Nesting / budget | **`CAP`** + `view=shell\|interior` | SysML part / def / usage |

Mathematically a directed map is a special constraint — fine as **prose**. Wire MVP does **not** lock `FN ⊂ CST` as two kinds. Optional later: `FN` as sugar alias for `CST; form=causal` (same store row class).

**Law placement (locked):** `law=` / `expr=` / params (`beta=`, `R=`, `a_s=`) on the **`CST` node**, never on the EDGE. Several equations on one node → one `law=` field, equations separated by `|`.

**Contrast (same kind, different orientation):**

| Device | Sketch | Ports |
|--------|--------|-------|
| Resistor Ohm | `CST` ; `form=acausal` (default) ; `law=V_a-V_b=I*R` | usually `inout` |
| BJT teachable | `CST` ; `form=causal` ; `law=I_c=beta*I_b\|I_e=I_b+I_c` | B `in`, C `out`, E `inout` |
| Op-amp gain | `CST` ; `form=causal` ; `law=V_out=a_s*(V_inp-V_inm)` | inputs `in`, out `out` |

Causality is **orientation on the leaf** (sides + optional `form=`) — **not** an EDGE pretending to be a function.

### 2.2 Kind roles

All rows below are **NODE kinds**. EDGE is separate.

| Kind | Wire | Role | 1.0 |
|------|------|------|-----|
| **Constraint** | **`CST`** | Law-bearing leaf; ports + `law=` on the node | **Lock** |
| **Capsule** | `CAP` | Pin-map nesting shell; sugar `ports=` / `contains=` — not a SysML part metamodel | **Lock** |
| **Port** | `PORT` | Endpoint; quantities on the port; `side=…` | **Lock** |
| **Function** | `FN` | Optional later sugar ≈ causal `CST` | **Defer** |
| **Pin / Net / CMP** | `PIN` / `NET` / `CMP` | Schematic locator grain (ingest) — not maths hubs | Keep as locators |
| **`RES` / `VAR`** | as today | Demote → `CST` + ports | Migrate |

Reject teachable leaf tokens `CONSTRAINT` / `CON` / `FUNC` / `FUNCTION` / `DEV` / `PASS` / `PART`. Prefer short **`CST`**.

**Ownership:** `CST|CAP --(exposes)--> PORT`. Capsule `contains` → leaf or child Capsule.

### 2.3 Design productions (ASCII)

```text
CapsuleNode    = CAP  [Id] ; name=Atom ; layer=Atom ; fields*
ConstraintNode = CST  [Id] ; name=Atom ; layer=Atom? ; form=causal|acausal? ; law=… ; fields*
PortNode       = PORT [Id] ; name=Atom ; side=in|out|inout|internal? ; fields*
ExposeEdge     = [OwnerId]   --(exposes)--> [PortId]     // Owner = CAP | CST
ContainEdge    = [CapsuleId] --(contains)--> [ChildId]  // Child = CAP | CST | …
ConnectEdge    = [PortId]    --(connects)--> [PortId]  ; carries=?   // carrier only
RefineEdge     = [PortId]    --(refines)--> [InteriorId]            // shell tip → finer
// Later optional: FN as emit/parse sugar for CST ; form=causal
```

Port-hood and capsule-hood are **structure** (kind + edges), not id punctuation. Underscore in ids (`CAP_InvAmp`, `PORT_Vin`) is only the familiar `KIND_rest` separator.

---

## 3. Ports and carriers

### 3.1 Three “port” grains (do not conflate)

| Grain | Kind / rel | Role |
|-------|------------|------|
| **Capsule / leaf Port** | `PORT` + `--(exposes)-->` | Shell or leaf contract; inter-capsule / inter-leaf wiring |
| **SysML port pin** | `POR` (+ `PRT`) | Locator into SysML — map with ingest edges; do not rename in place |
| **PCBA terminal** | `PIN` | Locator into `.ato` / schematic — keep `PIN_*`; optional `PORT --(refines)--> PIN\|NET` |

Also not: formula “field ports” (`FLD_*`) — rejected in [`memnet-field-formulas.md`](memnet-field-formulas.md).

Shell wiring: Port → Port uses `--(connects)-->`. Schematic pad → net stays `--(connects_to)-->`.

### 3.2 EDGE = carrier (locked)

| Rel | Endpoints | Notes |
|-----|-----------|-------|
| `exposes` | `CAP`/`CST` → Port | Contract / ownership |
| `contains` | Capsule → `CST` / child Capsule | Composition (immediate only) |
| `connects` | Port → Port | **Carrier** — wiring moves V/I (optional `carries=…`); does **not** own the law |
| `refines` | Port → finer Port / PIN / NET / CMP | Boundary bridge — **coarser → finer** only |
| `summarises` | Capsule / coarse → claim stub | Shell aggregate |
| `connects_to` | PIN → NET | Transitional schematic |
| `derives` / `constrains` **with law `expr`** | — | **Rejected** as 1.x teachable law |

**MUSTNOT:** put gain / Ohm / β-law on an EDGE; treat EDGE as the law leaf; orphan scalars on `RES` / free mirrors.

### 3.3 Wrong shapes (one box)

| Shape | Why wrong |
|-------|-----------|
| `[PORT] --(derives)--> [PORT] ; expr=…` | Formula-on-edge — EDGE ≠ `CST` |
| Binary fake `src` + multi-port device | Topology lie (BJT has three terminals) |
| `RES_a` with `Vinp`/`Vinm`/`Vdiff` mirrors + self-loop | Orphan scalars; mirrors are not graph endpoints |
| Amp as hollow `CAP` with no law leaf | Behaviour has nowhere owned to live — need a `CST` |
| Forever dual teaching (flat self-loop **and** ports-first as equals) | One target dialect; flat = transitional only |
| Locking `FN` + `CST` as two MVP kinds | Unearned complexity — causality via `side=` / `form=` on one leaf |

---

## 4. Capsules (shell and interior)

### 4.1 Name and anatomy

**Chosen name: capsule** (wire **`CAP`**). Prefer over `part` / `module` / `block` (packaging / SysML collisions). Job: **pin-map nesting** (shell vs interior). Optional later ingest may *map* SysML parts here — do not embed SysML textual syntax in the agent wire.

```text
Capsule = {
  shell_node:   CAP [Id],
  ports:        PORT[],                 // boundary
  shell_edges:  exposes / connects / summarises,
  interior:     NODE[] + EDGE[],        // may include child capsules
  cross_links:  refines | summarises | exposes
}
```

### 4.2 Shell vs interior = `view=` pair

| View | What `pin_map` shows | Budget |
|------|----------------------|--------|
| **Shell** (default for a Capsule anchor) | Compact `CAP` sugar (`ports=` / `contains=`) + summary / sibling Capsules / LAW | Small |
| **Interior** (descend) | Contained NODE\|EDGE ego — still `depth` / `max_rows` capped | Capped |

`layer=` on nodes is an **abstraction stratum** (`system` / `board` / …). Shell vs interior is **`view=`**, not `layer=shell`.

**Descend** = open the capsule (re-anchor or `view=interior`). Do not paste the whole interior into the shell pin map.

### 4.3 Capsule sugar (recommended agent shell)

| Option | Verdict |
|--------|---------|
| **A.** Expanded CAP + PORT + `exposes` always | Demoted for agents — costly |
| **B.** Compact `ports=` / `contains=` on `CAP`; engine desugars 1:1 | **Recommended** |
| **C.** Third primitive outside NODE\|EDGE | **Rejected** |

Write = display: shell `pin_map` emits the same compact sugar agents mutate. Interior stays ordinary NODE\|EDGE. Optional later: `view=atoms` for expanded shell debug.

```text
# Mutate (compact)
+ CAP [NEW] ; name=inverting_amp ; layer=board ; ports=Vin:in,Vout:out ; recycle=persistent

# Bare present (same shape; assigned ids)
CAP [CAP_InvAmp] ; name=inverting_amp ; layer=board ; ports=PORT_Vin:Vin:in,PORT_Vout:Vout:out ; recycle=persistent
```

Desugars to `CAP` + `PORT` + `exposes` / `contains` in the store. Whether `CST` also accepts `ports=` sugar is open (§9 #1).

### 4.4 Nested capsules

Recursive composition is allowed. Parent `--(contains)-->` child Capsule; wiring lands on **Ports**, not grandchild interiors.

| Rule | Detail |
|------|--------|
| **pin_map** | One shell at a time — opening the parent does not auto-expand grandchildren |
| **Depth** | `depth` / `max_rows` within the active view; prefer **one capsule-open step per turn** |
| **MUSTNOT** | Dump nested interiors in one call; encode nest level in the id |

```text
CAP [CAP_Pdu] ; name=pdu ; layer=system ; ports=PORT_Vbus:Vbus:out ; contains=CAP_Rail12 ; recycle=persistent
```

### 4.5 Interior interconnection

Interior wiring is ordinary dialect under the Capsule: membership `contains`, boundary `refines`, schematic `connects_to` (transitional), port↔port `connects` carriers, and `CST` law nodes. No third view token beyond `shell|interior`.

| Step | Call |
|------|------|
| 1. Shell | `pin_map(anchor=CAP_…, view=shell)` |
| 2. Descend | `pin_map(…, view=interior)` or re-anchor on a child / Port tip |
| 3. Ascend | Shell again — do not keep the whole interior in context |

Prefer `contains` for **immediate** children only (fan-out risk). Boundary descent uses `refines` from Ports.

---

## 5. Worked examples

All examples below are **proposed 1.x / not in engine**. Primary multi-port witness: **BJT**. Op-amp secondary. Law leaf is always **`CST`**; causality via `form=` + port `side=`.

### 5.1 BJT leaf (primary) — causal `CST`

**BJT:** one **`CST` NODE** with `form=causal` — three terminals (B/C/E), owner param `beta=`, and both teachable equations on the node: controlled source `I_c=beta*I_b` plus KCL `I_e=I_b+I_c`. Port sides: B `in`, C `out`, E `inout`. Load resistor is a separate **acausal `CST`**; wiring is a **carrier EDGE** only.

```text
CST [CST_Q1] ; name=bjt_npn ; form=causal ; beta=100 ; ports=PORT_B:B:in,PORT_C:C:out,PORT_E:E:inout ; law=I_c=beta*I_b|I_e=I_b+I_c ; recycle=persistent
CST [CST_Rc] ; name=Rc ; R=1000 ; ports=PORT_Rc_a:a:inout,PORT_Rc_b:b:inout ; law=V_a-V_b=I_a*R ; recycle=persistent
E_c [PORT_C] --(connects)--> [PORT_Rc_a] ; carries=I
```

```text
+ CST [NEW] ; name=bjt_npn ; form=causal ; beta=100 ; ports=B:in,C:out,E:inout ; law=I_c=beta*I_b|I_e=I_b+I_c ; recycle=persistent
```

Causality is `form=causal` plus law orientation (Ib → Ic); E is not optional — omitting the emitter truncates the device and leaves KCL unowned. Circuit terminals may still be all-`inout` when V/I both matter; `form=` + `law=` remain the causal claim.

**Rejected:**

```text
E_x [PORT_B] --(derives)--> [PORT_C] ; expr=I_c=beta*I_b
```

(That line is rejected: EDGE-as-law, binary topology lie, and no emitter / KCL.)

| Gap BJT exposes | Lesson |
|-----------------|--------|
| Three ports | Binary `derives` cannot be the device — need B, C, and E |
| Causality | Lives on the **law node** (`form=` + port sides), not on the EDGE |
| Law ≠ edge | Equations *are* the `CST`; `connects` only carries I/V |
| One leaf kind | No second `FN` tag required for the teachable leaf |

Teachable leaf = **`CST` with ports + law**. Full Ebers–Moll as mutual acausal constraints remains optional later.

### 5.2 Board Capsule + resistors

**Resistor:** Ohm on an **acausal `CST`** — ports `inout`. InvAmp board: Capsule shell; amp = **causal `CST`**; passives = **acausal `CST`**; `connects` carry quantities only.

```text
CAP [CAP_InvAmp] ; ports=PORT_Vin:Vin:in,PORT_Vout:Vout:out ; contains=CST_OpAmp,CST_Rin,CST_Rf ; recycle=persistent
CST [CST_OpAmp] ; name=opamp ; form=causal ; a_s=1e6 ; ports=PORT_Inm:Inm:in,PORT_Inp:Inp:in,PORT_Out:Out:out ; law=V_out=a_s*(V_inp-V_inm) ; recycle=persistent
CST [CST_Rin] ; name=Rin ; R=10000 ; ports=PORT_Rin_a:a:inout,PORT_Rin_b:b:inout ; law=V_a-V_b=I_a*R ; recycle=persistent
CST [CST_Rf] ; name=Rf ; R=100000 ; ports=PORT_Rf_a:a:inout,PORT_Rf_b:b:inout ; law=V_a-V_b=I_a*R ; recycle=persistent
E_w1 [PORT_Out] --(connects)--> [PORT_Rf_a] ; carries=V
E_w2 [PORT_Rf_b] --(connects)--> [PORT_Inm] ; carries=V
```

Do **not** teach hollow `CAP` + `RES` mirrors as the leaf. Flat InvAmp without Capsule wrap remains valid as a legacy / ingest example — see [`inverting-amplifier-memnet.md`](../application-notes/examples/inverting-amplifier-memnet.md).

### 5.3 Op-amp (secondary) — causal `CST`

Same pattern: **`CST; form=causal`** with `in`/`out` sides matching the gain law.

```text
CST [CST_OpAmp] ; name=opamp ; form=causal ; a_s=1e6 ; ports=PORT_Inm:Inm:in,PORT_Inp:Inp:in,PORT_Out:Out:out ; law=V_out=a_s*(V_inp-V_inm) ; recycle=persistent
```

```text
# REJECTED — edge-as-law (causality must not migrate onto the EDGE)
E_gain [PORT_Inm] --(derives)--> [PORT_Out] ; src_ports=PORT_Inp,PORT_Inm ; expr=a_s*(V_inp-V_inm)
```

Exact binding of port symbols in `law=` (`V_inp` vs `PORT_Inp.V`, optional `src_ports=` **on the node**) is open (§9 #2) — not fixed by putting the law on an EDGE.

---

## 6. Migration and demotions

Prefer **migrate → demote → sunset**, not forever parallel dialects.

| Stays | Migrates into 1.x | Demoted / sunset (agent surface) |
|-------|-------------------|----------------------------------|
| NODE\|EDGE store | Active stamps → **`CST`+ports+law** | Formula-on-edge; `RES`/`VAR` maths hubs |
| CAP sugar `ports=` / `contains=` | R/L/C / amp / BJT → **`CST`+ports+law** (+ `form=` when causal) | Agent-mirrored stamp fields; orphan scalars |
| Port→Port `connects` as carrier | Flat same-node `derives` → **law on `CST`** | Forever dual-MVP; `constrains` EDGE as the law |
| Transport; MCP tool *names* | Board wrap: leaves under `CAP` | Wire `CONSTRAINT` / `CON` / `DEV` / `PASS` / locked dual `FN`+`CST` |
| `PIN`/`NET`/`CMP` as **ingest** locators | — | Those kinds as long-term formula hubs |
| Recycle / session / ACL / RSV | — | — |

[`memnet-field-formulas.md`](memnet-field-formulas.md) same-node self-loop MVP = **transitional migration note only**. Target: law on `CST`; edges = carriers.

**Engine:** `CST` kind, law-on-node, optional `form=` / `carries=`, CAP shell views → **MemNet 1.0**, not a silent 0.3.x patch. `FN` sugar only if still needed after agents prove `form=` insufficient.

---

## 7. Pin map, layers, and workflow

### 7.1 What a “layer” is

A **layer** is an abstraction stratum used to project a bounded pin map — not a separate store.

| Axis | Examples |
|------|----------|
| Domain hierarchy | `system` / `board` / `net` / `equation` |
| Summary vs detail | shell fields vs interior |
| Normative vs working | `LAW` / requirements vs working pins |

**MVP:** field `layer=<token>` on nodes plus cross-stratum EDGEs. Demoted: a free-standing LAYER node kind agents must maintain as a second graph.

### 7.2 Bounded pin_map

```text
pin_map(session, anchor, depth, max_rows, layer?=board, view?=shell|interior)
```

| Rule | Detail |
|------|--------|
| Default | Expand within the anchor’s layer / capsule **shell** only |
| Up | `summarises` / parent `contains` inverse |
| Down | `refines` or re-anchor on a `contains` child — **one step** when possible |
| Caps | Existing `depth` / `max_rows` still apply inside the chosen view |
| Out of MVP | Whole-graph / multi-capsule flatten in one call |

Cross-layer links on the pin map are **thin**: enough to choose the next anchor, not a substitute for descend.

### 7.3 First-principles workflow

```text
1. pin_map(anchor=system_or_capsule, view=shell, layer=L)
2. Reason and mutate at L only
3. If blocked → follow one refines / contains tip
4. pin_map(child_or_port, view=shell|interior) — one open step
5. Write interior facts; refresh shell via summarises if needed
6. Ascend; settle tasks; do not keep nested shells in context
```

**Goldfish:** re-read the **current** shell each turn. Chat is not SSOT.

### 7.4 Interaction with other design

| Mechanism | Interaction |
|-----------|-------------|
| Formula / law | **1.x:** on `CST` nodes; flat self-loop = transitional |
| Nodal / InvAmp notes | Flat `NET`/`CMP`/`PIN` today; when wrapped → `CST` under `CAP` — do not rename `PIN`→`PORT` |
| LAW | Prefer normative / shell-adjacent; small `## Laws` on shell views OK |
| ACL / reserve | Unchanged order; shell lease ≠ interior lease until expand includes those ids |
| Grammar §3 “Layering” | Orthogonal — do not conflate names |

### 7.5 Risks (thin)

| Risk | Mitigation |
|------|------------|
| Layer sprawl | Closed vocabulary (`system`, `board`, `net`, `equation`, `law`, `working`) |
| Stale summaries | Explicit writer refresh in MVP; later materialise hooks |
| Sugar / expand mismatch | Shell compact both ways; expanded only in store / interior / `view=atoms` |
| Orphan ports | Reject stand-alone `+ PORT` without ownership when sugar is in force |
| Deep nest blow-up | One shell per call; optional nest-open cap |
| Port-grain conflation | Keep Capsule `PORT` / SysML `POR` / PCBA `PIN` distinct |
| `refines` polarity flip | Shell tip → finer only |

---

## 8. MVP vs later

“MVP” = first implementation drop of the **1.x dialect** (breaking vs 0.3.x teaching).

### MVP (design lock)

| Item | Lock |
|------|------|
| Atoms | NODE \| EDGE only |
| Ontology | **`CST`** + **`PORT`** + **`CAP`** (nesting) + carrier/membership EDGEs; law on `CST`; EDGE ≠ law |
| Causality | Port `side=` + optional `form=causal\|acausal` on **`CST`** — **not** a second leaf kind |
| Capsule | Sugar B on agent shell; nested capsules one shell at a time; CAP = pin-map nesting |
| `pin_map` | Honour `layer` and/or `view=shell\|interior` |
| Caps | Existing `depth` / `max_rows`; optional nest-open limit N |
| Engine auto-summary | **No** — agents / ingest write `summarises` |
| SysML | Optional ingest / analogy only — not product scope |

### Later

| Item |
|------|
| SCHEMA / TagMap formalisation + golden fixtures |
| Law-on-node evaluator; optional `carries=` |
| Optional `FN` sugar alias for `CST; form=causal` — only if earned |
| Engine nest-open cap + breadcrumb ancestors |
| Schematic pin↔pin migration of `connects_to` |
| Drop transitional flat self-loop teaching |
| `view=atoms`; multi-layer breadcrumb section |
| Automatic SysML part/port → capsule ingest |

---

## 9. Open decisions

Answer each as **“refactor to X”** for the 1.x target — not “extend today’s `RES` MVP forever”.

| # | Decision | Lock sketch | Reject / demote |
|---|----------|-------------|-----------------|
| **1** | **`ports=` sugar owners** | (a) sugar on `CST` too, **or** (b) `CAP` only with leaf ports as atoms | Contradictory sugar rules |
| **2** | **`law=` binding to port fields** | One rule **on the node**: port `name=` + quantity; **or** `src_ports=` / `tgt_ports=` on the node; **or** `PORT_x.V` | Ad-hoc mirrors; binding via EDGE endpoints |
| **3** | **Flat vs ports-first** | **One target:** law on `CST`; flat self-loop = transitional only | Forever dual-MVP; formula-on-edge |
| **4** | **Locator coexistence** | Ingest grain + `refines` with **exit criteria**; **or** keep forever as locator-only | `PIN`/`NET` as maths hubs |
| **5** | **Op-amp leaf** | **Locked:** `CST [CST_OpAmp]` + ports + `form=causal` + law on node; InvAmp = `CAP` + `CST_*` | Hollow `CAP`+`RES`; gain on `derives` EDGE |
| **6** | **`feeds` / `derives` as law carriers** | **Locked demote** for 1.x laws | Teaching those + `expr` as the law leaf |
| **7** | **Shell `CLM`** | Summary only; constitutive maths on `CST` | Shell self-loop as primary formula teaching |
| **8** | **Behaviour vs EDGE** | **Locked:** law on `CST`; EDGE = carrier / membership / boundary | Formula-on-edge; `constrains` EDGE is the law |
| **9** | **What `connects` carries** | Optional `carries=V` / `carries=I` — lock spelling before SCHEMA | Full flow type system in this doc |
| **10** | **BJT leaf** | **Locked:** `CST [CST_Q1]` + three `PORT`s + `beta=` + `law=…` on the node (`form=causal`) | β-law on EDGE; truncated ports; omit emitter; hollow `CAP` only |
| **11** | **Causality wire encoding** | **Locked narrow:** one leaf **`CST`**; causality via `side=` + optional `form=`; `FN` deferred sugar | Locking dual `FN`+`CST` kinds for 1.0; causality on EDGE; SysML constraint stack |

**Out of this lock set:** recycle policy; ACL / RSV; nest-open depth `N`; TagMap timing — separate tracks; do not justify dual dialect.

---

## 10. Related docs

| Path | Role |
|------|------|
| [`memnet-grammar-design.md`](memnet-grammar-design.md) | Shared dialect SSOT; §3 = I/O/store/transport (different “layering”) |
| [`memnet-field-formulas.md`](memnet-field-formulas.md) | Flat same-node `derives` (**transitional**); 1.x → law on `CST` |
| [`../application-notes/llm-nodal-analysis-formulas.md`](../application-notes/llm-nodal-analysis-formulas.md) | Circuit interior application |
| [`../application-notes/examples/inverting-amplifier-memnet.md`](../application-notes/examples/inverting-amplifier-memnet.md) | Worked InvAmp; wrap → `CST` under `CAP` |
| [`memnet-neighbourhood-reserve.md`](memnet-neighbourhood-reserve.md) | Reserve = pin_map ego within active view |
| [`memnet-security-multi-agent.md`](memnet-security-multi-agent.md) | ACL before reserve; shell lease ≠ interior |
| `docs/grammar/examples/` | Future golden fixtures for capsule/shell slices |
| SysML v2 models / ingest | Optional mapping target — not wire syntax or product scope |

---

## Requirement fit (thin)

| Aim | How this helps |
|-----|----------------|
| MN-REQ-00 | Compact shell sugar + descend once |
| MN-REQ-02 NODE\|EDGE | Store = atoms; sugar desugars 1:1 |
| MN-REQ-08 Write = display | Shell compact both ways |
| MN-REQ-10 / 11 pin caps | `depth`/`max_rows` + stratum filter |
| MN-REQ-11.13 no corpus dump | Shell never embeds full interior |

No change to `requirements.sysml` in this design task.
