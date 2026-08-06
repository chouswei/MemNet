# Multi-layer MemNet (design, slim)

**Status:** design only — **not** in 0.3.x. Target **MemNet 1.x**.  
**Mission:** agent memory graph (any domain), Write = display, bounded `pin_map`, tokens — **not** MBSE.  
**Store:** **NODE | EDGE** only. No third AST primitive.

[`memnet-grammar-design.md`](memnet-grammar-design.md) §3 *Layering* = I/O / store / transport. This doc = **stratified pin-map product graph** (right grain without budget blow-up).

---

## 1. Ontology (absolute minimum)

| Atom | Role |
|------|------|
| **NODE** | Kinded fact. Law leaf: prefer kind **`CST`** (or any NODE with `law=` + `ports=`). Device / constitutive / causal laws live **only** here. Disambiguate with **`role=`** / pin-map **`view=`** — no kind zoo (`REQ`/`PER`/`FN` as law leaves). |
| **EDGE** | One store primitive, **two endpoint grains** (dual EDGE). **No** `law=` on EDGE. |

**Dual EDGE (locked):**

```text
port ↔ port  →  bind / pipe   (ideal connection; sense on carries=)
node ↔ node  →  relation      (chart / semantic link; sense = label)
```

| Grain | Endpoints | Label | Sense |
|-------|-----------|-------|-------|
| **Bind** (ideal pipe) | Both `[Node.port]` (or both first-class PORT ids) | Default **`bind`**; optional synonym **`pipe`** (same meaning) | Fields: `carries=` / `event=` / `guard=` — **not** the label |
| **Relation** (chart / semantic) | Both bare `[NodeId]` | Relation name itself (`owns`, `knows`, `reports_to`, `helps`, …) | **The label is the sense** — do not pile `carries=` as a second name |

Same three ASCII wire forms for both grains (bare `IDENT` between dashes; charset `[A-Za-z_][A-Za-z0-9_]*` — [`MemNetLayer.g4`](antlr/MemNetLayer.g4)):

| Form | Wire | Meaning |
|------|------|---------|
| Directed | `--label-->` | One-way |
| Non-directed | `--label--` | Undirected (no arrowheads) |
| Bi-directed | `<--label-->` | Both directions explicit (≠ non-directed) |

```text
Eid [CST_Q1.C] --bind--> [CST_Rc.a] ; carries=token
Eid [CST_Alice] --knows--> [CST_Bob]
```

**Law leaf:** one shape. Put `law=` / params (`k=`, `gain=`, …) **on the node** (`CST`). `law=` is **LaTeX** (storage/display for the LLM — no evaluator required to render). Several equations → one field, `$…$` segments joined by `,` (same list joiner as `ports=`).

**Ideal bind:** port↔port EDGE is an ideal pipe — endpoints share the carried quantity as the domain defines (agent may rely on that continuity without EDGE `law=` text; further constraints stay on NODE laws or domain convention). Synonym **`pipe`** ≡ **`bind`** (accept on parse; emit **`bind`**). Legacy `connects` → `bind`. Demote other non-`bind`/`pipe` labels on port-grain edges (`contains`, `refines`, …).

**Relation:** node↔node EDGE is a chart/semantic link. Label = relation name. Prefer directed form for asymmetric links (`reports_to`, `owns`); non-directed / bi-directed when the chart needs them. No inventing `self` / `reports` ports just to force bind grain.

**Ports:** fields on the law node until separate atoms are proven necessary. Entry = `name: {attr=val, …}` (labelled record bag — TS/YAML-style; not a call):

```text
ports=x: {side=in, q=0},y: {side=out},state: {side=inout, q=$s$}
```

Attrs use the same `=` / `,` as elsewhere. `side=` is required in teachable bags (`in` / `out` / `inout`). Other attrs are **domain quantities at/through the port** — omit when unused (no empty bags beyond `side=`). “Through” quantities often align with directed binds / port side; non-directed binds need not invent direction. Do **not** celebrate a kind zoo. No `FN`. Orientation lives in `law=` and port `side=` on the **NODE**.

**`PORT` as first-class NODE:** only if endpoints must be wired independently (binds need stable ids). Quantity fields on that atom use ordinary `key=value` (teach `value=` / domain keys). Until then, keep ports as fields; engine may desugar later. First-class PORT↔PORT still uses **bind** grain (not relation).

**`CAP` / nesting:** deferred as metamodel. Pin-map **shell vs interior** is a **view budget** (`view=shell` or `view=interior` / re-anchor), not a chapter of kinds. Prefer compact shell first; descend one step when blocked; do not dump nested interiors in one call. Composition without `CAP`: membership **binds** with `carries=member` on port grain (`view=parts` / `layer=arch` — §3 parts note). Optional later sugar `CAP` + `contains=` is packaging, not ontology.

**Omit defaults (wire):** session/engine default covers `recycle=` (typically `persistent`) — **omit** `recycle=` on teachable mutate and pin_map lines unless the value is **non-default** (token waste otherwise). Same spirit for empty port attrs: `ports=x: {side=in}` not `ports=x: {side=in, q=}`.

**Endpoint lock:** `.` = ownership join inside `[…]` for bind. Prefer `[Node.port]` over EDGE `from=`/`to=` (hides grain). `{…}` = **brace-group / record** (`attr=val`, `,`-joined) — primary teachable use is port bags. **No** closed global allow-list of domain field names (domains differ) — prefer **author/agent discipline** below. Not on EDGE arrows. Demote braced `--{label}-->` and paren `--(label)-->`. `NEW` is mint-only, not a label. No `law=` on EDGE.

**Brace-group discipline (locked):** use `{…}` when the value is a **record of attrs**; use scalar `=` for a single value. Prefer flat attrs; nest only when needed (**depth ≤2**). Domain vocab is free under discipline — do **not** invent bag spam on every key. Soft MUSTNOT (keyword denylist, not an allow-list): dialect scalars `law` / `pseudo` / `recycle` / `role` / `view` / `layer` stay STRING / IDENT / number — never bags. OK: `meta={rev=1, src=doc}`; `units={x=m, y=s}`. Bad: `gain={k=2}` (single value → `gain=2`); `law={eq=$V=IR$}`.

**MUSTNOT:** mix endpoints (`[Node.port]` ↔ bare `[Node]`); put `law=` on an EDGE; treat **bind** as a **relation** (or vice versa — do not teach `--bind-->` on bare person ids, and do not use chart labels on port-grain pipes); treat EDGE as a function or multi-port device; invent causality on a bind; confuse non-directed with bi-directed; use `:` for scalars (`side:in` — use `side=in`); omit `:` on name-to-bag (`ports=x={…}` — use `ports=x: {…}`); pile port facts as `name:side:value` colon chains; put braces or attrs on the arrow label; invent new KINDs instead of `role=` / `view=`; bag dialect keywords (`law`/`pseudo`/`recycle`/`role`/`view`/`layer`).

---
## 2. Syntax (cheat sheet)

**Spine** = shared dialect Write=display ([`memnet-grammar-design.md`](memnet-grammar-design.md) §4–5; **in engine** — directed only today). **1.x overlays** below (`ports=` / `law=` / `pseudo=` / `carries=` / dual EDGE / three wire forms / stratified `view`/`layer`) = **proposed-1.x**, not in 0.3.x.

### Delimiters (locked)

| Char | Role |
|------|------|
| `;` | **Only** top-level field separator on a line |
| `=` | Assign a **value** to a **key** — top-level `key=value` (present / create); `+=` / `-=` only on `~`; attrs inside `{…}` (`side=in`). Scalars stay `=` — **no** `key: value` |
| `,` | **Sole** list joiner inside a field value (`ports=` entries, attrs in `{…}`, multi-eq `law=`, …) |
| `:` | Bind a **name** to a **brace-group** only: `name: {…}` (inside `ports=` list). **Not** scalar assign; **not** `side:in`; **not** `x={…}` without `:` |
| `{` `}` | **Brace-group / record** — `attr=val` pairs, `,`-joined. Primary teach: port bags after `name:` (`x: {side=in, q=0}`). Discipline: bag = record of attrs; scalar `=` for singles; nest only to depth ≤2; no bag spam. Soft MUSTNOT bags on `law`/`pseudo`/`recycle`/`role`/`view`/`layer`. OK: `meta={units={x=m,y=s}}`. Bad: `gain={k=2}`; `meta={a={b={c=1}}}`. Not on EDGE arrows |
| `.` | Ownership join inside `[…]` for EDGE endpoints: `[NodeId.PortName]` |
| `$…$` | LaTeX inline math **only** (not a field separator); Dirac bra-ket lives here (prefer `\langle`/`\rangle`) |
| `[` `]` | Wrap Id, mint `NEW`, or qualified port ref `NodeId.PortName` |
| `--` `-->` | **Directed** EDGE: `--label-->` (bare `IDENT` between dashes; no spaces) |
| `--` `--` | **Non-directed** EDGE: `--label--` |
| `<--` `-->` | **Bi-directed** EDGE: `<--label-->` (`<--` / `-->` = direction marks only — not Dirac) |
| `"` | STRING for awkward values (shared dialect) |
| `+` `~` `-` | Mutate ops (create / update / drop) — line prefix only |
| `#` | Line comment to end of line (fixtures / notes; skipped by lexer) |

**`=` vs `:` (locked):** `=` assigns values to keys (fields and bag attrs). `:` binds a name to a brace-group only (`name: {…}`). Good: `ports=x: {side=in}`. Bad: `ports=x={side=in}` or `{side:in}`.

**Defaults:** omit `recycle=` on wire unless non-default — session/engine default (typically `persistent`) already covers it.

**Record vs EDGE:** `{…}` = brace-group / record value (same shape everywhere). Primary teach: labelled port bags (`IDENT: {…}` inside `ports=`). Other keys follow **brace-group discipline** (record vs scalar; depth ≤2; no bag spam) — not a domain-field allow-list. Nested bags **max depth = 2** — OK `meta={units={x=m,y=s}}`; reject deeper. EDGE wire = bare `--label-->` / `--label--` / `<--label-->` after endpoint `]`. Grain from endpoints: both `.port` → bind/pipe; both bare → relation. `()` is **free** (held for later; not used on arrows).

No wire `|`. Query enums (`view=shell` or `interior`) are exclusive choices, not joined lists. Prefer `\lvert`/`\rvert` over bare `|` inside maths; if a value contains `;` or a list-joining `,` that is not a segment boundary, quote the whole field: `law="…"`. Same STRING rule for **`pseudo=`** bodies (steps often need `;` / `:` / spaces) — quote the whole value: `pseudo="…"`. No new punct for algorithms.

### Delimiter inventory (used vs free)

Compact map of ASCII punctuation for this slim dialect. **Do not** assign free marks without a real gap.

| Status | Characters | Notes |
|--------|------------|--------|
| **Used** | `;` `,` `=` `{` `}` `[` `]` `.` `:` `$` `"` `#` `+` `~` `-` | Fields; brace-group records (ports + other attrs); ids; ownership; LaTeX; STRING; comment; mutate |
| **Used (arrow compounds)** | `--` `-->` `<--` | Dual EDGE wires; bare `IDENT` label between dashes |
| **Demoted / avoid** | `\|` | No wire pipe; prefer `\lvert`/`\rvert` in maths; demote bare `x{…}` / `x(…)` ports; demote braced `--{label}-->` and paren `--(label)-->` (locked: bare `--label-->`) |
| **Free (held)** | `(` `)` `&` `*` `^` `!` `?` `` ` `` `@` `%` `'` `\` | `()` fully free (not binds); others held |

**Collisions (do not reassign):** `$` = LaTeX `law=` / attr maths (Dirac bra-ket allowed inside `$…$` only); `<` `>` = EDGE arrow direction marks (`<--` / `-->` — not Dirac); `.` = `[Node.port]`; `=` = value assign (never colon for scalars); `:` = name-to-bag **only** (`name: {…}` inside `ports=`); `{…}` = **brace-group / record** (ports primary; other keys by discipline — not arrow labels). `()` is free — not locked to EDGE.

**Sparing recommendations (0–2):**

1. **Keep `#` as line comment only** — already matches `MemNet.g4` / layer grammar; no second meaning.
2. **No new punct for through-quantity or EDGE sugar** — port `name: {attrs}` + `--label-->` already cover bind and relation; hold `&` `*` `^` `!` `?` `` ` ``.

### Generic skeleton

```text
CST [Id] ; name=… ; ports=name: {side=…, q=…},… ; law=$eq$,$eq$ ; param=…
Eid [Id.port] --bind--> [Id.port] ; carries=token
Eid [Id.port] --bind-- [Id.port] ; carries=token
Eid [Id.port] <--bind--> [Id.port] ; carries=token
Eid [NodeA] --rel_name--> [NodeB]
```

`ports=` entries are `,`-joined `name: {…}` labelled records on the NODE. Bind endpoints name those ports as `[NodeId.PortName]` (`pipe` ≡ `bind`). Relation endpoints are bare `[NodeId]`; label = relation name. `law=` holds LaTeX maths on the NODE only. Omit session-default `recycle=persistent`.

### `law=` expression rules (LaTeX)

- **Where:** one `law=` field on the **NODE** (prefer kind `CST`). **Never** on EDGE — bind implies continuity; relation is a chart link; do not teach equations on the arrow. **Proposed-1.x** — store/show the LaTeX string for agents; no render/eval engine required.
- **Wire:** each equation is **inline math** wrapped in `$…$`. Multi-eq: join those `$…$` segments with `,` (same joiner as `ports=`). Function and equation are the same shape — no `FN` kind; optional causality via port `side=` only.
- **Dirac:** bra-ket is a full citizen of `law=` maths — e.g. `law=$\langle\phi|\psi\rangle$`, `law=$|n\rangle$`. Lives **only** inside `$…$`; do **not** conflate with EDGE arrowheads `<--` / `-->` (direction marks on wires).
- **Completeness (soft-validate):** every symbol in `law=` MUST appear as a port quantity (name / attr / subscript), a node param, or be defined in the same `law=` list — no orphan predicates. **Lint (optional, thin):** warn when a math ident / macro base is not ⊆ ports ∪ params ∪ same-`law=` defs (ignore pure numerals and LaTeX operators / `\mathrm{…}` wrappers). Agents SHOULD fix before settle.
- **Binding (same node):** math idents / macros resolve to (1) **params** (`k=`, `beta=` ← `\beta`, `R=`, …), or (2) a **port name** when the ident equals a `ports=` name. Multi-quantity at one port: domain attrs in the bag (`q=`, …) or subscripts in `law=` — port name is the subscript. Qualified `PORT_x.q` deferred.
- **MUSTNOT:** ASCII-only ad-hoc `expr=` on EDGE; `law=` on bind or relation; fake `derives`/`feeds` as the 1.x law surface (transitional: [`memnet-field-formulas.md`](memnet-field-formulas.md)).

### Line shapes

| Shape | Form |
|-------|------|
| NODE (pin map / bare) | `KIND [Id] ; key=value ; …` |
| EDGE bind (port grain) | `Eid [Node.port] --bind--> [Node.port] ; …` (also `--bind--` / `<--bind-->`; `pipe` ≡ `bind`) |
| EDGE relation (node grain) | `Eid [NodeA] --rel_name--> [NodeB] ; …` (label = sense; bare ids only) |
| Create | `+ KIND [NEW\|Id] ; …` · `+ [NEW\|Eid]? [Node.port] --bind-- [Node.port] ; …` · or relation `--owns-->` / … |
| Update | `~ [Id] ; …` · `~ Eid ; …` · on `~` only: `key+=N` / `key-=N` |
| Drop | `- Eid` |

Pin map = **bare present** (no leading `+`/`~`/`-`). Ops are mutate-only. In the Create row, `\|` is documentation “or”, not a wire delimiter.

### Field forms (this doc)

| Field | Form |
|-------|------|
| `ports=` | `name: {side=…, …}`, `,`-joined — omit attrs beyond needed `side=` / quantities |
| `law=` | LaTeX `$…$` atom(s) on the **NODE** only; several → one field, `$eq$` segments `,`-joined — **forbidden** on EDGE |
| `pseudo=` | algorithmic steps as a STRING on the **NODE** (prefer quoted); not LaTeX; not an evaluator — see §3 pseudocode note |
| `name=` | short label |
| `role=` | CST disambiguator only (`requirement`, `person`, …) — **not** a new KIND |
| `state=` | optional present discrete state on the NODE (e.g. relay `energised` / `deenergised`) — display + agent cue; not an EDGE evaluator |
| params | domain keys **on the NODE** (`k=`, `gain=`, `I_th=`, …) |
| `value=` | on first-class **PORT** NODE — quantity at/through that endpoint (domain terms) |
| `carries=` | optional on **bind** forms; generic quantity/token name (`signal`, `q`, `member`, `event`, `token`, …) — **not** on relation grain |
| `event=` | optional bind metadata on a transition EDGE (statechart) — **not** `law=` |
| `guard=` | optional bind metadata (`$…$` predicate text) on a transition EDGE — **not** device `law=` |
| `recycle=` | **omit** unless non-default — session/engine default is typically `persistent` |
| `view=` / `layer=` | pin-map grain (`shell`/`interior`; also `flowchart` / `parts` / `statechart` / `persons` / `org`; `layer=arch` / `layer=req`; …) — query/envelope; not ontology |

### Port token (`ports=`)

```text
x: {side=in, q=0}
```

| Part | Meaning |
|------|---------|
| `x` | Port **name** (ties to symbols in `law=`) |
| `:` | Bind name to brace-group only (prefer one space after) |
| `{…}` | Brace-group / record: `attr=val` pairs, `,`-joined (same shape as other record field values) |
| `side=` | Required in teachable bags: `in` / `out` / `inout` — **MUSTNOT** `side:in` |
| other attrs | Domain quantities (e.g. `q=`); omit when unused |

Teach **always** `name: {…}` inside `ports=` (prefer one space after `:`; at least `side=`). Demote `x={…}`, bare `x{…}`, and `x(…)`. Bare `name` without `: {…}` is not a port entry. List joiner between ports stays `,`. Quote the whole `ports=` field if an attr value needs `;` or a list-joining `,` outside `$…$`.

### EDGE endpoint

**Bind (port grain):**

```text
[CST_Q1.C]
```

| Part | Meaning |
|------|---------|
| `CST_Q1` | Owner **NODE** id |
| `.` | Ownership join (inside brackets only) |
| `C` | Port **name** declared on that node’s `ports=` |

Both ends MUST be qualified (or both first-class PORT ids). Optional `carries=`. Label `bind` (emit) or `pipe` (synonym). Rejected: `from=`/`to=`; bare `[CST_Q1]--bind--[CST_Rc]` without port grain; chart relation labels on port endpoints.

**Relation (node grain):**

```text
[CST_Alice]
```

Both ends MUST be bare node ids. Label = relation name (`knows`, `reports_to`, …). Sense is the label — do not teach `carries=` as a duplicate name. Rejected: mixed `[Alice]` ↔ `[Bob.port]`; `--bind-->` / `--pipe-->` on bare person ids.

First-class PORT NODE remains an escape hatch only when a port must be an independent atom — otherwise qualified refs suffice for bind grain. Label / grain rules: §1 **Dual EDGE**.

---

## 3. Generic sketch, then domain instance

**Lead (any domain)** — abstract CST with ports, law, and binds:

```text
CST [CST_Blk] ; name=block ; k=2 ; ports=x: {side=in, q=1.0},y: {side=out} ; law=$y=k x$
CST [CST_Next] ; name=next ; ports=x: {side=in},y: {side=out} ; law=$y=x$
E1 [CST_Blk.y] --bind--> [CST_Next.x] ; carries=signal
```

Mutate (mint):

```text
+ CST [NEW] ; name=block ; k=2 ; ports=x: {side=in, q=1.0},y: {side=out} ; law=$y=k x$
```

A **bind** does **not** own `law=` or device params; it is an ideal pipe that names the ports it joins (optional `carries=`). A **relation** names two nodes and puts sense in the label.

### Application note: pipeline stage (programme instance)

**Instance only** — same ontology as any other CST. A **programme** here is a module/service stage with **ports** as data or control endpoints (payloads, events, API in/out) — not volts/amps, and not a SysML clone or a full programming language. Kind stays **`CST`**; `law=` is the behavioural contract (output as function of input, or pre/post). Agents use this grain on `pin_map`, not to execute code.

Mutate create (teachable assign) — z-score stage then threshold gate:

```text
+ CST [CST_Norm] ; name=zscore ; mu=0 ; sigma=1 ; ports=x: {side=in},y: {side=out} ; law=$y=(x-\mu)/\sigma$
+ CST [CST_Gate] ; name=threshold ; t=0.5 ; ports=x: {side=in},y: {side=out} ; law=$y=\mathbf{1}(x>t)$
+ E_pipe [CST_Norm.y] --bind--> [CST_Gate.x] ; carries=token
```

Pin-map present (same facts, no leading `+`):

```text
CST [CST_Norm] ; name=zscore ; mu=0 ; sigma=1 ; ports=x: {side=in},y: {side=out} ; law=$y=(x-\mu)/\sigma$
CST [CST_Gate] ; name=threshold ; t=0.5 ; ports=x: {side=in},y: {side=out} ; law=$y=\mathbf{1}(x>t)$
E_pipe [CST_Norm.y] --bind--> [CST_Gate.x] ; carries=token
```

`x`/`y` are data ports; the directed bind is an ideal pipe for the token stream (`carries=token`). Norm: `$y=(x-\mu)/\sigma$` with params `mu=`/`sigma=` (`\mu`/`\sigma`). Gate: `$y=\mathbf{1}(x>t)$` with param `t=` (1 when input exceeds threshold, else 0).

### Application note: requirements view (agent memory)

**Instance only** — bounded pin-map slice of requirement memory, **not** a SysML / MBSE requirements module. Prefer kind **`CST`** with `role=requirement` (law leaf + ports). Existing TagMap **`REQ`** stays a **SysML locator** pin (`requirementId=`, …); **`CLM`** stays soft claims/decisions — neither is the 1.x acceptance-criteria leaf. Traceability is an **ideal bind** between ports (`carries=trace`), not a chart relation and not `law=` on the arrow. Label stays **`bind`**; port names carry the roles (`stake` / `design` / optional `verify`).

Mutate create (one requirement CST bound to a programme stage port):

```text
+ CST [CST_R_lat] ; role=requirement ; name=cmd_latency ; ports=stake: {side=in, q=$t$},design: {side=out} ; t_lim=10 ; law=$t<t_{\mathrm{lim}}\,\mathrm{ms}$
+ CST [CST_Gate] ; name=threshold ; t=0.5 ; ports=x: {side=in},y: {side=out} ; law=$y=\mathbf{1}(x>t)$
+ E_tr [CST_R_lat.design] --bind--> [CST_Gate.x] ; carries=trace
```

Pin-map present (`layer=req`, or anchor on `CST_R_lat`):

```text
CST [CST_R_lat] ; role=requirement ; name=cmd_latency ; ports=stake: {side=in, q=$t$},design: {side=out} ; t_lim=10 ; law=$t<t_{\mathrm{lim}}\,\mathrm{ms}$
CST [CST_Gate] ; name=threshold ; t=0.5 ; ports=x: {side=in},y: {side=out} ; law=$y=\mathbf{1}(x>t)$
E_tr [CST_R_lat.design] --bind--> [CST_Gate.x] ; carries=trace
```

This view shows acceptance criteria on requirement CSTs and ideal binds that pin those criteria to design/programme ports. Symbols `$t$` / `t_lim` ⊆ ports∪params.

### Application note: pseudocode (programme steps)

**Instance only** — agent memory of algorithmic steps, **not** a programming language or runtime. Kind stays **`CST`** with in/out ports. Steps live in **`pseudo=`** (quoted STRING); keep **`law=`** for the formal contract / postcondition (LaTeX). Do **not** overload `law=` with code text. Prefer one CST over a chain of step NODEs. EDGE remains ideal bind/pipe into/out of ports — no control-flow on the arrow.

Mutate create (clamp stub):

```text
+ CST [CST_Clamp] ; name=clamp ; lo=0 ; hi=1 ; ports=x: {side=in},y: {side=out} ; pseudo="if x<lo then y:=lo elif x>hi then y:=hi else y:=x" ; law=$y=\mathrm{clip}(x,lo,hi)$
```

Pin-map present (same facts, no leading `+`):

```text
CST [CST_Clamp] ; name=clamp ; lo=0 ; hi=1 ; ports=x: {side=in},y: {side=out} ; pseudo="if x<lo then y:=lo elif x>hi then y:=hi else y:=x" ; law=$y=\mathrm{clip}(x,lo,hi)$
```

Quote `pseudo="…"` whenever the body would collide with `;` or list `,` (usual STRING rule). Optional: omit `law=` when only informal steps are known; add it when the postcondition is clear.

### Application note: flowchart (control flow)

**Instance only** — agent memory of control flow, **not** a flowchart language. Steps and decisions are **`CST`** nodes with ports; arrows are **ideal binds** (`carries=token`). Decision = one CST with ports matching `law=` symbols and `yes` / `no` exits. Pin-map grain: **`view=flowchart`**.

**Shell cap (locked):** `view=flowchart` / `view=statechart` shell ≤ **8 NODEs** and ≤ **12 EDGEs**, or **decision-only** (one hop: decision CST + exit binds). Full paths → re-anchor / `view=interior`.

ASCII (decision-only shell):

```text
           [Dec?]
          /      \
       yes        no
        v          v
      [Yes]      [No]
```

Mutate create (shell — decision only):

```text
+ CST [CST_Dec] ; name=ok ; ports=x: {side=in},yes: {side=out},no: {side=out} ; law=$x>0$
+ CST [CST_Yes] ; name=path_yes ; ports=in: {side=in}
+ CST [CST_No] ; name=path_no ; ports=in: {side=in}
+ E_dy [CST_Dec.yes] --bind--> [CST_Yes.in] ; carries=token
+ E_dn [CST_Dec.no] --bind--> [CST_No.in] ; carries=token
```

Pin-map present (`view=flowchart` shell — 3 NODEs / 2 EDGEs):

```text
CST [CST_Dec] ; name=ok ; ports=x: {side=in},yes: {side=out},no: {side=out} ; law=$x>0$
CST [CST_Yes] ; name=path_yes ; ports=in: {side=in}
CST [CST_No] ; name=path_no ; ports=in: {side=in}
E_dy [CST_Dec.yes] --bind--> [CST_Yes.in] ; carries=token
E_dn [CST_Dec.no] --bind--> [CST_No.in] ; carries=token
```

Predicate stays on the decision **NODE** (`law=` / `pseudo=`). EDGE remains ideal bind only. Start/End chains live in interior after re-anchor.

### Application note: parts architecture (composition)

**Instance only** — composition without a `CAP` metamodel. Parent and children are **`CST`**. Membership = ideal bind with **`carries=member`** (not a new EDGE kind; label stays `bind`). Outer ports export by binding parent ports to child ports. Pin-map grain: **`view=parts`** or **`layer=arch`**.

ASCII (box with two children):

```text
+---------- CST_Box ----------+
|  [A.x]--bind-->[B.x]        |
|    ^                 |      |
|  Box.in            Box.out  |
+-----------------------------+
  membership: Box.own --bind-- A.own / B.own ; carries=member
```

Mutate create:

```text
+ CST [CST_Box] ; name=box ; ports=in: {side=in},out: {side=out},own: {side=inout}
+ CST [CST_A] ; name=child_a ; ports=x: {side=in},y: {side=out},own: {side=inout} ; law=$y=x$
+ CST [CST_B] ; name=child_b ; ports=x: {side=in},y: {side=out},own: {side=inout} ; law=$y=x$
+ E_ma [CST_Box.own] --bind-- [CST_A.own] ; carries=member
+ E_mb [CST_Box.own] --bind-- [CST_B.own] ; carries=member
+ E_xin [CST_Box.in] --bind--> [CST_A.x] ; carries=signal
+ E_ab [CST_A.y] --bind--> [CST_B.x] ; carries=signal
+ E_out [CST_B.y] --bind--> [CST_Box.out] ; carries=signal
```

Pin-map present (`view=parts`):

```text
CST [CST_Box] ; name=box ; ports=in: {side=in},out: {side=out},own: {side=inout}
CST [CST_A] ; name=child_a ; ports=x: {side=in},y: {side=out},own: {side=inout} ; law=$y=x$
CST [CST_B] ; name=child_b ; ports=x: {side=in},y: {side=out},own: {side=inout} ; law=$y=x$
E_ma [CST_Box.own] --bind-- [CST_A.own] ; carries=member
E_mb [CST_Box.own] --bind-- [CST_B.own] ; carries=member
E_xin [CST_Box.in] --bind--> [CST_A.x] ; carries=signal
E_ab [CST_A.y] --bind--> [CST_B.x] ; carries=signal
E_out [CST_B.y] --bind--> [CST_Box.out] ; carries=signal
```

No `contains=` field and no `CAP` kind — membership is bind metadata via `carries=member`. Shell vs interior still uses `view=shell` / `view=interior` (§5).

### Application note: statechart (states + transitions)

**Instance only** — agent memory of discrete behaviour, **not** a state-machine language or UML clone. Prefer **one CST per state** with ports `enter` / `exit` (clearer on `pin_map` than a single machine CST with a state enum). Transitions = **directed** ideal binds between state ports. Event / guard live as **bind metadata** (`event=`, optional `guard=$…$`) — **not** `law=` on EDGE. Optional action/entry steps: `pseudo=` on the state CST. Pin-map grain: **`view=statechart`**. Honour the §3 flowchart **shell cap** (≤8 NODEs / ≤12 EDGEs) — Idle↔Run fits.

ASCII (Idle ↔ Run):

```text
  [Idle] --event=start--> [Run]
    ^                      |
    +----- event=stop -----+
```

Mutate create:

```text
+ CST [CST_Idle] ; name=idle ; ports=enter: {side=in},exit: {side=out}
+ CST [CST_Run] ; name=run ; ports=enter: {side=in},exit: {side=out}
+ E_start [CST_Idle.exit] --bind--> [CST_Run.enter] ; event=start ; carries=event
+ E_stop [CST_Run.exit] --bind--> [CST_Idle.enter] ; event=stop ; carries=event
```

Pin-map present (`view=statechart` — 2 NODEs / 2 EDGEs):

```text
CST [CST_Idle] ; name=idle ; ports=enter: {side=in},exit: {side=out}
CST [CST_Run] ; name=run ; ports=enter: {side=in},exit: {side=out}
E_start [CST_Idle.exit] --bind--> [CST_Run.enter] ; event=start ; carries=event
E_stop [CST_Run.exit] --bind--> [CST_Idle.enter] ; event=stop ; carries=event
```

Guarded transition (thin): keep `guard=$…$` on the bind as metadata; if the guard needs ports or `pseudo=`, mint a tiny junction CST instead — do **not** put device `law=` on the EDGE.

### Application note: persons / relation chart

**Instance only** — org chart, family, or collaborator graph for **agent pin_map** (who reports to whom, who knows whom) — **not** a social-network product. No TagMap **`PER`** / **`ACT`**; prefer light **`CST`** with `role=person` (no `law=` / `ports=` required for chart rows).

**Locked split (dual EDGE):**

| Domain | EDGE grain | Endpoints | Label |
|--------|------------|-----------|-------|
| Physical / programme / law CST | **Bind** | `[Node.port]` | `bind` (or `pipe`) |
| Persons / org / family chart | **Relation** | bare `[PersonA]` / `[PersonB]` | relation name (`reports_to`, `knows`, …) |

Do **not** generalise bare-id relations back onto BJT / pipeline / parts. Do **not** invent `self`/`reports`/`knows` ports to force bind grain. Sense = label; no `carries=` duplicate. Pin-map grain: **`view=persons`** or **`view=org`**.

ASCII (Boss ← Alice reports_to; Alice knows Bob):

```text
  [Boss]
     ^ reports_to
     |
  [Alice] --knows--> [Bob]
```

Mutate create:

```text
+ CST [CST_Boss] ; role=person ; name=Boss
+ CST [CST_Alice] ; role=person ; name=Alice
+ CST [CST_Bob] ; role=person ; name=Bob
+ E_ra [CST_Alice] --reports_to--> [CST_Boss]
+ E_kb [CST_Alice] --knows--> [CST_Bob]
```

Pin-map present (`view=persons`):

```text
CST [CST_Boss] ; role=person ; name=Boss
CST [CST_Alice] ; role=person ; name=Alice
CST [CST_Bob] ; role=person ; name=Bob
E_ra [CST_Alice] --reports_to--> [CST_Boss]
E_kb [CST_Alice] --knows--> [CST_Bob]
```

Team membership (thin): bare-id relation `--member_of-->` / `--member--` (non-directed when undirected). Keep the slice small — mission is tokens + accuracy, not a full org dump.

### Application note: BJT + resistor (electronics instance)

**Instance only** — not the default frame. Kind stays **`CST`** (no `FN`). Electrical attr keys (`V`, `I`) and `beta=` are domain spellings. Mutate create (teachable assign):

```text
+ CST [CST_Q1] ; name=bjt_npn ; beta=100 ; ports=B: {side=in, V=0.7, I=0.001},C: {side=out},E: {side=inout} ; law=$I_C=\beta I_B$,$I_E=I_B+I_C$
+ CST [CST_Rc] ; name=Rc ; R=1000 ; ports=a: {side=inout},b: {side=inout} ; law=$V_a-V_b=I_a R$,$I_a=-I_b$
+ E_c [CST_Q1.C] --bind--> [CST_Rc.a] ; carries=I
```

Pin-map present (same facts, no leading `+`):

```text
CST [CST_Q1] ; name=bjt_npn ; beta=100 ; ports=B: {side=in, V=0.7, I=0.001},C: {side=out},E: {side=inout} ; law=$I_C=\beta I_B$,$I_E=I_B+I_C$
CST [CST_Rc] ; name=Rc ; R=1000 ; ports=a: {side=inout},b: {side=inout} ; law=$V_a-V_b=I_a R$,$I_a=-I_b$
E_ab [CST_Rc.a] --bind-- [CST_Rc.b] ; carries=I
E_c [CST_Q1.C] --bind--> [CST_Rc.a] ; carries=I
E_ea [CST_Q1.E] <--bind--> [CST_Rc.b] ; carries=I
```

Collector current rides the **directed** bind `[CST_Q1.C]→[CST_Rc.a]`; resistor terminals **non-directed** on `a`/`b`; E↔Rc.b **bi-directed** when both directions are explicit. Omit E → truncated device / unowned KCL. Soft-validate: `$I_C$`/`$I_B$`/`$I_E$`/`$\beta$` ⊆ ports B,C,E + `beta=`; `$V_a$`/`$I_a$`/`$R$` ⊆ ports a,b + `R=`.

### Application note: relay SPDT (electronics instance)

**Instance only** — same grain as the BJT note. One **`CST`** owns coil + contact ports; galvanic isolation is **two domains on one NODE** (port attr `domain=coil` vs `domain=contact`), not a second kind. Contact path is **state-dependent bind**: `law=` states coil threshold, energised flag `s`, and COM–NO / COM–NC continuity; the live EDGE is whichever path is present; the agent **updates** that EDGE when `s` / `state=` flips — do **not** fake switching as EDGE-as-function.

Mutate create (teachable assign):

```text
+ CST [CST_K1] ; name=relay_spdt ; state=deenergised ; I_th=0.01 ; ports=A1: {side=in, domain=coil},A2: {side=in, domain=coil},COM: {side=inout, domain=contact},NO: {side=inout, domain=contact},NC: {side=inout, domain=contact} ; law=$I_{A1}=-I_{A2}$,$s=\mathbf{1}(\lvert I_{A1}\rvert>I_{th})$,$s=1\Rightarrow V_{\mathrm{COM}}=V_{\mathrm{NO}}\land I_{\mathrm{COM}}+I_{\mathrm{NO}}=0\land I_{\mathrm{NC}}=0$,$s=0\Rightarrow V_{\mathrm{COM}}=V_{\mathrm{NC}}\land I_{\mathrm{COM}}+I_{\mathrm{NC}}=0\land I_{\mathrm{NO}}=0$
+ E_coil [CST_Drv.out] --bind--> [CST_K1.A1] ; carries=I
+ E_ret [CST_K1.A2] --bind-- [CST_Gnd.a] ; carries=I
+ E_path [CST_K1.COM] --bind-- [CST_K1.NC] ; carries=I
```

Pin-map present after energise (`state=energised`; contact EDGE retargeted COM↔NO; warm slice omits idle V/I noise):

```text
CST [CST_K1] ; name=relay_spdt ; state=energised ; I_th=0.01 ; ports=A1: {side=in, domain=coil, V=12, I=0.02},A2: {side=in, domain=coil},COM: {side=inout, domain=contact},NO: {side=inout, domain=contact},NC: {side=inout, domain=contact} ; law=$I_{A1}=-I_{A2}$,$s=\mathbf{1}(\lvert I_{A1}\rvert>I_{th})$,$s=1\Rightarrow V_{\mathrm{COM}}=V_{\mathrm{NO}}\land I_{\mathrm{COM}}+I_{\mathrm{NO}}=0\land I_{\mathrm{NC}}=0$,$s=0\Rightarrow V_{\mathrm{COM}}=V_{\mathrm{NC}}\land I_{\mathrm{COM}}+I_{\mathrm{NC}}=0\land I_{\mathrm{NO}}=0$
E_coil [CST_Drv.out] --bind--> [CST_K1.A1] ; carries=I
E_ret [CST_K1.A2] --bind-- [CST_Gnd.a] ; carries=I
E_path [CST_K1.COM] --bind-- [CST_K1.NO] ; carries=I
```

**State / contact switching:** `s` is defined in the same `law=` list; `I_th` is a param; port subscripts A1/A2/COM/NO/NC match `ports=`. Live EDGE must match: `$s=1$` → `COM--NO`, `$s=0$` → `COM--NC`.

---

## 4. Wrong shapes (three)

- **Anything as EDGE law** — device FN on the arrow (`[A] --derives--> [B] ; law=$y=k x$`) **or** stuffing ideal-wire equations onto EDGE (`… --bind-- … ; law=$V_a=V_b$`). EDGE = bind or relation only; continuity is implied on bind; no equations on either grain.
- **Grain mismatch** — bare bind on law/physical CST (`[CST_Q1] --bind-- [CST_Rc]` — missing port grain); **or** port endpoints with a chart label (`[A.x] --knows--> [B.y]`); **or** mixed `[Node.port]` ↔ bare `[Node]`; **or** `--bind-->` / `--pipe-->` on bare person ids (use `--reports_to-->` / `--knows-->`).
- **Hollow nest with no behaviour leaf** — a shell without a node that owns `law=` or `pseudo=` (behaviour has nowhere to live). For person chart rows, no `law=` is fine — they are not behaviour leaves.

---

## 5. Pin map grain

Flat `depth` / `max_rows` alone fails at coarse → fine strata.

```text
pin_map(session, anchor, depth, max_rows, layer?=…, view?=shell|interior|flowchart|parts|statechart|persons|org|…)
```

(`shell|interior|…` above is API documentation “or”, not a wire list.)

1. Read shell (or current layer) — few rows.  
2. Reason / mutate at that grain.  
3. If blocked → one descend (re-anchor or `view=interior`).  
4. Ascend; do not keep nested shells in context.

`layer=` = abstraction stratum (project-chosen labels). Examples: **`layer=req`** — requirement CSTs + design binds; **`layer=arch`** — parts composition. Shell vs interior = **`view=`**, not a new atom. Other teachable **`view=`** grains (§3): `flowchart`, `parts`, `statechart`, `persons` / `org`. Do not invent a kind zoo per view — **`role=`** / **`view=`** only.

**Shell caps:** `view=flowchart` / `view=statechart` ≤ **8 NODEs** / ≤ **12 EDGEs**, or decision-only / one-hop. Prefer omit-default attrs and short `law=` on the warm slice.

**Goldfish:** re-read the current pin map each turn. Chat is not SSOT.

---

## 6. Migration (thin)

| Keep | Migrate into 1.x | Demote |
|------|------------------|--------|
| NODE\|EDGE store | Active stamps → node + `ports=` + `law=` | Formula-on-edge; maths hubs on wrong kinds |
| Write = display; pin_map caps | Flat self-loop `derives` → law on node; `connects` → `bind`; chart sense → relation label | Forever dual dialect; colon-pile port tokens; bare `--bind-->` for persons |
| Locator kinds (domain locators) | Non-directed `--bind--` / bi-directed `<--bind-->`; dual EDGE grains | Those kinds as formula hubs; braced `--{bind}-->`; `carries=` as fake relation name on bare ids |

Engine: law-on-node + dual EDGE → **1.0**, not a silent 0.3.x patch. Flat same-node `derives` in [`memnet-field-formulas.md`](memnet-field-formulas.md) = **transitional** only.

---

## 7. LLM cost & accuracy

**Verdict:** ontology (law on NODE; dual EDGE; `[Node.port]` bind vs bare-id relation; shell/interior) is sound for Write=display. The ranked cuts below are **applied** in this doc (not a wish-list).

| Axis | Finding |
|------|---------|
| **Tokens** | Locked bare `--label-->` (cheaper than demoted `--{label}-->` / `--(label)-->`). **Omit** `recycle=` unless non-default (session default covers it — default lines waste tokens). Port bags keep `side=`; skip unused attrs. Bind teach `bind` only (`pipe` synonym). Relation put sense in the label — no second `carries=` name. Relay `law=` stays the cautionary extreme — warm slice still short. |
| **Accuracy** | `{…}` = brace-group / record (ports primary; other attrs may take `{…}`, e.g. `meta={…}`). Nesting **capped at depth 2** — allow `meta={units={x=m,y=s}}`; reject depth 3+ (do **not** forbid nested bags outright). Soft-validate: `law=` symbols ⊆ ports∪params (optional lint). `role=`/`view=` only CST disambiguators. Dual EDGE: port↔port = bind; node↔node = relation; reject mixed endpoints. Sense: `carries=`/`event=` on bind; label on relation. |
| **Pin map** | Shell-first + re-anchor; flowchart/statechart shell ≤8/12 or decision-only. Warm BJT ~5 lines; relay omits idle V/I noise. |

**Ranked cuts — applied:**

1. **Omit `recycle=` by default** — session/engine default (typically `persistent`) covers it; emit only when non-default. Port bags keep required `side=`, skip empty/unused attrs. Examples already omit default `recycle=`.
2. **Dual EDGE labels** — bind: teach `bind` only (`pipe` synonym); sense via `carries=` / `event=`. Relation: label = sense on bare ids; demote `--bind-->` + `carries=` on persons.
3. **Soft-validate law symbols** — rule + optional thin lint (symbols ⊆ ports∪params); examples fixed (req `t`/`t_lim`; flowchart `x` port; Next `law=$y=x$`).
4. **Cap flowchart/statechart fan-out** — shell ≤8 NODEs / ≤12 EDGEs or decision-only; flowchart sketch trimmed to Dec+Yes+No.
5. **`role=` / `view=` only CST disambiguators** — no kind zoo; instances use `role=requirement` / `role=person`.
6. **Reject mixed endpoints** — soft-validate both ends same grain (port or bare); no port↔node EDGE.
7. **Brace nesting depth cap = 2** — allow one nested bag (`meta={units={x=m,y=s}}`); reject depth 3+; do **not** forbid nested `{a={…}}` outright. Grammar: one nested `recordBag` in `attrValue` ([`MemNetLayer.g4`](antlr/MemNetLayer.g4)).
8. **Brace-group discipline** — reject a closed domain-field allow-list. Teach: `{…}` = record of attrs; scalar `=` for singles; flat first; nest only to depth ≤2; no bag spam. Soft MUSTNOT bags on dialect keywords `law`/`pseudo`/`recycle`/`role`/`view`/`layer` (keyword denylist, not an allow-list). Replaces “allow-list which fields may take `{…}`”.

---

## 8. Open (three bullets max)

- **`ports=` / record attrs** — quantity keys and bag attrs vs params / `law=` idents still open; brace discipline + nesting depth=2 are locked.
- **When to mint first-class `PORT`** — only if a port must be an independent atom; default binds use `[Node.port]`.
- **Relation label vocabulary** — open set of `IDENT`s for now; optional SCHEMA / allow-list later (no flow type system here).

---

## 9. Related

| Path | Role |
|------|------|
| [`memnet-grammar-design.md`](memnet-grammar-design.md) | Shared dialect SSOT; §3 ≠ this doc |
| [`memnet-field-formulas.md`](memnet-field-formulas.md) | Flat `derives` (**transitional**); 1.x → law on node |
| [`../application-notes/examples/inverting-amplifier-memnet.md`](../application-notes/examples/inverting-amplifier-memnet.md) | Flat InvAmp today (electronics app note) |
| [`memnet-neighbourhood-reserve.md`](memnet-neighbourhood-reserve.md) | Reserve within active view |
| [`memnet-security-multi-agent.md`](memnet-security-multi-agent.md) | ACL before reserve |
| [`antlr/MemNetLayer.g4`](antlr/MemNetLayer.g4) | Proposed ANTLR4 for this slim dialect |

No change to `requirements.sysml` in this design task.
