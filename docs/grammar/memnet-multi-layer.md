# Multi-layer MemNet (design, slim)

**Status:** design only — **not** in 0.3.x. Target **MemNet 1.x**.  
**Mission:** agent memory graph (any domain), Write = display, bounded `pin_map`, tokens — **not** MBSE.  
**Store:** **NODE | EDGE** only. No third AST primitive.

[`memnet-grammar-design.md`](memnet-grammar-design.md) §3 *Layering* = I/O / store / transport. This doc = **stratified pin-map product graph** (right grain without budget blow-up).

---

## 1. Ontology (absolute minimum)

| Atom | Role |
|------|------|
| **NODE** | Kinded fact. Law leaf: prefer kind **`CST`** (or any NODE with `law=` + `ports=`). Device / constitutive / causal laws live **only** here. |
| **EDGE** | An **ideal pipe / bind** between endpoints (ports/ids). Not a relation, not law, not causality — **no** `law=` on EDGE. |

**Law leaf:** one shape. Put `law=` / params (`k=`, `gain=`, …) **on the node** (`CST`). `law=` is **LaTeX** (storage/display for the LLM — no evaluator required to render). Several equations → one field, `$…$` segments joined by `,` (same list joiner as `ports=`).

**Ideal bind:** an EDGE is an ideal pipe — endpoints share the carried quantity as the domain defines (agent may rely on that continuity without EDGE `law=` text; further constraints stay on NODE laws or domain convention).

**Ports:** fields on the law node until separate atoms are proven necessary. Entry = `name(attr=val, …)` (paren attr bag):

```text
ports=x(side=in, q=0),y(side=out),state(side=inout, q=$s$)
```

Attrs use the same `=` / `,` as elsewhere. `side=` is strongly usual (`in` / `out` / `inout`). Other attrs are **domain quantities at/through the port** (generic keys such as `q=`; not a fixed unit vocabulary). “Through” quantities often align with directed binds / port side; non-directed binds need not invent direction. Do **not** celebrate a kind zoo. No `FN`. Orientation lives in `law=` and port `side=` on the **NODE**.

**`PORT` as first-class NODE:** only if endpoints must be wired independently (binds need stable ids). Quantity fields on that atom use ordinary `key=value` (teach `value=` / domain keys). Until then, keep ports as fields; engine may desugar later.

**`CAP` / nesting:** deferred as metamodel. Pin-map **shell vs interior** is a **view budget** (`view=shell` or `view=interior` / re-anchor), not a chapter of kinds. Prefer compact shell first; descend one step when blocked; do not dump nested interiors in one call. Composition without `CAP`: membership binds with `carries=member` (`view=parts` / `layer=arch` — §3 parts note). Optional later sugar `CAP` + `contains=` is packaging, not ontology.

**Bind (thin)** — EDGE is an **ideal pipe / bind** between **ports of nodes** (not bare node-to-node). Slot label (default teach **`bind`**) is not a relation or law. Three wire forms only; endpoints are **qualified port refs** in brackets:

| Form | Wire | Sense |
|------|------|-------|
| Directed | `--(label)-->` | One-way bind/carrier |
| Non-directed | `--(label)--` | Undirected bind (no arrowheads) |
| Bi-directed | `<--(label)-->` | Both directions explicit (≠ non-directed) |

```text
Eid [CST_Q1.C] --(bind)--> [CST_Rc.a] ; carries=token
```

Locked endpoint shape: `[NodeId.PortName]` (`.` = ownership join inside `[…]`). Prefer this over EDGE fields `from=`/`to=` (hides grain) and over minting a first-class PORT NODE for every bind. Optional `carries=` on all three. Legacy alias: `connects` → `bind`. Rare labels (`contains`, `refines`) only when they earn their keep.

**MUSTNOT:** put `law=` (device equations **or** wire/continuity equations) on an EDGE; treat EDGE as a function or multi-port device; orphan stamp mirrors (fields that are not graph endpoints); invent causality on a bind; confuse non-directed with bi-directed; pile port facts as `name:side:value` colon chains; bind node ids without port grain.

---

## 2. Syntax (cheat sheet)

**Spine** = shared dialect Write=display ([`memnet-grammar-design.md`](memnet-grammar-design.md) §4–5; **in engine** — directed only today). **1.x overlays** below (`ports=` / `law=` / `pseudo=` / `carries=` / three bind forms / stratified `view`/`layer`) = **proposed-1.x**, not in 0.3.x.

### Delimiters (locked)

| Char | Role |
|------|------|
| `;` | **Only** top-level field separator on a line |
| `=` | `key=value` (present / create); `+=` / `-=` only on `~`; also attrs inside `(…)` |
| `,` | **Sole** list joiner inside a field value (`ports=` entries, attrs in `(…)`, multi-eq `law=`, …) |
| `(` `)` | Port attr bag: `name(side=in, q=0)` — `IDENT(` after the port name inside `ports=` |
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

**Port vs bind parens:** port bag = `IDENT(` immediately after the port name inside `ports=`; bind wire = `--(` / `<--(` after an endpoint `]`. Same `(` `)` glyphs; context decides.

No wire `|`. Query enums (`view=shell` or `interior`) are exclusive choices, not joined lists. Prefer `\lvert`/`\rvert` over bare `|` inside maths; if a value contains `;` or a list-joining `,` that is not a segment boundary, quote the whole field: `law="…"`. Same STRING rule for **`pseudo=`** bodies (steps often need `;` / `:` / spaces) — quote the whole value: `pseudo="…"`. No new punct for algorithms.

### Delimiter inventory (used vs free)

Compact map of ASCII punctuation for this slim dialect. **Do not** assign free marks without a real gap.

| Status | Characters | Notes |
|--------|------------|--------|
| **Used** | `;` `,` `=` `[` `]` `(` `)` `.` `:` `$` `"` `#` `+` `~` `-` | Fields; port bags; ids; ownership; structured joins; LaTeX; STRING; comment; mutate |
| **Used (arrow compounds)** | `--(` `)-->` `)--` `<--(` | Bind wires; consume `<` `>` only inside these tokens |
| **Demoted / avoid** | `\|` `{` `}` | No wire pipe; prefer `\lvert`/`\rvert` in maths; `{}` demoted for ports (use `(…)`); `{}` remains only inside LaTeX `$…$` |
| **Free (held)** | `&` `*` `^` `!` `?` `` ` `` `@` `%` `'` `\` | Available if a later gap appears; **none assigned yet** |

**Collisions (do not reassign):** `$` = LaTeX `law=` / attr maths; `<` `>` = bind arrow fragments; `.` = `[Node.port]` (not path punctuation in unquoted atoms); `(` `)` = port bags **and** bind wires (context: `IDENT(` vs `--(` / `<--(`).

**Sparing recommendations (0–2):**

1. **Keep `#` as line comment only** — already matches `MemNet.g4` / layer grammar; no second meaning.
2. **No new punct for through-quantity or bind sugar** — port `(attrs)` + directed/non-directed/bi-directed wires already cover that; hold `&` `*` `^` `!` `?` `` ` ``.

### Generic skeleton

```text
CST [Id] ; name=… ; ports=name(side=…, q=…),… ; law=$eq$,$eq$ ; param=… ; recycle=persistent
Eid [Id.port] --(bind)--> [Id.port] ; carries=token
Eid [Id.port] --(bind)-- [Id.port] ; carries=token
Eid [Id.port] <--(bind)--> [Id.port] ; carries=token
```

`ports=` entries are `,`-joined `name(…)` bags on the NODE. EDGE endpoints name those ports as `[NodeId.PortName]`. `law=` holds LaTeX maths on the NODE only. EDGE is ideal bind/pipe (`carries=` optional; no `law=`).

### `law=` expression rules (LaTeX)

- **Where:** one `law=` field on the **NODE** (prefer kind `CST`). **Never** on EDGE — ideal bind implies continuity; do not teach wire equations on the arrow. **Proposed-1.x** — store/show the LaTeX string for agents; no render/eval engine required.
- **Wire:** each equation is **inline math** wrapped in `$…$`. Multi-eq: join those `$…$` segments with `,` (same joiner as `ports=`). Function and equation are the same shape — no `FN` kind; optional causality via port `side=` only.
- **Completeness:** every symbol in `law=` MUST appear as a port quantity (name / attr / subscript), a node param, or be defined in the same `law=` list — no orphan predicates or hand-wavy stubs.
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
| `ports=` | `name(side=…, …)`, `,`-joined — e.g. `ports=x(side=in, q=0),y(side=out)` |
| `law=` | LaTeX `$…$` atom(s) on the **NODE** only; several → one field, `$eq$` segments `,`-joined — **forbidden** on EDGE |
| `pseudo=` | algorithmic steps as a STRING on the **NODE** (prefer quoted); not LaTeX; not an evaluator — see §3 pseudocode note |
| `name=` | short label |
| `state=` | optional present discrete state on the NODE (e.g. relay `energised` / `deenergised`) — display + agent cue; not an EDGE evaluator |
| params | domain keys **on the NODE** (`k=`, `gain=`, `I_th=`, …) |
| `value=` | on first-class **PORT** NODE — quantity at/through that endpoint (domain terms) |
| `carries=` | optional on any bind form; generic quantity/token name (`signal`, `q`, `member`, `event`, `token`, …) |
| `event=` | optional bind metadata on a transition EDGE (statechart) — **not** `law=` |
| `guard=` | optional bind metadata (`$…$` predicate text) on a transition EDGE — **not** device `law=` |
| `recycle=` | shared-dialect visibility (`persistent`, …) |
| `view=` / `layer=` | pin-map grain (`shell`/`interior`; also `flowchart` / `parts` / `statechart`; `layer=arch` / `layer=req`; …) — query/envelope; not ontology |

### Port token (`ports=`)

```text
x(side=in, q=0)
```

| Part | Meaning |
|------|---------|
| `x` | Port **name** (ties to symbols in `law=`) |
| `(…)` | Attr bag: `attr=val` pairs, `,`-joined |
| `side=` | Strongly usual: `in` / `out` / `inout` |
| other attrs | Domain quantities (e.g. `q=`); number, id, or `$latex$` |

Teach **always** `name(…)` (at least `side=`). Bare `name` without `()` is not used in the wire form (ambiguous with plain atoms). List joiner between ports stays `,`. Quote the whole `ports=` field if an attr value needs `;` or a list-joining `,` outside `$…$`.

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
CST [CST_Blk] ; name=block ; k=2 ; ports=x(side=in, q=1.0),y(side=out) ; law=$y=k x$ ; recycle=persistent
CST [CST_Next] ; name=next ; ports=x(side=in) ; law=$…$ ; recycle=persistent
E1 [CST_Blk.y] --(bind)--> [CST_Next.x] ; carries=signal
```

Mutate (mint):

```text
+ CST [NEW] ; name=block ; k=2 ; ports=x(side=in, q=1.0),y(side=out) ; law=$y=k x$ ; recycle=persistent
```

A bind does **not** own `law=` or device params; it is an ideal pipe that names the ports it joins (optional `carries=`).

### Application note: pipeline stage (programme instance)

**Instance only** — same ontology as any other CST. A **programme** here is a module/service stage with **ports** as data or control endpoints (payloads, events, API in/out) — not volts/amps, and not a SysML clone or a full programming language. Kind stays **`CST`**; `law=` is the behavioural contract (output as function of input, or pre/post). Agents use this grain on `pin_map`, not to execute code.

Mutate create (teachable assign) — z-score stage then threshold gate:

```text
+ CST [CST_Norm] ; name=zscore ; mu=0 ; sigma=1 ; ports=x(side=in),y(side=out) ; law=$y=(x-\mu)/\sigma$ ; recycle=persistent
+ CST [CST_Gate] ; name=threshold ; t=0.5 ; ports=x(side=in),y(side=out) ; law=$y=\mathbf{1}(x>t)$ ; recycle=persistent
+ E_pipe [CST_Norm.y] --(bind)--> [CST_Gate.x] ; carries=token
```

Pin-map present (same facts, no leading `+`):

```text
CST [CST_Norm] ; name=zscore ; mu=0 ; sigma=1 ; ports=x(side=in),y(side=out) ; law=$y=(x-\mu)/\sigma$ ; recycle=persistent
CST [CST_Gate] ; name=threshold ; t=0.5 ; ports=x(side=in),y(side=out) ; law=$y=\mathbf{1}(x>t)$ ; recycle=persistent
E_pipe [CST_Norm.y] --(bind)--> [CST_Gate.x] ; carries=token
```

`x`/`y` are data ports; the directed bind is an ideal pipe for the token stream (`carries=token`). Norm: `$y=(x-\mu)/\sigma$` with params `mu=`/`sigma=`. Gate: `$y=\mathbf{1}(x>t)$` with param `t=` (1 when input exceeds threshold, else 0).

### Application note: requirements view (agent memory)

**Instance only** — bounded pin-map slice of requirement memory, **not** a SysML / MBSE requirements module. Prefer kind **`CST`** with `role=requirement` (law leaf + ports). Existing TagMap **`REQ`** stays a **SysML locator** pin (`requirementId=`, …); **`CLM`** stays soft claims/decisions — neither is the 1.x acceptance-criteria leaf. Traceability is an **ideal bind** between ports (`carries=trace`), not EDGE-as-relation and not `law=` on the arrow. Label stays **`bind`**; port names carry the roles (`stake` / `design` / optional `verify`).

Mutate create (one requirement CST bound to a programme stage port):

```text
+ CST [CST_R_lat] ; role=requirement ; name=cmd_latency ; ports=stake(side=in),design(side=out) ; law=$t_{\mathrm{cmd}}<10\,\mathrm{ms}$ ; recycle=persistent
+ CST [CST_Gate] ; name=threshold ; t=0.5 ; ports=x(side=in),y(side=out) ; law=$y=\mathbf{1}(x>t)$ ; recycle=persistent
+ E_tr [CST_R_lat.design] --(bind)--> [CST_Gate.x] ; carries=trace
```

Pin-map present (`layer=req`, or anchor on `CST_R_lat`):

```text
CST [CST_R_lat] ; role=requirement ; name=cmd_latency ; ports=stake(side=in),design(side=out) ; law=$t_{\mathrm{cmd}}<10\,\mathrm{ms}$ ; recycle=persistent
CST [CST_Gate] ; name=threshold ; t=0.5 ; ports=x(side=in),y(side=out) ; law=$y=\mathbf{1}(x>t)$ ; recycle=persistent
E_tr [CST_R_lat.design] --(bind)--> [CST_Gate.x] ; carries=trace
```

This view shows acceptance criteria on requirement CSTs and ideal binds that pin those criteria to design/programme ports.

### Application note: pseudocode (programme steps)

**Instance only** — agent memory of algorithmic steps, **not** a programming language or runtime. Kind stays **`CST`** with in/out ports. Steps live in **`pseudo=`** (quoted STRING); keep **`law=`** for the formal contract / postcondition (LaTeX). Do **not** overload `law=` with code text. Prefer one CST over a chain of step NODEs. EDGE remains ideal bind/pipe into/out of ports — no control-flow on the arrow.

Mutate create (clamp stub):

```text
+ CST [CST_Clamp] ; name=clamp ; lo=0 ; hi=1 ; ports=x(side=in),y(side=out) ; pseudo="if x<lo then y:=lo elif x>hi then y:=hi else y:=x" ; law=$y=\mathrm{clip}(x,lo,hi)$ ; recycle=persistent
```

Pin-map present (same facts, no leading `+`):

```text
CST [CST_Clamp] ; name=clamp ; lo=0 ; hi=1 ; ports=x(side=in),y(side=out) ; pseudo="if x<lo then y:=lo elif x>hi then y:=hi else y:=x" ; law=$y=\mathrm{clip}(x,lo,hi)$ ; recycle=persistent
```

Quote `pseudo="…"` whenever the body would collide with `;` or list `,` (usual STRING rule). Optional: omit `law=` when only informal steps are known; add it when the postcondition is clear.

### Application note: flowchart (control flow)

**Instance only** — agent memory of control flow, **not** a flowchart language. Steps and decisions are **`CST`** nodes with ports; arrows are **ideal binds** (`carries=token` or `carries=flow`). Decision = one CST with ports `in` / `yes` / `no` and `law=` or `pseudo=` for the predicate. Pin-map grain: **`view=flowchart`**.

ASCII (start → decide → two paths → end):

```text
  [Start] --out--> [Dec?] --yes--> [Yes] --out--+
                      |                         v
                      +--no--> [No] --out--> [End]
```

Mutate create:

```text
+ CST [CST_Start] ; name=start ; ports=out(side=out) ; recycle=persistent
+ CST [CST_Dec] ; name=ok ; ports=in(side=in),yes(side=out),no(side=out) ; law=$x>0$ ; recycle=persistent
+ CST [CST_Yes] ; name=path_yes ; ports=in(side=in),out(side=out) ; recycle=persistent
+ CST [CST_No] ; name=path_no ; ports=in(side=in),out(side=out) ; recycle=persistent
+ CST [CST_End] ; name=end ; ports=in(side=in) ; recycle=persistent
+ E_sd [CST_Start.out] --(bind)--> [CST_Dec.in] ; carries=token
+ E_dy [CST_Dec.yes] --(bind)--> [CST_Yes.in] ; carries=token
+ E_dn [CST_Dec.no] --(bind)--> [CST_No.in] ; carries=token
+ E_ye [CST_Yes.out] --(bind)--> [CST_End.in] ; carries=token
+ E_ne [CST_No.out] --(bind)--> [CST_End.in] ; carries=token
```

Pin-map present (`view=flowchart`):

```text
CST [CST_Start] ; name=start ; ports=out(side=out) ; recycle=persistent
CST [CST_Dec] ; name=ok ; ports=in(side=in),yes(side=out),no(side=out) ; law=$x>0$ ; recycle=persistent
CST [CST_Yes] ; name=path_yes ; ports=in(side=in),out(side=out) ; recycle=persistent
CST [CST_No] ; name=path_no ; ports=in(side=in),out(side=out) ; recycle=persistent
CST [CST_End] ; name=end ; ports=in(side=in) ; recycle=persistent
E_sd [CST_Start.out] --(bind)--> [CST_Dec.in] ; carries=token
E_dy [CST_Dec.yes] --(bind)--> [CST_Yes.in] ; carries=token
E_dn [CST_Dec.no] --(bind)--> [CST_No.in] ; carries=token
E_ye [CST_Yes.out] --(bind)--> [CST_End.in] ; carries=token
E_ne [CST_No.out] --(bind)--> [CST_End.in] ; carries=token
```

Predicate stays on the decision **NODE** (`law=` / `pseudo=`). EDGE remains ideal bind only.

### Application note: parts architecture (composition)

**Instance only** — composition without a `CAP` metamodel. Parent and children are **`CST`**. Membership = ideal bind with **`carries=member`** (not a new EDGE kind; label stays `bind`). Outer ports export by binding parent ports to child ports. Pin-map grain: **`view=parts`** or **`layer=arch`**.

ASCII (box with two children):

```text
+---------- CST_Box ----------+
|  [A.x]--(bind)-->[B.x]      |
|    ^                 |      |
|  Box.in            Box.out  |
+-----------------------------+
  membership: Box.own --(bind)-- A.own / B.own ; carries=member
```

Mutate create:

```text
+ CST [CST_Box] ; name=box ; ports=in(side=in),out(side=out),own(side=inout) ; recycle=persistent
+ CST [CST_A] ; name=child_a ; ports=x(side=in),y(side=out),own(side=inout) ; law=$y=x$ ; recycle=persistent
+ CST [CST_B] ; name=child_b ; ports=x(side=in),y(side=out),own(side=inout) ; law=$y=x$ ; recycle=persistent
+ E_ma [CST_Box.own] --(bind)-- [CST_A.own] ; carries=member
+ E_mb [CST_Box.own] --(bind)-- [CST_B.own] ; carries=member
+ E_xin [CST_Box.in] --(bind)--> [CST_A.x] ; carries=signal
+ E_ab [CST_A.y] --(bind)--> [CST_B.x] ; carries=signal
+ E_out [CST_B.y] --(bind)--> [CST_Box.out] ; carries=signal
```

Pin-map present (`view=parts`):

```text
CST [CST_Box] ; name=box ; ports=in(side=in),out(side=out),own(side=inout) ; recycle=persistent
CST [CST_A] ; name=child_a ; ports=x(side=in),y(side=out),own(side=inout) ; law=$y=x$ ; recycle=persistent
CST [CST_B] ; name=child_b ; ports=x(side=in),y(side=out),own(side=inout) ; law=$y=x$ ; recycle=persistent
E_ma [CST_Box.own] --(bind)-- [CST_A.own] ; carries=member
E_mb [CST_Box.own] --(bind)-- [CST_B.own] ; carries=member
E_xin [CST_Box.in] --(bind)--> [CST_A.x] ; carries=signal
E_ab [CST_A.y] --(bind)--> [CST_B.x] ; carries=signal
E_out [CST_B.y] --(bind)--> [CST_Box.out] ; carries=signal
```

No `contains=` field and no `CAP` kind — membership is bind metadata via `carries=member`. Shell vs interior still uses `view=shell` / `view=interior` (§5).

### Application note: statechart (states + transitions)

**Instance only** — agent memory of discrete behaviour, **not** a state-machine language or UML clone. Prefer **one CST per state** with ports `enter` / `exit` / `in` (clearer on `pin_map` than a single machine CST with a state enum). Transitions = **directed** ideal binds between state ports. Event / guard live as **bind metadata** (`event=`, optional `guard=$…$`) — **not** `law=` on EDGE (device/constitutive law stays on NODE). Optional action/entry steps: `pseudo=` on the state CST. Pin-map grain: **`view=statechart`**.

ASCII (Idle ↔ Run):

```text
  [Idle] --event=start--> [Run]
    ^                      |
    +----- event=stop -----+
```

Mutate create:

```text
+ CST [CST_Idle] ; name=idle ; ports=enter(side=in),exit(side=out),in(side=inout) ; recycle=persistent
+ CST [CST_Run] ; name=run ; ports=enter(side=in),exit(side=out),in(side=inout) ; recycle=persistent
+ E_start [CST_Idle.exit] --(bind)--> [CST_Run.enter] ; event=start ; carries=event
+ E_stop [CST_Run.exit] --(bind)--> [CST_Idle.enter] ; event=stop ; carries=event
```

Pin-map present (`view=statechart`):

```text
CST [CST_Idle] ; name=idle ; ports=enter(side=in),exit(side=out),in(side=inout) ; recycle=persistent
CST [CST_Run] ; name=run ; ports=enter(side=in),exit(side=out),in(side=inout) ; recycle=persistent
E_start [CST_Idle.exit] --(bind)--> [CST_Run.enter] ; event=start ; carries=event
E_stop [CST_Run.exit] --(bind)--> [CST_Idle.enter] ; event=stop ; carries=event
```

Guarded transition (thin): keep `guard=$…$` on the bind as metadata; if the guard needs ports or `pseudo=`, mint a tiny junction CST instead — do **not** put device `law=` on the EDGE.

### Application note: BJT + resistor (electronics instance)

**Instance only** — not the default frame. Kind stays **`CST`** (no `FN`). Electrical attr keys (`V`, `I`) and `beta=` are domain spellings. Mutate create (teachable assign):

```text
+ CST [CST_Q1] ; name=bjt_npn ; beta=100 ; ports=B(side=in, V=0.7, I=0.001),C(side=out),E(side=inout) ; law=$I_C=\beta I_B$,$I_E=I_B+I_C$ ; recycle=persistent
+ CST [CST_Rc] ; name=Rc ; R=1000 ; ports=a(side=inout),b(side=inout) ; law=$V_a-V_b=I_a R$,$I_a=-I_b$ ; recycle=persistent
+ E_c [CST_Q1.C] --(bind)--> [CST_Rc.a] ; carries=I
```

Pin-map present (same facts, no leading `+`):

```text
CST [CST_Q1] ; name=bjt_npn ; beta=100 ; ports=B(side=in, V=0.7, I=0.001),C(side=out),E(side=inout) ; law=$I_C=\beta I_B$,$I_E=I_B+I_C$ ; recycle=persistent
CST [CST_Rc] ; name=Rc ; R=1000 ; ports=a(side=inout),b(side=inout) ; law=$V_a-V_b=I_a R$,$I_a=-I_b$ ; recycle=persistent
E_ab [CST_Rc.a] --(bind)-- [CST_Rc.b] ; carries=I
E_c [CST_Q1.C] --(bind)--> [CST_Rc.a] ; carries=I
E_ea [CST_Q1.E] <--(bind)--> [CST_Rc.b] ; carries=I
```

Collector current rides the **directed** bind `[CST_Q1.C]→[CST_Rc.a]`; resistor terminals **non-directed** on `a`/`b`; E↔Rc.b **bi-directed** when both directions are explicit. Omit E → truncated device / unowned KCL.

### Application note: relay SPDT (electronics instance)

**Instance only** — same grain as the BJT note. One **`CST`** owns coil + contact ports; galvanic isolation is **two domains on one NODE** (port attr `domain=coil` vs `domain=contact`), not a second kind. Contact path is **state-dependent bind**: `law=` states coil threshold, energised flag `s`, and COM–NO / COM–NC continuity; the live EDGE is whichever path is present; the agent **updates** that EDGE when `s` / `state=` flips — do **not** fake switching as EDGE-as-function.

Mutate create (teachable assign):

```text
+ CST [CST_K1] ; name=relay_spdt ; state=deenergised ; I_th=0.01 ; ports=A1(side=in, domain=coil, V=0, I=0),A2(side=in, domain=coil),COM(side=inout, domain=contact),NO(side=inout, domain=contact),NC(side=inout, domain=contact) ; law=$I_{A1}=-I_{A2}$,$s=\mathbf{1}(\lvert I_{A1}\rvert>I_{th})$,$s=1\Rightarrow V_{\mathrm{COM}}=V_{\mathrm{NO}}\land I_{\mathrm{COM}}+I_{\mathrm{NO}}=0\land I_{\mathrm{NC}}=0$,$s=0\Rightarrow V_{\mathrm{COM}}=V_{\mathrm{NC}}\land I_{\mathrm{COM}}+I_{\mathrm{NC}}=0\land I_{\mathrm{NO}}=0$ ; recycle=persistent
+ E_coil [CST_Drv.out] --(bind)--> [CST_K1.A1] ; carries=I
+ E_ret [CST_K1.A2] --(bind)-- [CST_Gnd.a] ; carries=I
+ E_path [CST_K1.COM] --(bind)-- [CST_K1.NC] ; carries=I
```

Pin-map present after energise (`state=energised`; contact EDGE retargeted COM↔NO):

```text
CST [CST_K1] ; name=relay_spdt ; state=energised ; I_th=0.01 ; ports=A1(side=in, domain=coil, V=12, I=0.02),A2(side=in, domain=coil),COM(side=inout, domain=contact),NO(side=inout, domain=contact),NC(side=inout, domain=contact) ; law=$I_{A1}=-I_{A2}$,$s=\mathbf{1}(\lvert I_{A1}\rvert>I_{th})$,$s=1\Rightarrow V_{\mathrm{COM}}=V_{\mathrm{NO}}\land I_{\mathrm{COM}}+I_{\mathrm{NO}}=0\land I_{\mathrm{NC}}=0$,$s=0\Rightarrow V_{\mathrm{COM}}=V_{\mathrm{NC}}\land I_{\mathrm{COM}}+I_{\mathrm{NC}}=0\land I_{\mathrm{NO}}=0$ ; recycle=persistent
E_coil [CST_Drv.out] --(bind)--> [CST_K1.A1] ; carries=I
E_ret [CST_K1.A2] --(bind)-- [CST_Gnd.a] ; carries=I
E_path [CST_K1.COM] --(bind)-- [CST_K1.NO] ; carries=I
```

**State / contact switching:** `s=1` means energised (`state=energised`); `s=0` means deenergised (`state=deenergised`). Coil: `$I_{A1}=-I_{A2}$` and `$s=\mathbf{1}(\lvert I_{A1}\rvert>I_{th})$`. Contacts: `$s=1$` closes COM–NO (equal voltage, KCL on that pair, `$I_{\mathrm{NC}}=0$`); `$s=0$` closes COM–NC (same for NC; `$I_{\mathrm{NO}}=0$`). Live EDGE must match: `$s=1$` → `COM--NO`, `$s=0$` → `COM--NC`.

---

## 4. Wrong shapes (three)

- **Anything as EDGE law** — device FN on the arrow (`[A] --(derives)--> [B] ; law=$y=k x$`) **or** stuffing ideal-wire equations onto EDGE (`… --(bind)-- … ; law=$V_a=V_b$`). EDGE = ideal pipe only; continuity is implied.
- **Node-to-node bind** — e.g. `[CST_Q1] --(bind)-- [CST_Rc]` with no `.port` (missing port grain; prefer `[CST_Q1.C]`).
- **Hollow nest with no behaviour leaf** — a shell without a node that owns `law=` or `pseudo=` (behaviour has nowhere to live).

---

## 5. Pin map grain

Flat `depth` / `max_rows` alone fails at coarse → fine strata.

```text
pin_map(session, anchor, depth, max_rows, layer?=…, view?=shell|interior|flowchart|parts|statechart|…)
```

(`shell|interior|…` above is API documentation “or”, not a wire list.)

1. Read shell (or current layer) — few rows.  
2. Reason / mutate at that grain.  
3. If blocked → one descend (re-anchor or `view=interior`).  
4. Ascend; do not keep nested shells in context.

`layer=` = abstraction stratum (project-chosen labels). Examples: **`layer=req`** — requirement CSTs + design binds; **`layer=arch`** — parts composition. Shell vs interior = **`view=`**, not a new atom. Other teachable **`view=`** grains (§3): `flowchart`, `parts`, `statechart`. Do not invent a kind zoo per view.

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

- **`ports=` binding** — attrs in `(…)` vs params / `law=` idents; quantity keys still open.
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
