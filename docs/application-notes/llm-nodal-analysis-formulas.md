# Nodal Analysis and Field Formulas — A MemNet Application Note

**Layer:** **circuitry with the node method** — express a circuit as a MemNet graph (NET/CMP/PIN topology, KCL/Ohm stamps, voltages/currents as absolute fields).  
**Uses (does not define):** the generic formula-as-EDGE grammar (`derives` / `feeds`, multi `src_fields`, `tgt_field`, `expr`) from [`memnet-field-formulas.md`](../grammar/memnet-field-formulas.md). That design doc is domain-agnostic; this note is one application of it plus topology. Do not conflate the two.  
**Documentation only** — does **not** implement a solver.

**British English.** Dialect examples ASCII. No `|` pipe on the agent surface.

### Two layers (do not conflate)

| Layer | What it is | Where |
|-------|------------|--------|
| **Nodal circuitry (this note)** | Use MemNet to express a circuit with the node method | this file |
| **Formula relations (grammar)** | Use MemNet to write down all relations (formulas) for any domain | [`memnet-field-formulas.md`](../grammar/memnet-field-formulas.md) |

This note also complements:

- [`llm-circuit-schematic.md`](llm-circuit-schematic.md) — `CMP` / `PIN` / `NET`, s-domain `VAR` / `EQN`, golden rules
- Grammar PCBA fixtures — `docs/grammar/examples/17_*.txt`, `18_*.txt`
- Worked inverting amplifier (topology + `derives`) — [`examples/inverting-amplifier-memnet.md`](examples/inverting-amplifier-memnet.md); golden seed `docs/grammar/examples/22_inverting_amp_nodal_good.txt`

---

## 1. Classical node method (recap)

| Element | Role |
|---------|------|
| Unknowns | Node voltages \(v_k\) (relative to a reference) |
| KCL | At each non-reference node: sum of currents into the node = 0 |
| Branch laws | Ohm, sources, \(Z(s)\) — relate branch currents to node voltages |
| System | Sparse stamp → \(G \cdot v = i\) (or s-domain equivalent) |

MemNet stores **topology + absolute numbers + law relations**. It does **not** assemble or invert \(G\).

---

## 2. What are NODEs?

Do not conflate MemNet NODE with circuit node.

| Circuit concept | MemNet kind | Id / locator |
|-----------------|-------------|--------------|
| Electrical node (equipotential) | `NET` | Stable: `NET_SUM`, `net=SUM`, `path=…ato` |
| Package / two-terminal | `CMP` | Stable: `ATO_R1`, `refdes=R1` |
| Terminal | `PIN` | Stable: `PIN_R1_1`, `pin=` |
| Unknown \(V_k\) | `VAR` (or numeric field on analysis atom) | Goldfish `[NEW]` then copy |
| KCL residual / equation locus | `EQN` | Goldfish; one per essential node |
| Assumption / result | `CLM` | Goldfish |

**Rule:** schematic copper uses **locator ground ids** (no client `NEW`). Analysis atoms (`VAR`, `EQN`, result `CLM`) may use `[NEW]`.

Optional numeric fields (illustrative): `V`, `I`, `R`, `residual` — always **absolute** on the pin map.

---

## 3. What are EDGEs?

| Relation | Ends | Meaning |
|----------|------|---------|
| `owns` | `CMP → PIN` | Package contains terminal |
| `connects_to` | `PIN → NET` | Copper attachment (undirected phys.; arrow is storage only) |
| `voltage_of` | `VAR → NET` | Unknown voltage for that net |
| `kcl_at` | `EQN → NET` | Which essential node this KCL is about |
| `uses` | `EQN → CMP` / `VAR` | Branch or unknown mentioned in the stamp |
| `derives` | formula | Target field = \(f(\mathrm{src\_fields})\) — Ohm, residual sum |
| `feeds` | formula | Source contributes into a target (`op=add` / `sub`) |

Branch **geometry** is PIN–NET connectivity. Branch **laws** are formula EDGEs (or stated `EQN`/`CLM` codes until an evaluator exists). Topology edges are not currents.

---

## 4. Multi-field formulas for KCL and Ohm

**Borrowed shape** (defined in `memnet-field-formulas.md`, not here): one `derives` EDGE, `src_fields=a,b,c`, `expr`, one `tgt_field`. Prefer **same-node self-loop** when all idents live on one analysis atom. Circuit Ohm/KCL are instances of that generic relation; they are not a separate formula dialect.

### 4.1 Ohm (branch law) — same-node or stated code

Self-loop on a branch analysis node that already holds both terminal voltages and resistance (denormalised for the MVP):

```text
BR [BR_Rin] ; Va=0 ; Vb=0 ; R=10000 ; I=0 ; recycle=persistent
E_ohm [BR_Rin] --(derives)--> [BR_Rin] ; tgt_field=I ; src_fields=Va,Vb,R ; expr=(Va-Vb)/R
```

Until cross-node qualified `expr` exists, prefer this denormalisation **or** keep Ohm as an `EQN`/`CLM` `code=` string (status quo in `llm-circuit-schematic.md`) and let the agent / external solver evaluate.

### 4.2 KCL — sum of branch currents

Classical: \(I_1 + I_2 + \cdots = 0\) at a non-reference node.

**Preferred pattern A — aggregate then self-loop `derives`:**

Copy (or materialise) incident branch currents as fields on the KCL `EQN` node, then one multi-source EDGE:

```text
EQN [EQN_KCL_SUM] ; method=nodal ; form=KCL ; I_Rin=0 ; I_Rf=0 ; residual=0 ; domain=s ; recycle=persistent
E_kcl [EQN_KCL_SUM] --(derives)--> [EQN_KCL_SUM] ; tgt_field=residual ; src_fields=I_Rin,I_Rf ; expr=I_Rin+I_Rf
E_at [EQN_KCL_SUM] --(kcl_at)--> [NET_SUM] ; recycle=persistent
```

Pin map shows absolute `I_*` and `residual`; the EDGE states the law. Settled analysis wants `residual` ≈ 0 (agent / solver writes absolutes; engine may later materialise from `derives`).

**Pattern B — many `feeds` into the residual (no hyper-edge):**

```text
E_f1 [BR_Rin] --(feeds)--> [EQN_KCL_SUM] ; tgt_field=residual ; src_fields=I ; op=add
E_f2 [BR_Rf]  --(feeds)--> [EQN_KCL_SUM] ; tgt_field=residual ; src_fields=I ; op=add
```

Each contribution is a binary EDGE. No n-ary hyper-edge kind. Cross-node `feeds` is **after** same-node MVP in the formula roadmap.

**Do not** invent a MemNet hyper-edge for KCL. **Do not** store a dense \(G\) matrix as one blob — stamp sparsely (one `EQN` per essential node + branch uses).

---

## 5. Self-loop `derives` vs many `feeds`

| Need | Fit |
|------|-----|
| All KCL currents already fields on one `EQN` | Self-loop `derives` — **MVP** |
| Currents live on separate branch NODEs | Many `feeds` + `op=add` (later), or denormalise onto `EQN` first |
| True n-ary “edge among N branches” | **Out of scope** — simulate with A or B |

Self-loop is enough when the agent (or a future materialiser) keeps branch currents mirrored on the residual node. That matches “multi-field sources OK” without waiting for qualified cross-node `expr`.

---

## 6. Reference node / ground

| Practice | MemNet |
|----------|--------|
| Choose datum | `NET` with `role=reference` (e.g. `NET_GND`) |
| \(V_\mathrm{ref}=0\) | `CLM` assumption and/or absolute `V=0` — not a free `VAR` |
| No KCL at reference | No `EQN` with `kcl_at` → reference net |

```text
NET [NET_GND] ; net=GND ; role=reference ; path=boards/afe/inverting.ato ; recycle=persistent
CLM [CLM_VREF] ; type=assumption ; code=V_GND_eq_0 ; domain=s ; recycle=persistent
E_ref [CLM_VREF] --(applies_to)--> [NET_GND] ; recycle=persistent
```

---

## 7. Absolute on pin map vs relations (laws)

| Layer | On pin map | Mutate |
|-------|------------|--------|
| Voltages, currents, R, residual | Absolute numbers | `~` with literals; `key+=N` / `key-=N` literal-only |
| Ohm, KCL sum, constraints | Formula EDGE lines (`derives` / `feeds`) and/or `EQN`/`CLM` `code=` | Create/patch EDGE; do not put live `expr=` as the value agents casually overwrite |
| Topology | `connects_to` / `owns` | Locator pins only |

Write = display: copy assigned ids and absolute fields; copy formula EDGE payloads when stating laws. Prefer materialise-on-write when an evaluator exists (`memnet-field-formulas.md`); until then agents evaluate offline and write absolutes.

---

## 8. Risks for LLM agents

| Risk | Discipline |
|------|------------|
| Solving vs stating | MemNet holds the stamp and results; **agent or external solver** produces \(v\). Do not expect SPICE inside the engine. |
| MemNet NODE ≠ circuit node | Circuit node = `NET`; MemNet NODE = any row kind. |
| `connects_to` as current sense | Copper only; current sense lives on branch law / pin `dir` / signed `I`. |
| One fat KCL for the whole netlist | One `EQN` per essential node (+ separate constraint eqns). |
| Dense \(G\) as prose / one field | Sparse atoms + formula EDGEs. |
| `NEW` on `ATO_*` / `NET_*` / `PIN_*` | Forbidden — locators. |
| Patching `formula_owned` targets by hand | Prefer refresh from EDGE; avoid stale `residual` while claiming the law holds. |
| Treating stated `code=` as evaluated truth | `code=` is intent; numeric fields are the absolutes the next turn trusts. |

---

## 9. Minimal resistive divider (sketch)

Two resistors, source, ground — KCL at the mid net only.

```text
NET [NET_GND] ; net=GND ; role=reference ; path=boards/demo/div.ato ; recycle=persistent
NET [NET_MID] ; net=MID ; path=boards/demo/div.ato ; recycle=persistent
NET [NET_VIN] ; net=VIN ; path=boards/demo/div.ato ; recycle=persistent

VAR [VAR_MID] ; symbol=V_MID ; unit=V ; recycle=persistent
E_v [VAR_MID] --(voltage_of)--> [NET_MID] ; recycle=persistent

EQN [EQN_KCL_MID] ; method=nodal ; form=KCL ; I_R1=0.001 ; I_R2=-0.001 ; residual=0 ; recycle=persistent
E_at [EQN_KCL_MID] --(kcl_at)--> [NET_MID] ; recycle=persistent
E_sum [EQN_KCL_MID] --(derives)--> [EQN_KCL_MID] ; tgt_field=residual ; src_fields=I_R1,I_R2 ; expr=I_R1+I_R2
```

(Wire `CMP`/`PIN`/`connects_to` as in `llm-circuit-schematic.md`. Numbers above are illustrative absolutes after a hand solve.)

---

## 10. Related

| Path | Role |
|------|------|
| `docs/application-notes/examples/inverting-amplifier-memnet.md` | Trivial ideal inverting amp — both layers + MCP seed |
| `docs/application-notes/llm-circuit-schematic.md` | Schematic grain, s-domain nodal `EQN`/`VAR` worked op-amp |
| `docs/grammar/examples/22_inverting_amp_nodal_good.txt` | Parse-ok golden nodal + `derives` fixture |
| `docs/grammar/memnet-field-formulas.md` | **Generic** formula EDGE SSOT (any domain; design; no evaluator) — this note only *uses* it |
| `docs/grammar/memnet-grammar-design.md` | Atomisation, locators, `+=`/`-=` |
| `.cursor/skills/memnet-reference/` | Repo dialect routing |

**This file is documentation only.** Use it to place KCL/Ohm as multi-field formula relations beside stable schematic pins — without building a circuit solver into MemNet.
