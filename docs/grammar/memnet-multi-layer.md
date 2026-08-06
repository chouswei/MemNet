# Multi-layer MemNet and capsules (design)

**Status:** design only — **no engine implementation** in 0.3.5 / 0.3.6 (SemVer today: `project.toml` **0.3.6**).  
**Refactor framing (locked for design prose):** ports-first + **`FN`** (active) + **`CST`** (constraint) + **`CAP`** composition is a **complete refactor** of MemNet’s **shared dialect / agent surface** (and the engine assumptions that serve that surface) — **not** a small dialect tweak on today’s `RES`/`VAR` stamp hubs. Store atomics remain NODE|EDGE; transport and (likely) MCP tool *names* can stay. See §3.7 scope box and §13.  
**Versioning implication:** treat the target dialect as **breaking / next major** — label design prose **MemNet 1.x dialect** (recommend ship path **0.4 design → 1.0** when SCHEMA + engine land). Do **not** pretend compatibility with 0.3.x agent teaching of `RES` self-loop hubs as the long-term surface.  
**Thesis:** MemNet stays **NODE | EDGE** only in the store; agents use **compact capsule sugar** on the shell (`ports=` / `contains=` on `CAP`) that desugars 1:1 to those atoms. Complex work zooms through **layers** and reusable **capsules** (SysML-like part-with-ports — including capsule-in-capsule). Port-hood is structure (store: kind `PORT` + `exposes`), not id punctuation.  
**Direction (locked for design prose):** elemental leaves with ports — **`FN`** and **`CST` are NODEs that *are* the function / constraint** (law / `expr` / `law=` lives **on the node**); Capsules (`CAP`) compose them. **EDGE ≠ function/constraint** — an EDGE is a **carrier** of what goes **in/out** between ports (flow / signal / incidence of quantities), not the gain or Ohm law. Never orphan scalars on `RES` / free fields. See §3.7.  
**Grammar incompleteness (open):** how the FN/CST **node** names multi-port IO in its law without smuggling via edge-as-function (e.g. `src_ports=` / `tgt_ports=` / `law=` **on the node**). Binary EDGE arity remains a store fact for carriers; **do not** “fix” multi-input by putting `expr` on an EDGE. §3.7; §13 #8–#9.  
**Aims:** MN-REQ-00 — save wall-clock and tokens while keeping factual accuracy; bounded live **pin map** each turn; Write = display.  
**Dialect:** shared dialect (ASCII; no `|` pipe on the agent surface). British English.  
**Related:** [`memnet-grammar-design.md`](memnet-grammar-design.md) (§3 store layering ≠ this doc), [`memnet-field-formulas.md`](memnet-field-formulas.md) (flat same-node `derives` = **transitional** only; 1.x = law on `FN`/`CST`), [`memnet-neighbourhood-reserve.md`](memnet-neighbourhood-reserve.md), [`memnet-security-multi-agent.md`](memnet-security-multi-agent.md), nodal / InvAmp app notes under `docs/application-notes/` (flat interior; optional Capsule wrap).

**Disambiguation:** §3 *Layering* in the grammar design doc is **I/O / store / transport**. This document is **stratified product graph** (abstraction strata + capsule shell/interior) so agents do not load the whole net into context. App-note phrases such as “Layer A / Layer B” in the inverting-amplifier example mean **circuitry vs formula relations**, not capsule strata and not grammar §3.

---

## 1. Problem

A single flat ego expand (`depth` / `max_rows`) cannot scale to system → board → net → equation (or LAW → working pins → stamp detail) without either:

- blowing the pin-map budget, or
- forcing the agent to reason without the right level of abstraction.

Agents need to **reason at layer L**, then **descend only when needed** — finite-a first, then refine — not dump every stratum at once.

---

## 2. Foundation (store unchanged; dialect refactors)

| Atom | Role |
|------|------|
| **NODE** | Kinded fact. **`FN` / `CST` *are* the behaviour / constitutive law** (params + `law=` / `expr` on the node). Also `CAP`, `PORT`, `CMP`, `NET`, `TSK`, `LAW`, … |
| **EDGE** | **Carrier / incidence** between endpoints — moves something **in/out** (e.g. `connects` between ports carries V/I). Membership (`contains` / `exposes`) and boundary (`refines`) too. **Not** the function or constraint itself |

**MUSTNOT:** invent a third conceptual primitive; treat an EDGE as the FN/CST (no `expr` / gain / Ohm on a `derives` / `constrains` edge as the teachable 1.x law). Capsules and layers are **patterns and projections** over NODE|EDGE. The **complete refactor** (§3.7) locks laws-on-nodes + edges-as-carriers.

---

## 3. Composition pattern: capsule (part with ports)

### 3.1 Name (locked for design prose)

**Chosen name: capsule** (English). Wire kind token: **`CAP`** (gloss: Capsule).

| Candidate | Why not (or why demoted) |
|-----------|--------------------------|
| `part` | SysML v2 familiarity is useful as **analogy**, but collides with repo layout `parts/` and reads as “copy SysML into the wire” |
| `module` | Overloaded (code modules, packaging) |
| `block` | SysML v1 baggage; vague shell semantics |
| `unit` | Too generic |
| `assembly` | Good engineering sense; weaker “exterior vs interior” metaphor for zoom |
| **capsule / `CAP`** | **Preferred** — emphasises a **bounded shell** (ports + summary) vs **interior** graph; distinct from SysML `part` and MemNet folder `parts/` |

**Ports** are boundary **NODEs**. Wire kind token: **`PORT`** (gloss: Port) — prefer this spelling over opaque `POR` in new capsule design prose. **Internal structure** is nested NODE|EDGE owned by / reachable under the capsule. **Connections between capsules** are EDGEs whose endpoints are **ports** (not arbitrary interior nodes), so the shell stays a stable contract.

SysML v2 **part with ports** is the **analogy and ingest target** — map part/port/connection into MemNet NODE|EDGE on ingest. **Do not** embed SysML textual syntax in the agent wire. Nested SysML parts map to **capsule-in-capsule** (§3.5); the wire still shows only NODE|EDGE. SysML ingest may still emit kind `POR` / `PRT` as artefact pins; capsule shells use `CAP` + `PORT` + `exposes`.

#### Three “port” grains (do not conflate)

| Grain | Kind / rel | Role | Not |
|-------|------------|------|-----|
| **Capsule Port** | `PORT` + Capsule `--(exposes)-->` Port | Shell contract of a Capsule; inter-capsule wiring | A schematic pad or a SysML artefact pin by default |
| **SysML port pin** | `POR` (+ `PRT`) + `--(hasPort)-->` | Locator into SysML model text | Capsule shell kind — map with edges / ingest, do not rename in place |
| **PCBA terminal** | `PIN` + `--(owns)-->` / `--(connects_to)-->` | Locator into `.ato` / schematic | Capsule `PORT` — keep `PIN_*` ids; optional `PORT --(refines)--> PIN|NET` when a capsule wraps the stage |

**Also not:** formula “field ports” (`FLD_*`) — rejected in [`memnet-field-formulas.md`](memnet-field-formulas.md). Capsule `PORT` is a **composition boundary**, not a field locator.

**Shell wiring rel:** Capsule Port → Capsule Port uses `--(connects)-->`. Schematic pin → net stays `--(connects_to)-->`. Different grains; do not merge the tokens.

### 3.2 Shared-dialect grammar (port-hood is structure)

**Locked preference:** port-hood and capsule-hood are **grammar / graph structure**, not id punctuation.

| Fact | Carried by | Not by |
|------|------------|--------|
| This node is a Capsule | kind `CAP` (+ optional `role=capsule`, `layer=`) | Id shape alone |
| This node is a Port | kind `PORT` (+ optional `side=in\|out\|inout`, `name=`) | Underscores, dotted paths, or `__` in the id |
| Port belongs to Capsule | EDGE `Capsule --(exposes)--> Port` | Encoding “owner” inside the port id |
| Child Capsule / interior atom | EDGE `Capsule --(contains)--> Child` | Nested path-in-id |

**Design productions** (ASCII; same shapes for bare present and mutate; TagMap / SCHEMA formal lock later):

```text
CapsuleNode    = CAP  [Id] ; name=Atom ; layer=Atom ; role=capsule? ; fields*
FunctionNode   = FN   [Id] ; name=Atom ; layer=Atom? ; fields*       // active elemental (§3.7)
ConstraintNode = CST  [Id] ; name=Atom ; layer=Atom? ; fields*       // constitutive elemental (§3.7)
PortNode       = PORT [Id] ; name=Atom ; side=in|out|inout|internal? ; layer=Atom? ; fields*
ExposeEdge     = [OwnerId]   --(exposes)--> [PortId]   ; fields*      // Owner = CAP | FN | CST
ContainEdge    = [CapsuleId] --(contains)--> [ChildId] ; fields*      // Child = CAP | FN | CST | …
ConnectEdge    = [PortId]    --(connects)--> [PortId]  ; carries=? ; fields*  // carrier in/out (not the FN/CST law)
RefineEdge     = [PortId]    --(refines)--> [InteriorId] ; fields*    // locked: shell tip -> finer grain
```

`layer=` on nodes is an **abstraction-stratum** token (`system` / `board` / … — §4). Shell vs interior is the pin-map **`view=`** envelope argument, not a second meaning of `layer=`. Do not write `layer=shell` / `layer=interior` on edges.

`role=port` is **demoted** when kind is already `PORT` (noise). Keep `role=capsule` optional on `CAP` only if a session mixes capsule shells with other `CAP`-looking ids before SCHEMA lock — default: kind alone is enough.

#### Ids and underscore (`_`)

Underscore in ground ids (`CAP_InvAmp`, `PORT_Vin`, `ATO_R1`, `LAW_KCL`) is only the familiar **`KIND_rest` separator** used across MemNet — **optional locator sugar**, never the sole signal that a node is a port of a Capsule.

| Verdict | Detail |
|---------|--------|
| **Keep `_` as KIND_rest** | Same house style as `ATO_R1` / `MOD_wire`; ASCII; LLM-familiar |
| **Discourage id-as-grammar** | Do **not** teach `CAP_inv._`, `CAP_inv__in`, `CAP_inv.P_in`, or nested path-in-id as how agents “know” a port |
| **Truth on the wire** | kind + `exposes` / `contains` (+ short fields). Copy assigned ids from pin map / mint ack |

**MUSTNOT:** invent a third AST primitive; encode hierarchy only in `note=`; make port-hood depend on counting underscores.

### 3.3 Anatomy (pattern, not new AST kinds)

```text
Capsule = {
  shell_node:     NODE,              // CAP [Id] ; …  (Capsule)
  ports:          NODE[],            // PORT [Id] ; … (Port) — boundary only
  shell_edges:    EDGE[],            // exposes / connects / summarises
  interior:       NODE[] + EDGE[],   // refined graph — may include child capsules
  cross_links:    EDGE[],            // summarises | refines | exposes (shell <-> interior)
}
```

**Bare present** (default **shell** pin_map — compact capsule sugar §8.1; no interior dump):

```text
## Nodes
CAP [CAP_InvAmp] ; name=inverting_amp ; layer=board ; ports=PORT_Vin:Vin:in,PORT_Vout:Vout:out ; recycle=persistent
CLM [CLM_gain] ; layer=board ; gain_v=-10 ; recycle=persistent

## Edges
Ec [CAP_InvAmp] --(summarises)--> [CLM_gain]
```

**Interior** (after descend / `view=interior` — still `depth` / `max_rows` capped). Nodal / schematic atoms stay `NET` / `CMP` / `PIN` — do not rename them to `PORT`. Thin sketch (membership + boundary only); full wiring is §3.6:

```text
## Nodes
NET [NET_VIN] ; layer=board ; recycle=persistent
CMP [ATO_Rf] ; refdes=Rf ; layer=board ; path=boards/amp/amp.ato ; recycle=persistent

## Edges
E3 [CAP_InvAmp] --(contains)--> [NET_VIN]
E4 [CAP_InvAmp] --(contains)--> [ATO_Rf]
E6 [PORT_Vin] --(refines)--> [NET_VIN]
```

Prefer `contains` for **immediate** children (child Capsules, key nets/parts) — not a mandatory edge to every leaf (fan-out risk). Boundary descent uses `refines` from Ports. Interior **interconnection** (PIN↔NET, port `connects` carriers, `FN`/`CST` law nodes) is ordinary dialect inside the open Capsule — §3.6 / §3.7.

**Mutate** (compact sugar; ops mutate-only; desugars to store atoms §8.1):

```text
+ CAP [NEW] ; name=inverting_amp ; layer=board ; ports=Vin:in,Vout:out ; recycle=persistent
~ [CAP_InvAmp] ; contains=ATO_Rf
```

Kind tokens `CAP` / `PORT` remain the **store** kinds; agent shell prefers sugar fields on `CAP`. Final TagMap / SCHEMA is a later lock. No third conceptual primitive beyond NODE|EDGE.

### 3.4 Shell vs interior = view pair

| View (`view=`) | What pin_map shows | Budget |
|----------------|--------------------|--------|
| **Shell** (default for a Capsule anchor) | Compact `CAP` sugar (`ports=` / `contains=`) + summary / `connects` / sibling Capsules / LAW — not full Port+`exposes` expand (§8.1) | Small — stays under `max_rows` |
| **Interior** (descend) | Contained NODE\|EDGE ego from an interior anchor or `view=interior` | Still capped by `depth` / `max_rows` |

**Descend = open the capsule** — change anchor to a Port / interior node, or pass an explicit view; do **not** paste the whole interior into the shell pin map. Stratum field `layer=` (system/board/…) is orthogonal to this view pair (§4).

### 3.5 Nested capsules (capsule-in-capsule)

**Yes — recursive composition is allowed.** A Capsule’s interior may contain child Capsules (and leaf atoms). Analogy: SysML v2 **nested parts** — each child is again a part-with-ports; MemNet expresses the same idea as NODE|EDGE with `contains` / `exposes` / `refines` / `summarises`, not a new primitive.

```text
CAP (Capsule system)
  exposes → PORT …           # system shell ports
  contains → CAP (board)     # child Capsule (shell visible when parent opens interior)
               exposes → PORT …
               contains → CAP (stage) / NET / CMP …
```

| Rule | Detail |
|------|--------|
| **Composition** | Parent `--(contains)-->` child Capsule shell; child keeps its own Ports via `exposes`; parent–child or sibling wiring still lands on **Ports**, not arbitrary grandchild interiors |
| **Descend** | Parent Port `--(refines)-->` child Port / interior; or re-anchor via `contains` — same thin cross-links as §5.2 |
| **pin_map** | **One shell at a time.** Default view for a Capsule anchor = that Capsule’s shell only. Opening the parent does **not** auto-expand grandchild interiors. Re-anchor (or `view=interior` one step) to open the next Capsule |
| **Depth limits** | Hard budget remains `depth` / `max_rows` **within** the active shell/interior view. Design default: **one capsule-open step per turn** when possible; engine MVP may also cap nesting depth (e.g. refuse expand past N nested opens in one call) — exact N is an implementation lock |
| **MUSTNOT** | Dump nested interiors in one pin map; treat nesting as prose in `note=`; invent a “nested capsule” AST kind outside NODE\|EDGE; encode nest level in the id |

Illustrative nest sketch (**parent shell only**, compact sugar — child’s own ports appear when that child is the anchor):

```text
## Nodes
CAP [CAP_Pdu] ; name=pdu ; layer=system ; ports=PORT_Vbus:Vbus:out ; contains=CAP_Rail12 ; recycle=persistent
CAP [CAP_Rail12] ; name=rail_12v ; layer=board ; recycle=persistent

## Edges
Ef [PORT_Vbus] --(refines)--> [CAP_Rail12] ; note=descend_hint
```

Workflow: `pin_map(CAP_Pdu, view=shell)` → reason → if needed `pin_map(CAP_Rail12, view=shell)` (child’s `ports=` sugar) → only then interior leaves. Goldfish: re-read the **current** shell each turn; do not keep the whole nest in context.

### 3.6 Interior interconnection view (worked)

**Question:** once a Capsule is open, how do agents see **wiring between ports and interior parts** — not only shell `ports=` sugar?

**Answer:** the interior interconnection view is ordinary NODE|EDGE schematic / nodal dialect **under** the Capsule. There is **no** third view token beyond `view=shell|interior` (optional later: `view=atoms` for expanded shell). Interconn lives **inside** `view=interior` (or an interior re-anchor). Shell `connects` (Port→Port) stays on the shell; interior uses schematic `connects_to` (PIN→NET) plus Port `refines` as the boundary bridge.

#### How the agent opens the interior

| Step | Call | What you get |
|------|------|----------------|
| 1. Shell | `pin_map(anchor=CAP_InvAmp, view=shell)` | Compact `CAP` + `ports=` / `contains=` / `summarises` — **no** PIN/NET dump |
| 2a. Descend (preferred) | `pin_map(anchor=CAP_InvAmp, view=interior)` | Contained ego: children, Port `refines`, PIN–NET / port `connects` carriers, `FN`/`CST` law nodes — still `depth` / `max_rows` capped |
| 2b. Re-anchor | Follow one `refines` / `contains` tip → `pin_map(anchor=NET_VMINUS)` (or `ATO_Rf`, …) | Same interior grain, tighter ego around that node |
| 3. Ascend | `pin_map(anchor=CAP_InvAmp, view=shell)` again | Shell contract only; do not keep the whole interior in context |

**MUSTNOT:** paste interior interconnect into the shell pin map; invent `view=interconn` as a separate dialect; use Port→Port `connects` for schematic pads; rename `PIN`/`NET` to `PORT`.

#### What lines appear (InvAmp Capsule interior)

Shell first (contract only):

```text
## Nodes
CAP [CAP_InvAmp] ; name=inverting_amp ; layer=board ; ports=PORT_Vin:Vin:in,PORT_Vout:Vout:out ; contains=NET_VIN,NET_VMINUS,NET_VOUT,NET_VGND,ATO_Rin,ATO_Rf ; recycle=persistent
CLM [CLM_gain] ; layer=board ; gain_v=-10 ; recycle=persistent

## Edges
Es [CAP_InvAmp] --(summarises)--> [CLM_gain]
```

Interior interconnect after `view=interior` (ASCII shared dialect; bare present). Membership, boundary `refines`, schematic wiring, and one formula edge.

**Note:** the `RES_A` closed-loop stamp below is **transitional** (today’s flat maths hub). Target amp leaf = **`FN_OpAmp`** (§3.7 / next subsection); passives migrate to `CST`. Do not invent a competing `CAP_OpAmp` for the amp.

```text
## Nodes
NET [NET_VIN] ; net=VIN ; layer=board ; recycle=persistent
NET [NET_VMINUS] ; net=VMINUS ; layer=board ; recycle=persistent
NET [NET_VOUT] ; net=VOUT ; layer=board ; recycle=persistent
NET [NET_VGND] ; net=VGND ; role=reference ; layer=board ; recycle=persistent
CMP [ATO_Rin] ; refdes=R1 ; value=10k ; R=10000 ; layer=board ; recycle=persistent
CMP [ATO_Rf] ; refdes=R2 ; value=100k ; R=100000 ; layer=board ; recycle=persistent
PIN [PIN_R1_a] ; refdes=R1 ; pin=1 ; recycle=persistent
PIN [PIN_R1_b] ; refdes=R1 ; pin=2 ; recycle=persistent
PIN [PIN_R2_a] ; refdes=R2 ; pin=1 ; recycle=persistent
PIN [PIN_R2_b] ; refdes=R2 ; pin=2 ; recycle=persistent
RES [RES_A] ; A_s=-10.0 ; Rf=100000 ; Rin=10000 ; domain=s ; recycle=persistent

## Edges
# ownership (immediate children — not every leaf required)
Ec1 [CAP_InvAmp] --(contains)--> [NET_VIN]
Ec2 [CAP_InvAmp] --(contains)--> [NET_VMINUS]
Ec3 [CAP_InvAmp] --(contains)--> [NET_VOUT]
Ec4 [CAP_InvAmp] --(contains)--> [ATO_Rin]
Ec5 [CAP_InvAmp] --(contains)--> [ATO_Rf]
Ec6 [CAP_InvAmp] --(contains)--> [RES_A]

# shell Port -> interior net (boundary bridge; locked polarity)
Er1 [PORT_Vin] --(refines)--> [NET_VIN]
Er2 [PORT_Vout] --(refines)--> [NET_VOUT]

# schematic interconnect (interior only — not connects)
Ew1 [PIN_R1_a] --(connects_to)--> [NET_VIN]
Ew2 [PIN_R1_b] --(connects_to)--> [NET_VMINUS]
Ew3 [PIN_R2_a] --(connects_to)--> [NET_VOUT]
Ew4 [PIN_R2_b] --(connects_to)--> [NET_VMINUS]

# formula (TRANSITIONAL flat RES self-loop — not 1.x; see §3.7 law-on-FN/CST)
Ef1 [RES_A] --(derives)--> [RES_A] ; tgt_field=A_s ; src_fields=Rf,Rin ; expr=-(Rf/Rin)
```

Topology this encodes: `Vin -- Rin -- VMINUS -- Rf -- Vout` with feedback at `VMINUS`. The **op-amp itself is one leaf `FN`** (§3.7), not a child Capsule soup — board interior contains `FN_OpAmp` plus `CST` resistors; Port–Port `connects` wire them. Do **not** teach `CAP_OpAmp` + `RES_a` mirrors as the default leaf.

#### Op-amp as one NODE (canonical leaf)

**Question:** if an op-amp is a node, how do you express it?

**Answer:** one **`FN`** node that *is* the amp: it owns ports and holds the law (and `a_s`). Board assembly uses **`connects` EDGEs only as carriers** of V/I between ports — never a `derives` EDGE pretending to *be* the gain. Use a child `CAP` around the amp **only** when you need a nestable composition shell with its own exposed board contract (rare for a single behavioural leaf).

**Rejected (wrong twice — do not teach):** EDGE as the function *and* binary fake `src`:

```text
# REJECTED — edge-as-FN + incomplete topology
FN [FN_OpAmp] ; name=opamp ; a_s=1e6 ; ports=PORT_Inm:Inm:in,PORT_Inp:Inp:in,PORT_Out:Out:out ; recycle=persistent
E_gain [PORT_Inm] --(derives)--> [PORT_Out] ; src_ports=PORT_Inp,PORT_Inm ; owner=FN_OpAmp ; expr=a_s*(V_inp-V_inm) ; tgt_field=V
```

Also reject multi-from `derives` with `expr` on the EDGE — that still treats the edge as the function (§3.7).

**Proposed 1.x / not in engine** (law on FN node; carriers only when wiring):

```text
# Proposed — FN *is* the amp; law + ports on the node
FN [FN_OpAmp] ; name=opamp ; a_s=1e6 ; ports=PORT_Inm:Inm:in,PORT_Inp:Inp:in,PORT_Out:Out:out ; law=V_out=a_s*(V_inp-V_inm) ; recycle=persistent
```

Open (not fixed by edge-as-function): exact field spelling for naming port IO in the law (`law=` vs `expr=`; whether `src_ports=` / `tgt_ports=` appear **on the FN node** — §13 #2 / #8).

Mutate sugar (engine desugars `ports=` on `FN` the same way as on `CAP` / `CST` — §13 #1):

```text
+ FN [NEW] ; name=opamp ; a_s=1e6 ; ports=Inm:in,Inp:in,Out:out ; law=V_out=a_s*(V_inp-V_inm) ; recycle=persistent
```

**Wrong shapes (do not teach):**

| Shape | Why wrong |
|-------|-----------|
| Any `derives` / `constrains` EDGE carrying `expr=` as the gain / Ohm law | **EDGE ≠ FN/CST** — law lives on the node; EDGE only carries in/out |
| Binary `[PORT_Inm] --(derives)--> [PORT_Out]` + `src_ports=…` | Edge-as-FN **and** topology lie |
| Multi-from `[PORT_Inp,PORT_Inm] --(derives)--> [PORT_Out] ; expr=…` | Still formula-on-edge — rejected |
| `RES_a` with `Vinp`/`Vinm`/`Vdiff` mirrors + self-loop `derives` | Orphan scalars; mirrors are not graph endpoints |
| Amp as only `CAP_OpAmp` with no `FN` | Capsule is composition; behaviour has nowhere owned to live |
| Amp as three free nodes (`VAR`/`NET`/`RES`) | Soup — not one leaf with a contract |

**Transitional pain (demoted):** Port → Net → Var → `RES_a` mirrors under a child `CAP_OpAmp` is what agents invent today. **Do not teach it.** Prefer the `FN` leaf with law on the node. Kept historically only as the failure mode §3.7 removes.

**Descend path (board):** `pin_map(CAP_InvAmp, view=shell)` → interior (sees `FN_OpAmp` + `CST_*` + `connects` carriers). Re-anchor on `FN_OpAmp` only if you need that leaf’s ports/law ego — **not** a nested Capsule open for a lone amp.

**MUSTNOT:** invent `view=opamp` / `view=interconn`; dump amp ports into the InvAmp **shell**; put Rin/Rf inside the op-amp node; rename Capsule/FN Ports to schematic `PIN_*`; teach `CAP_OpAmp`+`RES` as the long-term leaf; teach formula-on-edge (`derives`/`constrains` + `expr`) as 1.x.

### 3.7 Direction: function / constraint with ports

**Complete-refactor statement:** this section is the **target ontology** for MemNet’s agent dialect after a **breaking** redesign — not an optional overlay on 0.3.x stamp teaching. Prefer **one target dialect** + migration notes; reject forever dual-MVP (§13 #3).

#### Ontology lock (laws on nodes; edges as carriers)

| Claim | Consequence |
|-------|-------------|
| **`FN` / `CST` are NODEs** | The node *is* the function or constitutive constraint; **`law=` / `expr=` / params (`a_s`, `R`) live on that node** (or on a child formula NODE owned by FN/CST — still a NODE) |
| **EDGE ≠ FN/CST** | An EDGE must **not** carry the gain / Ohm / free `expr` that *is* the behaviour |
| **EDGE = carrier (in/out)** | Port↔port **`connects`** (and membership `exposes` / `contains`, boundary `refines`) **carry** what goes between endpoints — flow / signal / incidence of quantities (e.g. voltage, current). Wiring moves something; it does not *be* the law |

**Rejected as teachable 1.x:** formula-on-edge (`[PORT] --(derives)--> [PORT] ; expr=…`); “`constrains` EDGE is the CST”; multi-from hyper-edge with `expr` on the EDGE (still edge-as-function). Flat same-node `derives` in [`memnet-field-formulas.md`](memnet-field-formulas.md) = **transitional migration note only**.

**Still open (grammar incompleteness — not fixed by edge-as-FN):** how the FN/CST **node** binds multi-port symbols in `law=` (Inp **and** Inm → Out) — e.g. `src_ports=` / `tgt_ports=` / port `name=` + quantity **on the node**. Binary EDGE remains fine for **carriers** (one wire, two ends). Optional later: `carries=V` (or item flow) on `connects` — sketch only (§13 #9); do not over-invent.

**Core interconnect rule:** every **wiring** EDGE is **port→port** (or pin→pin transitional). Elemental leaves that expose ports:

| Leaf | Wire | Nature |
|------|------|--------|
| **Function** | **`FN`** | Active NODE — law maps input-port quantities → output-port quantities (e.g. op-amp gain) |
| **Constraint** | **`CST`** | Constitutive NODE — law among port variables (e.g. Ohm `V_a-V_b=I*R`) |

Capsules (`CAP`) are **composition shells** that nest `FN`, `CST`, and child Capsules. Shared dialect stays NODE|EDGE only.

SysML analogy: *part* ≈ Capsule; *action / calc with ports* ≈ Function **node**; *constraint on values* ≈ Constraint **node**; *connection* ≈ EDGE **carrier** between ports.

**Kind token lock:** wire **`CST`** (gloss: Constraint). Reject wire `CONSTRAINT` (too long). Demote **`CON`** (collides mentally with `connects` / connection). Earlier candidates **`DEV` / `PASS` / `PART`** for passives are **demoted** — passive R/C look like constraints, not devices-as-parts.

#### Scope of the complete refactor

| **In** (must change for 1.x dialect) | **Out** (may stay; separate tracks) |
|--------------------------------------|-------------------------------------|
| Elemental ontology: **`FN` / `CST` / `PORT` / `CAP`** as the taught leaves + shell | Store atomics still **NODE \| EDGE** only (sugar desugars; no third AST primitive) |
| **Laws on FN/CST nodes**; interconnect EDGEs = **carriers** only (`connects` / membership / `refines`) | Transport: **in-process first**, TCP fallback |
| Demotion of formula-on-edge / `constrains`-edge-as-CST | Session / MCP **tool names** may keep (`pin_map`, `add`, `update`, …) — payloads change |
| `pin_map` views: shell sugar + interior under Capsules; Write = display | **ACL / RSV** (neighbourhood reserve) — orthogonal design track (§7) |
| Capsule sugar (`ports=` / `contains=`) as default agent shell (§8.1) | Recycle policy; nest-open depth `N`; TagMap formalisation timing |
| Demotion / sunset of **`RES` / `VAR` / `NET` / `PIN`-as-hubs** as the agent maths surface | Locator grains `PIN`/`NET`/`CMP` may linger as **ingest** until exit criteria (§13 #4) |
| Field-formulas **same-node self-loop MVP** → superseded by law-on-FN/CST (migration notes only) | Security multi-agent doc — not blocked by this dialect lock |

#### Today (0.3.x) vs target (1.x dialect)

| Today (scatter) | Target (complete refactor) |
|-----------------|----------------------------|
| `RES` / `VAR` / `NET` / `PIN` + agent-mirrored fields | **`FN` \| `CST` + `PORT`**; law on node; EDGE = carrier |
| Same-node `RES` self-loop `derives` + informal mirrors | `FN`/`CST` hold `law=`; port↔port `connects` carries V/I |
| Capsule interior = stamp bags | `CAP` nests `FN` / `CST`; shell sugar `ports=` stays |
| Dual teaching (flat self-loop **and** ports-first) | **One** target dialect; flat self-loop = **transitional** teaching only (§13 #3) |

#### Kind roles

| Kind | Wire token | Role |
|------|------------|------|
| **Function** | **`FN`** | Active elemental NODE — ports in/out; params (`a_s=`); **`law=` / `expr=` on the node** |
| **Constraint** | **`CST`** | Constitutive elemental NODE — ports (often `inout`); params (`R=`); **Ohm / C / L law on the node** |
| **Capsule** | `CAP` | Composition shell — nests `FN` / `CST` / child `CAP`; sugar `ports=` / `contains=` |
| **Port** | `PORT` | Endpoint; `V=` / `I=` live **on** the port; `side=in\|out\|inout\|internal` |
| **Pin / Net / CMP** | `PIN` / `NET` / `CMP` | Schematic locator grain — keep until pin↔pin migration; optional `CST --(refines)--> CMP` |
| **`RES` / `VAR`** | as today | Demoted hubs — migrate into `FN`/`CST` + ports under Capsules |
| **`DEV` / `PASS` / `PART`** | — | **Demoted** naming for passives; use `CST` |

**Ownership:** `FN|CST --(exposes)--> PORT`. Capsule `contains` → leaf; shell ports bind via sugar / `connects` / `refines`. Interior ports (`side=internal`) belong to the leaf (e.g. optional `PORT_Vdiff` on `FN_OpAmp` when an intermediate quantity is modelled as a port — law still on the FN).

**Amp leaf lock:** **op-amp node = `FN`** (`FN_OpAmp`) with law on the node. `CAP` only when you need a nestable composition shell with its own exposed ports (board / subsystem) — not as a hollow wrapper around a lone behavioural amp.

#### EDGE endpoint rule (carriers and membership — not laws)

| Rel | Endpoints | Notes |
|-----|-----------|-------|
| `exposes` | `CAP`/`FN`/`CST` → Port | Contract / ownership |
| `contains` | Capsule → `FN` / `CST` / child Capsule | Composition (immediate only) |
| `connects` | Port → Port | **Carrier** — wiring moves V/I (or later `carries=…`) between ports |
| `refines` | Port → finer Port / PIN / NET / CMP | Boundary / locator bridge |
| `connects_to` | PIN → NET | Transitional schematic |
| `derives` / `feeds` / `constrains` **with `expr` as the law** | — | **Rejected** for 1.x teachable surface (formula-on-edge) |

**MUSTNOT:** orphan `Vdiff` on `RES`; agent-mirrored `Vinp`/`Vinm`; teach Port→Net→Var→mirror as Capsule interior; invent `FLD_*`; wire kinds `FUNC` / `FUNCTION` / `CONSTRAINT` / `CON` / `DEV` as the passive leaf; put gain / Ohm `expr` on an EDGE.

#### Worked mini-example: op-amp leaf, then InvAmp board

**1. Op-amp = one `FN` node** (canonical leaf — proposed 1.x / not in engine):

```text
FN [FN_OpAmp] ; name=opamp ; a_s=1e6 ; ports=PORT_Inm:Inm:in,PORT_Inp:Inp:in,PORT_Out:Out:out ; law=V_out=a_s*(V_inp-V_inm) ; recycle=persistent
```

**2. InvAmp = board Capsule** — `CST` resistors hold Ohm on the node; **`connects` only carry** quantities between ports:

```text
CAP [CAP_InvAmp] ; ports=PORT_Vin:Vin:in,PORT_Vout:Vout:out ; contains=FN_OpAmp,CST_Rin,CST_Rf ; recycle=persistent
CST [CST_Rin] ; name=Rin ; R=10000 ; ports=PORT_Rin_a:a:inout,PORT_Rin_b:b:inout ; law=V_a-V_b=I_a*R ; recycle=persistent
CST [CST_Rf] ; name=Rf ; R=100000 ; ports=PORT_Rf_a:a:inout,PORT_Rf_b:b:inout ; law=V_a-V_b=I_a*R ; recycle=persistent
# board wiring: carriers only (sketch — Vin→Rin→Inm, Out→Rf→Inm feedback, …)
E_w1 [PORT_Out] --(connects)--> [PORT_Rf_a] ; carries=V
E_w2 [PORT_Rf_b] --(connects)--> [PORT_Inm] ; carries=V
```

`a_s` and gain law on `FN_OpAmp`; `R` and Ohm law on each `CST`; voltages/currents on ports; **`connects` carries** the net quantity — optional `carries=V` is a sketch (§13 #9), not a SCHEMA lock. No `derives`/`constrains` EDGE as the amp or resistor.

#### Compatibility / migration (under complete-refactor framing)

Prefer **migrate → demote → sunset**, not forever parallel dialects.

| Stays (substrate) | Migrates (into 1.x dialect) | Demoted / sunset (agent surface) |
|-------------------|-----------------------------|----------------------------------|
| NODE\|EDGE store; CAP sugar `ports=` / `contains=` | Active stamps → **`FN`+ports+law**; R/L/C → **`CST`+ports+law** | `DEV` / `PASS` / `PART` as passive kind |
| Port→Port `connects` as **carrier**; transport; tool *names* | `RES` self-loop `derives` → **law on FN/CST node** | Formula-on-edge; agent-mirrored stamp fields; **`RES`/`VAR` as maths hubs** |
| Flat InvAmp / PIN–NET as **legacy / ingest** examples | When wrapped: board passives → `CST`; amp → `FN` under `CAP` | Orphan scalars; Port→Net→Var→mirror path |
| Field-formulas same-node MVP as **migration note** only | Target: **law on FN/CST**; edges = carriers only | Wire `CONSTRAINT` / `CON`; forever dual-MVP; `constrains` EDGE as the CST |

**Engine:** design only — **not** in 0.3.5 / 0.3.6 (`FN` / `CST` kinds, law-on-node evaluator, optional `carries=`). Landing implies **MemNet 1.0** (or clearly labelled 1.x dialect) — not a silent 0.3.x patch.

#### Rel cheat-sheet (shell vs interior)

| Rel | Where | Endpoints |
|-----|--------|-----------|
| `exposes` / sugar `ports=` | Shell (`CAP` / `FN` / `CST`) | Owner → Port |
| `connects` | Wiring (**carrier**) | Port → Port |
| `contains` | Capsule interior | Capsule → `FN` / `CST` / child Capsule |
| `refines` | Boundary | Port → NET / PIN / CMP / child Port |
| `connects_to` | Schematic (transitional) | PIN → NET |
| `derives` / `constrains` + law `expr` | — | **Rejected** as 1.x law carrier |

Flat InvAmp without Capsule wrap remains valid — see [`inverting-amplifier-memnet.md`](../application-notes/examples/inverting-amplifier-memnet.md). When wrapped, board passives → `CST`, behavioural amp → `FN` (§3.7).

---

## 4. What a “layer” is

A **layer** is an **abstraction stratum** used to project a bounded pin map — not a separate store.

Three useful axes (orthogonal; mix carefully):

| Axis | Examples | Typical use |
|------|----------|-------------|
| **Domain hierarchy** | `system` / `board` / `net` / `equation` | Engineering zoom |
| **Summary vs detail** | shell fields vs stamp / formula interior | Capsule open/close |
| **Normative vs working** | `LAW` / requirements vs working pins / tasks | Goldfish + durable rules |

**MVP encoding (preferred):** field `layer=<token>` on nodes (and optionally edges), plus **cross-layer EDGEs** (`summarises` / `refines` / `exposes` / `contains`).  
**Demoted for MVP:** a free-standing LAYER node kind that agents must maintain as a second graph — sprawl risk.

Optional later: `layer=` as an envelope filter on `pin_map` only (projection hint), still backed by the same fields/edges.

---

## 5. How pin_map stays bounded

### 5.1 Pin map per layer (or per capsule view)

```text
pin_map(session, anchor, depth, max_rows, layer?=board, view?=shell|interior)
```

| Rule | Detail |
|------|--------|
| **Default** | Expand within the anchor’s layer / capsule **shell** only |
| **Up** | Follow `summarises` / parent `contains` inverse → coarser stratum (few rows) |
| **Down** | Follow `refines` (Port → finer) or re-anchor on a `contains` child Capsule; **one step** per turn when possible |
| **Nested open** | Parent shell → child shell → grandchild …; never flatten the whole nest in one call (§3.5) |
| **Caps unchanged** | Existing `depth` / `max_rows` still apply **inside** the chosen stratum |
| **No whole-graph dump** | Multi-layer / multi-capsule expand in one call is **out of MVP** |

Cross-layer links on the pin map are **thin**: endpoints + `rel` + short fields — enough to choose the next anchor, not enough to substitute for a descend.

### 5.2 EDGE kinds (design defaults)

| `rel` | Direction (convention) | Meaning |
|-------|------------------------|---------|
| `contains` | Capsule → interior node (or child Capsule) | Ownership / membership |
| `exposes` | Capsule → Port | Shell contract (port-hood link) |
| `summarises` | Capsule / coarse → key claim or interior stub | Aggregate fact visible on the shell |
| `refines` | Port / shell tip → finer grain (interior node, child Port, or schematic `PIN`/`NET`) | Descend hint — **locked polarity** below |
| `connects` | Capsule Port → Capsule Port | Inter-capsule shell wiring (not schematic `connects_to`) |

**Locked `refines` polarity (design):** coarser / shell tip `--(refines)-->` finer detail. Examples: `[PORT_Vin] --(refines)--> [NET_VIN]`; `[PORT_Vbus] --(refines)--> [PORT_RailOut]`. Ascend by inverse walk, `summarises`, or parent `contains` — do **not** emit the opposite arrow as `refines`. Agents copy what the pin map shows.

**MUSTNOT:** encode hierarchy only as prose in `note=`; use EDGE + stratum `layer=` + `view=` for shell/interior.

---

## 6. First-principles workflow (finite-a then limit)

Same spirit as nodal / formula work: settle the coarse model before refining.

```text
1. pin_map(anchor=system_or_capsule, view=shell, layer=L)
2. Reason and mutate at L only (absolute fields; short pins)
3. If blocked or inconsistent → follow one refines/exposes/contains edge
4. pin_map(anchor=child_capsule_or_port, view=shell|interior) — one open step; still depth/max_rows capped
5. Write interior facts; optionally refresh shell via summarises / materialised fields
6. Ascend; settle tasks; do not keep nested shells or all layers in context
```

**Goldfish:** chat is not SSOT; re-read the **current** layer’s pin map each turn. Do not reason on a stale multi-layer dump from an earlier turn.

Analogy: finite element / asymptotic reasoning — pick the scale that answers the question; refine locally when the residual matters.

---

## 7. Interaction with existing design

| Mechanism | Interaction |
|-----------|-------------|
| **`depth` / `max_rows`** | Still the hard budget **within** a layer/view; layers prevent burning the budget on irrelevant strata |
| **Formula / law placement** | **1.x locked:** `law=` / `expr=` on **`FN`/`CST` nodes**; `connects` = carrier only. Flat same-node self-loop `derives` = transitional only (§13 #3 / #8). See [`memnet-field-formulas.md`](memnet-field-formulas.md) |
| **Nodal / inverting-amp notes** | Topology + KCL/Ohm stay **flat** `NET`/`CMP`/`PIN` today. When wrapped: passives → **`CST`**, amp → **`FN`**, under `CAP` (§3.7) — app notes do **not** rename `PIN`→`PORT` |
| **LAW** | Prefer **normative layer** / shell-adjacent; exempt from neighbourhood reserve checks (as in reserve design); pin map may keep a small `## Laws` section even on shell views |
| **Session ACL / reserve** | Unchanged order: ACL then reserve. Reserve scope = ego at requested `depth` **within** the active layer/view (same expand as `pin_map`). Holding a shell does not silently lease the entire interior until expand includes those ids |
| **Goldfish loop** | `pin_map` → reason → mutate → `pin_map`; layer/view is an argument to step 0/1, not a second dialect |
| **Grammar §3 “Layering”** | Orthogonal (I/O vs store vs transport) — do not conflate names in agent prompts |

---

## 8. Dialect sketch (shared dialect only)

Under the **complete-refactor** framing (§3.7), this sketch is the **1.x agent surface** direction — shell sugar + stratified views — not an optional add-on to 0.3.x `RES` hubs. Bare present (pin map) and mutate (`+` / `~` / `-`) use the same shapes.

```text
## Laws
LAW [LAW_KCL] ; code=sum_i_at_net_zero ; recycle=persistent

## Nodes
CAP [CAP_InvAmp] ; name=inverting_amp ; layer=board ; ports=PORT_Vin:Vin:in,PORT_Vout:Vout:out
CLM [CLM_gain] ; layer=board ; gain_v=-10 ; recycle=persistent

## Edges
Ec [CAP_InvAmp] --(summarises)--> [CLM_gain]
```

*(Shell `CLM` holds a summary number; constitutive maths live on interior `FN`/`CST` nodes — not on a self-loop `derives` EDGE. §13 #7.)*

Mutate examples:

```text
+ CAP [NEW] ; name=pdu ; layer=system ; ports=Vbus:out ; recycle=persistent
~ [CLM_gain] ; gain_v=-9.8
```

**Forbidden on agent surface:** `@TAG|pipe`, TOON/TRON, embedding full SysML text as a field blob, dumping all layers in one pin map, encoding port-of-Capsule only in id punctuation (`_`, `__`, dotted id paths), teaching expanded Port+`exposes` as the default shell dialect when sugar applies.

### 8.1 Capsule sugar (recommended agent surface)

Expanded CAP + PORT + `exposes` / `contains` lines are **store atoms** (and the interior / debug expand). They are **not** the preferred agent shell surface — they burn tokens and invite inventing Port nodes without ownership edges.

| Option | What it is | Verdict |
|--------|------------|---------|
| **A. Expanded atoms only** | Agents always write/read every `PORT` row and `exposes` / `contains` EDGE | Demoted for agents — accurate store, costly context |
| **B. Compact capsule sugar** | One (or few) `CAP` lines with `ports=` / `contains=`; engine **desugars 1:1** to A in the store | **Recommended agent surface (MVP design)** |
| **C. Third primitive** | Capsule outside NODE\|EDGE | **Rejected** |

**Write ≈ display (locked for accuracy):** shell `pin_map` **emits the same compact sugar** agents mutate. Do **not** teach sugar-on-write + expanded-on-read — that second dialect is what confuses models. Interior `view=interior` stays ordinary NODE\|EDGE (nets, pins, `FN`/`CST` law nodes, `connects` carriers). Optional later: `view=atoms` for expanded shell debug.

| Concern | Why B for agents |
|---------|------------------|
| **Token thrift** | One `CAP` line replaces N Port rows + N `exposes` edges on the shell |
| **LLM accuracy** | Ports and ownership travel together; harder to mint orphan `PORT`s or drop `exposes` |
| **Write ≈ display** | Same compact lines both ways on the shell |
| **Store fidelity** | Desugar always → `CAP` + `PORT` + `exposes` / `contains` (no third store kind) |
| **Reserve / ACL** | Sugar lists **assigned** Port / child ids so leases still target ground ids |

**Sugar fields on `CAP` only** (compile away; not schematic `ports=` bags that never expand):

| Field | Shape | Compiles to |
|-------|-------|-------------|
| `ports=` | `Id:name:side` list (comma-separated); on create, `name:side` and engine mints Port ids | `PORT` nodes + Capsule `--(exposes)-->` Port |
| `contains=` | Comma-separated child Capsule or immediate-child ids | Capsule `--(contains)-->` Child (immediate only) |

**MUST:** every sugar create/update expands 1:1 to store atoms before persist. **MUSTNOT:** store only the list with no Port nodes; invent `@TAG|pipe`; use sugar for PCBA `PIN` / SysML `POR` grains.

#### Sugar vs expanded (ASCII sketch)

```text
# Agent shell — mutate (compact)
+ CAP [NEW] ; name=inverting_amp ; layer=board ; ports=Vin:in,Vout:out ; recycle=persistent

# Agent shell — pin_map bare present (same compact shape; assigned ids)
CAP [CAP_InvAmp] ; name=inverting_amp ; layer=board ; ports=PORT_Vin:Vin:in,PORT_Vout:Vout:out ; recycle=persistent
CLM [CLM_gain] ; layer=board ; gain_v=-10 ; recycle=persistent
Ea [CAP_InvAmp] --(summarises)--> [CLM_gain]

# Store atoms after desugar (not the default shell pin_map)
CAP [CAP_InvAmp] ; name=inverting_amp ; layer=board ; recycle=persistent
PORT [PORT_Vin] ; name=Vin ; side=in ; recycle=persistent
PORT [PORT_Vout] ; name=Vout ; side=out ; recycle=persistent
E1 [CAP_InvAmp] --(exposes)--> [PORT_Vin]
E2 [CAP_InvAmp] --(exposes)--> [PORT_Vout]
```

```text
# Nest sugar (parent shell)
+ CAP [NEW] ; name=pdu ; layer=system ; ports=Vbus:out ; contains=CAP_Rail12 ; recycle=persistent

# pin_map shell (compact)
CAP [CAP_Pdu] ; name=pdu ; layer=system ; ports=PORT_Vbus:Vbus:out ; contains=CAP_Rail12 ; recycle=persistent

# Desugars to (store)
CAP [CAP_Pdu] ; …
PORT [PORT_Vbus] ; name=Vbus ; side=out ; …
E_ex [CAP_Pdu] --(exposes)--> [PORT_Vbus]
E_co [CAP_Pdu] --(contains)--> [CAP_Rail12]
```

Patch a single Port when needed: `~ [PORT_Vin] ; name=Vin_p` (ids appear inside `ports=`). Inter-capsule wiring stays expanded EDGE: `[PORT_a] --(connects)--> [PORT_b]`.

**Locked recommendation:** teach **B** as the agent shell dialect; keep **A** as store + interior + debug expand; never **C**.

---

## 9. MVP vs later

**Version note:** “MVP” here means the **first implementation drop of the 1.x dialect** (breaking vs 0.3.x agent teaching), not a soft extension of today’s `RES` surface. Prefer one target + migration notes over dual forever (§13 #3).

### MVP (design lock for first 1.x implementation drop)

| Item | MVP |
|------|-----|
| Atoms | NODE \| EDGE only |
| Capsule pattern | Documented; kinds `CAP` (Capsule) + `PORT` (Port) + `contains` / `exposes` / `summarises` / `refines` — port-hood = structure (§3.2) |
| Nested capsules | **Design-locked** (§3.5): recursive `contains` of child Capsules; pin_map one shell at a time; one open-step preference |
| `layer=` field | Optional filter + display field |
| `pin_map` | Honour `layer` and/or `view=shell\|interior` **or** document agent convention: shell = stop at `exposes` / do not auto-expand `contains` (including child capsules) |
| Caps | Existing `depth` / `max_rows`; optional engine nest-open limit (N) when implementing |
| Engine auto-summary | **No** — agents or ingest write `summarises` / shell fields |
| Capsule syntax | **B sugar on agent shell** (`ports=` / `contains=` on `CAP`); desugar to store atoms; no third primitive (§8.1) |
| Shell pin_map | Emit **compact** sugar (Write ≈ display); not full Port+`exposes` expand by default |
| SysML | Analogy + future ingest mapping only (nested parts → nested capsules) |
| Function / constraint with ports (§3.7) | **Design-locked complete refactor** — kinds `FN` + `CST`; **law on node**; EDGE = **carrier** (`connects`); engine / SCHEMA → **1.0** |

### Later

| Item | Later |
|------|-------|
| Engine-maintained summary refresh when interior mutates | Consistency job / hooks |
| Engine nest-open depth cap + breadcrumb ancestors | Enforce §3.5 limits in `pin_map` |
| SCHEMA / TagMap formalisation of `CAP` / `PORT` / `FN` / `CST` + sugar fields | With golden fixtures (1.x) |
| `FN`/`CST` + law-on-node evaluator; optional `carries=` on `connects` | Implements §3.7 |
| Schematic pin↔pin / pin→net-port migration of `connects_to` | Sunset path under Capsule wrap (§13 #4) |
| Drop transitional flat self-loop formula teaching | After migration notes + fixtures exist |
| `view=atoms` expanded shell for debug | Optional |
| `pin_map` multi-layer “breadcrumb” section (ancestors only, tiny) | Optional |
| Automatic SysML part/port ingest → capsules | PinMapIngest path |
| Cross-session layer catalogues | Out of scope until needed |

---

## 10. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| **Layer sprawl** | Small closed vocabulary for MVP (`system`, `board`, `net`, `equation`, `law`, `working`); reject free prose tokens in lint later |
| **Stale summaries** | Shell fields and `summarises` targets are **explicit**; MVP = writer refreshes; later = materialise hooks. Prefer absolute shell numbers + visible `FN`/`CST` laws over silent cache |
| **Inconsistent cross-layer ids** | Same ground-id rules as grammar §4.2.1 — locators for artefact pins; `NEW` only for MemNet-only facts; re-id/merge under reserve/ACL. Ports keep stable ids when interior nets are reminted |
| **Third-primitive drift** | Reviewers reject any AST that is not NODE\|EDGE; sugar desugars to atoms (§8.1 C rejected) |
| **Sugar / expand mismatch** | Shell pin_map and mutate both use compact form; expanded only in store / interior / `view=atoms` (§8.1) |
| **Orphan ports** | Reject stand-alone agent `+ PORT` without Capsule sugar or `exposes` ownership when shell sugar is in force |
| **Accidental whole-interior expand** | Default shell view; `contains` not followed unless `view=interior` or anchor is interior |
| **Interconn on shell** | Keep PIN-NET `connects_to` in interior only; shell shows `ports=` / Port-Port `connects` (§3.6) |
| **Deep nest blow-up** | One shell per pin_map; one open-step preference; optional engine nest-open cap (§3.5) |
| **`contains` fan-out** | Contain immediate children / child Capsules only; use Port `refines` for boundary nets — not one `contains` per leaf (§3.3) |
| **Id-as-grammar drift** | Port-hood = kind `PORT` + `exposes`; `_` in ids is KIND_rest only (§3.2) — reject `__` / dotted-id “port of CAP” conventions |
| **Name collision with SysML / `parts/`** | Use **capsule** / `CAP` in MemNet doctrine; say “SysML part (ingest)” when mapping; prefer wire `PORT` over opaque `POR` in new capsule prose |
| **Port-grain conflation** | Keep Capsule `PORT` / SysML `POR` / PCBA `PIN` distinct (§3.1); relate with `refines` / ingest edges — never overwrite locator kinds |
| **Mirror / orphan-field interior** | Teach §3.7 `FN`/`CST`+ports; reject `RES_*` stamp mirrors and orphan `Vdiff` |
| **`refines` polarity flip** | Shell tip → finer only; reject fine→coarse as `refines` (§5.2) |
| **`layer=` vs `view=` overload** | Stratum tokens on nodes; shell/interior via `view=` only — no `layer=shell` |

---

## 11. Requirement / mission fit (thin)

| Aim | How this helps |
|-----|----------------|
| MN-REQ-00 tokens / wall-clock | Compact shell sugar + descend once |
| MN-REQ-02 NODE\|EDGE | Store = atoms; sugar desugars 1:1 (§8.1) |
| MN-REQ-08 Write = display | Shell compact both ways; interior stays expanded atoms |
| MN-REQ-10 / 11 pin caps | `depth`/`max_rows` + stratum filter |
| MN-REQ-11.13 no corpus dump | Shell never embeds full interior source |

No change to `requirements.sysml` in this design task.

---

## 12. Related paths

| Path | Role |
|------|------|
| `docs/grammar/memnet-grammar-design.md` | Shared dialect SSOT; §3 = I/O/store/transport (different “layering”); points here for Capsule/Port |
| `docs/grammar/memnet-field-formulas.md` | Flat same-node `derives` MVP (**transitional**); 1.x capsule interiors → law on `FN`/`CST` nodes; EDGE = carrier (§3.7) |
| `docs/application-notes/llm-nodal-analysis-formulas.md` | Circuit interior application (flat atoms; optional capsule wrap) |
| `docs/application-notes/examples/inverting-amplifier-memnet.md` | Worked InvAmp; “Layer A/B” = circuitry vs formulas; when wrapped: `CST` passives + `FN` amp (§3.7) |
| `docs/grammar/memnet-neighbourhood-reserve.md` | Reserve = pin_map ego within active view |
| `docs/grammar/memnet-security-multi-agent.md` | ACL before reserve; shell lease ≠ interior lease |
| `docs/grammar/examples/` | Future golden fixtures for capsule/shell slices |
| SysML v2 models / ingest | Analogy and target mapping — not wire syntax |

---

## 13. Open decisions (lock before SCHEMA / engine)

Stub only — answers belong in the locked sections above once chosen. Completeness review (2026-08-06).

**How to lock:** answer each row as **“refactor to X”** (1.x target dialect), **not** “extend today’s `RES` / self-loop MVP”. Under complete-refactor framing (§3.7), prefer **one target dialect** + short migration notes; do **not** design for forever dual teaching.

| # | Decision | Tension | Lock as “refactor to …” (sketch) | Reject / demote |
|---|----------|---------|-----------------------------------|-----------------|
| **1** | **`ports=` sugar owners** | §3.7 shows sugar on `FN`/`CST`; §8.1 says sugar on **`CAP` only** | Refactor to: (a) sugar on `FN`/`CST` too (same desugar), **or** (b) sugar on `CAP` only with leaf ports as atoms | Leaving sugar rules contradictory across sections |
| **2** | **`law=` / `expr` binding to port fields** | Mini-example uses `V_inp`, `V_a` without a binding rule | Refactor to one binding rule **on the FN/CST node**: port `name=` + quantity; **or** `src_ports=` / `tgt_ports=` on the node; **or** `PORT_x.V` | Ad-hoc mirror fields on `RES`; binding via EDGE endpoints |
| **3** | **Flat vs ports-first formula MVP** | Field-formulas = same-node self-loop; §3.7 = law on FN/CST | **Refactor to one target:** law on `FN`/`CST` everywhere; flat self-loop = **transitional migration note only** | **Forever dual-MVP**; formula-on-edge as the long-term surface |
| **4** | **Locator coexistence** | `PIN`/`NET`/`CMP` “until pin↔pin migration” — no exit criteria | Refactor to: ingest grain + `refines` with **exit criteria**; **or** keep forever as locator-only (never maths hubs) | `PIN`/`NET` as long-term formula hubs |
| **5** | **Op-amp leaf shape** | Was: §3.6 `CAP_OpAmp`+`RES` vs §3.7 `FN` | **Locked:** amp = **`FN [FN_OpAmp]`** + ports + **`law=` on the node**; InvAmp = `CAP` containing `FN_OpAmp` + `CST_*`; wiring = `connects` carriers | `CAP_OpAmp`+`RES`; amp as CAP-only; gain on a `derives` EDGE |
| **6** | **`feeds` / `derives` as law carriers** | Earlier prose treated them as FN formulae | **Locked demote for 1.x laws:** behaviour on FN/CST nodes; edges ≠ laws. Keep tokens only if redefined as non-law (else drop) | Teaching `derives`/`constrains` + `expr` as the FN/CST |
| **7** | **Shell `CLM` + self-loop `derives`** | §8 once showed claim-level formula EDGE | Refactor to: `CLM` = shell **summary** only; constitutive maths only on `FN`/`CST` nodes | Shell self-loop as the primary formula teaching |
| **8** | **Behaviour on FN/CST; edges ≠ laws** | Edge-as-function vs node-as-function | **Locked:** FN/CST nodes hold the law; EDGE = **carrier** (in/out) / membership / boundary only | Formula-on-edge; multi-from EDGE with `expr`; `constrains` EDGE is the CST |
| **9** | **What `connects` carries** | Carrier ontology needs a quantity token? | Optional sketch: `carries=V` / `carries=I` (or item flow) on `connects` — lock spelling before SCHEMA | Over-inventing a full flow type system in this doc |

**Out of this redesign’s lock set (pointers only):** recycle policy; session ACL / RSV (§7 — shell lease ≠ interior); nest-open depth `N`; SCHEMA TagMap formalisation. These stay on separate tracks and do **not** justify forever dual dialect.
