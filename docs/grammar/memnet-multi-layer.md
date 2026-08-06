# Multi-layer MemNet and capsules (design)

**Status:** design only — **no engine implementation** in 0.3.5 / 0.3.6.  
**Thesis:** MemNet stays **NODE | EDGE** only; complex work zooms through **layers** and reusable **capsules** (SysML-like part-with-ports compositions built *from* those atoms — including capsule-in-capsule). Port-hood is **shared-dialect structure** (kind `PORT` + `exposes`), not id punctuation.  
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

**Bare present** (what `pin_map` shows at **shell** — Capsule + Ports + thin edges; no interior dump):

```text
## Nodes
CAP [CAP_InvAmp] ; name=inverting_amp ; layer=board ; recycle=persistent
PORT [PORT_Vin] ; name=Vin ; side=in ; recycle=persistent
PORT [PORT_Vout] ; name=Vout ; side=out ; recycle=persistent
CLM [CLM_gain] ; layer=board ; gain_v=-10 ; recycle=persistent

## Edges
E1 [CAP_InvAmp] --(exposes)--> [PORT_Vin]
E2 [CAP_InvAmp] --(exposes)--> [PORT_Vout]
Ec [CAP_InvAmp] --(summarises)--> [CLM_gain]
```

**Interior** (after descend / `view=interior` — still `depth` / `max_rows` capped). Nodal / schematic atoms stay `NET` / `CMP` / `PIN` — do not rename them to `PORT`:

```text
## Nodes
NET [NET_VIN] ; layer=board ; recycle=persistent
CMP [ATO_Rf] ; refdes=Rf ; layer=board ; path=boards/amp/amp.ato ; recycle=persistent

## Edges
E3 [CAP_InvAmp] --(contains)--> [NET_VIN]
E4 [CAP_InvAmp] --(contains)--> [ATO_Rf]
E6 [PORT_Vin] --(refines)--> [NET_VIN]
```

Prefer `contains` for **immediate** children (child Capsules, key nets/parts) — not a mandatory edge to every leaf (fan-out risk). Boundary descent uses `refines` from Ports.

**Mutate** (same shapes; ops mutate-only):

```text
+ CAP [NEW] ; name=inverting_amp ; layer=board ; recycle=persistent
+ PORT [NEW] ; name=Vin ; side=in ; recycle=persistent
+ NEW [CAP…] --(exposes)--> [PORT…]
+ NEW [CAP…] --(contains)--> [ATO_Rf]
```

Kind tokens `CAP` / `PORT` are the **design preference**; final TagMap / SCHEMA is a later lock. The pattern does not depend on minting new conceptual kinds beyond NODE|EDGE.

### 3.4 Shell vs interior = view pair

| View (`view=`) | What pin_map shows | Budget |
|----------------|--------------------|--------|
| **Shell** (default for a Capsule anchor) | Capsule node + Port nodes + `exposes` / `connects` / summary edges + sibling Capsules / LAW | Small — stays under `max_rows` |
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

Illustrative nest sketch (**parent shell only** — child Capsule as contained id; child’s own `exposes` appear when that child is the anchor):

```text
## Nodes
CAP [CAP_Pdu] ; name=pdu ; layer=system ; recycle=persistent
CAP [CAP_Rail12] ; name=rail_12v ; layer=board ; recycle=persistent
PORT [PORT_Vbus] ; name=Vbus ; side=out ; layer=system ; recycle=persistent

## Edges
Ep [CAP_Pdu] --(exposes)--> [PORT_Vbus]
Ec [CAP_Pdu] --(contains)--> [CAP_Rail12]
Ef [PORT_Vbus] --(refines)--> [CAP_Rail12] ; note=descend_hint
```

Workflow: `pin_map(CAP_Pdu, view=shell)` → reason → if needed `pin_map(CAP_Rail12, view=shell)` (then child’s Ports via `exposes`) → only then interior leaves. Goldfish: re-read the **current** shell each turn; do not keep the whole nest in context.

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
| **Formula `derives` / `feeds`** | Same-node self-loop `derives` (MVP in field-formulas) may sit on shell summary nodes (`CLM_gain`, `RES_A`) or interior stamps. Cross-node / across-port `derives` / `feeds` remains **later** (after reserve/ACL) — do not teach it as capsule MVP. Not a separate layer system — see [`memnet-field-formulas.md`](memnet-field-formulas.md) |
| **Nodal / inverting-amp notes** | Topology + KCL/Ohm stay **flat** `NET`/`CMP`/`PIN` + `derives` today. When wrapped: those atoms are **interior** of a board/stage Capsule; shell shows Capsule `PORT`s + summary gain — app notes apply formula grammar and do **not** redefine capsules or rename `PIN`→`PORT` |
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
CAP [CAP_InvAmp] ; name=inverting_amp ; layer=board
PORT [PORT_Vin] ; name=Vin ; side=in ; layer=board
CLM [CLM_gain] ; layer=board ; gain_v=-10 ; recycle=persistent

## Edges
Ea [CAP_InvAmp] --(exposes)--> [PORT_Vin]
Eb [CLM_gain] --(derives)--> [CLM_gain] ; src_fields=Rf,Rg ; expr=-Rf/Rg ; tgt_field=gain_v
Ec [CAP_InvAmp] --(summarises)--> [CLM_gain]
```

Mutate examples:

```text
+ CAP [NEW] ; name=pdu ; layer=system ; recycle=persistent
+ PORT [NEW] ; name=Vbus ; side=out ; layer=system ; recycle=persistent
+ NEW [CAP…] --(exposes)--> [PORT…]
~ [CLM_gain] ; gain_v=-9.8
```

**Forbidden on agent surface:** `@TAG|pipe`, TOON/TRON, embedding full SysML text as a field blob, dumping all layers in one pin map, encoding port-of-Capsule only in id punctuation (`_`, `__`, dotted id paths).

### 8.1 Syntax sugar vs atoms (recommendation)

| Option | What it is | Verdict |
|--------|------------|---------|
| **A. Pattern only** | Capsule = `CAP` + `PORT` + `exposes` / `contains` / … over NODE\|EDGE | **MVP lock** — teach and emit this |
| **B. Mutate sugar** | Compact create lines that **desugar** 1:1 into A (same family as optional `:=` → `derives`) | **Later, optional** — only if measured agent friction |
| **C. Third primitive** | A real Capsule AST / non-NODE\|EDGE grammar object | **Rejected** — breaks MN-REQ-02; SysML-shaped wire creep |

**Why A stays easiest for MemNet’s mission**

| Concern | Why pure NODE\|EDGE wins |
|---------|--------------------------|
| **Write = display** | Pin map already shows shell as ordinary NODE/EDGE lines; sugar that is not re-shown forces a second dialect |
| **Token budget** | Shell view is already the compression; inventing a denser *syntax* does not shrink ego expand — `view=` / `max_rows` do |
| **LLM clarity** | One shape to copy; no “is this sugar or store truth?” fork |
| **Parser / harness** | No new productions in `MemNet.g4` for MVP; soft lint stays kind/`rel` allowlists |
| **SysML analogy** | Ingest maps part/port → atoms; agents never author SysML text or a parallel capsule language |
| **Reserve / ACL** | Leases attach to ground ids; a collapsed sugar blob has no natural lease endpoints until expanded |

**When B would help:** bulk *create* of a shell (many ports) in one mutate turn — same niche as `:=` compile-to-EDGE. **MUST:** sugar is mutate-only; pin map and subsequent `~` / `-` use **expanded** CAP/PORT/`exposes`/`contains` only. **MUSTNOT:** leave `ports=…` / embedded id lists as standing present fields (same lint class as schematic `ports=` / `07_bad_embedded_relation`).

Illustrative sugar → expand (ASCII shared dialect; not implemented; **not** `@TAG|pipe`):

```text
# Sugar (mutate compile — later optional)
+ CAP [NEW] ; name=inverting_amp ; layer=board ; with_ports=Vin:in,Vout:out ; recycle=persistent

# Must desugar to (what pin_map shows — Write = display)
+ CAP [CAP_InvAmp] ; name=inverting_amp ; layer=board ; recycle=persistent
+ PORT [PORT_Vin] ; name=Vin ; side=in ; recycle=persistent
+ PORT [PORT_Vout] ; name=Vout ; side=out ; recycle=persistent
+ NEW [CAP_InvAmp] --(exposes)--> [PORT_Vin]
+ NEW [CAP_InvAmp] --(exposes)--> [PORT_Vout]
```

```text
# Optional second sugar: membership list → N contains edges
+ CAP [CAP_InvAmp] ; with_contains=ATO_Rf,NET_VIN

# Desugars to
+ NEW [CAP_InvAmp] --(contains)--> [ATO_Rf]
+ NEW [CAP_InvAmp] --(contains)--> [NET_VIN]
```

**Locked recommendation:** ship and teach **A**. Defer **B** until SCHEMA lock + golden fixtures prove agents need compact create; if added, mirror formula-sugar policy (compile on write, absolute expanded present). Never **C**.

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
| Capsule syntax | **A only** — pattern over NODE\|EDGE; no sugar, no third primitive (§8.1) |
| SysML | Analogy + future ingest mapping only (nested parts → nested capsules) |

### Later

| Item | Later |
|------|-------|
| Engine-maintained summary refresh when interior mutates | Consistency job / hooks |
| Engine nest-open depth cap + breadcrumb ancestors | Enforce §3.5 limits in `pin_map` |
| SCHEMA / TagMap formalisation of `CAP` / `PORT` | With golden fixtures |
| Optional mutate sugar `with_ports=` / `with_contains=` → expand (§8.1 B) | Only if agent friction measured; pin map stays expanded |
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
| **Third-primitive drift** | Reviewers reject any AST that is not NODE\|EDGE; capsule is a **pattern** (§8.1 C rejected) |
| **Sugar as second dialect** | If B lands: mutate compile only; pin map never emits `with_ports=` / standing port lists (§8.1) |
| **Accidental whole-interior expand** | Default shell view; `contains` not followed unless `view=interior` or anchor is interior |
| **Deep nest blow-up** | One shell per pin_map; one open-step preference; optional engine nest-open cap (§3.5) |
| **`contains` fan-out** | Contain immediate children / child Capsules only; use Port `refines` for boundary nets — not one `contains` per leaf (§3.3) |
| **Id-as-grammar drift** | Port-hood = kind `PORT` + `exposes`; `_` in ids is KIND_rest only (§3.2) — reject `__` / dotted-id “port of CAP” conventions |
| **Name collision with SysML / `parts/`** | Use **capsule** / `CAP` in MemNet doctrine; say “SysML part (ingest)” when mapping; prefer wire `PORT` over opaque `POR` in new capsule prose |
| **Port-grain conflation** | Keep Capsule `PORT` / SysML `POR` / PCBA `PIN` distinct (§3.1); relate with `refines` / ingest edges — never overwrite locator kinds |
| **`refines` polarity flip** | Shell tip → finer only; reject fine→coarse as `refines` (§5.2) |
| **`layer=` vs `view=` overload** | Stratum tokens on nodes; shell/interior via `view=` only — no `layer=shell` |

---

## 11. Requirement / mission fit (thin)

| Aim | How this helps |
|-----|----------------|
| MN-REQ-00 tokens / wall-clock | Reason at shell; descend once |
| MN-REQ-02 NODE\|EDGE | Capsule = composition of atoms |
| MN-REQ-08 Write = display | Same lines; layer/view only change which bounded set appears |
| MN-REQ-10 / 11 pin caps | `depth`/`max_rows` + stratum filter |
| MN-REQ-11.13 no corpus dump | Shell never embeds full interior source |

No change to `requirements.sysml` in this design task.

---

## 12. Related paths

| Path | Role |
|------|------|
| `docs/grammar/memnet-grammar-design.md` | Shared dialect SSOT; §3 = I/O/store/transport (different “layering”); points here for Capsule/Port |
| `docs/grammar/memnet-field-formulas.md` | Same-node `derives` on shell/interior; cross-port later |
| `docs/application-notes/llm-nodal-analysis-formulas.md` | Circuit interior application (flat atoms; optional capsule wrap) |
| `docs/application-notes/examples/inverting-amplifier-memnet.md` | Worked InvAmp; “Layer A/B” = circuitry vs formulas, not capsule strata |
| `docs/grammar/memnet-neighbourhood-reserve.md` | Reserve = pin_map ego within active view |
| `docs/grammar/memnet-security-multi-agent.md` | ACL before reserve; shell lease ≠ interior lease |
| `docs/grammar/examples/` | Future golden fixtures for capsule/shell slices |
| SysML v2 models / ingest | Analogy and target mapping — not wire syntax |
