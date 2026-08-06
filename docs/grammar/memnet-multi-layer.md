# Multi-layer MemNet (design, slim)

**Status:** design + **engine vertical slice (step 3)** — Layer codec / MutateGate /
store ports on NODE + dual EDGE (`src_port`/`dist_port`/`wire`) land in 0.3.x
additively; MCP `pin_map(view=)` and full formula-on-EDGE migration still target
**MemNet 1.x**.  
**Mission:** agent memory graph (any domain), Write = display, bounded `pin_map`, tokens — **not** MBSE.  
**Store:** **NODE | EDGE** only. No third AST primitive.  
**Mission freeze:** A only for named functions; teach `direc=` / `bind` / `view=` only; no B (`def=`/`uses=`/`role=lib`); no `CAP`/`contains=`/`carries=member`; membership = node↔node relation.

[`memnet-grammar-design.md`](memnet-grammar-design.md) §3 *Layering* = I/O / store / transport. This doc = **stratified pin-map product graph** (right grain without budget blow-up).

---

## 1. Ontology (absolute minimum)

| Atom | Role |
|------|------|
| **NODE** | Kinded fact. Law leaf: prefer kind **`CST`** (or any NODE with `law=` + `ports=`). Device / constitutive / causal laws live **only** here. Disambiguate with thin **`role=`** / pin-map **`view=`** — no kind zoo (`REQ`/`PER`/`FN` as law leaves). |
| **EDGE** | One store primitive, **two endpoint grains** (dual EDGE). **No** `law=` on EDGE. |

**Dual EDGE (locked):**

```text
port ↔ port  →  bind        (ideal connection; optional carries=)
node ↔ node  →  relation    (chart / semantic link; sense = label)
```

| Grain | Endpoints | Label | Sense |
|-------|-----------|-------|-------|
| **Bind** (ideal pipe) | Both `[Node.port]` | Teach **`bind`** only (`pipe` accept-only — do not teach) | Optional `carries=`; `event=`/`guard=` only with flowchart/statechart — **not** the label |
| **Relation** (chart / semantic) | Both bare `[NodeId]` | Relation name itself (`owns`, `knows`, `reports_to`, `member_of`, …) — open `IDENT`; no SCHEMA vocab now | **The label is the sense** — do not pile `carries=` as a second name |

Same three ASCII wire forms for both grains (bare `IDENT` between dashes; charset `[A-Za-z_][A-Za-z0-9_]*` — [`MemNetLayer.g4`](antlr/MemNetLayer.g4)):

| Form | Wire | Meaning |
|------|------|---------|
| Directed | `--label-->` | One-way — **primary teach** |
| Non-directed | `--label--` | Undirected (no arrowheads) |
| Bi-directed | `<--label-->` | Both directions explicit (≠ non-directed) — **accept; demote teach** |

```text
Eid [CST_Q1.C] --bind--> [CST_Rc.a] ; carries=token
Eid [CST_Alice] --knows--> [CST_Bob]
```

**Law leaf:** one shape. Put `law=` / params (`k=`, `gain=`, …) **on the node** (`CST`). `law=` is **LaTeX** (storage/display for the LLM — no evaluator required to render). Several equations → one field, `$…$` segments joined by `,` (same list joiner as `ports=`).

**Ideal bind:** port↔port EDGE is an ideal pipe — endpoints share the carried quantity as the domain defines (agent may rely on that continuity without EDGE `law=` text; further constraints stay on NODE laws or domain convention). Teach **`bind`** only; `pipe` accept-only (emit `bind`). Legacy `connects` → `bind`. Demote other labels on port-grain edges (`contains`, `refines`, …).

**Relation:** node↔node EDGE is a chart/semantic link. Label = relation name (open `IDENT`). Prefer directed form for asymmetric links (`reports_to`, `owns`, `member_of`); non-directed when the chart needs it. No inventing `self` / `reports` ports just to force bind grain.

**Ports:** fields on the law node. Entry = `name: {attr=val, …}` (labelled record bag — TS/YAML-style; not a call):

```text
ports=x: {direc=in, q=0},y: {direc=out},state: {direc=inout, q=$s$}
```

Attrs use the same `=` / `,` as elsewhere. Teach **`direc=`** only (`in` / `out` / `inout`); `direction=` accept-only — do not teach. Required in teachable bags. Other attrs are **domain quantities at/through the port** — omit when unused (no empty bags beyond `direc=`). Generic **`q=`** + named domain keys. No `FN`. Orientation lives in `law=` and port `direc=` on the **NODE**.

**`PORT` as first-class NODE:** **deferred / no** until forced (Open §8). Keep ports as fields; binds use `[Node.port]`.

**Nesting / membership:** no `CAP` / `contains=` / `carries=member`. Pin-map **shell vs interior** is a **view budget** (`view=shell` or `view=interior` / re-anchor), not a chapter of kinds. Prefer compact shell first; descend one step when blocked. Composition membership = **node↔node relation** (`--member_of-->` / `--member--`); outer ports still export via port↔port **bind**. See §3 parts note.

**Omit defaults (wire):** session/engine default covers `recycle=` (typically `persistent`) — **omit** `recycle=` on teachable mutate and pin_map lines unless the value is **non-default**. Same spirit for empty port attrs: `ports=x: {direc=in}` not `ports=x: {direc=in, q=}`.

**Endpoint lock:** `.` = ownership join inside `[…]` for bind. Prefer `[Node.port]` over EDGE `from=`/`to=` (hides grain). `{…}` = **brace-group / record** (`attr=val`, `,`-joined) — primary teachable use is port bags. **No** closed global allow-list of domain field names — prefer **author/agent discipline** below. Not on EDGE arrows. Demote braced `--{label}-->` and paren `--(label)-->`. `NEW` is mint-only, not a label. No `law=` on EDGE.

**Brace-group discipline (locked):** use `{…}` when the value is a **record of attrs**; use scalar `=` for a single value. Prefer flat attrs; nest only when needed (**depth ≤2**). Do **not** invent bag spam; do **not** promote `meta=`/`units=` teach. Soft MUSTNOT (keyword denylist, not an allow-list): dialect scalars `law` / `pseudo` / `recycle` / `role` / `view` stay STRING / IDENT / number / `$…$` — never bags. OK (instance-only, not teach): `meta={rev=1, src=doc}`; `units={x=m, y=s}`. Bad: `gain={k=2}` (single value → `gain=2`); `law={eq=$V=IR$}`.

**MUSTNOT:** mix endpoints (`[Node.port]` ↔ bare `[Node]`); put `law=` on an EDGE; treat **bind** as a **relation** (or vice versa — do not teach `--bind-->` on bare person ids, and do not use chart labels on port-grain pipes); treat EDGE as a function or multi-port device; invent causality on a bind; confuse non-directed with bi-directed; use `:` for scalars (`direc:in` — use `direc=in`); omit `:` on name-to-bag (`ports=x={…}` — use `ports=x: {…}`); pile port facts as `name:direc:value` colon chains; put braces or attrs on the arrow label; invent new KINDs instead of thin `role=` / `view=`; bag dialect keywords (`law`/`pseudo`/`recycle`/`role`/`view`); mint `CAP` / `contains=` / `carries=member`; teach `def=`/`uses=`/`role=lib` (B removed).

---

## 2. Syntax (cheat sheet)

**Spine** = shared dialect Write=display ([`memnet-grammar-design.md`](memnet-grammar-design.md) §4–5; **in engine** — directed only today). **1.x overlays** below (`ports=` / `law=` / `pseudo=` / dual EDGE / three wire forms / stratified `view`) = **proposed-1.x**, not in 0.3.x.

### Delimiters (locked)

| Char | Role |
|------|------|
| `;` | **Only** top-level field separator on a line |
| `=` | Assign a **value** to a **key** — top-level `key=value` (present / create); `+=` / `-=` only on `~`; attrs inside `{…}` (`direc=in`). Scalars stay `=` — **no** `key: value` |
| `,` | **Sole** list joiner inside a field value (`ports=` entries, attrs in `{…}`, multi-eq `law=`, …) |
| `:` | Bind a **name** to a **brace-group** only: `name: {…}` (inside `ports=` list). **Not** scalar assign; **not** `x={…}` without `:` |
| `{` `}` | **Brace-group / record** — `attr=val` pairs, `,`-joined. Primary teach: port bags after `name:` (`x: {direc=in, q=0}`). Discipline: bag = record of attrs; scalar `=` for singles; nest only to depth ≤2; no bag spam. Soft MUSTNOT bags on `law`/`pseudo`/`recycle`/`role`/`view`. Not on EDGE arrows |
| `.` | Ownership join inside `[…]` for EDGE endpoints: `[NodeId.PortName]` |
| `$…$` | LaTeX inline math **only** (not a field separator); Dirac bra-ket lives here (prefer `\langle`/`\rangle`) |
| `[` `]` | Wrap Id, mint `NEW`, or qualified port ref `NodeId.PortName` |
| `--` `-->` | **Directed** EDGE: `--label-->` (bare `IDENT` between dashes; no spaces) |
| `--` `--` | **Non-directed** EDGE: `--label--` |
| `<--` `-->` | **Bi-directed** EDGE: `<--label-->` — accept; demote teach |
| `"` | STRING for awkward values (shared dialect) |
| `+` `~` `-` | Mutate ops (create / update / drop) — line prefix only |
| `#` | Line comment to end of line (fixtures / notes; skipped by lexer) |

**`=` vs `:` (locked):** `=` assigns values to keys (fields and bag attrs). `:` binds a name to a brace-group only (`name: {…}`). Good: `ports=x: {direc=in}`. Bad: `ports=x={direc=in}` or `{direc:in}`.

**Defaults:** omit `recycle=` on wire unless non-default — session/engine default (typically `persistent`) already covers it.

**Record vs EDGE:** `{…}` = brace-group / record value. Primary teach: labelled port bags (`IDENT: {…}` inside `ports=`). Nested bags **max depth = 2** — reject deeper; do not promote `meta=`/`units=` teach. EDGE wire = bare `--label-->` / `--label--` / `<--label-->` after endpoint `]`. Grain from endpoints: both `.port` → bind; both bare → relation. `()` is **free** (held for later; not used on arrows).

No wire `|`. Query enums (`view=shell` or `interior`) are exclusive choices, not joined lists. Prefer `\lvert`/`\rvert` over bare `|` inside maths; if a value contains `;` or a list-joining `,` that is not a segment boundary, quote the whole field: `law="…"`. Same STRING rule for **`pseudo=`** bodies — quote the whole value: `pseudo="…"`. No new punct for algorithms.

### Delimiter inventory (used vs free)

| Status | Characters | Notes |
|--------|------------|--------|
| **Used** | `;` `,` `=` `{` `}` `[` `]` `.` `:` `$` `"` `#` `+` `~` `-` `@` | Fields; brace-group records; ids; ownership; LaTeX; STRING; comment; mutate; `@ident` alias |
| **Used (arrow compounds)** | `--` `-->` `<--` | Dual EDGE wires; bare `IDENT` label between dashes |
| **Demoted / avoid** | `\|` | No wire pipe; prefer `\lvert`/`\rvert` in maths; demote bare `x{…}` / `x(…)` ports; demote braced `--{label}-->` and paren `--(label)-->` |
| **Free (held)** | `(` `)` `&` `*` `^` `!` `?` `` ` `` `%` `'` `\` | `()` fully free (not binds); others held |

**Collisions (do not reassign):** `$` = LaTeX `law=` / attr maths; `<` `>` = EDGE arrow direction marks; `.` = `[Node.port]` and `port.qty` in `law=`; `=` = value assign; `:` = name-to-bag **only**; `{…}` = brace-group / record; `@` = declare alias as bag quantity value (`V=@va`) and **repeat `@va` inside** `$…$` law — not free text.

**Sparing recommendations (0–2):**

1. **Keep `#` as line comment only** — already matches `MemNet.g4` / layer grammar.
2. **No new punct for EDGE sugar** — port `name: {attrs}` + `--label-->` cover bind/relation; `@` reserved for bag quantity aliases; hold `&` `*` `^` `!` `?` `` ` ``.

### Generic skeleton

```text
CST [Id] ; name=… ; ports=name: {direc=…, q=…},… ; law=$eq$,$eq$ ; param=…
Eid [Id.port] --bind--> [Id.port]
Eid [Id.port] --bind-- [Id.port]
Eid [NodeA] --rel_name--> [NodeB]
```

`ports=` entries are `,`-joined `name: {…}` labelled records on the NODE. Bind endpoints name those ports as `[NodeId.PortName]`. Relation endpoints are bare `[NodeId]`; label = relation name. `law=` holds LaTeX maths on the NODE only. Omit session-default `recycle=persistent`. Optional `carries=` on binds when useful — **not** mandatory on every teach line.

### `law=` expression rules (LaTeX)

- **Where:** one `law=` field on the **NODE** (prefer kind `CST`). **Never** on EDGE — bind implies continuity; relation is a chart link; do not teach equations on the arrow. **Proposed-1.x** — store/show the LaTeX string for agents; no render/eval engine required.
- **Wire:** each equation is **inline math** wrapped in `$…$`. Multi-eq: join those `$…$` segments with `,` (same joiner as `ports=`). Function and equation are the same shape — no `FN` kind; optional causality via port `direc=` only.
- **Dirac:** bra-ket is a full citizen of `law=` maths — e.g. `law=$\langle\phi|\psi\rangle$`. Lives **only** inside `$…$`; do **not** conflate with EDGE arrowheads `<--` / `-->`.
- **Quantity symbols (two OK forms, locked):**
  1. **Alias (primary teach, in-NODE):** bag declares `V=@v1, I=@i1`; law **keeps `@`** — e.g. `$@v1 = @i1 \times R$`. `@ident` as bag quantity-key **value** only; same spelling inside `$…$`.
  2. **Qualified (`port.qty`) — secondary:** when multi-qty ports need clarity or the slice is small — e.g. `$pin1.V = pin1.I * R$`. Not equal dual teach.
- **Completeness (soft-validate):** every quantity symbol in `law=` MUST ∈ this NODE’s ports ∪ params ∪ `@` aliases (also `{port.qty}` / bare port name under single-quantity discipline). No orphan bare `V`/`I` on multi-qty ports. Demote pretty-only `$V_{\mathrm{pin1}}$` for lint. Agents SHOULD fix before settle.
- **Binding (same node):** math idents resolve to (1) **params** (`k=`, `beta=` ← `\beta`, `R=`, …), (2) an **`@alias`** declared as a quantity-key value and repeated with `@` in `law=`, (3) **`port.qty`** ASCII matching `ports=` name + bag attr, or (4) a **bare port name** under single-quantity discipline. **MUSTNOT** orphan bare `V` / `I` unless that single-port discipline holds; **MUSTNOT** `@spam` outside bag quantity values.
- **Alias scope (locked):** `@ident` lives on the **owning NODE**. Two nodes may both use `@va` without clash; each `law=` sees only that node’s `@` set ∪ params ∪ local ports. Cross-node coupling is via **port binds**, **not** a shared `@` namespace. Need a global name → use **`port.qty`** or distinct aliases by discipline. **No** automatic merge of `@`.
- **Alias naming (discipline, not SCHEMA-hard):** grammar accepts any free `IDENT` after `@`. Prefer unique-in-slice aliases when several NODEs appear together; short `@va` / `@ia` **within one NODE** only; `port.qty` when the slice is small (skip `@`).
- **MUSTNOT:** ASCII-only ad-hoc `expr=` on EDGE; `law=` on bind or relation; fake `derives`/`feeds` as the 1.x law surface (transitional: [`memnet-field-formulas.md`](memnet-field-formulas.md)); call-in-`law=` via `def=`/`uses=` (B removed — use A).

### Named functions in `law=` (A only)

Want `z = sum(x, y) = x + y` reusable? **A only** — function as CST (composition / bind). **Never** put the function on an EDGE. **B removed** (`def=` / `uses=` / call-in-`law=` / `role=lib` — do not teach; soft denylist no longer lists them as dialect bags).

**A — Function as CST (composition / bind).** Graph-honest: the formula is a law leaf with ports; callers **bind** ports. No call syntax in `law=`. Prefer **A** for composition, multi-port devices, and anything that should survive off-slice.

```text
        [Caller]
       /   |    \
   .a      .b     .out
    |      |       ^
    v      v       |
  [Sum.x][Sum.y] [Sum.z]
      \    |    /
       [CST_Sum]
```

```text
CST [CST_Sum] ; ports=x: {direc=in, q=@sx},y: {direc=in, q=@sy},z: {direc=out, q=@sz} ; law=$@sz=@sx+@sy$
CST [CST_Caller] ; ports=a: {direc=out, q=@sx},b: {direc=out, q=@sy},out: {direc=in, q=@sz}
E1 [CST_Caller.a] --bind--> [CST_Sum.x]
E2 [CST_Caller.b] --bind--> [CST_Sum.y]
E3 [CST_Sum.z] --bind--> [CST_Caller.out]
```

LaTeX macros (`$y=\mathrm{clip}(x,lo,hi)$`) are ordinary law maths — not a named-function call. Informal steps stay in `pseudo=`.

### Line shapes

| Shape | Form |
|-------|------|
| NODE (pin map / bare) | `KIND [Id] ; key=value ; …` |
| EDGE bind (port grain) | `Eid [Node.port] --bind--> [Node.port] ; …` (also `--bind--`; bi-directed accept / demote teach) |
| EDGE relation (node grain) | `Eid [NodeA] --rel_name--> [NodeB] ; …` (label = sense; bare ids only) |
| Create | `+ KIND [NEW\|Id] ; …` · `+ [NEW\|Eid]? [Node.port] --bind-- [Node.port] ; …` · or relation `--owns-->` / … |
| Update | `~ [Id] ; …` · `~ Eid ; …` · on `~` only: `key+=N` / `key-=N` |
| Drop | `- Eid` |

Pin map = **bare present** (no leading `+`/`~`/`-`). Ops are mutate-only. In the Create row, `\|` is documentation “or”, not a wire delimiter.

### Field forms (this doc)

| Field | Form |
|-------|------|
| `ports=` | `name: {direc=…, …}`, `,`-joined — omit attrs beyond needed `direc=` / quantities |
| `law=` | LaTeX `$…$` atom(s) on the **NODE** only; several → one field, `$eq$` segments `,`-joined — **forbidden** on EDGE |
| `pseudo=` | optional algorithmic steps as a STRING on the **NODE** (prefer quoted); programme/code-shaped behaviour only — not LaTeX; not an evaluator — see §3 |
| `name=` | short label |
| `role=` | thin CST disambiguator only (`requirement`, `person`, …) — **not** a new KIND; **no** `lib`; no zoo |
| `state=` | deferred — instance-only with `view=statechart`; not general teach |
| params | domain keys **on the NODE** (`k=`, `gain=`, `I_th=`, …) |
| `carries=` | **optional** on **bind** forms; generic quantity/token name — **not** mandatory; **not** on relation grain; **no** `carries=member` |
| `event=` / `guard=` | deferred — bind metadata only with flowchart/statechart; **not** `law=` |
| `recycle=` | **omit** unless non-default — session/engine default is typically `persistent` |
| `view=` | pin-map grain (`shell`/`interior`; also `flowchart` / `parts` / `statechart`) — query/envelope; not ontology. Teach **`view=`** only — do not teach `layer=` as a peer axis |

### Port token (`ports=`)

```text
x: {direc=in, q=0}
```

| Part | Meaning |
|------|---------|
| `x` | Port **name** (ties to symbols in `law=`) |
| `:` | Bind name to brace-group only (prefer one space after) |
| `{…}` | Brace-group / record: `attr=val` pairs, `,`-joined |
| `direc=` | Required in teachable bags: `in` / `out` / `inout`. Teach **`direc=`** only; `direction=` accept-only. **MUSTNOT** `direc:in` |
| other attrs | Domain quantities (generic `q=` or named keys); numeric present or `@alias` value; omit when unused |

Teach **always** `name: {…}` inside `ports=` (prefer one space after `:`; at least `direc=`). Demote `x={…}`, bare `x{…}`, and `x(…)`. Bare `name` without `: {…}` is not a port entry. List joiner between ports stays `,`.

**Electronics instance (not core):** an IC pin is **one** port with **two** quantities — voltage **at** the pin (`V`) and current **through** it (`I`). Do **not** split V and I into two ports. Sign of `I` follows `direc=` / device `law=`. Alias primary; qualified secondary:

```text
# alias (primary teach — @ in bag and in law)
CST [CST_Pin] ; name=pin_load ; R=50 ; ports=pin1: {direc=inout, V=@v1, I=@i1} ; law=$@v1 = @i1 \times 50ohm$
# qualified (secondary — multi-qty / clarity)
CST [CST_Pin] ; name=pin_load ; R=1000 ; ports=pin1: {direc=inout, V=0, I=0} ; law=$pin1.V = pin1.I * R$
```

Two nodes + one bind — scope allows reuse of `@va`, but prefer unique-in-slice names:

```text
CST [CST_Src] ; name=Vs ; ports=p: {direc=out, V=@va_S, I=@ia_S} ; law=$@va_S=5$
CST [CST_R] ; R=50 ; ports=a: {direc=in, V=@va_R, I=@ia_R} ; law=$@va_R=@ia_R*R$
E1 [CST_Src.p] --bind-- [CST_R.a]
```

Generic bags stay domain-free (`q=` or other named quantities); `V`/`I` are the electronics spelling of across + through.

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

Both ends MUST be qualified. Optional `carries=` (not mandatory). Label teach **`bind`** only. Rejected: `from=`/`to=`; bare `[CST_Q1]--bind--[CST_Rc]` without port grain; chart relation labels on port endpoints.

**Relation (node grain):**

```text
[CST_Alice]
```

Both ends MUST be bare node ids. Label = relation name (`knows`, `reports_to`, `member_of`, …) — open `IDENT`. Sense is the label — do not teach `carries=`. Rejected: mixed `[Alice]` ↔ `[Bob.port]`; `--bind-->` on bare person ids.

Label / grain rules: §1 **Dual EDGE**.

---

## 3. Generic sketch, then domain instance

**Lead (any domain)** — abstract CST with ports, law, and binds:

```text
CST [CST_Blk] ; name=block ; k=2 ; ports=x: {direc=in, q=1.0},y: {direc=out} ; law=$y=k x$
CST [CST_Next] ; name=next ; ports=x: {direc=in},y: {direc=out} ; law=$y=x$
E1 [CST_Blk.y] --bind--> [CST_Next.x]
```

Mutate (mint):

```text
+ CST [NEW] ; name=block ; k=2 ; ports=x: {direc=in, q=1.0},y: {direc=out} ; law=$y=k x$
```

A **bind** does **not** own `law=` or device params; it is an ideal pipe that names the ports it joins (optional `carries=`). A **relation** names two nodes and puts sense in the label.

### Application note: pipeline stage (programme instance)

**Instance only** — same ontology as any other CST. A **programme** here is a module/service stage with **ports** as data or control endpoints — not volts/amps, and not a SysML clone. Kind stays **`CST`**; `law=` is the behavioural contract. Agents use this grain on `pin_map`, not to execute code.

Mutate create (teachable assign) — z-score stage then threshold gate:

```text
+ CST [CST_Norm] ; name=zscore ; mu=0 ; sigma=1 ; ports=x: {direc=in},y: {direc=out} ; law=$y=(x-\mu)/\sigma$
+ CST [CST_Gate] ; name=threshold ; t=0.5 ; ports=x: {direc=in},y: {direc=out} ; law=$y=\mathbf{1}(x>t)$
+ E_ng [CST_Norm.y] --bind--> [CST_Gate.x] ; carries=token
```

Pin-map present (same facts, no leading `+`):

```text
CST [CST_Norm] ; name=zscore ; mu=0 ; sigma=1 ; ports=x: {direc=in},y: {direc=out} ; law=$y=(x-\mu)/\sigma$
CST [CST_Gate] ; name=threshold ; t=0.5 ; ports=x: {direc=in},y: {direc=out} ; law=$y=\mathbf{1}(x>t)$
E_ng [CST_Norm.y] --bind--> [CST_Gate.x] ; carries=token
```

`x`/`y` are data ports; the directed bind is an ideal pipe (`carries=token` optional here for stream sense). Norm: `$y=(x-\mu)/\sigma$` with params `mu=`/`sigma=`. Gate: `$y=\mathbf{1}(x>t)$` with param `t=`.

### Application note: requirements view (agent memory)

**Instance only** — bounded pin-map slice of requirement memory, **not** a SysML / MBSE requirements module. Prefer kind **`CST`** with `role=requirement`. Existing TagMap **`REQ`** stays a **SysML locator** pin; **`CLM`** stays soft claims/decisions. Traceability is an **ideal bind** between ports (`carries=trace` optional), not a chart relation and not `law=` on the arrow. Port names carry the roles (`stake` / `design` / optional `verify`).

Mutate create (one requirement CST bound to a programme stage port):

```text
+ CST [CST_R_lat] ; role=requirement ; name=cmd_latency ; ports=stake: {direc=in, q=$t$},design: {direc=out} ; t_lim=10 ; law=$t<t_{\mathrm{lim}}\,\mathrm{ms}$
+ CST [CST_Gate] ; name=threshold ; t=0.5 ; ports=x: {direc=in},y: {direc=out} ; law=$y=\mathbf{1}(x>t)$
+ E_tr [CST_R_lat.design] --bind--> [CST_Gate.x] ; carries=trace
```

Pin-map present (anchor on `CST_R_lat`):

```text
CST [CST_R_lat] ; role=requirement ; name=cmd_latency ; ports=stake: {direc=in, q=$t$},design: {direc=out} ; t_lim=10 ; law=$t<t_{\mathrm{lim}}\,\mathrm{ms}$
CST [CST_Gate] ; name=threshold ; t=0.5 ; ports=x: {direc=in},y: {direc=out} ; law=$y=\mathbf{1}(x>t)$
E_tr [CST_R_lat.design] --bind--> [CST_Gate.x] ; carries=trace
```

Symbols `$t$` / `t_lim` ⊆ ports∪params.

### Application note: pseudocode (programme steps)

**Instance only** — agent memory of algorithmic steps, **not** a programming language or runtime. Kind stays **`CST`** with in/out ports. Steps live in optional **`pseudo=`** (quoted STRING) for programme/code-shaped behaviour; keep **`law=`** for the formal contract / postcondition (LaTeX). Do **not** overload `law=` with code text. Prefer one CST over a chain of step NODEs. EDGE remains ideal bind into/out of ports — no control-flow on the arrow.

Mutate create (clamp stub):

```text
+ CST [CST_Clamp] ; name=clamp ; lo=0 ; hi=1 ; ports=x: {direc=in},y: {direc=out} ; pseudo="if x<lo then y:=lo elif x>hi then y:=hi else y:=x" ; law=$y=\mathrm{clip}(x,lo,hi)$
```

Pin-map present (same facts, no leading `+`):

```text
CST [CST_Clamp] ; name=clamp ; lo=0 ; hi=1 ; ports=x: {direc=in},y: {direc=out} ; pseudo="if x<lo then y:=lo elif x>hi then y:=hi else y:=x" ; law=$y=\mathrm{clip}(x,lo,hi)$
```

Quote `pseudo="…"` whenever the body would collide with `;` or list `,`. Optional: omit `law=` when only informal steps are known. `\mathrm{clip}(…)` is LaTeX in `law=` — not a call-in-`law=` sugar.

### Application note: flowchart (control flow)

**Instance only** — agent memory of control flow, **not** a flowchart language. Steps and decisions are **`CST`** nodes with ports; arrows are **ideal binds**. Decision = one CST with ports matching `law=` symbols and `yes` / `no` exits. Pin-map grain: **`view=flowchart`**.

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
+ CST [CST_Dec] ; name=ok ; ports=x: {direc=in},yes: {direc=out},no: {direc=out} ; law=$x>0$
+ CST [CST_Yes] ; name=path_yes ; ports=in: {direc=in}
+ CST [CST_No] ; name=path_no ; ports=in: {direc=in}
+ E_dy [CST_Dec.yes] --bind--> [CST_Yes.in]
+ E_dn [CST_Dec.no] --bind--> [CST_No.in]
```

Pin-map present (`view=flowchart` shell — 3 NODEs / 2 EDGEs):

```text
CST [CST_Dec] ; name=ok ; ports=x: {direc=in},yes: {direc=out},no: {direc=out} ; law=$x>0$
CST [CST_Yes] ; name=path_yes ; ports=in: {direc=in}
CST [CST_No] ; name=path_no ; ports=in: {direc=in}
E_dy [CST_Dec.yes] --bind--> [CST_Yes.in]
E_dn [CST_Dec.no] --bind--> [CST_No.in]
```

Predicate stays on the decision **NODE** (`law=` / optional `pseudo=`). EDGE remains ideal bind only. `event=`/`guard=` stay deferred with this view (Open §8). Start/End chains live in interior after re-anchor.

### Application note: parts architecture (composition)

**Instance only** — composition without a `CAP` metamodel. Parent and children are **`CST`**. Membership = **node↔node relation** (`--member_of-->` / `--member--`) — **not** port bind with `carries=member`; no `contains=`. Outer ports export by binding parent ports to child ports. Pin-map grain: **`view=parts`**.

ASCII (box with two children):

```text
+---------- CST_Box ----------+
|  [A.x]--bind-->[B.x]        |
|    ^                 |      |
|  Box.in            Box.out  |
+-----------------------------+
  membership: Box --member_of--> A / B   (relation grain)
```

Mutate create:

```text
+ CST [CST_Box] ; name=box ; ports=in: {direc=in},out: {direc=out}
+ CST [CST_A] ; name=child_a ; ports=x: {direc=in},y: {direc=out} ; law=$y=x$
+ CST [CST_B] ; name=child_b ; ports=x: {direc=in},y: {direc=out} ; law=$y=x$
+ E_ma [CST_A] --member_of--> [CST_Box]
+ E_mb [CST_B] --member_of--> [CST_Box]
+ E_xin [CST_Box.in] --bind--> [CST_A.x]
+ E_ab [CST_A.y] --bind--> [CST_B.x]
+ E_out [CST_B.y] --bind--> [CST_Box.out]
```

Pin-map present (`view=parts`):

```text
CST [CST_Box] ; name=box ; ports=in: {direc=in},out: {direc=out}
CST [CST_A] ; name=child_a ; ports=x: {direc=in},y: {direc=out} ; law=$y=x$
CST [CST_B] ; name=child_b ; ports=x: {direc=in},y: {direc=out} ; law=$y=x$
E_ma [CST_A] --member_of--> [CST_Box]
E_mb [CST_B] --member_of--> [CST_Box]
E_xin [CST_Box.in] --bind--> [CST_A.x]
E_ab [CST_A.y] --bind--> [CST_B.x]
E_out [CST_B.y] --bind--> [CST_Box.out]
```

No `contains=` field, no `CAP` kind, no `carries=member`. Shell vs interior still uses `view=shell` / `view=interior` (§5).

### Application note: statechart (states + transitions)

**Instance only / deferred teach** — agent memory of discrete behaviour when `view=statechart` remains. Prefer **one CST per state** with ports `enter` / `exit`. Transitions = **directed** ideal binds between state ports. `event=` / optional `guard=$…$` = bind metadata **only with this view** — **not** `law=` on EDGE; not general teach. Optional `state=` on NODE — instance-only with this view. Optional action/entry steps: `pseudo=` on the state CST. Honour the §3 flowchart **shell cap** (≤8 NODEs / ≤12 EDGEs).

ASCII (Idle ↔ Run):

```text
  [Idle] --event=start--> [Run]
    ^                      |
    +----- event=stop -----+
```

Mutate create:

```text
+ CST [CST_Idle] ; name=idle ; ports=enter: {direc=in},exit: {direc=out}
+ CST [CST_Run] ; name=run ; ports=enter: {direc=in},exit: {direc=out}
+ E_start [CST_Idle.exit] --bind--> [CST_Run.enter] ; event=start
+ E_stop [CST_Run.exit] --bind--> [CST_Idle.enter] ; event=stop
```

Pin-map present (`view=statechart` — 2 NODEs / 2 EDGEs):

```text
CST [CST_Idle] ; name=idle ; ports=enter: {direc=in},exit: {direc=out}
CST [CST_Run] ; name=run ; ports=enter: {direc=in},exit: {direc=out}
E_start [CST_Idle.exit] --bind--> [CST_Run.enter] ; event=start
E_stop [CST_Run.exit] --bind--> [CST_Idle.enter] ; event=stop
```

Guarded transition (thin): keep `guard=$…$` on the bind as metadata; if the guard needs ports or `pseudo=`, mint a tiny junction CST — do **not** put device `law=` on the EDGE.

### Application note: persons / relation chart

**Instance only** — org chart, family, or collaborator graph for **agent pin_map** — **not** a social-network product; **not** a first-class `view=` enum. Prefer light **`CST`** with `role=person` (no `law=` / `ports=` required for chart rows). Slice via anchor / relation neighbourhood — not special `view=persons` / `view=org` teach.

**Locked split (dual EDGE):**

| Domain | EDGE grain | Endpoints | Label |
|--------|------------|-----------|-------|
| Physical / programme / law CST | **Bind** | `[Node.port]` | `bind` |
| Persons / org / family chart | **Relation** | bare `[PersonA]` / `[PersonB]` | relation name (`reports_to`, `knows`, …) |

Do **not** generalise bare-id relations back onto BJT / pipeline port pipes. Do **not** invent `self`/`reports`/`knows` ports to force bind grain. Sense = label; no `carries=` duplicate.

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

Pin-map present (anchor on `CST_Alice`):

```text
CST [CST_Boss] ; role=person ; name=Boss
CST [CST_Alice] ; role=person ; name=Alice
CST [CST_Bob] ; role=person ; name=Bob
E_ra [CST_Alice] --reports_to--> [CST_Boss]
E_kb [CST_Alice] --knows--> [CST_Bob]
```

Team membership (thin): bare-id relation `--member_of-->` / `--member--` (same grain as parts membership). Keep the slice small.

### Application note: resistor (electronics instance — tiny)

**Instance only** — each terminal is one port holding `V` (at) and `I` (through); Ohm’s law + KCL on the NODE. Alias form (keep `@` in `law=`):

```text
+ CST [CST_R] ; R=50 ; ports=a: {direc=inout, V=@va, I=@ia},b: {direc=inout, V=@vb, I=@ib} ; law=$@va-@vb=@ia*R$,$@ia=-@ib$
```

Pin-map present (qualified form also OK — `$a.V-b.V=a.I*R$`):

```text
CST [CST_R] ; R=50 ; ports=a: {direc=inout, V=@va, I=@ia},b: {direc=inout, V=@vb, I=@ib} ; law=$@va-@vb=@ia*R$,$@ia=-@ib$
```

### Application note: BJT + resistor (electronics instance)

**Instance only** — not the default frame. Kind stays **`CST`** (no `FN`). Electrical attr keys (`V`, `I`) and `beta=` are domain spellings; each pin is one port (across + through). Mutate create (teachable assign):

```text
+ CST [CST_Q1] ; name=bjt_npn ; beta=100 ; ports=B: {direc=in, V=0.7, I=0.001},C: {direc=out, V=5, I=0.1},E: {direc=inout, V=0, I=-0.101} ; law=$I_C=\beta I_B$,$I_E=I_B+I_C$
+ CST [CST_Rc] ; name=Rc ; R=1000 ; ports=a: {direc=inout, V=0, I=0},b: {direc=inout, V=0, I=0} ; law=$V_a-V_b=I_a R$,$I_a=-I_b$
+ E_c [CST_Q1.C] --bind--> [CST_Rc.a] ; carries=I
```

Pin-map present (same facts, no leading `+`):

```text
CST [CST_Q1] ; name=bjt_npn ; beta=100 ; ports=B: {direc=in, V=0.7, I=0.001},C: {direc=out, V=5, I=0.1},E: {direc=inout, V=0, I=-0.101} ; law=$I_C=\beta I_B$,$I_E=I_B+I_C$
CST [CST_Rc] ; name=Rc ; R=1000 ; ports=a: {direc=inout, V=5, I=0.1},b: {direc=inout, V=0, I=-0.1} ; law=$V_a-V_b=I_a R$,$I_a=-I_b$
E_ab [CST_Rc.a] --bind-- [CST_Rc.b] ; carries=I
E_c [CST_Q1.C] --bind--> [CST_Rc.a] ; carries=I
E_ea [CST_Q1.E] --bind-- [CST_Rc.b] ; carries=I
```

Collector current rides the **directed** bind `[CST_Q1.C]→[CST_Rc.a]`; resistor terminals **non-directed** on `a`/`b`. Bi-directed form accepted when both directions are explicit — demote teach (use directed / non-directed in teach lines). Soft-validate: `$I_C$`/`$I_B$`/`$I_E$`/`$\beta$` ⊆ ports B,C,E + `beta=`; `$V_a$`/`$I_a$`/`$R$` ⊆ ports a,b + `R=`.

### Application note: relay SPDT (electronics instance)

**Instance only** — same grain as the BJT note. One **`CST`** owns coil + contact ports; galvanic isolation is **two domains on one NODE** (port attr `domain=coil` vs `domain=contact`), not a second kind. Contact path is **state-dependent bind**: `law=` states coil threshold, energised flag `s`, and COM–NO / COM–NC continuity; the live EDGE is whichever path is present; the agent **updates** that EDGE when `s` flips — do **not** fake switching as EDGE-as-function. Present `state=` here is instance cue only (same deferred family as statechart).

Mutate create (teachable assign):

```text
+ CST [CST_K1] ; name=relay_spdt ; state=deenergised ; I_th=0.01 ; ports=A1: {direc=in, domain=coil},A2: {direc=in, domain=coil},COM: {direc=inout, domain=contact},NO: {direc=inout, domain=contact},NC: {direc=inout, domain=contact} ; law=$I_{A1}=-I_{A2}$,$s=\mathbf{1}(\lvert I_{A1}\rvert>I_{th})$,$s=1\Rightarrow V_{\mathrm{COM}}=V_{\mathrm{NO}}\land I_{\mathrm{COM}}+I_{\mathrm{NO}}=0\land I_{\mathrm{NC}}=0$,$s=0\Rightarrow V_{\mathrm{COM}}=V_{\mathrm{NC}}\land I_{\mathrm{COM}}+I_{\mathrm{NC}}=0\land I_{\mathrm{NO}}=0$
+ E_coil [CST_Drv.out] --bind--> [CST_K1.A1] ; carries=I
+ E_ret [CST_K1.A2] --bind-- [CST_Gnd.a] ; carries=I
+ E_path [CST_K1.COM] --bind-- [CST_K1.NC] ; carries=I
```

Pin-map present after energise (`state=energised`; contact EDGE retargeted COM↔NO; warm slice omits idle V/I noise):

```text
CST [CST_K1] ; name=relay_spdt ; state=energised ; I_th=0.01 ; ports=A1: {direc=in, domain=coil, V=12, I=0.02},A2: {direc=in, domain=coil},COM: {direc=inout, domain=contact},NO: {direc=inout, domain=contact},NC: {direc=inout, domain=contact} ; law=$I_{A1}=-I_{A2}$,$s=\mathbf{1}(\lvert I_{A1}\rvert>I_{th})$,$s=1\Rightarrow V_{\mathrm{COM}}=V_{\mathrm{NO}}\land I_{\mathrm{COM}}+I_{\mathrm{NO}}=0\land I_{\mathrm{NC}}=0$,$s=0\Rightarrow V_{\mathrm{COM}}=V_{\mathrm{NC}}\land I_{\mathrm{COM}}+I_{\mathrm{NC}}=0\land I_{\mathrm{NO}}=0$
E_coil [CST_Drv.out] --bind--> [CST_K1.A1] ; carries=I
E_ret [CST_K1.A2] --bind-- [CST_Gnd.a] ; carries=I
E_path [CST_K1.COM] --bind-- [CST_K1.NO] ; carries=I
```

**State / contact switching:** `s` is defined in the same `law=` list; `I_th` is a param; port subscripts A1/A2/COM/NO/NC match `ports=`. Live EDGE must match: `$s=1$` → `COM--NO`, `$s=0$` → `COM--NC`.

---

## 4. Wrong shapes (three)

- **Anything as EDGE law** — device FN on the arrow (`[A] --derives--> [B] ; law=$y=k x$`) **or** stuffing ideal-wire equations onto EDGE (`… --bind-- … ; law=$V_a=V_b$`). EDGE = bind or relation only; continuity is implied on bind; no equations on either grain.
- **Grain mismatch** — bare bind on law/physical CST (`[CST_Q1] --bind-- [CST_Rc]` — missing port grain); **or** port endpoints with a chart label (`[A.x] --knows--> [B.y]`); **or** mixed `[Node.port]` ↔ bare `[Node]`; **or** `--bind-->` on bare person ids (use `--reports_to-->` / `--knows-->`); **or** membership as `carries=member` bind (use node↔node relation).
- **Hollow nest with no behaviour leaf** — a shell without a node that owns `law=` or `pseudo=` (behaviour has nowhere to live). For person chart rows, no `law=` is fine — they are not behaviour leaves.

---

## 5. Pin map grain

Flat `depth` / `max_rows` alone fails at coarse → fine strata.

```text
pin_map(session, anchor, depth, max_rows, view?=shell|interior|flowchart|parts|statechart|…)
```

(`shell|interior|…` above is API documentation “or”, not a wire list.)

1. Read shell — few rows.  
2. Reason / mutate at that grain.  
3. If blocked → one descend (re-anchor or `view=interior`).  
4. Ascend; do not keep nested shells in context.

Teach **`view=`** only (one grain axis). Shell vs interior = **`view=`**, not a new atom. Teachable grains: `shell` / `interior`, `flowchart`, `parts`, `statechart`. Persons/org = relation slice via anchor — not special first-class views. Do not teach `layer=` as a peer axis. Do not invent a kind zoo per view — thin **`role=`** / **`view=`** only.

**Shell caps:** `view=flowchart` / `view=statechart` ≤ **8 NODEs** / ≤ **12 EDGEs**, or decision-only / one-hop. Prefer omit-default attrs and short `law=` on the warm slice.

**Goldfish:** re-read the current pin map each turn. Chat is not SSOT.

---

## 6. Migration (thin)

| Keep | Migrate into 1.x | Demote |
|------|------------------|--------|
| NODE\|EDGE store | Active stamps → node + `ports=` + `law=` | Formula-on-edge; maths hubs on wrong kinds |
| Write = display; pin_map caps | Flat self-loop `derives` → law on node; `connects` → `bind`; chart sense → relation label | Forever dual dialect; colon-pile port tokens; bare `--bind-->` for persons; B (`def=`/`uses=`) |
| Locator kinds (domain locators) | Non-directed `--bind--`; dual EDGE grains; membership → node↔node relation | Those kinds as formula hubs; braced `--{bind}-->`; `carries=member`; bi-directed as default teach; `layer=` peer axis |

Engine: law-on-node + dual EDGE → **1.0**, not a silent 0.3.x patch. Flat same-node `derives` in [`memnet-field-formulas.md`](memnet-field-formulas.md) = **transitional** only.

---

## 7. LLM cost & accuracy

**Verdict:** ontology (law on NODE; dual EDGE; `[Node.port]` bind vs bare-id relation; shell/interior) is sound for Write=display. The ranked cuts below are **applied** in this doc (not a wish-list).

| Axis | Finding |
|------|---------|
| **Tokens** | Locked bare `--label-->`. **Omit** `recycle=` unless non-default. Port bags keep `direc=`; skip unused attrs. Bind teach `bind` only. Relation put sense in the label. Optional `carries=` — not every bind line. Relay `law=` stays the cautionary extreme — warm slice still short. |
| **Accuracy** | `{…}` = brace-group / record (ports primary). Nesting **capped at depth 2**. Soft-validate: `law=` symbols ⊆ ports∪params∪`@`. Thin `role=`/`view=` only. Dual EDGE: port↔port = bind; node↔node = relation; reject mixed endpoints. Membership = relation grain. |
| **Pin map** | Shell-first + re-anchor; flowchart/statechart shell ≤8/12 or decision-only. Warm BJT ~5 lines; relay omits idle V/I noise. |

**Ranked cuts — applied:**

1. **Omit `recycle=` by default** — emit only when non-default. Port bags keep required `direc=`, skip empty/unused attrs.
2. **Dual EDGE labels** — bind: teach `bind` only; optional `carries=`. Relation: label = sense on bare ids; demote `--bind-->` + `carries=` on persons.
3. **Soft-validate law symbols** — symbols ⊆ ports∪params∪`@`; no B call-name soft-validate.
4. **Cap flowchart/statechart fan-out** — shell ≤8 NODEs / ≤12 EDGEs or decision-only.
5. **Thin `role=` / `view=`** — no kind zoo; no `role=lib`; no `layer=` peer; persons/org not special views.
6. **Reject mixed endpoints** — soft-validate both ends same grain (port or bare).
7. **Brace nesting depth cap = 2** — reject depth 3+; do not promote `meta=`/`units=` teach. Grammar: one nested `recordBag` in `attrValue` ([`MemNetLayer.g4`](antlr/MemNetLayer.g4)).
8. **Brace-group discipline** — soft MUSTNOT bags on `law`/`pseudo`/`recycle`/`role`/`view` (denylist shrunk — B fields gone). A only for named functions.

---

## 8. Open (three bullets max)

- **First-class `PORT` NODE** — deferred / no until forced; default binds use `[Node.port]`.
- **SCHEMA freeze** — relation labels stay open `IDENT` (no vocab now); fat field allow-list deferred — small core later; soft denylist now (`law`/`pseudo`/`recycle`/`role`/`view`).
- **Deferred teach** — `state=` (statechart/instance only); bind `event=`/`guard=` (flowchart/statechart only); bi-directed wire (accept, demote teach); `direction=` / `pipe` (accept-only).

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
| [`examples/layer/`](examples/layer/) | Golden fixtures (`layer_*.txt`) — parse / soft-validate |
| [`tools/layer_soft_validate.py`](tools/layer_soft_validate.py) | Soft-validate hung off ANTLR parse (not in 0.3 engine) |

No change to `requirements.sysml` in this design task.
