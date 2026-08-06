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

## 2. Worked BJT (complete)

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

## 3. Wrong shapes (three)

- **Law on EDGE** — e.g. `[B] --(derives)--> [C] ; expr=I_c=beta*I_b` (EDGE ≠ law; binary lie; no emitter).
- **Orphan stamp mirrors** — `RES`/`VAR` with Vinp/Vdiff fields that are not graph endpoints.
- **Hollow nest with no law leaf** — a shell without a node that owns `law=` (behaviour has nowhere to live).

---

## 4. Pin map grain

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

## 5. Migration (thin)

| Keep | Migrate into 1.x | Demote |
|------|------------------|--------|
| NODE\|EDGE store | Active stamps → node + `ports=` + `law=` | Formula-on-edge; `RES`/`VAR` maths hubs |
| Write = display; pin_map caps | Flat self-loop `derives` → law on node | Forever dual dialect |
| Locator kinds (`PIN`/`NET`/`CMP`, …) | — | Those kinds as formula hubs |

Engine: law-on-node + optional port sugar → **1.0**, not a silent 0.3.x patch. Flat same-node `derives` in [`memnet-field-formulas.md`](memnet-field-formulas.md) = **transitional** only.

---

## 6. Open (three bullets max)

- **`ports=` binding** — port `name=` + quantity in `law=`, or qualified `PORT_x.V`; pick one rule on the node.
- **When to mint first-class `PORT`** — only if carrier endpoints need stable ids independent of the owner; else fields stay on the node.
- **`connects` spelling** — optional `carries=V|I` before SCHEMA lock; no flow type system here.

---

## 7. Related

| Path | Role |
|------|------|
| [`memnet-grammar-design.md`](memnet-grammar-design.md) | Shared dialect SSOT; §3 ≠ this doc |
| [`memnet-field-formulas.md`](memnet-field-formulas.md) | Flat `derives` (**transitional**); 1.x → law on node |
| [`../application-notes/examples/inverting-amplifier-memnet.md`](../application-notes/examples/inverting-amplifier-memnet.md) | Flat InvAmp today |
| [`memnet-neighbourhood-reserve.md`](memnet-neighbourhood-reserve.md) | Reserve within active view |
| [`memnet-security-multi-agent.md`](memnet-security-multi-agent.md) | ACL before reserve |

No change to `requirements.sysml` in this design task.
