# Multi-layer MemNet (design, slim)

**Status:** design only — **not** in 0.3.x. Target **MemNet 1.x**.  
**Mission:** agent memory graph, Write = display, bounded `pin_map`, tokens — **not** MBSE.  
**Store:** **NODE | EDGE** only. No third AST primitive.

[`memnet-grammar-design.md`](memnet-grammar-design.md) §3 *Layering* = I/O / store / transport. This doc = **stratified pin-map product graph** (right grain without budget blow-up).

---

## 1. Ontology (absolute minimum)

| Atom | Role |
|------|------|
| **NODE** | Kinded fact. Law leaf: prefer kind **`CST`** (or any NODE with `law=` + `ports=`). |
| **EDGE** | Incidence / carrier only — never the law. |

**Law leaf:** one shape. Put `law=` / params (`beta=`, `R=`, …) **on the node**. Several equations → one `law=` field, equations separated by `|`.

**Ports:** fields on the law node until separate atoms are proven necessary:

```text
ports=B:in,C:out,E:inout
```

Do **not** celebrate a kind zoo. No `FN`. No `form=causal` essays on the wire — orientation lives in `law=` and optional port sides.

**`PORT` as first-class NODE:** only if endpoints must be wired independently (carrier edges need stable ids). Until then, keep ports as fields; engine may desugar later.

**`CAP` / nesting:** deferred as metamodel. Pin-map **shell vs interior** is a **view budget** (`view=shell|interior` / re-anchor), not a chapter of kinds. One paragraph: prefer compact shell first; descend one step when blocked; do not dump nested interiors in one call. Optional later sugar `CAP` + `contains=` is packaging, not ontology.

**EDGE relations (thin):**

| Rel | Use |
|-----|-----|
| `connects` | Carrier between port endpoints (optional `carries=V\|I`) |
| `contains` | Membership (immediate children only) — when nesting exists |
| `refines` | Coarser tip → finer (boundary bridge) |

**MUSTNOT:** put gain / Ohm / β on an EDGE; treat binary EDGE as a multi-terminal device; orphan stamp mirrors (`RES`/`VAR` Vinp/Vdiff theatre).

---

## 2. Syntax (cheat sheet)

**Spine** = shared dialect Write=display ([`memnet-grammar-design.md`](memnet-grammar-design.md) §4–5; **in engine**). **1.x overlays** below (`ports=` / `law=` / `carries=` / stratified `view`/`layer`) = **proposed-1.x**, not in 0.3.x.

### Line shapes

| Shape | Form |
|-------|------|
| NODE (pin map / bare) | `KIND [Id] ; key=value ; …` |
| EDGE (pin map / bare) | `Eid [from] --(rel)--> [to] ; key=value ; …` |
| Create | `+ KIND [NEW\|Id] ; …` · `+ [NEW\|Eid]? [from] --(rel)--> [to] ; …` |
| Update | `~ [Id] ; …` · `~ Eid ; …` · on `~` only: `key+=N` / `key-=N` |
| Drop | `- Eid` |

Pin map = **bare present** (no leading `+`/`~`/`-`). Ops are mutate-only.

### Delimiters

| Char | Role |
|------|------|
| `;` | Join **fields** |
| `=` | `key=value` (present / create); `+=` / `-=` only on `~` |
| `[` `]` | Wrap Id or mint `NEW` |
| `--(` `)-->` | Directed EDGE; `rel` between `--(` and `)-->` |
| `,` | **1.x** list join **inside** `ports=` value |
| `:` | **1.x** port token `name:side` **inside** `ports=` (not a field separator) |
| `\|` | **1.x** join **inside** one field value (`law=` eqs; `carries=` / `view=` alts) — **not** a field separator |
| `"` | STRING for awkward paths (shared dialect) |

### Field forms (this doc)

| Field | Form |
|-------|------|
| `ports=` | `name:side` tokens, `,`-joined — e.g. `ports=B:in,C:out,E:inout` |
| `law=` | equation atom(s); several eqs → one field, joined by `\|` |
| `name=` | short label |
| `beta=` / `R=` / … | law params **on the NODE** |
| `carries=` | optional on `connects`; `V` or `I` (alt spelling `V\|I` before SCHEMA lock) |
| `recycle=` | shared-dialect visibility (`persistent`, …) |
| `view=` / `layer=` | pin-map grain (`shell\|interior`; `system`/`board`/`net`/`equation`) — query/envelope; not ontology |

### Port token (`ports=`)

```text
B:in
```

| Segment | Meaning |
|---------|---------|
| `B` | Port **name** (ties to quantities in `law=`, e.g. `I_b`) |
| `in` | **Side:** `in` \| `out` \| `inout` |

First-class PORT NODE (only when `connects` needs stable endpoints): Id like `[PORT_Q1_C]` — **not** a three-part `PORT_*:name:side` wire form here. Thin EDGE rels: `connects`, `contains`, `refines`.

---

## 3. Worked BJT (complete)

One **`CST`** node owns B/C/E and both teachable laws. Wiring is one carrier line (endpoints need ids — mint `PORT` only when `connects` requires them; otherwise keep `ports=` on the node).

```text
CST [CST_Q1] ; name=bjt_npn ; beta=100 ; ports=B:in,C:out,E:inout ; law=I_c=beta*I_b|I_e=I_b+I_c ; recycle=persistent
CST [CST_Rc] ; name=Rc ; R=1000 ; ports=a:inout,b:inout ; law=V_a-V_b=I_a*R ; recycle=persistent
E_c [PORT_Q1_C] --(connects)--> [PORT_Rc_a] ; carries=I
```

Mutate (mint):

```text
+ CST [NEW] ; name=bjt_npn ; beta=100 ; ports=B:in,C:out,E:inout ; law=I_c=beta*I_b|I_e=I_b+I_c ; recycle=persistent
```

Omit E → truncated device and unowned KCL. Carrier `connects` does **not** own β or KCL.

---

## 4. Wrong shapes (three)

- **Law on EDGE** — e.g. `[B] --(derives)--> [C] ; expr=I_c=beta*I_b` (EDGE ≠ law; binary lie; no emitter).
- **Orphan stamp mirrors** — `RES`/`VAR` with Vinp/Vdiff fields that are not graph endpoints.
- **Hollow nest with no law leaf** — a shell without a node that owns `law=` (behaviour has nowhere to live).

---

## 5. Pin map grain

Flat `depth` / `max_rows` alone fails at system → board → net → equation.

```text
pin_map(session, anchor, depth, max_rows, layer?=board, view?=shell|interior)
```

1. Read shell (or current layer) — few rows.  
2. Reason / mutate at that grain.  
3. If blocked → one descend (re-anchor or `view=interior`).  
4. Ascend; do not keep nested shells in context.

`layer=` = abstraction stratum (`system` / `board` / `net` / `equation`). Shell vs interior = **`view=`**, not a new atom.

**Goldfish:** re-read the current pin map each turn. Chat is not SSOT.

---

## 6. Migration (thin)

| Keep | Migrate into 1.x | Demote |
|------|------------------|--------|
| NODE\|EDGE store | Active stamps → node + `ports=` + `law=` | Formula-on-edge; `RES`/`VAR` maths hubs |
| Write = display; pin_map caps | Flat self-loop `derives` → law on node | Forever dual dialect |
| Locator kinds (`PIN`/`NET`/`CMP`, …) | — | Those kinds as formula hubs |

Engine: law-on-node + optional port sugar → **1.0**, not a silent 0.3.x patch. Flat same-node `derives` in [`memnet-field-formulas.md`](memnet-field-formulas.md) = **transitional** only.

---

## 7. Open (three bullets max)

- **`ports=` binding** — port `name=` + quantity in `law=`, or qualified `PORT_x.V`; pick one rule on the node.
- **When to mint first-class `PORT`** — only if carrier endpoints need stable ids independent of the owner; else fields stay on the node.
- **`connects` spelling** — optional `carries=V|I` before SCHEMA lock; no flow type system here.

---

## 8. Related

| Path | Role |
|------|------|
| [`memnet-grammar-design.md`](memnet-grammar-design.md) | Shared dialect SSOT; §3 ≠ this doc |
| [`memnet-field-formulas.md`](memnet-field-formulas.md) | Flat `derives` (**transitional**); 1.x → law on node |
| [`../application-notes/examples/inverting-amplifier-memnet.md`](../application-notes/examples/inverting-amplifier-memnet.md) | Flat InvAmp today |
| [`memnet-neighbourhood-reserve.md`](memnet-neighbourhood-reserve.md) | Reserve within active view |
| [`memnet-security-multi-agent.md`](memnet-security-multi-agent.md) | ACL before reserve |

No change to `requirements.sysml` in this design task.
