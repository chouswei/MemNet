# Inverting amplifier — math SSOT

> **Wire teach:** **GQL only** — [`inverting-amplifier-gql-case-study.md`](inverting-amplifier-gql-case-study.md) and [`../../grammar/gql-wire-profile.md`](../../grammar/gql-wire-profile.md).  
> **This file:** closed-loop transfer **math derivation** only. Layer / Tier A ASCII is archive, not agent wire.

Derive the closed-loop transfer **A(s)** from Ohm, KCL, and a **finite** open-loop gain **a(s)**; take the ideal limit **only at the end**. MemNet **states** stamps and results; it does **not** solve them.

**Notation:** **a(s)** — open-loop gain, \(V_\mathrm{OUT} = a(s)\,(V_+ - V_-)\). **A(s)** — closed-loop stage transfer, \(V_\mathrm{OUT}/V_\mathrm{IN}\). Param **`a_s`** / field **`A_s`** hold numeric values; `domain=s` marks the Laplace frame.

**British English.** ASCII.

---

## 1. Bedrock

### 1.1 Topology

```text
Vin -- Rin -- VMINUS ---- U1 ---- Vout
                |                  |
                +------- Rf -------+
(IN+) ---------- VGND (reference)
```

Nets meet at port binds: `VIN`, `VMINUS`, `VOUT`, `VGND`. `(IN+)` is tied to reference. Resistive feedback from `VOUT` to `VMINUS` is **negative**.

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
| Negative feedback | Topology §1.1 | Required for stable linear closure |

With \(V_+=0\): \(V_\mathrm{OUT}(s)=-a(s)\,V_-(s)\).

**Not assumed at the start:** infinite \(a(s)\), virtual short, or \(V_-=0\). Those appear in §2 as **limits**.

**Out of scope:** saturation, slew, GBW rolloff inside \(a(s)\), bias current, clipping.

---

## 2. Derivation of A(s)

**Step 1 — KCL with \(I_-=0\):**

\[
\frac{V_--V_\mathrm{IN}}{R_\mathrm{in}}+\frac{V_--V_\mathrm{OUT}}{R_f}=0.
\]

**Step 2 — Eliminate \(V_\mathrm{OUT}\) via \(V_\mathrm{OUT}=-a(s)\,V_-\):**

\[
V_-(s)=\frac{V_\mathrm{IN}(s)\,R_f}{R_f+R_\mathrm{in}+a(s)\,R_\mathrm{in}}.
\]

**Step 3 — Closed-loop transfer \(A(s)=V_\mathrm{OUT}/V_\mathrm{IN}\):**

\[
\boxed{A(s)=-\,\frac{a(s)\,R_f}{R_f+R_\mathrm{in}+a(s)\,R_\mathrm{in}}
=-\frac{R_f}{R_\mathrm{in}}\cdot
\frac{a(s)}{a(s)+1+R_f/R_\mathrm{in}}.}
\]

**Step 4 — Ideal limit (final stage only):**

\[
\lim_{a(s)\to\infty}A(s)=-\frac{R_f}{R_\mathrm{in}},
\qquad
\lim_{a(s)\to\infty}V_-(s)=0.
\]

For the worked values, \(A(s)=-10\) and \(V_\mathrm{OUT}=-10\,\mathrm{V}\). With \(V_-=0\): \(I_{R_\mathrm{in}}=-0.1\,\mathrm{mA}\), \(I_{R_f}=+0.1\,\mathrm{mA}\); KCL sum is zero.

MemNet does **not** take this limit or evaluate `law` LaTeX. It stores stamps for the agent.

---

## Related

| Path | Role |
|------|------|
| [`inverting-amplifier-gql-case-study.md`](inverting-amplifier-gql-case-study.md) | **GQL wire teach** (same topology) |
| [`../llm-nodal-analysis-formulas.md`](../llm-nodal-analysis-formulas.md) | Node method (GQL) |
| [`../llm-circuit-schematic.md`](../llm-circuit-schematic.md) | Schematic / s-domain (GQL) |
