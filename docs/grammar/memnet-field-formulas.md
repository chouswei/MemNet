# Field formulas (design)

> **Not primary agent teach.** Prefer **law on node** + GQL relationships per [`gql-wire-profile.md`](gql-wire-profile.md).  
> This doc is historical formula-as-EDGE design; do **not** dual-teach with GQL wire. Former Layer ontology: [`archive/docs/memnet-multi-layer.md`](archive/docs/memnet-multi-layer.md).

**Status:** design only — **no expression engine** in 0.3.6+.  
**Scope:** domain-agnostic formula relations (`derives` / `feeds`, …) for **any** domain.  
**Not this doc:** circuit nodal analysis — see application notes + GQL case study.  
**British English.** Paths ASCII.

### Two layers (do not conflate)

| Layer | What it is | Where |
|-------|------------|--------|
| **Formula relations (this doc)** | Generic grammar/design: write down all relations as formula-as-EDGE for any domain | `docs/grammar/memnet-field-formulas.md` |
| **Nodal circuitry (application)** | Express a circuit with the node method: topology + KCL/Ohm stamps + absolute V/I — *uses* formula edges; does not define them | `docs/application-notes/llm-nodal-analysis-formulas.md` |

---

## Problem

Agents need derived numerics in **any** domain, e.g. `cashflow = rent - expenses`, `net = income - tax - fees` (many inputs → one target), or `wealth` fed by `income`. (Circuit Ohm/KCL is the same shape applied later — not the motivating SSOT.) Today the store holds **absolute** field values; `~` may apply `key+=N` / `key-=N` with a **number literal** only; the pin map never shows ops.

The missing piece is not a second field syntax — it is a **durable link** from **source fact(s)** to a target fact, visible in the same NODE|EDGE dialect. A formula may be driven by **multiple fields**; the MVP shape already encodes that as a **list** on one EDGE.

---

## Thesis (relation-first)

| Claim | Consequence |
|-------|-------------|
| Formula **is a kind of relation** | Model it as an **EDGE** (`rel=formula` / `derives` / `computes`), not a magic NODE field |
| Sources and target are graph endpoints | Endpoints are **nodes**; **which fields** participate live on the **edge payload** |
| Pin map shows the relation | Bare-present EDGE lines (Write = display); target **values** stay absolute numbers |
| Evaluation is engine policy | Materialise target on write (preferred) or optionally on pin-map read — definition stays on the EDGE |

**Demoted (not primary):** `cashflow:=rent-expenses` or `cashflow#=…` on the node field bag. Those may remain tiny **sugar** later that *compile to* a formula EDGE; they are not the SSOT shape.

**Do not** overload `LAW` prose as an expression language. **Do not** invent CALC as a third conceptual kind — tags realise NODE kinds only; formula is EDGE.

---

## 1. Semantics

### What is stored

| Layer | Stored? | Shown on pin map? |
|-------|---------|-------------------|
| Source / target **nodes** | Yes (absolute fields) | Yes — absolute values |
| **Formula EDGE** | Yes (`rel`, field locators, `expr`, …) | Yes — relation line (copy eid / endpoints) |
| Evaluated target number | Yes if **materialise-on-write**; ephemeral if compute-on-read only | Absolute `tgt=…` on the target node (never live `expr=` as the value to casually `~`) |

### Evaluation modes

| Mode | When | Fits Write=display? |
|------|------|---------------------|
| **Materialise-on-write** | Dep `~` / formula create / explicit refresh → write absolute target field | **Preferred** — same as `+=`/`-=` result |
| **Materialise-on-pin-map-read** | Warm expands before emit | OK if emit is still absolute; burns budget; harder multi-agent consistency |
| **Definition only** | EDGE stored; agent evaluates offline | No engine; status quo with visible intent |

**Locked preference when an engine lands:** materialise-on-write; pin map emits absolute target fields + the formula EDGE as a normal relation.

---

## 2. Anatomy of a formula EDGE

```text
FormulaEdge = {
  id?,                          // engine-minted eid
  from: Id,                     // source node (or primary source)
  rel:  formula | derives | computes,   // English / snake token
  to:   Id,                     // target node (may equal from for same-node)
  fields: {
    tgt_field,                  // required — which field on `to` is written
    src_fields?,                // optional list — fields read (default: parse from expr)
    expr?,                      // whitelist arithmetic over field names (+ literals)
    op?,                        // optional fixed op: add | sub | … (instead of free expr)
    mode?                       // materialise | display_only (default materialise)
  }
}
```

- **Endpoints are nodes** — MemNet has no first-class “field port” type in v1.
- **Field scope is edge payload** — `tgt_field` / `src_fields` (or names inside `expr`) locate fields on those nodes.
- Same-node derive ⇒ **self-loop** EDGE (`from == to`) with distinct field roles.
- **Multi-source is the default MVP shape** — one EDGE, `src_fields=a,b,c` (comma-separated ASCII list), `expr` over those names, one `tgt_field`. Single-source is just a list of length one.
- Cross-node multi-field ⇒ later (`from ≠ to`; qualified idents / `feeds`); not MVP.

### Multi-field inputs (locked for MVP prose)

| Rule | Detail |
|------|--------|
| **One EDGE, many inputs** | `src_fields=rent,expenses,fees` + `expr=rent-expenses-fees` + `tgt_field=cashflow` |
| **Cardinality** | N ≥ 1 source field names; exactly one `tgt_field` per `derives` EDGE |
| **Binding** | Unqualified idents in `expr` bind to fields on **`from`** (self-loop ⇒ all on that node) |
| **Not single-source-only** | Do not teach “one source field per EDGE” as the MVP; the list is intentional |

**Why not N separate EDGEs by default?** One derive owns one target field and one expression. Splitting into N edges would either (a) invent partial exprs with no clear owner of `tgt_field`, or (b) require an aggregation story the MVP does not have. Keep **one `derives` EDGE per target field**. Optional later: N `feeds` edges (each one source → same target, `op=add|sub`, **no** free `expr`) when the relation is “contribute into”, not “compute as f(…)”.

**Same-node vs cross-node multi-field**

| Case | MVP? | Shape |
|------|------|-------|
| Same node, 2+ source fields → one target field | **Yes** | Self-loop `derives`; `src_fields=…` list; `expr` over local keys |
| Cross-node, fields on several nodes → one target | Later | After reserve/ACL; qualified expr and/or several `feeds` |

---

## 3. Field locators (clear story — no field ports yet)

| Approach | Shape | Verdict |
|----------|--------|---------|
| **A. Node endpoints + field keys on EDGE** | `[HH01] --(derives)--> [HH01] ; tgt_field=cashflow ; expr=rent-expenses` | **MVP** — fits AST Node\|Edge; no new conceptual kind |
| **B. Qualified names in expr** | `expr=[Inc].amount-[Exp].total` with ends = those nodes | Later — needs id tokens in expr AST |
| **C. Field-as-port NODEs** | Mint `FLD_*` pins per field, EDGE between ports | Reject for now — pin-map noise; invents structure agents must mint |

**MVP locator rule:** endpoints = nodes; fields = ASCII keys on the edge (`tgt_field`, `src_fields` / `expr` idents). Idents in `expr` bind to fields on **`from`** unless qualified later. For self-loop, all idents are on that one node; `tgt_field` is the write key on `to` (same id).

---

## 4. Dialect surface (sketch — ASCII, shared dialect, no pipe)

None implemented. Prefer ordinary EDGE mutate + bare present on pin map.

### Same-node (self-loop) — primary MVP shape (two sources)

```text
+ HH [HH01] ; rent=1000 ; expenses=400 ; cashflow=0 ; recycle=persistent
+ NEW [HH01] --(derives)--> [HH01] ; tgt_field=cashflow ; src_fields=rent,expenses ; expr=rent-expenses
```

Pin map (illustrative):

```text
## Nodes
HH [HH01] ; rent=1000 ; expenses=400 ; cashflow=600 ; recycle=persistent

## Edges
E12 [HH01] --(derives)--> [HH01] ; tgt_field=cashflow ; src_fields=rent,expenses ; expr=rent-expenses
```

After `~ [HH01] ; rent+=50`, engine (when implemented) re-materialises `cashflow` from EDGE `E12`.

### Same-node — three or more sources (still one EDGE)

```text
+ HH [HH02] ; income=5000 ; tax=800 ; fees=50 ; net=0 ; recycle=persistent
+ NEW [HH02] --(derives)--> [HH02] ; tgt_field=net ; src_fields=income,tax,fees ; expr=income-tax-fees
```

Pin map (illustrative):

```text
## Nodes
HH [HH02] ; income=5000 ; tax=800 ; fees=50 ; net=4150 ; recycle=persistent

## Edges
E13 [HH02] --(derives)--> [HH02] ; tgt_field=net ; src_fields=income,tax,fees ; expr=income-tax-fees
```

Still **one** `derives` EDGE: list length is three; `tgt_field` remains singular. Do not emit three parallel `derives` edges for the same `net`.

### Cross-node (later)

```text
+ NEW [N_rent] --(derives)--> [N_cash] ; tgt_field=value ; src_fields=value ; expr=value
+ NEW [N_inc] --(feeds)--> [N_wealth] ; tgt_field=wealth ; src_fields=amount ; op=add
```

`feeds` + `op=add` is a typed relation without a free `expr` (safer). Several `feeds` into one target may model multi-source **contribution** later; free multi-field `expr` across nodes needs qualified idents — defer both.

### Rel name

| Token | Use |
|-------|-----|
| `derives` | Target field is a function of source fields (default) |
| `feeds` | Source contributes into target (`op=add` / `sub`) — close to “wealth += income” *as a relation* |
| `formula` | Generic; prefer `derives` / `feeds` in agent prose |

One EDGE kind in the store sense (still EDGE); **rel** distinguishes behaviour.

### Explicitly not preferred as SSOT

```text
~ [HH01] ; cashflow:=rent-expenses          # node-inline — sugar only if it emits a derives EDGE
+ F1 [N_rent] --(formula)--> [N_cashflow] ; expr=rent-expenses   # vague ends: which fields?
```

If sugar exists later: compile `:=` into a self-loop `derives` EDGE + materialise; do not leave formula only in the field bag.

---

## 5. Interaction with existing features

### `+=` / `-=` (locked §4.2.0b)

- Remain **number-literal RHS** on `~` field patches.
- Do **not** overload `wealth+=income` as `+=` with a field name.
- Relation form for “add this field into that”: `feeds` EDGE + `op=add` (materialise), or agent reads pin map and writes `wealth+=N`.
- Hand `cashflow+=10` while a `derives` EDGE owns `cashflow` → policy: reject (`formula_owned`), or allow and mark `formula_stale` until refresh.

### Re-id / merge

- Formula EDGEs are normal edges: `src`/`dist` **retarget** on node re-id / merge (§4.2.0).
- Edge re-id: `~ Eid ; id=NewEid` as today.
- Field keys on the edge payload are **not** renamed by node re-id; merge with conflicting `tgt_field` owners → reject or drop one EDGE.

### Pin map budget

- Formula EDGEs count toward edge lines in the ego digest (same caps as other edges).
- Prefer showing the EDGE when the target or any `src` node is in view.
- Target **values** absolute only; do not expand `expr` into synthetic nodes.

### Multi-agent / reserve

- Creating/patching/dropping a formula EDGE is a mutate on that eid + logically touches `from`/`to`.
- Under neighbourhood reserve: holder must cover **both** endpoints (self-loop ⇒ one id). Cross-node without full lease → reject.
- Re-materialise on dep write requires write rights on the **target** node (and reserve hold).
- Session ACL gates writers; formula edges are not an ACL bypass.

---

## 6. Scope: same-node MVP vs cross-node

| Scope | Shape | Rank |
|-------|--------|------|
| **Same-node multi-field** via self-loop `derives` EDGE | `from=to`; `expr` over local keys; materialise `tgt_field` | **MVP** |
| **Cross-node** `derives` / `feeds` | Two ids; reserve both; optional qualified expr | After reserve/ACL |
| Node-inline `:=` sugar | Compiles to self-loop EDGE | Optional after MVP |
| SCHEMA-declared default derive | Registry emits template EDGE on kind create | Later |
| Field-port NODEs / CALC kind | New structure | Avoid |

---

## 7. Risks

| Risk | Mitigation |
|------|------------|
| **Cycles** (A derives B derives A) | EDGE dep graph on `(node, field)` pairs; reject `formula_cycle` |
| **Non-numeric** | `bad_numeric` / `formula_type` on evaluate |
| **Unsafe expr** | Whitelist AST: field idents, `NUMBER`, `+ - * /`, `()`; max length/depth; **never** `eval`/`exec` |
| **Ambiguous endpoints** | Require `tgt_field`; bind unqualified idents to `from` (MVP self-loop) |
| **Stale target** | Materialise-on-write; `formula_stale` if target patched under an owning `derives` |
| **Pin-map noise** | One EDGE per **target field** derive (multi-source via `src_fields` list); no FLD_* ports; cap formula edges in ego view |
| **Misread as single-source** | Document `src_fields` as a list; examples with 2+ and 3+ names; reject N×`derives` for one `tgt_field` |
| **LLM invents edges** | Soft lint: unknown `rel` / fat `expr`; SCHEMA may allowlist `derives`/`feeds` |

---

## 8. MVP recommendation vs later (ranked)

| Rank | Item | When |
|------|------|------|
| **0** | **Status quo** — agent computes; absolutes / `+=N` / `-=N`; no formula EDGE | **Now** |
| **1** | **Dialect + store shape** — document/accept self-loop `derives` EDGE payload (`tgt_field`, `src_fields` **list**, `expr`, …) as ordinary EDGE; **no evaluator** (intent-visible only) | Small docs/parser allowlist if needed |
| **2** | **Evaluator MVP** — whitelist AST; materialise-on-write for same-node self-loop only (N sources on one EDGE) | First engine drop |
| **3** | **`feeds` + `op=add|sub`** — optional per-source contribution edges (no free `expr`); not a substitute for multi-field `derives` | With or just after 2 |
| **4** | Cross-node + reserve-aware recompute | After reserve/ACL |
| **5** | `:=` sugar → compile to EDGE; SCHEMA default derives | Convenience |
| **6** | Qualified cross-node expr; field-port NODEs | Avoid unless forced |

**Decision:** re-centre on **formula as EDGE relation** for the **flat same-node transitional MVP** only. Do **not** implement an expression engine yet. First concrete dialect candidate remains the **same-node self-loop** `derives` line with **`src_fields` as a multi-name list**. Keep `+=`/`-=` literal-only. **1.x ([`memnet-multi-layer.md`](memnet-multi-layer.md)):** laws live on the **node** (`CST` + `law=` / `ports=`); EDGE is **bind** (port↔port) or **relation** (node↔node) — do **not** treat formula-on-edge as the long-term teachable surface.

---

## Related

| Path | Role |
|------|------|
| `docs/grammar/memnet-grammar-design.md` §4.2 / §4.2.0b | EDGE mutate; locked numeric `+=`/`-=` |
| `docs/grammar/memnet-multi-layer.md` | Stratified pin maps; law on node (`CST` + `ports=`/`law=`); EDGE = **carrier**, not the law |
| `docs/grammar/memnet-neighbourhood-reserve.md` | Lease both endpoints before cross-node |
| `docs/grammar/memnet-security-multi-agent.md` | Session ACL before coop formula writes |
| `docs/application-notes/llm-nodal-analysis-formulas.md` | **Application** of this grammar: nodal circuit graph + KCL/Ohm (no solver; does not redefine formula EDGE) |
| `parts/common/memnet/memnet/mutate_gate.py` | Absolute materialise for `+=`/`-=` today |
