# Nodal analysis — circuit domain (ports / law / bind)

> **Dialect (1.x):** **GQL only** — [`../grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md). Do **not** teach Layer / Tier A. Note body may still show historical seeds until **M3**; prefer [`examples/inverting-amplifier-gql-case-study.md`](examples/inverting-amplifier-gql-case-study.md) for wire shapes.

**Teach:** GQL wire profile + shaped `pin_map`. Historical body examples below are M3-bound.
**Documentation only** — does **not** implement a solver.  
**British English.** ASCII. No `|` pipe on the agent surface.

Doctrine: [`gql-wire-profile.md`](../grammar/gql-wire-profile.md). Formula-on-EDGE (`derives` / `feeds`) is **legacy** — short pointer in §8, not dual teach.

Complements:

- [`llm-circuit-schematic.md`](llm-circuit-schematic.md) — schematic / s-domain Layer grain
- [`examples/inverting-amplifier-memnet.md`](examples/inverting-amplifier-memnet.md) — worked InvAmp + Layer seed
- Layer goldens — `docs/grammar/archive/examples-layer/` (historical only)

---

## 1. Classical node method (recap)

| Element | Role |
|---------|------|
| Unknowns | Node voltages \(v_k\) (relative to a reference) |
| KCL | At each non-reference node: sum of currents into the node = 0 |
| Branch laws | Ohm, sources, \(Z(s)\) — on the **device NODE** (`law=`) |
| System | Sparse stamp → \(G \cdot v = i\) (or s-domain equivalent) |

MemNet stores **topology (binds) + absolute numbers + law LaTeX**. It does **not** assemble or invert \(G\).

---

## 2. Circuit concept → Layer shape

Do not conflate MemNet NODE with circuit node.

| Circuit concept | Layer shape |
|-----------------|-------------|
| Two-terminal / device | **`CST`** with `ports=` + `law=` + params (`R=`, …) |
| Terminal (across + through) | **One port bag** — `name: {direc=…, V=@…, I=@…}` (not a separate `PIN` atom) |
| Equipotential / copper | Port↔port **`--bind-->`** / **`--bind--`** (ideal pipe; optional `carries=I`) |
| Reference / ground | `CST` with `law=` fixing \(V=0\), or a port bound to that ground |
| KCL residual (optional stamp) | Thin `CST` with ports for incident currents + `law=` sum = 0 — **or** leave KCL implied by \(I_-=0\) + resistor laws at a star bind |
| Closed-loop result | `CST` with params `A_s=` / `law=` for \(A(s)\) |

**MUSTNOT:** `law=` on EDGE; mix `[Node.port]` ↔ bare `[Node]`; teach `connects_to` / paren `--(rel)-->` as primary; invent B (`def=`/`uses=`).

Teach **`direc=`** (`in` / `out` / `inout`); omit session-default `recycle=`.

---

## 3. Dual EDGE (locked)

| Grain | Endpoints | Label | Use |
|-------|-----------|-------|-----|
| **Bind** | Both `[Node.port]` | **`bind`** only | Copper / ideal continuity |
| **Relation** | Both bare `[NodeId]` | Open `IDENT` (`owns`, `about`, …) | Chart / semantic — not copper |

```text
E1 [CST_R.a] --bind-- [CST_Src.p] ; carries=I
E2 [CST_Stage] --about--> [CST_R]
```

---

## 4. Ohm and KCL on the NODE

### 4.1 Ohm (branch law)

Alias primary — keep `@` in bag and in `law=`:

```text
CST [CST_R] ; R=10000 ; ports=a: {direc=inout, V=@va, I=@ia},b: {direc=inout, V=@vb, I=@ib} ; law=$@va-@vb=@ia*R$,$@ia=-@ib$
```

Qualified secondary (multi-qty clarity): `law=$a.V-b.V=a.I*R$,$a.I=-b.I$`.

### 4.2 KCL at a star

Classical: \(I_1 + I_2 + \cdots = 0\) at a non-reference node.

**Preferred (slim):** bind branch ports that share the equipotential; put \(I=0\) on high-Z device ports; agent checks current sum from port absolutes. No EDGE formula.

**Optional explicit stamp** (when the residual must appear on the pin map):

```text
CST [CST_KCL] ; name=KCL_mid ; ports=i1: {direc=in, q=@i1},i2: {direc=in, q=@i2},out: {direc=out, q=@res} ; law=$@res=@i1+@i2$
```

Named-function **A** (Sum-style CST + binds) is allowed for reusable sums — **never** put the sum on an EDGE.

**Do not** invent a hyper-edge for KCL. **Do not** store a dense \(G\) matrix as one blob.

---

## 5. Reference node / ground

```text
CST [CST_Gnd] ; name=GND ; ports=a: {direc=inout, V=@vg, I=@ig} ; law=$@vg=0$
```

No free unknown at the datum. Do not mint a KCL stamp whose locus is the reference.

---

## 6. Absolute on pin map vs law text

| Layer | On pin map | Mutate |
|-------|------------|--------|
| Voltages, currents, R, residual | Absolute numbers / `@` aliases in port bags | `~` with literals; `key+=N` / `key-=N` on `~` only |
| Ohm, KCL, gain | **`law=` LaTeX on NODE** | Create/patch NODE; never put live maths on the arrow |
| Topology | `--bind-->` between ports | Port grain both ends |

Write = display. Agents evaluate offline and write absolutes until an evaluator exists.

---

## 7. Minimal resistive divider (Layer sketch)

Two resistors, source, ground — KCL at the mid net via star binds.

```text
CST [CST_Vin] ; name=Vin ; Vin=5.0 ; ports=p: {direc=out, V=@vin, I=@iin} ; law=$@vin=Vin$
CST [CST_R1] ; R=1000 ; ports=a: {direc=inout, V=@va1, I=@ia1},b: {direc=inout, V=@vb1, I=@ib1} ; law=$@va1-@vb1=@ia1*R$,$@ia1=-@ib1$
CST [CST_R2] ; R=1000 ; ports=a: {direc=inout, V=@va2, I=@ia2},b: {direc=inout, V=@vb2, I=@ib2} ; law=$@va2-@vb2=@ia2*R$,$@ia2=-@ib2$
CST [CST_Gnd] ; name=GND ; ports=a: {direc=inout, V=@vg, I=@ig} ; law=$@vg=0$
E_s [CST_Vin.p] --bind--> [CST_R1.a] ; carries=I
E_m [CST_R1.b] --bind-- [CST_R2.a] ; carries=I
E_g [CST_R2.b] --bind-- [CST_Gnd.a] ; carries=I
```

Illustrative mid absolutes after a hand solve (equal divider): \(V_\mathrm{mid}=2.5\,\mathrm{V}\), \(I=2.5\,\mathrm{mA}\). Full InvAmp: [`examples/inverting-amplifier-memnet.md`](examples/inverting-amplifier-memnet.md).

---

## 8. Risks for LLM agents

| Risk | Discipline |
|------|------------|
| Solving vs stating | Graph holds stamp + results; **agent / external solver** produces \(v\). No SPICE in-engine. |
| MemNet NODE ≠ circuit node | Circuit node = equipotential at bound ports; MemNet NODE = any row. |
| Bind as current sense | Continuity only; signed `I` + `direc=` / device `law=` carry sense. |
| One fat KCL for the whole netlist | One stamp per essential node (or implied at each star). |
| Dense \(G\) as prose | Sparse CSTs + binds. |
| Formula-on-EDGE / `derives` | Legacy — do not teach as primary. |
| Paren arrows `--(rel)-->` | Demoted; teach bare `--bind-->` / `--rel_name-->`. |

---

## 9. Legacy Tier A (pointer only)

Flat `NET`/`CMP`/`PIN` + self-loop `derives` / `feeds` remains an **accept path** through 0.5.x. Design leftover: [`memnet-field-formulas.md`](../grammar/memnet-field-formulas.md). Fixture: `docs/grammar/examples/22_inverting_amp_nodal_good.txt`. **Do not** copy those shapes into new agent seeds — migrate law → NODE, copper → `bind`.

---

## 10. Related

| Path | Role |
|------|------|
| [`examples/inverting-amplifier-memnet.md`](examples/inverting-amplifier-memnet.md) | InvAmp derivation + Layer MCP seed |
| [`llm-circuit-schematic.md`](llm-circuit-schematic.md) | Schematic / s-domain Layer grain |
| [`../grammar/memnet-multi-layer.md`](../grammar/memnet-multi-layer.md) | Layer SSOT |
| [`../grammar/examples/layer/layer_09_inv_amp_good.txt`](../grammar/examples/layer/layer_09_inv_amp_good.txt) | InvAmp Layer golden |
| `~/.cursor/skills/memnet-format/` | Shared / Layer wire (user pack) |

**This file is documentation only.** Use it to place Ohm/KCL as NODE `law=` beside port binds — without building a circuit solver into MemNet.
