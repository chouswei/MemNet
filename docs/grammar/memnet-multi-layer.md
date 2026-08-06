# Multi-layer MemNet (design, slim)

**Status:** design only — **not** in 0.3.x. Target **MemNet 1.x**.  
**Mission:** agent memory graph (any domain), Write = display, bounded `pin_map`, tokens — **not** MBSE.  
**Store:** **NODE | EDGE** only. No third AST primitive.

[`memnet-grammar-design.md`](memnet-grammar-design.md) §3 *Layering* = I/O / store / transport. This doc = **stratified pin-map product graph** (right grain without budget blow-up).

---

## 1. Ontology (absolute minimum)

| Atom | Role |
|------|------|
| **NODE** | Kinded fact. Law leaf: prefer kind **`CST`** (or any NODE with `law=` + `ports=`). |
| **EDGE** | Incidence / carrier only — never the law. |

**Law leaf:** one shape. Put `law=` / params (`k=`, `gain=`, …) **on the node**. `law=` is **LaTeX** (storage/display for the LLM — no evaluator required to render). Several equations → one field, `$…$` segments joined by `,` (same list joiner as `ports=`).

**Ports:** fields on the law node until separate atoms are proven necessary:

```text
ports=in:in,out:out,state:inout
```

Do **not** celebrate a kind zoo. No `FN`. No essays of causal form on the wire — orientation lives in `law=` and optional port sides.

**`PORT` as first-class NODE:** only if endpoints must be wired independently (carrier edges need stable ids). Until then, keep ports as fields; engine may desugar later.

**`CAP` / nesting:** deferred as metamodel. Pin-map **shell vs interior** is a **view budget** (`view=shell` or `view=interior` / re-anchor), not a chapter of kinds. Prefer compact shell first; descend one step when blocked; do not dump nested interiors in one call. Optional later sugar `CAP` + `contains=` is packaging, not ontology.

**EDGE relations (thin):**

| Rel | Use |
|-----|-----|
| `connects` | Carrier between port endpoints (optional `carries=` quantity/token name) |
| `contains` | Membership (immediate children only) — when nesting exists |
| `refines` | Coarser tip → finer (boundary bridge) |

**MUSTNOT:** put the governing equation or its params on an EDGE; treat a binary EDGE as a multi-port device; orphan stamp mirrors (fields that are not graph endpoints).

---

## 2. Syntax (cheat sheet)

**Spine** = shared dialect Write=display ([`memnet-grammar-design.md`](memnet-grammar-design.md) §4–5; **in engine**). **1.x overlays** below (`ports=` / `law=` / `carries=` / stratified `view`/`layer`) = **proposed-1.x**, not in 0.3.x.

### Delimiters (locked)

| Char | Role |
|------|------|
| `;` | **Only** top-level field separator on a line |
| `=` | `key=value` (present / create); `+=` / `-=` only on `~` |
| `,` | **Sole** list joiner inside a field value (`ports=`, multi-eq `law=`, …) |
| `:` | Structured-token separator (pair/tuple join **inside** a field value) — e.g. port `name:side`, `id:label`, `qty:unit` (not a field separator) |
| `$…$` | LaTeX inline math **only** (not a field separator) |
| `[` `]` | Wrap Id or mint `NEW` |
| `--(` `)-->` | Directed EDGE; `rel` between `--(` and `)-->` |
| `"` | STRING for awkward values (shared dialect) |

No wire `|`. Query enums (`view=shell` or `interior`) are exclusive choices, not joined lists. Prefer `\lvert`/`\rvert` over bare `|` inside maths; if a value contains `;` or a list-joining `,` that is not a segment boundary, quote the whole field: `law="…"`.

### Generic skeleton

```text
CST [Id] ; name=… ; ports=name:side,… ; law=$eq$,$eq$ ; param=… ; recycle=persistent
Eid [PORT_A] --(connects)--> [PORT_B] ; carries=token
```

`ports=` uses `name:side` with side ∈ {`in`, `out`, `inout`}. `law=` holds LaTeX maths on the NODE. `carries=` is an optional quantity/token name on a carrier edge (`signal`, `q`, or domain tokens such as `V`/`I` — dialect is not electrical).

### `law=` expression rules (LaTeX)

- **Where:** one `law=` field on the **NODE** (prefer kind `CST`). Never on EDGE. **Proposed-1.x** — store/show the LaTeX string for agents; no render/eval engine required.
- **Wire:** each equation is **inline math** wrapped in `$…$`. Multi-eq: join those `$…$` segments with `,` (same joiner as `ports=`). Function and equation are the same shape — no `FN` kind; optional causality via port side only.
- **Binding (same node):** math idents / macros resolve to (1) **params** (`k=`, `beta=` ← `\beta`, `R=`, …), or (2) a **port name** when the ident equals a `ports=` name. Multi-quantity at one port: `I_c` / `I_{c}` / `V_a` — port name is the subscript. Qualified `PORT_x.q` deferred.
- **MUSTNOT:** ASCII-only ad-hoc `expr=` on EDGE; `law=` on `connects`; fake `derives`/`feeds` as the 1.x law surface (transitional: [`memnet-field-formulas.md`](memnet-field-formulas.md)).

### Line shapes

| Shape | Form |
|-------|------|
| NODE (pin map / bare) | `KIND [Id] ; key=value ; …` |
| EDGE (pin map / bare) | `Eid [from] --(rel)--> [to] ; key=value ; …` |
| Create | `+ KIND [NEW\|Id] ; …` · `+ [NEW\|Eid]? [from] --(rel)--> [to] ; …` |
| Update | `~ [Id] ; …` · `~ Eid ; …` · on `~` only: `key+=N` / `key-=N` |
| Drop | `- Eid` |

Pin map = **bare present** (no leading `+`/`~`/`-`). Ops are mutate-only. In the Create row, `\|` is documentation “or”, not a wire delimiter.

### Field forms (this doc)

| Field | Form |
|-------|------|
| `ports=` | `name:side` tokens, `,`-joined — e.g. `ports=in:in,out:out,state:inout` |
| `law=` | LaTeX `$…$` atom(s) on the NODE; several → one field, `$eq$` segments `,`-joined |
| `name=` | short label |
| params | domain keys **on the NODE** (`k=`, `gain=`, …) |
| `carries=` | optional on `connects`; quantity/token name (`signal`, `q`, `V`, `I`, …) |
| `recycle=` | shared-dialect visibility (`persistent`, …) |
| `view=` / `layer=` | pin-map grain (exclusive: `shell` or `interior`; coarse→fine strata) — query/envelope; not ontology |

### Port token (`ports=`)

```text
in:in
```

| Segment | Meaning |
|---------|---------|
| `in` | Port **name** (ties to symbols in `law=`) |
| `in` | **Side:** `in` / `out` / `inout` |

First-class PORT NODE (only when `connects` needs stable endpoints): Id like `[PORT_X_out]` — **not** a three-part wire form here. Thin EDGE rels: `connects`, `contains`, `refines`.

---

## 3. Generic sketch, then domain instance

**Lead (any domain)** — abstract CST with ports, law, and a carrier:

```text
CST [CST_Blk] ; name=block ; k=2 ; ports=x:in,y:out ; law=$y=k x$ ; recycle=persistent
E1 [PORT_Blk_y] --(connects)--> [PORT_Next_x] ; carries=signal
```

Mutate (mint):

```text
+ CST [NEW] ; name=block ; k=2 ; ports=x:in,y:out ; law=$y=k x$ ; recycle=persistent
```

Carrier `connects` does **not** own the law or its params.

### Application note: BJT (electronics instance)

One domain instance only — not the default frame. One **`CST`** owns B/C/E and both teachable laws:

```text
CST [CST_Q1] ; name=bjt_npn ; beta=100 ; ports=B:in,C:out,E:inout ; law=$I_c=\beta I_b$,$I_e=I_b+I_c$ ; recycle=persistent
CST [CST_Rc] ; name=Rc ; R=1000 ; ports=a:inout,b:inout ; law=$V_a-V_b=I_a R$ ; recycle=persistent
E_c [PORT_Q1_C] --(connects)--> [PORT_Rc_a] ; carries=I
```

Omit E → truncated device and unowned KCL. Same syntax skeleton as above; electrical `V`/`I`/`beta` are instance tokens.

---

## 4. Wrong shapes (three)

- **Law on EDGE** — e.g. `[A] --(derives)--> [B] ; expr=$y=k x$` (EDGE ≠ law; binary lie; missing ports).
- **Orphan stamp mirrors** — fields that are not graph endpoints.
- **Hollow nest with no law leaf** — a shell without a node that owns `law=` (behaviour has nowhere to live).

---

## 5. Pin map grain

Flat `depth` / `max_rows` alone fails at coarse → fine strata.

```text
pin_map(session, anchor, depth, max_rows, layer?=…, view?=shell|interior)
```

(`shell|interior` above is API documentation “or”, not a wire list.)

1. Read shell (or current layer) — few rows.  
2. Reason / mutate at that grain.  
3. If blocked → one descend (re-anchor or `view=interior`).  
4. Ascend; do not keep nested shells in context.

`layer=` = abstraction stratum (project-chosen labels). Shell vs interior = **`view=`**, not a new atom.

**Goldfish:** re-read the current pin map each turn. Chat is not SSOT.

---

## 6. Migration (thin)

| Keep | Migrate into 1.x | Demote |
|------|------------------|--------|
| NODE\|EDGE store | Active stamps → node + `ports=` + `law=` | Formula-on-edge; maths hubs on wrong kinds |
| Write = display; pin_map caps | Flat self-loop `derives` → law on node | Forever dual dialect |
| Locator kinds (domain locators) | — | Those kinds as formula hubs |

Engine: law-on-node + optional port sugar → **1.0**, not a silent 0.3.x patch. Flat same-node `derives` in [`memnet-field-formulas.md`](memnet-field-formulas.md) = **transitional** only.

---

## 7. Open (three bullets max)

- **`ports=` binding** — proposed above (param / port name / `qty_portName`); qualified `PORT_x.q` still open if fields prove insufficient.
- **When to mint first-class `PORT`** — only if carrier endpoints need stable ids independent of the owner; else fields stay on the node.
- **`connects` spelling** — optional `carries=` token before SCHEMA lock; no flow type system here.

---

## 8. Related

| Path | Role |
|------|------|
| [`memnet-grammar-design.md`](memnet-grammar-design.md) | Shared dialect SSOT; §3 ≠ this doc |
| [`memnet-field-formulas.md`](memnet-field-formulas.md) | Flat `derives` (**transitional**); 1.x → law on node |
| [`../application-notes/examples/inverting-amplifier-memnet.md`](../application-notes/examples/inverting-amplifier-memnet.md) | Flat InvAmp today (electronics app note) |
| [`memnet-neighbourhood-reserve.md`](memnet-neighbourhood-reserve.md) | Reserve within active view |
| [`memnet-security-multi-agent.md`](memnet-security-multi-agent.md) | ACL before reserve |

No change to `requirements.sysml` in this design task.
