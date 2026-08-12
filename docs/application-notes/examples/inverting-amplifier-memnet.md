# Inverting amplifier — math SSOT (+ retired Layer encoding)

> **Wire teach (1.x):** **GQL only** — [`inverting-amplifier-gql-case-study.md`](inverting-amplifier-gql-case-study.md) and [`../../grammar/gql-wire-profile.md`](../../grammar/gql-wire-profile.md).  
> **This file:** closed-loop transfer **math derivation** remains SSOT for §§1–2. The Layer ASCII encoding below is **retired historical** (not agent wire). Do **not** teach Layer / Tier A.

Derive the closed-loop transfer **A(s)** from Ohm, KCL, and a **finite** open-loop gain **a(s)**; take the ideal limit **only at the end**. MemNet **states** stamps and results; it does **not** solve them.

**Notation:** **a(s)** — open-loop gain, \(V_\mathrm{OUT} = a(s)\,(V_+ - V_-)\). **A(s)** — closed-loop stage transfer, \(V_\mathrm{OUT}/V_\mathrm{IN}\). Param **`a_s`** / field **`A_s`** hold numeric values; `domain=s` marks the Laplace frame.

**British English.** ASCII. Historical Layer sections below are archive-flavoured only.

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

---

## 3. Retired Layer encoding (historical)

| Idea | Shape |
|------|--------|
| Device / law leaf | **`CST`** with `ports=` + `law=` (LaTeX on NODE) |
| Terminal | One port bag: `name: {direc=…, V=@…, I=@…}` — across + through on **one** port |
| Copper / ideal pipe | Port↔port **`--bind-->`** / **`--bind--`** — **no** `law=` on EDGE |
| Chart / semantic | Bare-id relation (not used for copper here) |
| Params | `R=`, `a_s=`, `A_s=` on the NODE |

**MUSTNOT:** formula-on-EDGE (`derives`); mix `[Node.port]` ↔ bare `[Node]`; invent B (`def=`/`uses=`).

### 3.1 Devices (present form)

Alias primary teach — keep `@` in bag and in `law=`:

```text
CST [CST_Vin] ; name=Vin ; Vin=1.0 ; ports=p: {direc=out, V=@vin, I=@iin} ; law=$@vin=Vin$
CST [CST_Rin] ; name=Rin ; R=10000 ; ports=a: {direc=inout, V=@va_r, I=@ia_r},b: {direc=inout, V=@vb_r, I=@ib_r} ; law=$@va_r-@vb_r=@ia_r*R$,$@ia_r=-@ib_r$
CST [CST_Rf] ; name=Rf ; R=100000 ; ports=a: {direc=inout, V=@va_f, I=@ia_f},b: {direc=inout, V=@vb_f, I=@ib_f} ; law=$@va_f-@vb_f=@ia_f*R$,$@ia_f=-@ib_f$
CST [CST_U1] ; name=opamp ; a_s=1000000 ; ports=inp: {direc=in, V=@vp, I=@ip},inm: {direc=in, V=@vm, I=@im},out: {direc=out, V=@vo, I=@io} ; law=$@ip=0$,$@im=0$,$@vo=a_s*(@vp-@vm)$
CST [CST_Gnd] ; name=VGND ; ports=a: {direc=inout, V=@vg, I=@ig} ; law=$@vg=0$
CST [CST_A] ; name=closed_loop ; a_s=1000000 ; Rin=10000 ; Rf=100000 ; A_s=-10.0 ; A_s_lim=-10.0 ; Vin=1.0 ; Vout=-10.0 ; ports=in: {direc=in, V=@vin_a},out: {direc=out, V=@vout_a} ; law=$@vout_a=@vin_a*A_s$,$A_s=-(Rf/Rin)*a_s/(a_s+1+Rf/Rin)$,$A_s_lim=-(Rf/Rin)$
```

Finite \(a_s\) lives on **`CST_U1`** and **`CST_A`**. Virtual ground is the **limit** \(V_-\to 0\) as \(a_s\to\infty\) — do not seed it as an independent axiom before the limit.

### 3.2 Binds (topology)

```text
E_vin [CST_Vin.p] --bind--> [CST_Rin.a] ; carries=I
E_sum_r [CST_Rin.b] --bind-- [CST_U1.inm] ; carries=I
E_sum_f [CST_Rf.b] --bind-- [CST_U1.inm] ; carries=I
E_out_f [CST_U1.out] --bind-- [CST_Rf.a] ; carries=I
E_inp [CST_U1.inp] --bind-- [CST_Gnd.a] ; carries=I
E_A_in [CST_Vin.p] --bind--> [CST_A.in]
E_A_out [CST_U1.out] --bind--> [CST_A.out]
```

Star at `VMINUS`: both `Rin.b` and `Rf.b` bind to `U1.inm` (voltage continuity on the bind; KCL from \(I_-=0\) + resistor laws). Optional named-function **A** (Sum-style CST + binds) is unused here — Ohm / gain stay on device CSTs.

Historical Layer golden (archive only): [`../../grammar/archive/examples-layer/`](../../grammar/archive/examples-layer/).

---

## 4. Mutate seed (create)

Omit session-default `recycle=persistent`. Prefix `+` for create:

```text
+ CST [CST_Vin] ; name=Vin ; Vin=1.0 ; ports=p: {direc=out, V=@vin, I=@iin} ; law=$@vin=Vin$
+ CST [CST_Rin] ; name=Rin ; R=10000 ; ports=a: {direc=inout, V=@va_r, I=@ia_r},b: {direc=inout, V=@vb_r, I=@ib_r} ; law=$@va_r-@vb_r=@ia_r*R$,$@ia_r=-@ib_r$
+ CST [CST_Rf] ; name=Rf ; R=100000 ; ports=a: {direc=inout, V=@va_f, I=@ia_f},b: {direc=inout, V=@vb_f, I=@ib_f} ; law=$@va_f-@vb_f=@ia_f*R$,$@ia_f=-@ib_f$
+ CST [CST_U1] ; name=opamp ; a_s=1000000 ; ports=inp: {direc=in, V=@vp, I=@ip},inm: {direc=in, V=@vm, I=@im},out: {direc=out, V=@vo, I=@io} ; law=$@ip=0$,$@im=0$,$@vo=a_s*(@vp-@vm)$
+ CST [CST_Gnd] ; name=VGND ; ports=a: {direc=inout, V=@vg, I=@ig} ; law=$@vg=0$
+ CST [CST_A] ; name=closed_loop ; a_s=1000000 ; Rin=10000 ; Rf=100000 ; A_s=-10.0 ; A_s_lim=-10.0 ; Vin=1.0 ; Vout=-10.0 ; ports=in: {direc=in, V=@vin_a},out: {direc=out, V=@vout_a} ; law=$@vout_a=@vin_a*A_s$,$A_s=-(Rf/Rin)*a_s/(a_s+1+Rf/Rin)$,$A_s_lim=-(Rf/Rin)$
+ E_vin [CST_Vin.p] --bind--> [CST_Rin.a] ; carries=I
+ E_sum_r [CST_Rin.b] --bind-- [CST_U1.inm] ; carries=I
+ E_sum_f [CST_Rf.b] --bind-- [CST_U1.inm] ; carries=I
+ E_out_f [CST_U1.out] --bind-- [CST_Rf.a] ; carries=I
+ E_inp [CST_U1.inp] --bind-- [CST_Gnd.a] ; carries=I
+ E_A_in [CST_Vin.p] --bind--> [CST_A.in]
+ E_A_out [CST_U1.out] --bind--> [CST_A.out]
```

At \(a_s=10^6\) the pin-map absolutes match the ideal limit (`A_s=-10`, `Vout=-10`).

---

## 5. How to test with MCP

1. **`session_open`** — `session=inv_amp_demo`; optional `seed_lines` from §4.
2. **`add`** — if not seeded at open.
3. **`pin_map`** — `anchor=CST_A` (optional `view=shell`): closed-loop `law=`, binds into `in`/`out`.
4. **`pin_map`** — `anchor=CST_U1`: finite-gain law + binds at `inm` / `out` / `inp`.
5. **`update`** — `~ [CST_U1] ; a_s=1000` and re-evaluate §2; write new `A_s` / `Vout` on `CST_A`; virtual ground fails if \(a_s\) is too small.

CLI: `memnet query pin-map --anchor CST_A`.

---

## 6. Retired Tier A / Layer (archive only)

Flat CMP/PIN/NET + self-loop `derives` and Layer ASCII are **not** product accept or teach. Quarantine: [`../../grammar/archive/`](../../grammar/archive/). **1.x wire:** [`inverting-amplifier-gql-case-study.md`](inverting-amplifier-gql-case-study.md).

---

## 7. What MemNet does not do

- Take limits or solve algebra; no SPICE.
- Evaluate `law=` LaTeX (storage/display for the agent).
- Treat virtual ground as an axiom independent of \(a(s)\).

---

## Related

- [`inverting-amplifier-gql-case-study.md`](inverting-amplifier-gql-case-study.md) — **primary GQL wire teach**
- [`../llm-nodal-analysis-formulas.md`](../llm-nodal-analysis-formulas.md) — node method (GQL)
- [`../llm-circuit-schematic.md`](../llm-circuit-schematic.md) — schematic / s-domain (GQL)
- [`../../grammar/archive/`](../../grammar/archive/) — quarantined Layer sources
