# Multi-layer MemNet and capsules (design)

**Status:** design only — **no engine implementation** in 0.3.5 / 0.3.6.  
**Thesis:** MemNet stays **NODE | EDGE** only in the store; agents use **compact capsule sugar** on the shell (`ports=` / `contains=` on `CAP`) that desugars 1:1 to those atoms. Complex work zooms through **layers** and reusable **capsules** (SysML-like part-with-ports — including capsule-in-capsule). Port-hood is structure (store: kind `PORT` + `exposes`), not id punctuation.  
**Direction (locked for design prose):** **ports-first interconnect** — every connection / formula EDGE lands on **ports** (or schematic **pins**), never on opaque free fields or agent-mirrored stamp bags. See §3.7.  
**Aims:** MN-REQ-00 — save wall-clock and tokens while keeping factual accuracy; bounded live **pin map** each turn; Write = display.  
**Dialect:** shared dialect (ASCII; no `|` pipe on the agent surface). British English.  
**Related:** [`memnet-grammar-design.md`](memnet-grammar-design.md) (§3 store layering ≠ this doc), [`memnet-field-formulas.md`](memnet-field-formulas.md), [`memnet-neighbourhood-reserve.md`](memnet-neighbourhood-reserve.md), [`memnet-security-multi-agent.md`](memnet-security-multi-agent.md), nodal / InvAmp app notes under `docs/application-notes/` (flat interior; optional Capsule wrap).

**Disambiguation:** §3 *Layering* in the grammar design doc is **I/O / store / transport**. This document is **stratified product graph** (abstraction strata + capsule shell/interior) so agents do not load the whole net into context. App-note phrases such as “Layer A / Layer B” in the inverting-amplifier example mean **circuitry vs formula relations**, not capsule strata and not grammar §3.

---

## 1. Problem

A single flat ego expand (`depth` / `max_rows`) cannot scale to system → board → net → equation (or LAW → working pins → stamp detail) without either:

- blowing the pin-map budget, or
- forcing the agent to reason without the right level of abstraction.

Agents need to **reason at layer L**, then **descend only when needed** — finite-a first, then refine — not dump every stratum at once.

---

## 2. Foundation (unchanged)

| Atom | Role |
|------|------|
| **NODE** | Kinded fact (`CMP`, `NET`, `TSK`, `LAW`, Capsule `CAP`, Port `PORT`, …) |
| **EDGE** | Directed relation with English / snake `rel` and optional fields |

**MUSTNOT:** invent a third conceptual primitive (no free-standing “layer object” or “SysML part” type outside NODE|EDGE). Surface spellings remain node kinds / edge relations (MN-REQ-02.7). Capsules and layers are **patterns and projections** over the same atoms.

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
CapsuleNode  = CAP  [Id] ; name=Atom ; layer=Atom ; role=capsule? ; fields*
PortNode     = PORT [Id] ; name=Atom ; side=in|out|inout? ; layer=Atom? ; fields*
ExposeEdge   = [CapsuleId] --(exposes)--> [PortId]   ; fields*
ContainEdge  = [CapsuleId] --(contains)--> [ChildId] ; fields*
ConnectEdge  = [PortId]    --(connects)--> [PortId]  ; fields*          // shell wiring (not connects_to)
RefineEdge   = [PortId]    --(refines)--> [InteriorId] ; fields*      // locked: shell tip -> finer grain
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

Prefer `contains` for **immediate** children (child Capsules, key nets/parts) — not a mandatory edge to every leaf (fan-out risk). Boundary descent uses `refines` from Ports. Interior **interconnection** (PIN↔NET, optional formula edges) is ordinary schematic dialect inside the open Capsule — §3.6.

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
| 2a. Descend (preferred) | `pin_map(anchor=CAP_InvAmp, view=interior)` | Contained ego: children, Port `refines`, PIN–NET wiring, optional `derives` — still `depth` / `max_rows` capped |
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

Interior interconnect after `view=interior` (ASCII shared dialect; bare present). Membership, boundary `refines`, schematic wiring, and one formula edge:

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

# formula (same interior view; circuitry vs formula is not capsule shell/interior)
Ef1 [RES_A] --(derives)--> [RES_A] ; tgt_field=A_s ; src_fields=Rf,Rin ; expr=-(Rf/Rin)
```

Topology this encodes: `Vin -- Rin -- VMINUS -- Rf -- Vout` with feedback at `VMINUS`. An op-amp child Capsule (if present) would appear as `CAP_InvAmp --(contains)--> CAP_OpAmp` plus Port–Port `connects` **on the child shell** when that child is the anchor — not as renamed schematic pins inside the parent dump.

#### Interior of CAP_OpAmp (child Capsule)

**Question:** how do you express the interconnect **inside the op-amp** — not the InvAmp board with Rin/Rf?

**Answer:** same grammar, different anchor. Re-anchor on `CAP_OpAmp` (or `pin_map(anchor=CAP_OpAmp, view=interior)`). Still only `view=shell|interior` — **no** new view name. The board’s InvAmp interior (§3.6 above) stays parent; the op-amp’s differential / gain / output atoms live under the child Capsule.

**Shell** of the op-amp Capsule (contract only — three ports + open-loop summary):

```text
## Nodes
CAP [CAP_OpAmp] ; name=opamp ; layer=net ; ports=PORT_Inm:Inm:in,PORT_Inp:Inp:in,PORT_Out:Out:out ; a_s=1000000 ; recycle=persistent
CLM [CLM_a_s] ; type=assumption ; code=Vout_eq_a_s_times_Vdiff ; domain=s ; recycle=persistent

## Edges
Es_oa [CAP_OpAmp] --(summarises)--> [CLM_a_s]
```

Mutate sugar (create shell; engine desugars `ports=`):

```text
+ CAP [NEW] ; name=opamp ; layer=net ; ports=Inm:in,Inp:in,Out:out ; recycle=persistent
~ [CAP_InvAmp] ; contains=CAP_OpAmp
```

Parent–child shell wiring lands on Ports (not grandchild interiors): e.g. when InvAmp interior is open, board nets that feed the amp use `refines` into `PORT_Inm` / `PORT_Inp` / `PORT_Out`, or Port→Port `connects` once both Port ids are assigned. Do **not** paste those edges into the InvAmp **shell** dump.

**Interior interconnect (transitional — today’s pain):** Port → Net → Var → `RES_a` mirrors → same-node `derives` is what agents currently invent. It only works if mirrors stay in sync; it invites **orphan** `Vdiff`/`Vout` and informal field copies. **Do not teach it as the target dialect.** Prefer **ports-first** (§3.7). Kept below only as the transitional sketch that §3.7 replaces.

```text
## Nodes
NET [NET_INM] ; net=INM ; layer=net ; recycle=persistent
NET [NET_INP] ; net=INP ; layer=net ; recycle=persistent
NET [NET_OUT] ; net=OUT ; layer=net ; recycle=persistent
VAR [VAR_INM] ; symbol=V_INM ; unit=V ; domain=s ; V=0.0 ; recycle=persistent
VAR [VAR_INP] ; symbol=V_INP ; unit=V ; domain=s ; V=0.0 ; recycle=persistent
VAR [VAR_OUT] ; symbol=V_OUT ; unit=V ; domain=s ; V=0.0 ; recycle=persistent
RES [RES_a] ; a_s=1000000 ; Vinp=0.0 ; Vinm=0.0 ; Vdiff=0.0 ; Vout=0.0 ; domain=s ; recycle=persistent

## Edges
Ec_oa1 [CAP_OpAmp] --(contains)--> [NET_INM]
Ec_oa2 [CAP_OpAmp] --(contains)--> [NET_INP]
Ec_oa3 [CAP_OpAmp] --(contains)--> [NET_OUT]
Ec_oa4 [CAP_OpAmp] --(contains)--> [RES_a]
Er_inm [PORT_Inm] --(refines)--> [NET_INM]
Er_inp [PORT_Inp] --(refines)--> [NET_INP]
Er_out [PORT_Out] --(refines)--> [NET_OUT]
Ev1 [VAR_INM] --(voltage_of)--> [NET_INM]
Ev2 [VAR_INP] --(voltage_of)--> [NET_INP]
Ev3 [VAR_OUT] --(voltage_of)--> [NET_OUT]
Ef_diff [RES_a] --(derives)--> [RES_a] ; tgt_field=Vdiff ; src_fields=Vinp,Vinm ; expr=Vinp-Vinm
Ef_gain [RES_a] --(derives)--> [RES_a] ; tgt_field=Vout ; src_fields=a_s,Vdiff ; expr=a_s*Vdiff
```

**Pain:** `Vinp`/`Vinm` are agent-mirrored fields, not graph endpoints; `Vdiff` lives on a stamp bag that is not a port. That is the failure mode §3.7 removes.

**Descend path:** `pin_map(CAP_InvAmp, view=shell)` → interior → `pin_map(CAP_OpAmp, view=shell)` → `pin_map(CAP_OpAmp, view=interior)`. One Capsule-open step per turn when possible.

**MUSTNOT:** invent `view=opamp` / `view=interconn`; dump op-amp interior into the InvAmp shell; put Rin/Rf inside `CAP_OpAmp`; rename Capsule Ports to schematic `PIN_*`; teach the transitional mirror chain as the long-term interior dialect.

### 3.7 Direction: ports-first interconnect

**Core rule:** every interconnect EDGE is **port→port** (capsule grain) or **pin→pin** / **pin→net-port** (schematic grain); formula sources and targets are **fields on those ports**, never free-floating scalars or agent-mirrored stamp bags.

This is the SysML v2 analogy done properly in shared dialect: a part **exposes** ports; connections and behavioural bindings join **ports**, not opaque interiors.

#### What exposes ports

| Kind | Exposes? | Role |
|------|----------|------|
| **`CAP`** | Yes (shell contract) | Capsule — preferred composition shell; sugar `ports=` stays |
| **`PORT`** | No (it *is* the endpoint) | First-class boundary / interior tip; fields such as `V=` live **on** the port |
| **`PIN`** | Is the schematic endpoint | PCBA / `.ato` terminal — keep locator kind; treat as the pin-grain peer of `PORT` |
| **`NET`** | Optional later (net-as-bus with named tips) | Topology carrier; not a formula stamp bag |
| **`RES` / `CLM`** | Demoted as interconnect hubs | May hold **owner params** (`a_s=`) referenced *via* a port EDGE; MUSTNOT be the only home of `Vdiff` / mirrored `Vinp` |
| SysML `PRT` / `POR` | Ingest pins | Map to `CAP`/`PORT` on capsule wrap; do not overwrite locator kinds |

**Also allowed:** interior-only ports (`side=internal`) owned by `contains` — e.g. `PORT_Vdiff` — so intermediate results are still ports, not orphan fields.

#### EDGE endpoint rule

| Rel | Endpoints (ports-first) | Notes |
|-----|-------------------------|-------|
| `connects` | Port → Port | Shell / inter-capsule wiring (unchanged) |
| `derives` / `feeds` | Port → Port (preferred) | `tgt_field` / `src_fields` bind to **port** fields; multi-source via `src_ports=` list on the EDGE payload |
| `exposes` | Capsule → Port | Unchanged |
| `contains` | Capsule → child / interior port | Immediate children only |
| `refines` | Port → finer Port / PIN / NET | Boundary bridge when schematic grain still present |
| `connects_to` | PIN → NET | **Migrates** toward pin↔pin or pin→net-port when schematic capsules land; keep until then |

**MUSTNOT:** same-node `RES --(derives)--> RES` whose `src_fields` are informal mirrors of other nodes; Port→Net→Var→mirror as the taught path; invent `FLD_*` field-ports (rejected in field-formulas) — use real `PORT` / `PIN` instead.

#### CAP_OpAmp under ports-first (worked mini-example)

Shell (sugar; `a_s` on the Capsule, not a stamp bag):

```text
CAP [CAP_OpAmp] ; name=opamp ; layer=net ; ports=PORT_Inm:Inm:in,PORT_Inp:Inp:in,PORT_Out:Out:out ; a_s=1000000 ; recycle=persistent
CLM [CLM_a_s] ; type=assumption ; code=Vout_eq_a_s_times_Vdiff ; domain=s ; recycle=persistent
Es [CAP_OpAmp] --(summarises)--> [CLM_a_s]
```

Interior after `view=interior` — **no** `NET`/`VAR`/`RES_a` mirror chain:

```text
## Nodes
PORT [PORT_Inm] ; name=Inm ; side=in ; V=0.0 ; recycle=persistent
PORT [PORT_Inp] ; name=Inp ; side=in ; V=0.0 ; recycle=persistent
PORT [PORT_Out] ; name=Out ; side=out ; V=0.0 ; recycle=persistent
PORT [PORT_Vdiff] ; name=Vdiff ; side=internal ; V=0.0 ; recycle=persistent

## Edges
E_ex1 [CAP_OpAmp] --(exposes)--> [PORT_Inm]
E_ex2 [CAP_OpAmp] --(exposes)--> [PORT_Inp]
E_ex3 [CAP_OpAmp] --(exposes)--> [PORT_Out]
E_ci  [CAP_OpAmp] --(contains)--> [PORT_Vdiff]
# differential: Inp.V - Inm.V → Vdiff.V  (endpoints = ports)
E_diff [PORT_Inp] --(derives)--> [PORT_Vdiff] ; tgt_field=V ; src_ports=PORT_Inp,PORT_Inm ; src_fields=V,V ; expr=V_inp-V_inm
# gain: a_s * Vdiff.V → Out.V  (a_s on owning CAP, referenced from the EDGE)
E_gain [PORT_Vdiff] --(derives)--> [PORT_Out] ; tgt_field=V ; src_ports=PORT_Vdiff ; src_fields=V ; owner=CAP_OpAmp ; owner_fields=a_s ; expr=a_s*V
```

Readable chain: **Inm / Inp → Vdiff → Out**, all ports; gain param stays on the Capsule. Parent InvAmp still wires board nets to `PORT_Inm` / `PORT_Inp` / `PORT_Out` via `connects` / `refines` — not into a stamp bag.

#### Compatibility / migration

| Stays | Migrates | Demoted / later |
|-------|----------|-----------------|
| `CAP` sugar `ports=` / `contains=` ; desugar to `PORT` + `exposes` | Interior formula from `RES` self-loop → **port→port** `derives` | Agent-mirrored `Vinp`/`Vinm` on `RES_*` |
| Shell Port→Port `connects` | Optional: schematic `connects_to` PIN→NET → pin↔pin or pin→net-port under a Capsule | Port→Net→Var→mirror as taught path |
| `contains` / `exposes` / `summarises` | `refines` kept as **boundary bridge** when a schematic NET/PIN grain still exists under the Capsule | Orphan scalars (`Vdiff` with no owning EDGE) |
| Flat InvAmp without Capsule wrap | When wrapped, board interior may keep PIN/NET until ports-first schematic sugar exists | `voltage_of` VAR chain **inside** a behavioural Capsule (prefer `V=` on the port) |
| Field-formulas same-node MVP for **flat** domains (cashflow, …) | Capsule / multi-port interiors adopt `src_ports=` + port endpoints (elevates cross-port earlier than field-formulas §6 “later”) | `FLD_*` field-port nodes — still rejected; use `PORT`/`PIN` |

**Engine:** design direction only — **not** implemented in 0.3.5 / 0.3.6 (no port→port formula evaluator, no `src_ports=` lock in SCHEMA yet).

#### Rel cheat-sheet (shell vs interior)

| Rel | Where | Endpoints |
|-----|--------|-----------|
| `exposes` / sugar `ports=` | Shell (store / sugar) | Capsule → Port |
| `connects` | Shell (inter-capsule) | Port → Port |
| `contains` | Interior open | Capsule → child Capsule / key NET / CMP / RES / interior Port |
| `refines` | Boundary | Port → NET / PIN / child Port |
| `connects_to` | Interior interconnect (transitional) | PIN → NET — migrate toward pin grain under §3.7 |
| `derives` / `feeds` | Interior (ports-first) | **Port → Port**; flat same-node MVP still in field-formulas |

Flat InvAmp without Capsule wrap remains valid — see [`inverting-amplifier-memnet.md`](../application-notes/examples/inverting-amplifier-memnet.md). When wrapped, that file’s Layer A/B atoms are the **board interior**; behavioural Capsules follow §3.7.

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
| **Formula `derives` / `feeds`** | Flat domains: same-node self-loop MVP (field-formulas). **Capsule interiors:** prefer **port→port** `derives` with `src_ports=` (§3.7) — design direction ahead of engine. Not a separate layer system — see [`memnet-field-formulas.md`](memnet-field-formulas.md) |
| **Nodal / inverting-amp notes** | Topology + KCL/Ohm stay **flat** `NET`/`CMP`/`PIN` + `derives` today. When wrapped: board atoms are **interior** of a stage Capsule; behavioural children (op-amp) follow §3.7 ports-first — app notes do **not** redefine capsules or rename `PIN`→`PORT` |
| **LAW** | Prefer **normative layer** / shell-adjacent; exempt from neighbourhood reserve checks (as in reserve design); pin map may keep a small `## Laws` section even on shell views |
| **Session ACL / reserve** | Unchanged order: ACL then reserve. Reserve scope = ego at requested `depth` **within** the active layer/view (same expand as `pin_map`). Holding a shell does not silently lease the entire interior until expand includes those ids |
| **Goldfish loop** | `pin_map` → reason → mutate → `pin_map`; layer/view is an argument to step 0/1, not a second dialect |
| **Grammar §3 “Layering”** | Orthogonal (I/O vs store vs transport) — do not conflate names in agent prompts |

---

## 8. Dialect sketch (shared dialect only)

Bare present (pin map) and mutate (`+` / `~` / `-`) use the same shapes.

```text
## Laws
LAW [LAW_KCL] ; code=sum_i_at_net_zero ; recycle=persistent

## Nodes
CAP [CAP_InvAmp] ; name=inverting_amp ; layer=board ; ports=PORT_Vin:Vin:in,PORT_Vout:Vout:out
CLM [CLM_gain] ; layer=board ; gain_v=-10 ; recycle=persistent

## Edges
Eb [CLM_gain] --(derives)--> [CLM_gain] ; src_fields=Rf,Rg ; expr=-Rf/Rg ; tgt_field=gain_v
Ec [CAP_InvAmp] --(summarises)--> [CLM_gain]
```

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

**Write ≈ display (locked for accuracy):** shell `pin_map` **emits the same compact sugar** agents mutate. Do **not** teach sugar-on-write + expanded-on-read — that second dialect is what confuses models. Interior `view=interior` stays ordinary NODE\|EDGE (nets, pins, `derives`). Optional later: `view=atoms` for expanded shell debug.

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

### MVP (design lock for first implementation drop)

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
| Ports-first interior (§3.7) | **Design-locked direction** — teach in docs; engine / SCHEMA not yet |

### Later

| Item | Later |
|------|-------|
| Engine-maintained summary refresh when interior mutates | Consistency job / hooks |
| Engine nest-open depth cap + breadcrumb ancestors | Enforce §3.5 limits in `pin_map` |
| SCHEMA / TagMap formalisation of `CAP` / `PORT` + sugar fields | With golden fixtures |
| Port→port `derives` + `src_ports=` / `owner_fields=` evaluator | Implements §3.7; elevates cross-port ahead of flat field-formulas “later” |
| Schematic pin↔pin / pin→net-port migration of `connects_to` | Optional under Capsule wrap |
| `view=atoms` expanded shell for debug | Optional |
| `pin_map` multi-layer “breadcrumb” section (ancestors only, tiny) | Optional |
| Automatic SysML part/port ingest → capsules | PinMapIngest path |
| Cross-session layer catalogues | Out of scope until needed |

---

## 10. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| **Layer sprawl** | Small closed vocabulary for MVP (`system`, `board`, `net`, `equation`, `law`, `working`); reject free prose tokens in lint later |
| **Stale summaries** | Shell fields and `summarises` targets are **explicit**; MVP = writer refreshes; later = materialise hooks. Prefer absolute shell numbers + visible `derives` over silent cache |
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
| **Mirror / orphan-field interior** | Teach §3.7 ports-first; reject `RES_*` stamp mirrors and orphan `Vdiff` as the Capsule interior dialect |
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
| `docs/grammar/memnet-field-formulas.md` | Flat same-node `derives` MVP; capsule interiors → port→port (§3.7) |
| `docs/application-notes/llm-nodal-analysis-formulas.md` | Circuit interior application (flat atoms; optional capsule wrap) |
| `docs/application-notes/examples/inverting-amplifier-memnet.md` | Worked InvAmp; “Layer A/B” = circuitry vs formulas, not capsule strata; board interior §3.6; op-amp child → §3.7 ports-first |
| `docs/grammar/memnet-neighbourhood-reserve.md` | Reserve = pin_map ego within active view |
| `docs/grammar/memnet-security-multi-agent.md` | ACL before reserve; shell lease ≠ interior lease |
| `docs/grammar/examples/` | Future golden fixtures for capsule/shell slices |
| SysML v2 models / ingest | Analogy and target mapping — not wire syntax |
