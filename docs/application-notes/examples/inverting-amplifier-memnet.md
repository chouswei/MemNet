# Inverting amplifier — from first principles to MemNet

Derive the closed-loop transfer **A(s)** from Ohm, KCL, and a **finite** open-loop gain **a(s)**; take the ideal limit **only at the end**. Then encode topology and formula relations in MemNet shared dialect (NODE | EDGE). MemNet **states** stamps and results; it does **not** solve them.

**Notation:** **a(s)** — open-loop gain, \(V_\mathrm{OUT} = a(s)\,(V_+ - V_-)\). **A(s)** — closed-loop stage transfer, \(V_\mathrm{OUT}/V_\mathrm{IN}\). Pin-map field **`A_s`** stores the numeric value of A(s); **`a_s`** stores a(s) when the finite form is kept. `domain=s` marks the Laplace frame.

British English. ASCII. No `|` pipe on the agent surface. See [`memnet-field-formulas.md`](../../grammar/memnet-field-formulas.md), [`llm-nodal-analysis-formulas.md`](../llm-nodal-analysis-formulas.md).

---

## 1. Bedrock

### 1.1 Topology

```text
Vin -- Rin -- VMINUS ---- U1 ---- Vout
                |                  |
                +------- Rf -------+
(IN+) ---------- VGND (reference)
```

Nets: `VIN`, `VMINUS`, `VOUT`, `VGND`. `(IN+)` is tied to reference. Resistive feedback from `VOUT` to `VMINUS` is **negative** (output opposes the input-driven current at the inverting node).

Worked values: \(R_\mathrm{in}=10\,\mathrm{k\Omega}\), \(R_f=100\,\mathrm{k\Omega}\), \(V_\mathrm{IN}=1\,\mathrm{V}\) (DC).

### 1.2 Ohm (s-domain, ideal R)

\[
I_{R_\mathrm{in}}(s)=\frac{V_-(s)-V_\mathrm{IN}(s)}{R_\mathrm{in}},\qquad
I_{R_f}(s)=\frac{V_-(s)-V_\mathrm{OUT}(s)}{R_f},
\]

where \(V_-(s)\equiv V_\mathrm{VMINUS}(s)\). **Do not set \(V_-=0\) yet.**

### 1.3 KCL at the inverting node

\[
I_{R_\mathrm{in}}(s)+I_{R_f}(s)+I_-(s)=0.
\]

### 1.4 Op-amp model (finite gain, linear band)

| Assumption | Equation | Notes |
|------------|----------|-------|
| Finite open-loop gain | \(V_\mathrm{OUT}(s)=a(s)\,\bigl(V_+(s)-V_-(s)\bigr)\) | **a(s) is finite** throughout the algebra |
| High input impedance | \(I_+=I_-=0\) | Op-amp current absent from KCL |
| `(IN+)` at reference | \(V_+(s)=0\) | Non-inverting input on `VGND` |
| Negative feedback | Topology §1.1 | Required for stable linear closure; not a substitute for algebra |

With \(V_+=0\): \(V_\mathrm{OUT}(s)=-a(s)\,V_-(s)\).

**Not assumed at the start:** infinite \(a(s)\), virtual short \(V_+=V_-\), or \(V_-=0\). Those appear in §2.5 as **limits**.

**Out of scope:** saturation, slew, GBW rolloff inside \(a(s)\), bias current, clipping.

---

## 2. Derivation of A(s)

Write everything with finite \(a(s)\) and finite \(V_-\).

**Step 1 — KCL with \(I_-=0\).** From §1.2–1.3:

\[
\frac{V_--V_\mathrm{IN}}{R_\mathrm{in}}+\frac{V_--V_\mathrm{OUT}}{R_f}=0.
\]

**Step 2 — Eliminate \(V_\mathrm{OUT}\) via the op-amp.** Substitute \(V_\mathrm{OUT}=-a(s)\,V_-\):

\[
\frac{V_--V_\mathrm{IN}}{R_\mathrm{in}}+\frac{V_-+a(s)\,V_-}{R_f}=0
\;\Rightarrow\;
V_-\!\left(\frac{1}{R_\mathrm{in}}+\frac{1}{R_f}+\frac{a(s)}{R_f}\right)=\frac{V_\mathrm{IN}}{R_\mathrm{in}}.
\]

**Step 3 — Solve for \(V_-\).** Multiply through by \(R_\mathrm{in}R_f\):

\[
V_-(s)=\frac{V_\mathrm{IN}(s)\,R_f}{R_f+R_\mathrm{in}+a(s)\,R_\mathrm{in}}.
\]

**Step 4 — Closed-loop transfer.** Use \(V_\mathrm{OUT}=-a(s)\,V_-\) and \(A(s)=V_\mathrm{OUT}/V_\mathrm{IN}\):

\[
\boxed{A(s)=\frac{V_\mathrm{OUT}}{V_\mathrm{IN}}
=-\,\frac{a(s)\,R_f}{R_f+R_\mathrm{in}+a(s)\,R_\mathrm{in}}
=-\frac{R_f}{R_\mathrm{in}}\cdot
\frac{a(s)}{a(s)+1+R_f/R_\mathrm{in}}.}
\]

Equivalent form: \(A(s)=-\dfrac{a(s)\,R_f}{R_f+R_\mathrm{in}\bigl(1+a(s)\bigr)}\).

This is exact for the finite-gain linear model. No virtual ground was used.

**Step 5 — Ideal limit (final stage only).** Push the limit **after** the closed form:

\[
\lim_{a(s)\to\infty}A(s)=-\frac{R_f}{R_\mathrm{in}},
\qquad
\lim_{a(s)\to\infty}V_-(s)=0.
\]

Only here does **virtual ground** appear: \(V_+\) is fixed at 0 and \(|a(s)|\) forces \(V_-\to V_+\). For the worked values, \(A(s)=-10\) and \(V_\mathrm{OUT}=-10\,\mathrm{V}\).

**Step 6 — Consistency check (limit).** With \(V_-=0\): \(I_{R_\mathrm{in}}=-0.1\,\mathrm{mA}\), \(I_{R_f}=+0.1\,\mathrm{mA}\); KCL sum is zero.

---

## 3. MemNet encoding

Two layers: **circuitry** (topology + nodal atoms) and **formula relations** (`derives` EDGEs). Write = display.

### 3.1 Layer A — node method

| Idea | Kind | Id |
|------|------|-----|
| Net | `NET` | `NET_VMINUS`, … |
| Resistor | `CMP` | `ATO_Rin`, `ATO_Rf` |
| Node voltage | `VAR` | `VAR_VMINUS` (`V` holds \(V_-\), not assumed zero in the stamp) |
| KCL locus | `EQN` | `EQN_KCL_VMINUS` |
| Open-loop gain fact | `CLM` | `CLM_a_s` with field `a_s` |
| Limit result | `CLM` | `CLM_VIRT` — virtual ground **as limit**, not an upfront axiom |

Do **not** seed `EQN_VIRT` with `code=V_VMINUS_eq_0` as if it were independent of \(a(s)\). Prefer `CLM_VIRT` with `code=V_minus_to_zero_as_a_s_to_infinity` linked to the finite derivation.

### 3.2 Layer B — `derives` relations

| Step | Shape |
|------|--------|
| Ohm | `BR_*`: `I=(Va-Vb)/R` |
| KCL | `EQN_KCL_VMINUS`: `residual=I_Rin+I_Rf` |
| **Finite A(s)** | `RES_A`: `A_s=-(Rf/Rin)*a_s/(a_s+1+Rf/Rin)` |
| **Limit A(s)** | `RES_A`: `A_s_lim=-(Rf/Rin)` (valid when `a_s` is large) |
| Output | `RES_A`: `Vout=A_s*Vin` |

Node **`RES_A`** holds `a_s`, `A_s` (evaluated transfer), `A_s_lim`, `Vin`, `Vout`, `Rf`, `Rin`. **`A_s`** is always the pin-map name for A(s); store the finite evaluation in `A_s` and the ideal limit in `A_s_lim` when both are useful.

No expression engine in 0.3.6+ — agents evaluate and `update` absolutes.

---

## 4. Shared-dialect seed

Golden fixture: [`22_inverting_amp_nodal_good.txt`](../../grammar/examples/22_inverting_amp_nodal_good.txt).

Mutate block (`a_s=1e6` ≈ ideal; `A_s` and `Vout` at the limit):

```text
+ NET [NET_VGND] ; net=VGND ; role=reference ; path=boards/demo/inverting_amp.ato ; recycle=persistent
+ NET [NET_VIN] ; net=VIN ; path=boards/demo/inverting_amp.ato ; recycle=persistent
+ NET [NET_VMINUS] ; net=VMINUS ; path=boards/demo/inverting_amp.ato ; recycle=persistent
+ NET [NET_VOUT] ; net=VOUT ; path=boards/demo/inverting_amp.ato ; recycle=persistent
+ CMP [ATO_Rin] ; refdes=R1 ; value=10k ; R=10000 ; path=boards/demo/inverting_amp.ato ; recycle=persistent
+ CMP [ATO_Rf] ; refdes=R2 ; value=100k ; R=100000 ; path=boards/demo/inverting_amp.ato ; recycle=persistent
+ PIN [PIN_R1_a] ; refdes=R1 ; pin=1 ; path=boards/demo/inverting_amp.ato ; recycle=persistent
+ PIN [PIN_R1_b] ; refdes=R1 ; pin=2 ; path=boards/demo/inverting_amp.ato ; recycle=persistent
+ PIN [PIN_R2_a] ; refdes=R2 ; pin=1 ; path=boards/demo/inverting_amp.ato ; recycle=persistent
+ PIN [PIN_R2_b] ; refdes=R2 ; pin=2 ; path=boards/demo/inverting_amp.ato ; recycle=persistent
+ NEW [PIN_R1_a] --(connects_to)--> [NET_VIN] ; recycle=persistent
+ NEW [PIN_R1_b] --(connects_to)--> [NET_VMINUS] ; recycle=persistent
+ NEW [PIN_R2_a] --(connects_to)--> [NET_VOUT] ; recycle=persistent
+ NEW [PIN_R2_b] --(connects_to)--> [NET_VMINUS] ; recycle=persistent
+ CLM [CLM_a_s] ; type=assumption ; code=Vout_eq_a_s_times_Vdiff ; domain=s ; a_s=1000000 ; recycle=persistent
+ CLM [CLM_NFB] ; type=fact ; code=neg_feedback ; domain=s ; recycle=persistent
+ CLM [CLM_VIRT] ; type=result ; code=V_minus_to_zero_as_a_s_to_infinity ; domain=s ; recycle=persistent
+ NEW [CLM_VIRT] --(derived_from)--> [CLM_a_s] ; recycle=persistent
+ VAR [VAR_VIN] ; symbol=V_VIN ; unit=V ; domain=s ; V=1.0 ; recycle=persistent
+ VAR [VAR_VOUT] ; symbol=V_VOUT ; unit=V ; domain=s ; V=-10.0 ; recycle=persistent
+ VAR [VAR_VMINUS] ; symbol=V_VMINUS ; unit=V ; domain=s ; V=0.0 ; recycle=persistent
+ NEW [VAR_VIN] --(voltage_of)--> [NET_VIN] ; recycle=persistent
+ NEW [VAR_VOUT] --(voltage_of)--> [NET_VOUT] ; recycle=persistent
+ NEW [VAR_VMINUS] --(voltage_of)--> [NET_VMINUS] ; recycle=persistent
+ BR [BR_Rin] ; Va=1.0 ; Vb=0.0 ; R=10000 ; I=-0.0001 ; recycle=persistent
+ BR [BR_Rf] ; Va=0.0 ; Vb=-10.0 ; R=100000 ; I=0.0001 ; recycle=persistent
+ NEW [BR_Rin] --(derives)--> [BR_Rin] ; tgt_field=I ; src_fields=Va,Vb,R ; expr=(Va-Vb)/R ; recycle=persistent
+ NEW [BR_Rf] --(derives)--> [BR_Rf] ; tgt_field=I ; src_fields=Va,Vb,R ; expr=(Va-Vb)/R ; recycle=persistent
+ EQN [EQN_KCL_VMINUS] ; method=nodal ; form=KCL ; I_Rin=-0.0001 ; I_Rf=0.0001 ; residual=0.0 ; domain=s ; recycle=persistent
+ NEW [EQN_KCL_VMINUS] --(kcl_at)--> [NET_VMINUS] ; recycle=persistent
+ NEW [EQN_KCL_VMINUS] --(derives)--> [EQN_KCL_VMINUS] ; tgt_field=residual ; src_fields=I_Rin,I_Rf ; expr=I_Rin+I_Rf ; recycle=persistent
+ RES [RES_A] ; a_s=1000000 ; A_s=-10.0 ; A_s_lim=-10.0 ; Vin=1.0 ; Vout=-10.0 ; Rf=100000 ; Rin=10000 ; domain=s ; recycle=persistent
+ NEW [RES_A] --(derives)--> [RES_A] ; tgt_field=A_s ; src_fields=a_s,Rf,Rin ; expr=-(Rf/Rin)*a_s/(a_s+1+Rf/Rin) ; recycle=persistent
+ NEW [RES_A] --(derives)--> [RES_A] ; tgt_field=A_s_lim ; src_fields=Rf,Rin ; expr=-(Rf/Rin) ; recycle=persistent
+ NEW [RES_A] --(derives)--> [RES_A] ; tgt_field=Vout ; src_fields=A_s,Vin ; expr=A_s*Vin ; recycle=persistent
+ CLM [CLM_A] ; type=result ; code=A_s_finite_then_limit ; domain=s ; A_s=-10.0 ; recycle=persistent
+ NEW [CLM_A] --(derived_from)--> [RES_A] ; recycle=persistent
```

`VAR_VMINUS.V=0.0` is the **limit** value after \(a_s\to\infty\), not an independent constraint.

---

## 5. How to test with MCP

1. **`session_open`** — `session=inv_amp_demo`; optional `seed_lines` from §4.
2. **`add`** — if not seeded at open.
3. **`pin_map`** — `anchor=RES_A`: finite `derives` on `A_s`, limit `derives` on `A_s_lim`, `a_s=1000000`, `A_s=-10.0`.
4. **`pin_map`** — `anchor=EQN_KCL_VMINUS`: KCL residual and branch currents at the limit.
5. **`update`** — lower `a_s` (e.g. `~ [CLM_a_s] ; a_s=1000`), re-evaluate §2 Step 4, write new `A_s` and `Vout`; virtual ground fails if \(a_s\) is too small.

CLI: `memnet query pin-map --anchor RES_A`.

---

## 6. What MemNet does not do

- Take limits or solve algebra; no SPICE.
- Evaluate `derives` `expr` (design-only until an engine lands).
- Treat virtual ground as an axiom independent of \(a(s)\).

---

## Related

- [`llm-nodal-analysis-formulas.md`](../llm-nodal-analysis-formulas.md)
- [`llm-circuit-schematic.md`](../llm-circuit-schematic.md)
- [`22_inverting_amp_nodal_good.txt`](../../grammar/examples/22_inverting_amp_nodal_good.txt)
