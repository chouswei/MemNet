# Nodal analysis — circuit domain (ports / law / bind)

> **Dialect (product 0.8):** **GQL only** — [`../grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md). Do **not** teach Layer / Tier A. Wire: [`examples/inverting-amplifier-gql-case-study.md`](examples/inverting-amplifier-gql-case-study.md).

**Teach:** GQL wire profile + shaped `pin_map` + gated mutate.  
**Documentation only** — does **not** implement a solver.  
**British English.** ASCII.

Doctrine: [`gql-wire-profile.md`](../grammar/gql-wire-profile.md). Formula-on-relationship (`derives` / `feeds`) is **retired** — short pointer in §8, not dual teach.

Complements:

- [`llm-circuit-schematic.md`](llm-circuit-schematic.md) — schematic / s-domain GQL grain
- [`examples/inverting-amplifier-gql-case-study.md`](examples/inverting-amplifier-gql-case-study.md) — InvAmp GQL wire
- [`examples/inverting-amplifier-memnet.md`](examples/inverting-amplifier-memnet.md) — math SSOT

---

## 1. Classical node method (recap)

| Element | Role |
|---------|------|
| Unknowns | Node voltages \(v_k\) (relative to a reference) |
| KCL | At each non-reference node: sum of currents into the node = 0 |
| Branch laws | Ohm, sources, \(Z(s)\) — on the **device node** (`law`) |
| System | Sparse stamp → \(G \cdot v = i\) (or s-domain equivalent) |

MemNet stores **topology (`:bind`) + absolute numbers + law LaTeX**. It does **not** assemble or invert \(G\).

---

## 2. Circuit concept → GQL shape

Do not conflate MemNet node with circuit node.

| Circuit concept | GQL shape |
|-----------------|-----------|
| Two-terminal / device | **`:CST`** with `ports` + `law` + params (`R`, …) |
| Terminal (across + through) | **One port bag** — `name: {direc:…, V:'@…', I:'@…'}` (not a separate `PIN` atom) |
| Equipotential / copper | Port↔port **`:bind`** with `fromPort`/`toPort` (optional `carries:'I'`) |
| Reference / ground | `:CST` with `law` fixing \(V=0\), or a port bound to that ground |
| KCL residual (optional stamp) | Thin `:CST` with ports for incident currents + `law` sum = 0 — **or** leave KCL implied by \(I_-=0\) + resistor laws at a star bind |
| Closed-loop result | `:CST` with params `A_s` / `law` for \(A(s)\) |

**MUST NOT:** `law` on a relationship; teach Layer ASCII / `connects_to` / paren arrows as primary; invent B (`def`/`uses` as peer ontology).

Teach **`direc`** (`in` / `out` / `inout`); omit session-default `recycle`.

---

## 3. Dual relationship grains (locked)

| Grain | Endpoints | Type | Use |
|-------|-----------|------|-----|
| **Bind** | Port-qualified via `fromPort`/`toPort` | **`:bind`** only | Copper / ideal continuity |
| **Relation** | Bare node ids | Open type (`:owns`, `:about`, …) | Chart / semantic — not copper |

```cypher
(:CST {id:'CST_R'})-[:bind {id:'E1', fromPort:'a', toPort:'p', carries:'I'}]->(:CST {id:'CST_Src'})
(:CST {id:'CST_Stage'})-[:about {id:'E2'}]->(:CST {id:'CST_R'})
```

---

## 4. Ohm and KCL on the node

### 4.1 Ohm (branch law)

```cypher
(:CST {
  id:'CST_R', R:10000,
  ports:{a:{direc:'inout', V:'@va', I:'@ia'}, b:{direc:'inout', V:'@vb', I:'@ib'}},
  law:'$@va-@vb=@ia*R$,$@ia=-@ib$'
})
```

### 4.2 KCL at a star

Classical: \(I_1 + I_2 + \cdots = 0\) at a non-reference node.

**Preferred (slim):** bind branch ports that share the equipotential; put \(I=0\) on high-Z device ports; agent checks current sum from port absolutes. No relationship formula.

**Optional explicit stamp:**

```cypher
(:CST {
  id:'CST_KCL', name:'KCL_mid',
  ports:{i1:{direc:'in', q:'@i1'}, i2:{direc:'in', q:'@i2'}, out:{direc:'out', q:'@res'}},
  law:'$@res=@i1+@i2$'
})
```

**Do not** invent a hyper-edge for KCL. **Do not** store a dense \(G\) matrix as one blob.

---

## 5. Reference node / ground

```cypher
(:CST {id:'CST_Gnd', name:'GND', ports:{a:{direc:'inout', V:'@vg', I:'@ig'}}, law:'$@vg=0$'})
```

---

## 6. Absolute on pin map vs law text

| Concern | On pin map | Mutate |
|---------|------------|--------|
| Voltages, currents, R, residual | Absolute numbers / `@` aliases in port bags | `MATCH … SET` with literals |
| Ohm, KCL, gain | **`law` LaTeX on node** | Create/patch node; never put live maths on the relationship |
| Topology | `:bind` between ports | Port grain both ends |

Shaped `pin_map` = goldfish read. Cue then `pin_map`; skip if empty. Agents evaluate offline and write absolutes until an evaluator exists.

---

## 7. Minimal resistive divider (GQL sketch)

```cypher
CREATE (vin:CST {id:'CST_Vin', name:'Vin', Vin:5.0, ports:{p:{direc:'out', V:'@vin', I:'@iin'}}, law:'$@vin=Vin$'})
CREATE (r1:CST {id:'CST_R1', R:1000, ports:{a:{direc:'inout', V:'@va1', I:'@ia1'}, b:{direc:'inout', V:'@vb1', I:'@ib1'}}, law:'$@va1-@vb1=@ia1*R$,$@ia1=-@ib1$'})
CREATE (r2:CST {id:'CST_R2', R:1000, ports:{a:{direc:'inout', V:'@va2', I:'@ia2'}, b:{direc:'inout', V:'@vb2', I:'@ib2'}}, law:'$@va2-@vb2=@ia2*R$,$@ia2=-@ib2$'})
CREATE (gnd:CST {id:'CST_Gnd', name:'GND', ports:{a:{direc:'inout', V:'@vg', I:'@ig'}}, law:'$@vg=0$'})
MATCH (vin:CST {id:'CST_Vin'}), (r1:CST {id:'CST_R1'})
CREATE (vin)-[:bind {fromPort:'p', toPort:'a', carries:'I'}]->(r1)
MATCH (r1:CST {id:'CST_R1'}), (r2:CST {id:'CST_R2'})
CREATE (r1)-[:bind {fromPort:'b', toPort:'a', carries:'I'}]->(r2)
MATCH (r2:CST {id:'CST_R2'}), (gnd:CST {id:'CST_Gnd'})
CREATE (r2)-[:bind {fromPort:'b', toPort:'a', carries:'I'}]->(gnd)
```

Illustrative mid absolutes after a hand solve (equal divider): \(V_\mathrm{mid}=2.5\,\mathrm{V}\), \(I=2.5\,\mathrm{mA}\). Full InvAmp GQL: [`examples/inverting-amplifier-gql-case-study.md`](examples/inverting-amplifier-gql-case-study.md).

---

## 8. Risks for LLM agents

| Risk | Discipline |
|------|------------|
| Solving vs stating | Graph holds stamp + results; **agent / external solver** produces \(v\). No SPICE in-engine. |
| MemNet node ≠ circuit node | Circuit node = equipotential at bound ports; MemNet node = any row. |
| Bind as current sense | Continuity only; signed `I` + `direc` / device `law` carry sense. |
| Formula-on-relationship / `derives` | Retired — do not teach as primary. |
| Layer ASCII / paren arrows | Retired — teach GQL + `:bind` / typed rels. |

---

## 9. Retired Layer / Tier A

Layer ASCII and leftover CMP/PIN/NET + `derives` are **not** product accept or teach. Wire teach = GQL profile only.

---

## 10. Related

| Path | Role |
|------|------|
| [`examples/inverting-amplifier-gql-case-study.md`](examples/inverting-amplifier-gql-case-study.md) | **Primary** InvAmp GQL teach |
| [`examples/inverting-amplifier-memnet.md`](examples/inverting-amplifier-memnet.md) | Math SSOT |
| [`llm-circuit-schematic.md`](llm-circuit-schematic.md) | Schematic / s-domain GQL grain |
| [`../grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md) | GQL wire SSOT |

**This file is documentation only.** Use it to place Ohm/KCL as node `law` beside port binds — without building a circuit solver into MemNet.
