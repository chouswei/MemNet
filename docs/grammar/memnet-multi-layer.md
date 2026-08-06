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

1. [Purpose](#1-purpose)
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

Agents need to **reason at layer L**, then **descend only when needed** — finite-a first, then refine. Capsules give a SysML-like **part-with-ports** shell; elemental leaves hold constitutive / behavioural law **on the node**.

This is a **complete refactor** of the agent dialect (and the engine assumptions that serve it), not a small tweak on today’s stamp hubs. Transport and MCP tool *names* may stay; payloads and kinds change.

---

## 2. Atoms

| Atom | Role |
|------|------|
| **NODE** | Kinded fact. Elemental leaves: **`CST`** / **`FN`**. Composition: **`CAP`**. Boundary: **`PORT`**. Also locator / session kinds (`CMP`, `NET`, `PIN`, `TSK`, `LAW`, …) |
| **EDGE** | **Carrier / incidence** between endpoints — moves something **in/out** (`connects`), or membership / boundary (`contains` / `exposes` / `refines` / `summarises`). **Not** the function or constraint |

### 2.1 Constraint family: FN ⊂ CST

Mathematically a **function is a special constraint**: directed / explicit (`y = f(x)`) versus a general constitutive relation (`F(…)=0`).

| Tag | Role | Law shape (sketch) |
|-----|------|--------------------|
| **`CST`** | General **constraint** node — constitutive law among port quantities | e.g. Ohm `V_a-V_b=I*R` (undirected / implicit) |
| **`FN`** | **Specialisation of `CST`**: directed / explicit map (inputs → outputs), still a constraint | e.g. BJT `I_c=beta*I_b`; op-amp `V_out=a_s*(V_inp-V_inm)` |

**Hierarchy (prose lock):** `FN ⊂ CST` — every FN is a constraint; not every CST is a directed map.

**Wire preference:** keep short agent tags **`FN`** and **`CST`** (familiar, thrifty). Do **not** invent a third primitive; optional later SCHEMA may encode subtype formally (`form=explicit|implicit` under one kind) — agents still write `FN` / `CST`.

**Law placement (locked):** `law=` / `expr=` / params (`beta=`, `R=`, `a_s=`) live **on the FN/CST node**, never on the EDGE.

**Witnesses:** BJT teachable law → **`FN`**; resistor Ohm → **`CST`**; op-amp gain → **`FN`**.

### 2.2 Kind roles

| Kind | Wire | Role |
|------|------|------|
| **Constraint** | **`CST`** | Constitutive elemental — ports (often `inout`); Ohm / C / L on the node |
| **Function** | **`FN`** | Directed CST — ports in/out; controlled-source / gain map on the node |
| **Capsule** | `CAP` | Composition shell — nests `FN` / `CST` / child `CAP`; sugar `ports=` / `contains=` |
| **Port** | `PORT` | Endpoint; quantities (`V=`, `I=`) live **on** the port; `side=in\|out\|inout\|internal` |
| **Pin / Net / CMP** | `PIN` / `NET` / `CMP` | Schematic locator grain (ingest) until exit criteria — not maths hubs |
| **`RES` / `VAR`** | as today | Demoted hubs — migrate into `FN`/`CST` + ports |

Reject wire tokens `CONSTRAINT` / `CON` / `FUNC` / `FUNCTION` / `DEV` / `PASS` / `PART` as the teachable passive leaf.

**Ownership:** `FN|CST|CAP --(exposes)--> PORT`. Capsule `contains` → leaf or child Capsule.

### 2.3 Design productions (ASCII)

```text
CapsuleNode    = CAP  [Id] ; name=Atom ; layer=Atom ; fields*
FunctionNode   = FN   [Id] ; name=Atom ; layer=Atom? ; law=… ; fields*   // FN ⊂ CST
ConstraintNode = CST  [Id] ; name=Atom ; layer=Atom? ; law=… ; fields*
PortNode       = PORT [Id] ; name=Atom ; side=in|out|inout|internal? ; fields*
ExposeEdge     = [OwnerId]   --(exposes)--> [PortId]     // Owner = CAP | FN | CST
ContainEdge    = [CapsuleId] --(contains)--> [ChildId]  // Child = CAP | FN | CST | …
ConnectEdge    = [PortId]    --(connects)--> [PortId]  ; carries=?   // carrier only
RefineEdge     = [PortId]    --(refines)--> [InteriorId]            // shell tip → finer
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
| `exposes` | `CAP`/`FN`/`CST` → Port | Contract / ownership |
| `contains` | Capsule → `FN` / `CST` / child Capsule | Composition (immediate only) |
| `connects` | Port → Port | **Carrier** — wiring moves V/I (optional `carries=…`) |
| `refines` | Port → finer Port / PIN / NET / CMP | Boundary bridge — **coarser → finer** only |
| `summarises` | Capsule / coarse → claim stub | Shell aggregate |
| `connects_to` | PIN → NET | Transitional schematic |
| `derives` / `constrains` **with law `expr`** | — | **Rejected** as 1.x teachable law |

**MUSTNOT:** put gain / Ohm / β-law on an EDGE; treat EDGE as FN or CST; orphan scalars on `RES` / free mirrors.

### 3.3 Wrong shapes (one box)

| Shape | Why wrong |
|-------|-----------|
| `[PORT] --(derives)--> [PORT] ; expr=…` | Formula-on-edge — EDGE ≠ FN/CST |
| Binary fake `src` + multi-port device | Topology lie (BJT has three terminals) |
| `RES_a` with `Vinp`/`Vinm`/`Vdiff` mirrors + self-loop | Orphan scalars; mirrors are not graph endpoints |
| Amp as hollow `CAP` with no `FN` | Behaviour has nowhere owned to live |
| Forever dual teaching (flat self-loop **and** ports-first as equals) | One target dialect; flat = transitional only |

---

## 4. Capsules (shell and interior)

### 4.1 Name and anatomy

**Chosen name: capsule** (wire **`CAP`**). Prefer over `part` / `module` / `block` (SysML / packaging collisions). SysML **part with ports** is the analogy and ingest target — do not embed SysML textual syntax in the agent wire.

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

Desugars to `CAP` + `PORT` + `exposes` / `contains` in the store. Whether `FN`/`CST` also accept `ports=` sugar is open (§9 #1).

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

Interior wiring is ordinary dialect under the Capsule: membership `contains`, boundary `refines`, schematic `connects_to` (transitional), port↔port `connects` carriers, and `FN`/`CST` law nodes. No third view token beyond `shell|interior`.

| Step | Call |
|------|------|
| 1. Shell | `pin_map(anchor=CAP_…, view=shell)` |
| 2. Descend | `pin_map(…, view=interior)` or re-anchor on a child / Port tip |
| 3. Ascend | Shell again — do not keep the whole interior in context |

Prefer `contains` for **immediate** children only (fan-out risk). Boundary descent uses `refines` from Ports.

---

## 5. Worked examples

All examples below are **proposed 1.x / not in engine**. Primary multi-port witness: **BJT**. Op-amp secondary.

### 5.1 BJT leaf (primary)

One **`FN`** node (directed CST): three ports B/C/E; law on the node. Load resistor is a separate **`CST`**; wiring is a **carrier** only.

```text
FN [FN_Q1] ; name=bjt_npn ; beta=100 ; ports=PORT_B:B:inout,PORT_C:C:inout,PORT_E:E:inout ; law=I_c=beta*I_b ; recycle=persistent
CST [CST_Rc] ; name=Rc ; R=1000 ; ports=PORT_Rc_a:a:inout,PORT_Rc_b:b:inout ; law=V_a-V_b=I_a*R ; recycle=persistent
E_c [PORT_C] --(connects)--> [PORT_Rc_a] ; carries=I
```

```text
+ FN [NEW] ; name=bjt_npn ; beta=100 ; ports=B:inout,C:inout,E:inout ; law=I_c=beta*I_b ; recycle=persistent
```

**Rejected:**

```text
# REJECTED — edge-as-FN + lies about three-terminal topology
E_x [PORT_B] --(derives)--> [PORT_C] ; expr=I_c=beta*I_b
```

| Gap BJT exposes | Lesson |
|-----------------|--------|
| Three ports | Binary `derives` cannot be the device |
| Multi-quantity | Binding lives **on the FN node**, not on EDGE endpoints |
| Law ≠ edge | `I_c=β·I_b` *is* the FN; `connects` only carries I/V |

Teachable leaf = **`FN`**. Full Ebers–Moll as mutual port constraints would be general **`CST`** — optional later, not the default teaching leaf.

### 5.2 Board Capsule + resistors

InvAmp board: Capsule shell; amp = **`FN`**; passives = **`CST`**; `connects` carry quantities only.

```text
CAP [CAP_InvAmp] ; ports=PORT_Vin:Vin:in,PORT_Vout:Vout:out ; contains=FN_OpAmp,CST_Rin,CST_Rf ; recycle=persistent
FN [FN_OpAmp] ; name=opamp ; a_s=1e6 ; ports=PORT_Inm:Inm:in,PORT_Inp:Inp:in,PORT_Out:Out:out ; law=V_out=a_s*(V_inp-V_inm) ; recycle=persistent
CST [CST_Rin] ; name=Rin ; R=10000 ; ports=PORT_Rin_a:a:inout,PORT_Rin_b:b:inout ; law=V_a-V_b=I_a*R ; recycle=persistent
CST [CST_Rf] ; name=Rf ; R=100000 ; ports=PORT_Rf_a:a:inout,PORT_Rf_b:b:inout ; law=V_a-V_b=I_a*R ; recycle=persistent
E_w1 [PORT_Out] --(connects)--> [PORT_Rf_a] ; carries=V
E_w2 [PORT_Rf_b] --(connects)--> [PORT_Inm] ; carries=V
```

Do **not** teach `CAP_OpAmp` + `RES` mirrors as the leaf. Flat InvAmp without Capsule wrap remains valid as a legacy / ingest example — see [`inverting-amplifier-memnet.md`](../application-notes/examples/inverting-amplifier-memnet.md).

### 5.3 Op-amp (secondary, same pattern)

```text
FN [FN_OpAmp] ; name=opamp ; a_s=1e6 ; ports=PORT_Inm:Inm:in,PORT_Inp:Inp:in,PORT_Out:Out:out ; law=V_out=a_s*(V_inp-V_inm) ; recycle=persistent
```

```text
# REJECTED — edge-as-FN
E_gain [PORT_Inm] --(derives)--> [PORT_Out] ; src_ports=PORT_Inp,PORT_Inm ; expr=a_s*(V_inp-V_inm)
```

Exact binding of port symbols in `law=` (`V_inp` vs `PORT_Inp.V`, optional `src_ports=` **on the node**) is open (§9 #2) — not fixed by putting the law on an EDGE.

---

## 6. Migration and demotions

Prefer **migrate → demote → sunset**, not forever parallel dialects.

| Stays | Migrates into 1.x | Demoted / sunset (agent surface) |
|-------|-------------------|----------------------------------|
| NODE\|EDGE store | Active stamps → **`FN`+ports+law** | Formula-on-edge; `RES`/`VAR` maths hubs |
| CAP sugar `ports=` / `contains=` | R/L/C → **`CST`+ports+law** | Agent-mirrored stamp fields; orphan scalars |
| Port→Port `connects` as carrier | Flat same-node `derives` → **law on FN/CST** | Forever dual-MVP; `constrains` EDGE as the CST |
| Transport; MCP tool *names* | Board wrap: passives → `CST`, amp/BJT → `FN` under `CAP` | Wire `CONSTRAINT` / `CON` / `DEV` / `PASS` |
| `PIN`/`NET`/`CMP` as **ingest** locators | — | Those kinds as long-term formula hubs |

[`memnet-field-formulas.md`](memnet-field-formulas.md) same-node self-loop MVP = **transitional migration note only**. Target: law on FN/CST; edges = carriers.

**Engine:** `FN` / `CST` kinds, law-on-node evaluator, optional `carries=` → **MemNet 1.0**, not a silent 0.3.x patch.

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
| Formula / law | **1.x:** on `FN`/`CST` nodes; flat self-loop = transitional |
| Nodal / InvAmp notes | Flat `NET`/`CMP`/`PIN` today; when wrapped → `CST` + `FN` under `CAP` — do not rename `PIN`→`PORT` |
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
| Ontology | `FN` ⊂ `CST`; law on node; EDGE = carrier; kinds `CAP` / `PORT` / `FN` / `CST` |
| Capsule | Sugar B on agent shell; nested capsules one shell at a time |
| `pin_map` | Honour `layer` and/or `view=shell\|interior` |
| Caps | Existing `depth` / `max_rows`; optional nest-open limit N |
| Engine auto-summary | **No** — agents / ingest write `summarises` |
| SysML | Analogy + future ingest only |

### Later

| Item |
|------|
| SCHEMA / TagMap formalisation + golden fixtures |
| Law-on-node evaluator; optional `carries=` |
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
| **1** | **`ports=` sugar owners** | (a) sugar on `FN`/`CST` too, **or** (b) `CAP` only with leaf ports as atoms | Contradictory sugar rules |
| **2** | **`law=` binding to port fields** | One rule **on the node**: port `name=` + quantity; **or** `src_ports=` / `tgt_ports=` on the node; **or** `PORT_x.V` | Ad-hoc mirrors; binding via EDGE endpoints |
| **3** | **Flat vs ports-first** | **One target:** law on FN/CST; flat self-loop = transitional only | Forever dual-MVP; formula-on-edge |
| **4** | **Locator coexistence** | Ingest grain + `refines` with **exit criteria**; **or** keep forever as locator-only | `PIN`/`NET` as maths hubs |
| **5** | **Op-amp leaf** | **Locked:** `FN [FN_OpAmp]` + ports + law on node; InvAmp = `CAP` + `FN` + `CST_*` | `CAP_OpAmp`+`RES`; gain on `derives` EDGE |
| **6** | **`feeds` / `derives` as law carriers** | **Locked demote** for 1.x laws | Teaching those + `expr` as FN/CST |
| **7** | **Shell `CLM`** | Summary only; constitutive maths on FN/CST | Shell self-loop as primary formula teaching |
| **8** | **Behaviour vs EDGE** | **Locked:** law on FN/CST; EDGE = carrier / membership / boundary | Formula-on-edge; `constrains` EDGE is the CST |
| **9** | **What `connects` carries** | Optional `carries=V` / `carries=I` — lock spelling before SCHEMA | Full flow type system in this doc |
| **10** | **BJT leaf** | **Locked:** `FN [FN_Q1]` + B/C/E + `law=I_c=beta*I_b` on node | β-law on EDGE; BJT as hollow `CAP` only |
| **11** | **FN ⊂ CST wire encoding** | Keep tags `FN`/`CST`; optional SCHEMA subtype later | Treating FN and CST as unrelated forever; inventing a third family |

**Out of this lock set:** recycle policy; ACL / RSV; nest-open depth `N`; TagMap timing — separate tracks; do not justify dual dialect.

---

## 10. Related docs

| Path | Role |
|------|------|
| [`memnet-grammar-design.md`](memnet-grammar-design.md) | Shared dialect SSOT; §3 = I/O/store/transport (different “layering”) |
| [`memnet-field-formulas.md`](memnet-field-formulas.md) | Flat same-node `derives` (**transitional**); 1.x → law on FN/CST |
| [`../application-notes/llm-nodal-analysis-formulas.md`](../application-notes/llm-nodal-analysis-formulas.md) | Circuit interior application |
| [`../application-notes/examples/inverting-amplifier-memnet.md`](../application-notes/examples/inverting-amplifier-memnet.md) | Worked InvAmp; wrap → CST + FN under CAP |
| [`memnet-neighbourhood-reserve.md`](memnet-neighbourhood-reserve.md) | Reserve = pin_map ego within active view |
| [`memnet-security-multi-agent.md`](memnet-security-multi-agent.md) | ACL before reserve; shell lease ≠ interior |
| `docs/grammar/examples/` | Future golden fixtures for capsule/shell slices |
| SysML v2 models / ingest | Analogy and target mapping — not wire syntax |

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
