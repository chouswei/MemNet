# Multi-layer MemNet and capsules (design)

**Status:** design only — **no engine implementation** in 0.3.5 / 0.3.6.  
**Thesis:** MemNet stays **NODE | EDGE** only; complex work zooms through **layers** and reusable **capsules** (SysML-like part-with-ports compositions built *from* those atoms — including capsule-in-capsule).  
**Aims:** MN-REQ-00 — save wall-clock and tokens while keeping factual accuracy; bounded live **pin map** each turn; Write = display.  
**Dialect:** shared dialect (ASCII; no `|` pipe on the agent surface). British English.  
**Related:** [`memnet-grammar-design.md`](memnet-grammar-design.md) (§3 store layering ≠ this doc), [`memnet-field-formulas.md`](memnet-field-formulas.md), [`memnet-neighbourhood-reserve.md`](memnet-neighbourhood-reserve.md), [`memnet-security-multi-agent.md`](memnet-security-multi-agent.md), nodal app note `docs/application-notes/llm-nodal-analysis-formulas.md`.

**Disambiguation:** §3 *Layering* in the grammar design doc is **I/O / store / transport**. This document is **stratified product graph** (abstraction strata + capsule shell/interior) so agents do not load the whole net into context.

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
| **NODE** | Kinded fact (`CMP`, `NET`, `TSK`, `LAW`, port nodes, …) |
| **EDGE** | Directed relation with English / snake `rel` and optional fields |

**MUSTNOT:** invent a third conceptual primitive (no free-standing “layer object” or “SysML part” type outside NODE|EDGE). Surface spellings remain node kinds / edge relations (MN-REQ-02.7). Capsules and layers are **patterns and projections** over the same atoms.

---

## 3. Composition pattern: capsule (part with ports)

### 3.1 Name (locked for design prose)

**Chosen name: `capsule`.**

| Candidate | Why not (or why demoted) |
|-----------|--------------------------|
| `part` | SysML v2 familiarity is useful as **analogy**, but collides with repo layout `parts/` and reads as “copy SysML into the wire” |
| `module` | Overloaded (code modules, packaging) |
| `block` | SysML v1 baggage; vague shell semantics |
| `unit` | Too generic |
| `assembly` | Good engineering sense; weaker “exterior vs interior” metaphor for zoom |
| **`capsule`** | **Preferred** — emphasises a **bounded shell** (ports + summary) vs **interior** graph; distinct from SysML `part` and MemNet folder `parts/` |

**Ports** are boundary **NODEs** (or typed pin nodes with locator fields). **Internal structure** is nested NODE|EDGE owned by / reachable under the capsule. **Connections between capsules** are EDGEs whose endpoints are **ports** (not arbitrary interior nodes), so the shell stays a stable contract.

SysML v2 **part with ports** is the **analogy and ingest target** — map part/port/connection into MemNet NODE|EDGE on ingest. **Do not** embed SysML textual syntax in the agent wire. Nested SysML parts map to **capsule-in-capsule** (§3.4); the wire still shows only NODE|EDGE.

### 3.2 Anatomy (pattern, not new AST kinds)

```text
Capsule = {
  shell_node:     NODE,              // e.g. CAP [CAP_InvAmp] ; layer=board ; …
  ports:          NODE[],            // boundary; e.g. PRT / PIN / POR kinds
  shell_edges:    EDGE[],            // owns / exposes / connects_at_shell
  interior:       NODE[] + EDGE[],   // refined graph — may include child capsules
  cross_links:    EDGE[],            // summarises | refines | exposes (shell <-> interior)
}
```

Illustrative shared-dialect sketch (ASCII; Write = display shapes):

```text
## Nodes
CAP [CAP_InvAmp] ; name=inverting_amp ; layer=board ; role=capsule ; recycle=persistent
POR [POR_Vin] ; name=Vin ; side=in ; recycle=persistent
POR [POR_Vout] ; name=Vout ; side=out ; recycle=persistent
NET [NET_n1] ; layer=interior ; recycle=persistent
CMP [ATO_Rf] ; refdes=Rf ; layer=interior ; path=boards/amp/amp.ato ; recycle=persistent

## Edges
E1 [CAP_InvAmp] --(exposes)--> [POR_Vin] ; layer=shell
E2 [CAP_InvAmp] --(exposes)--> [POR_Vout] ; layer=shell
E3 [CAP_InvAmp] --(contains)--> [NET_n1] ; layer=interior
E4 [CAP_InvAmp] --(contains)--> [ATO_Rf] ; layer=interior
E5 [CAP_InvAmp] --(summarises)--> [NET_n1] ; note=virtual_ground_approx
E6 [POR_Vin] --(refines)--> [NET_n_in] ;   # descend: port -> interior net
```

**Kind tokens** (`CAP`, `POR`, …) are illustrative for design — final TagMap / SCHEMA is a later lock; the pattern does not depend on exact spellings.

### 3.3 Shell vs interior = layer pair

| View | What pin_map shows | Budget |
|------|--------------------|--------|
| **Shell** (default for a capsule anchor) | Capsule node + ports + summary fields + edges to sibling capsules / LAW | Small — stays under `max_rows` |
| **Interior** (descend) | Contained NODE|EDGE ego from an interior anchor or `view=interior` | Still capped by `depth` / `max_rows` |

**Descend = open the capsule** — change anchor to a port / interior node, or pass an explicit view; do **not** paste the whole interior into the shell pin map.

### 3.4 Nested capsules (capsule-in-capsule)

**Yes — recursive composition is allowed.** A capsule’s interior may contain child capsules (and leaf atoms). Analogy: SysML v2 **nested parts** — each child is again a part-with-ports; MemNet expresses the same idea as NODE|EDGE with `contains` / `exposes` / `refines` / `summarises`, not a new primitive.

```text
CAP_System
  exposes → POR_…          # system shell ports
  contains → CAP_Board     # child capsule (shell visible when parent opens interior)
               exposes → POR_…
               contains → CAP_Stage / NET / CMP …
```

| Rule | Detail |
|------|--------|
| **Composition** | Parent `--(contains)-->` child capsule shell; child keeps its own ports via `exposes`; parent–child or sibling wiring still lands on **ports**, not arbitrary grandchild interiors |
| **Descend** | Parent port or child shell `--(refines)-->` / is reached via `contains` — same thin cross-links as §5.1 |
| **pin_map** | **One shell at a time.** Default view for a capsule anchor = that capsule’s shell only. Opening the parent does **not** auto-expand grandchild interiors. Re-anchor (or `view=interior` one step) to open the next capsule |
| **Depth limits** | Hard budget remains `depth` / `max_rows` **within** the active shell/interior view. Design default: **one capsule-open step per turn** when possible; engine MVP may also cap nesting depth (e.g. refuse expand past N nested opens in one call) — exact N is an implementation lock |
| **MUSTNOT** | Dump nested interiors in one pin map; treat nesting as prose in `note=`; invent a “nested capsule” AST kind outside NODE\|EDGE |

Illustrative nest sketch:

```text
## Nodes
CAP [CAP_Pdu] ; name=pdu ; layer=system ; role=capsule ; recycle=persistent
CAP [CAP_Rail12] ; name=rail_12v ; layer=board ; role=capsule ; recycle=persistent
POR [POR_Vbus] ; name=Vbus ; side=out ; layer=system ; recycle=persistent
POR [POR_RailOut] ; name=Vout ; side=out ; layer=board ; recycle=persistent

## Edges
Ep [CAP_Pdu] --(exposes)--> [POR_Vbus] ; layer=shell
Ec [CAP_Pdu] --(contains)--> [CAP_Rail12] ; layer=interior
Er [CAP_Rail12] --(exposes)--> [POR_RailOut] ; layer=shell
Ef [POR_Vbus] --(refines)--> [POR_RailOut] ; note=descend_hint
```

Workflow: `pin_map(CAP_Pdu, view=shell)` → reason → if needed `pin_map(CAP_Rail12, view=shell)` → only then interior leaves. Goldfish: re-read the **current** shell each turn; do not keep the whole nest in context.

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
| **Down** | Follow `refines` / `exposes` → port → interior **or** child capsule shell; **one step** per turn when possible |
| **Nested open** | Parent shell → child shell → grandchild …; never flatten the whole nest in one call (§3.4) |
| **Caps unchanged** | Existing `depth` / `max_rows` still apply **inside** the chosen stratum |
| **No whole-graph dump** | Multi-layer / multi-capsule expand in one call is **out of MVP** |

Cross-layer links on the pin map are **thin**: endpoints + `rel` + short fields — enough to choose the next anchor, not enough to substitute for a descend.

### 5.2 EDGE kinds (design defaults)

| `rel` | Direction (convention) | Meaning |
|-------|------------------------|---------|
| `contains` | capsule → interior node | Ownership / membership |
| `exposes` | capsule → port | Shell contract |
| `summarises` | coarse → fine (or capsule → key interior) | Aggregate fact / stub |
| `refines` | fine → coarse **or** port → interior detail | Descend hint (pick one polarity in impl and stick to it) |
| `connects` | port → port | Inter-capsule wiring at the shell |

**Locked preference for `refines` polarity (design):** fine/detail node `--(refines)-->` coarse/summary **or** interior `--(refines)-->` shell port’s abstract claim — document in engine notes when implementing; agents copy what pin map shows.

**MUSTNOT:** encode hierarchy only as prose in `note=`; use EDGE + `layer=`.

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
| **Formula `derives` / `feeds`** | Live **inside** a capsule interior, on the shell (summary gains), or **across** ports when endpoints are port/boundary nodes — see [`memnet-field-formulas.md`](memnet-field-formulas.md). Not a separate layer system |
| **Nodal circuit note** | Topology + KCL/Ohm stamps are typically **interior** of a board/circuit capsule; shell shows ports (Vin, Vout, rails) + summary gain/bias — app note applies formula grammar, does not redefine layers |
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
CAP [CAP_InvAmp] ; name=inverting_amp ; layer=board ; role=capsule
POR [POR_Vin] ; name=Vin ; layer=board
CLM [CLM_gain] ; layer=board ; gain_v=-10 ; recycle=persistent

## Edges
Ea [CAP_InvAmp] --(exposes)--> [POR_Vin]
Eb [CLM_gain] --(derives)--> [CLM_gain] ; src_fields=Rf,Rg ; expr=-Rf/Rg ; tgt_field=gain_v
Ec [CAP_InvAmp] --(summarises)--> [CLM_gain]
```

Mutate examples:

```text
+ CAP [NEW] ; name=pdu ; layer=system ; role=capsule ; recycle=persistent
+ POR [NEW] ; name=Vbus ; side=out ; layer=system ; recycle=persistent
+ NEW [CAP…] --(exposes)--> [POR…]
~ [CLM_gain] ; gain_v=-9.8
```

**Forbidden on agent surface:** `@TAG|pipe`, TOON/TRON, embedding full SysML text as a field blob, dumping all layers in one pin map.

---

## 9. MVP vs later

### MVP (design lock for first implementation drop)

| Item | MVP |
|------|-----|
| Atoms | NODE \| EDGE only |
| Capsule pattern | Documented; kinds may start as `CAP` + port nodes + `contains` / `exposes` / `summarises` / `refines` |
| Nested capsules | **Design-locked** (§3.4): recursive `contains` of child capsules; pin_map one shell at a time; one open-step preference |
| `layer=` field | Optional filter + display field |
| `pin_map` | Honour `layer` and/or `view=shell\|interior` **or** document agent convention: shell = stop at `exposes` / do not auto-expand `contains` (including child capsules) |
| Caps | Existing `depth` / `max_rows`; optional engine nest-open limit (N) when implementing |
| Engine auto-summary | **No** — agents or ingest write `summarises` / shell fields |
| SysML | Analogy + future ingest mapping only (nested parts → nested capsules) |

### Later

| Item | Later |
|------|-------|
| Engine-maintained summary refresh when interior mutates | Consistency job / hooks |
| Engine nest-open depth cap + breadcrumb ancestors | Enforce §3.4 limits in `pin_map` |
| SCHEMA / TagMap formalisation of `CAP` / `POR` | With golden fixtures |
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
| **Third-primitive drift** | Reviewers reject any AST that is not NODE\|EDGE; capsule is a **pattern** |
| **Accidental whole-interior expand** | Default shell view; `contains` not followed unless `view=interior` or anchor is interior |
| **Deep nest blow-up** | One shell per pin_map; one open-step preference; optional engine nest-open cap (§3.4) |
| **Name collision with SysML / `parts/`** | Use **capsule** in MemNet doctrine; say “SysML part (ingest)” when mapping |

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
| `docs/grammar/memnet-grammar-design.md` | Shared dialect SSOT; §3 = I/O/store/transport (different “layering”) |
| `docs/grammar/memnet-field-formulas.md` | `derives` / `feeds` inside or across capsules |
| `docs/application-notes/llm-nodal-analysis-formulas.md` | Circuit interior application |
| `docs/grammar/memnet-neighbourhood-reserve.md` | Reserve = pin_map ego within active view |
| `docs/grammar/memnet-security-multi-agent.md` | ACL before reserve |
| `docs/grammar/examples/` | Future golden fixtures for capsule/shell slices |
| SysML v2 models / ingest | Analogy and target mapping — not wire syntax |
