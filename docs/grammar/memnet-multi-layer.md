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
| **EDGE** | A **bind** between endpoints (ports/ids). Not a relation, not law, not causality. |

**Law leaf:** one shape. Put `law=` / params (`k=`, `gain=`, …) **on the node**. `law=` is **LaTeX** (storage/display for the LLM — no evaluator required to render). Several equations → one field, `$…$` segments joined by `,` (same list joiner as `ports=`).

**Ports:** fields on the law node until separate atoms are proven necessary. Entry = `name{ attr=val, … }` (brace attr bag):

```text
ports=x{side=in, q=0},y{side=out},state{side=inout, q=$s$}
```

Attrs use the same `=` / `,` as elsewhere. `side=` is strongly usual (`in` / `out` / `inout`). Other attrs are **domain quantities at/through the port** (generic keys such as `q=`; not a fixed unit vocabulary). “Through” quantities often align with directed binds / port side; non-directed binds need not invent direction. Do **not** celebrate a kind zoo. No `FN`. Orientation lives in `law=` and port `side=` on the **NODE**.

**`PORT` as first-class NODE:** only if endpoints must be wired independently (binds need stable ids). Quantity fields on that atom use ordinary `key=value` (teach `value=` / domain keys). Until then, keep ports as fields; engine may desugar later.

**`CAP` / nesting:** deferred as metamodel. Pin-map **shell vs interior** is a **view budget** (`view=shell` or `view=interior` / re-anchor), not a chapter of kinds. Prefer compact shell first; descend one step when blocked; do not dump nested interiors in one call. Optional later sugar `CAP` + `contains=` is packaging, not ontology.

**Bind (thin)** — EDGE binds **ports of nodes** (not bare node-to-node). Slot label (default teach **`bind`**) is not a relation or law. Three wire forms only; endpoints are **qualified port refs** in brackets:

| Form | Wire | Sense |
|------|------|-------|
| Directed | `--(label)-->` | One-way bind/carrier |
| Non-directed | `--(label)--` | Undirected bind (no arrowheads) |
| Bi-directed | `<--(label)-->` | Both directions explicit (≠ non-directed) |

```text
Eid [CST_Q1.C] --(bind)--> [CST_Rc.a] ; carries=token
```

Locked endpoint shape: `[NodeId.PortName]` (`.` = ownership join inside `[…]`). Prefer this over EDGE fields `from=`/`to=` (hides grain) and over minting a first-class PORT NODE for every bind. Optional `carries=` on all three. Legacy alias: `connects` → `bind`. Rare labels (`contains`, `refines`) only when they earn their keep.

**MUSTNOT:** put the governing equation or its params on an EDGE; treat a binary EDGE as a multi-port device; orphan stamp mirrors (fields that are not graph endpoints); invent causality on a bind; confuse non-directed with bi-directed; pile port facts as `name:side:value` colon chains; bind node ids without port grain.

---

## 2. Syntax (cheat sheet)

**Spine** = shared dialect Write=display ([`memnet-grammar-design.md`](memnet-grammar-design.md) §4–5; **in engine** — directed only today). **1.x overlays** below (`ports=` / `law=` / `carries=` / three bind forms / stratified `view`/`layer`) = **proposed-1.x**, not in 0.3.x.

### Delimiters (locked)

| Char | Role |
|------|------|
| `;` | **Only** top-level field separator on a line |
| `=` | `key=value` (present / create); `+=` / `-=` only on `~`; also attrs inside `{…}` |
| `,` | **Sole** list joiner inside a field value (`ports=` entries, attrs in `{…}`, multi-eq `law=`, …) |
| `{` `}` | Attr bag on a structured token — **ports first**: `name{side=in, q=0}` |
| `.` | Ownership join inside `[…]` for EDGE endpoints: `[NodeId.PortName]` |
| `:` | Other structured joins inside a field value (`id:label`, `qty:unit`) — **not** for port piles or EDGE endpoints |
| `$…$` | LaTeX inline math **only** (not a field separator) |
| `[` `]` | Wrap Id, mint `NEW`, or qualified port ref `NodeId.PortName` |
| `--(` `)-->` | **Directed** bind |
| `--(` `)--` | **Non-directed** bind (parens + label; no spaces inside parens) |
| `<--(` `)-->` | **Bi-directed** bind (`<` / `>` live only in these arrow fragments) |
| `"` | STRING for awkward values (shared dialect) |
| `+` `~` `-` | Mutate ops (create / update / drop) — line prefix only |
| `#` | Line comment to end of line (fixtures / notes; skipped by lexer) |

No wire `|`. Query enums (`view=shell` or `interior`) are exclusive choices, not joined lists. Prefer `\lvert`/`\rvert` over bare `|` inside maths; if a value contains `;` or a list-joining `,` that is not a segment boundary, quote the whole field: `law="…"`.

### Delimiter inventory (used vs free)

Compact map of ASCII punctuation for this slim dialect. **Do not** assign free marks without a real gap.

| Status | Characters | Notes |
|--------|------------|--------|
| **Used** | `;` `,` `=` `{` `}` `[` `]` `(` `)` `.` `:` `$` `"` `#` `+` `~` `-` | Fields; port bags; ids; ownership; structured joins; LaTeX; STRING; comment; mutate |
| **Used (arrow compounds)** | `--(` `)-->` `)--` `<--(` | Bind wires; consume `<` `>` only inside these tokens |
| **Demoted / avoid** | `\|` | No wire pipe; prefer `\lvert`/`\rvert` in maths |
| **Free (held)** | `&` `*` `^` `!` `?` `` ` `` `@` `%` `'` `\` | Available if a later gap appears; **none assigned yet** |

**Collisions (do not reassign):** `$` = LaTeX `law=` / attr maths; `<` `>` = bind arrow fragments; `.` = `[Node.port]` (not path punctuation in unquoted atoms).

**Sparing recommendations (0–2):**

1. **Keep `#` as line comment only** — already matches `MemNet.g4` / layer grammar; no second meaning.
2. **No new punct for through-quantity or bind sugar** — port `{attrs}` + directed/non-directed/bi-directed wires already cover that; hold `&` `*` `^` `!` `?` `` ` ``.

### Generic skeleton

```text
CST [Id] ; name=… ; ports=name{side=…, q=…},… ; law=$eq$,$eq$ ; param=… ; recycle=persistent
Eid [Id.port] --(bind)--> [Id.port] ; carries=token
Eid [Id.port] --(bind)-- [Id.port] ; carries=token
Eid [Id.port] <--(bind)--> [Id.port] ; carries=token
```

`ports=` entries are `,`-joined `name{…}` bags on the NODE. EDGE endpoints name those ports as `[NodeId.PortName]`. `law=` holds LaTeX maths on the NODE. `carries=` is optional on all three bind forms (generic token, e.g. `signal`, `q`).

### `law=` expression rules (LaTeX)

- **Where:** one `law=` field on the **NODE** (prefer kind `CST`). Never on EDGE. **Proposed-1.x** — store/show the LaTeX string for agents; no render/eval engine required.
- **Wire:** each equation is **inline math** wrapped in `$…$`. Multi-eq: join those `$…$` segments with `,` (same joiner as `ports=`). Function and equation are the same shape — no `FN` kind; optional causality via port `side=` only.
- **Binding (same node):** math idents / macros resolve to (1) **params** (`k=`, `beta=` ← `\beta`, `R=`, …), or (2) a **port name** when the ident equals a `ports=` name. Multi-quantity at one port: domain attrs in the bag (`q=`, …) or subscripts in `law=` — port name is the subscript. Qualified `PORT_x.q` deferred.
- **MUSTNOT:** ASCII-only ad-hoc `expr=` on EDGE; `law=` on a bind; fake `derives`/`feeds` as the 1.x law surface (transitional: [`memnet-field-formulas.md`](memnet-field-formulas.md)).

### Line shapes

| Shape | Form |
|-------|------|
| NODE (pin map / bare) | `KIND [Id] ; key=value ; …` |
| EDGE directed | `Eid [Node.port] --(bind)--> [Node.port] ; key=value ; …` |
| EDGE non-directed | `Eid [Node.port] --(bind)-- [Node.port] ; key=value ; …` |
| EDGE bi-directed | `Eid [Node.port] <--(bind)--> [Node.port] ; key=value ; …` |
| Create | `+ KIND [NEW\|Id] ; …` · `+ [NEW\|Eid]? [Node.port] --(bind)-- [Node.port] ; …` · or `--(bind)-->` / `<--(bind)-->` |
| Update | `~ [Id] ; …` · `~ Eid ; …` · on `~` only: `key+=N` / `key-=N` |
| Drop | `- Eid` |

Pin map = **bare present** (no leading `+`/`~`/`-`). Ops are mutate-only. In the Create row, `\|` is documentation “or”, not a wire delimiter.

### Field forms (this doc)

| Field | Form |
|-------|------|
| `ports=` | `name{side=…, …}`, `,`-joined — e.g. `ports=x{side=in, q=0},y{side=out}` |
| `law=` | LaTeX `$…$` atom(s) on the NODE; several → one field, `$eq$` segments `,`-joined |
| `name=` | short label |
| params | domain keys **on the NODE** (`k=`, `gain=`, …) |
| `value=` | on first-class **PORT** NODE — quantity at/through that endpoint (domain terms) |
| `carries=` | optional on any bind form; generic quantity/token name (`signal`, `q`, …) |
| `recycle=` | shared-dialect visibility (`persistent`, …) |
| `view=` / `layer=` | pin-map grain (exclusive: `shell` or `interior`; coarse→fine strata) — query/envelope; not ontology |

### Port token (`ports=`)

```text
x{side=in, q=0}
```

| Part | Meaning |
|------|---------|
| `x` | Port **name** (ties to symbols in `law=`) |
| `{…}` | Attr bag: `attr=val` pairs, `,`-joined |
| `side=` | Strongly usual: `in` / `out` / `inout` |
| other attrs | Domain quantities (e.g. `q=`); number, id, or `$latex$` |

Teach **always** `name{…}` (at least `side=`). Bare `name` without `{}` is not used in the wire form (ambiguous with plain atoms). List joiner between ports stays `,`. Quote the whole `ports=` field if an attr value needs `;` or a list-joining `,` outside `$…$`.

### EDGE endpoint (`[Node.port]`)

```text
[CST_Q1.C]
```

| Part | Meaning |
|------|---------|
| `CST_Q1` | Owner **NODE** id |
| `.` | Ownership join (inside brackets only) |
| `C` | Port **name** declared on that node’s `ports=` |

Wire forms around the label unchanged. Optional `carries=`. Rejected as teachable defaults: `from=`/`to=` on the EDGE; node-to-node `[CST_Q1]--(bind)--[CST_Rc]` without port grain. First-class PORT NODE remains an escape hatch only when a port must be an independent atom — otherwise qualified refs suffice. Teachable bind label: `bind` (`connects` = legacy alias).

---

## 3. Generic sketch, then domain instance

**Lead (any domain)** — abstract CST with ports, law, and binds:

```text
CST [CST_Blk] ; name=block ; k=2 ; ports=x{side=in, q=1.0},y{side=out} ; law=$y=k x$ ; recycle=persistent
CST [CST_Next] ; name=next ; ports=x{side=in} ; law=$…$ ; recycle=persistent
E1 [CST_Blk.y] --(bind)--> [CST_Next.x] ; carries=signal
```

Mutate (mint):

```text
+ CST [NEW] ; name=block ; k=2 ; ports=x{side=in, q=1.0},y{side=out} ; law=$y=k x$ ; recycle=persistent
```

A bind does **not** own the law or its params; it only names the ports it joins.

### Application note: BJT + resistor (electronics instance)

**Instance only** — not the default frame. Kind stays **`CST`** (no `FN`). Electrical attr keys (`V`, `I`) and `beta=` are domain spellings. Mutate create (teachable assign):

```text
+ CST [CST_Q1] ; name=bjt_npn ; beta=100 ; ports=B{side=in, V=0.7, I=0.001},C{side=out},E{side=inout} ; law=$I_c=\beta I_b$,$I_e=I_b+I_c$ ; recycle=persistent
+ CST [CST_Rc] ; name=Rc ; R=1000 ; ports=a{side=inout},b{side=inout} ; law=$V_a-V_b=I_a R$ ; recycle=persistent
+ E_c [CST_Q1.C] --(bind)--> [CST_Rc.a] ; carries=I
```

Pin-map present (same facts, no leading `+`):

```text
CST [CST_Q1] ; name=bjt_npn ; beta=100 ; ports=B{side=in, V=0.7, I=0.001},C{side=out},E{side=inout} ; law=$I_c=\beta I_b$,$I_e=I_b+I_c$ ; recycle=persistent
CST [CST_Rc] ; name=Rc ; R=1000 ; ports=a{side=inout},b{side=inout} ; law=$V_a-V_b=I_a R$ ; recycle=persistent
E_ab [CST_Rc.a] --(bind)-- [CST_Rc.b] ; carries=I
E_c [CST_Q1.C] --(bind)--> [CST_Rc.a] ; carries=I
E_ea [CST_Q1.E] <--(bind)--> [CST_Rc.b] ; carries=I
```

Collector current rides the **directed** bind `[CST_Q1.C]→[CST_Rc.a]`; resistor terminals **non-directed** on `a`/`b`; E↔Rc.b **bi-directed** when both directions are explicit. Omit E → truncated device / unowned KCL.

---

## 4. Wrong shapes (three)

- **Law on EDGE** — e.g. `[A] --(derives)--> [B] ; expr=$y=k x$` (bind ≠ law; binary lie; missing ports).
- **Node-to-node bind** — e.g. `[CST_Q1] --(bind)-- [CST_Rc]` with no `.port` (missing port grain; prefer `[CST_Q1.C]`).
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
| Write = display; pin_map caps | Flat self-loop `derives` → law on node; `connects` → `bind` | Forever dual dialect; colon-pile port tokens |
| Locator kinds (domain locators) | Non-directed `--(bind)--` and bi-directed `<--(bind)-->` | Those kinds as formula hubs |

Engine: law-on-node + bind forms → **1.0**, not a silent 0.3.x patch. Flat same-node `derives` in [`memnet-field-formulas.md`](memnet-field-formulas.md) = **transitional** only.

---

## 7. Open (three bullets max)

- **`ports=` binding** — attrs in `{…}` vs params / `law=` idents; quantity keys still open.
- **When to mint first-class `PORT`** — only if a port must be an independent atom; default binds use `[Node.port]`.
- **`carries=` spelling** — optional token before SCHEMA lock; no flow type system here.

---

## 8. Related

| Path | Role |
|------|------|
| [`memnet-grammar-design.md`](memnet-grammar-design.md) | Shared dialect SSOT; §3 ≠ this doc |
| [`memnet-field-formulas.md`](memnet-field-formulas.md) | Flat `derives` (**transitional**); 1.x → law on node |
| [`../application-notes/examples/inverting-amplifier-memnet.md`](../application-notes/examples/inverting-amplifier-memnet.md) | Flat InvAmp today (electronics app note) |
| [`memnet-neighbourhood-reserve.md`](memnet-neighbourhood-reserve.md) | Reserve within active view |
| [`memnet-security-multi-agent.md`](memnet-security-multi-agent.md) | ACL before reserve |
| [`antlr/MemNetLayer.g4`](antlr/MemNetLayer.g4) | Proposed ANTLR4 for this slim dialect |

No change to `requirements.sysml` in this design task.
