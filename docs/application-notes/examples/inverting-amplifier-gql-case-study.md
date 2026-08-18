# Inverting amplifier — GQL-wire MemNet case study

Work the known inverting op-amp topology through the **post ADR-001** model: openCypher-shaped **GQL** as agent wire, **shaped `pin_map`** as primary read.

**Product shape:** [`../../SHAPE.md`](../../SHAPE.md). **Brand:** MemNet (Net of Memory). **Not shipped behaviour** — teach sketch aligned with [`../../grammar/gql-wire-profile.md`](../../grammar/gql-wire-profile.md).  
**Open:** `SCHEMA CST` (+ `TSK`) in `map_lines` — no bundled circuit map. Device `CST_*` / bind `E_*` ids here are **canonical ground** for this netlist. Goldfish `TSK` uses `id:'NEW'`.  
**Derivation SSOT (math):** [`inverting-amplifier-memnet.md`](inverting-amplifier-memnet.md) §§1–2.  
**Decision:** [`../../adr/ADR-001-gql-agent-wire.md`](../../adr/ADR-001-gql-agent-wire.md).  
**Paradox (GQL wire):** [`../../grammar/gql-model-exam.md`](../../grammar/gql-model-exam.md) (historical filename).  
British English. ASCII ids.

---

## 1. Topology (same circuit)

```text
Vin -- Rin -- VMINUS ---- U1 ---- Vout
                |                  |
                +------- Rf -------+
(IN+) ---------- VGND
```

Worked values: \(R_\mathrm{in}=10\,\mathrm{k\Omega}\), \(R_f=100\,\mathrm{k\Omega}\), \(V_\mathrm{IN}=1\,\mathrm{V}\), finite \(a_s=10^6\).

MemNet **states** stamps; it does **not** solve the network.

---

## 2. Property-graph encoding (GQL-shaped)

### 2.1 Labels, properties, law-on-node

| Construct | Convention in this sketch |
|-----------|---------------------------|
| **Label** | `:CST` (constitutive / device leaf) |
| **Stable id** | property `id` (house pin) |
| **Law** | node property `law` (LaTeX string) — **never** on a relationship |
| **Ports** | node property `ports` (map / structured bag) — `PortIncidence` |
| **Params** | ordinary node properties (`R`, `a_s`, …) |

### 2.2 Dual EDGE as relationship types

| Grain | Relationship type | Endpoints |
|-------|-------------------|-----------|
| **Bind** (copper / ideal pipe) | `:bind` | Port-qualified via `fromPort` / `toPort` properties (M1 may freeze an alternate) |
| **Relation** (chart / semantic) | e.g. `:about` | Bare node ids only |

**MUST NOT** put Ohm / KCL / gain on a relationship. Continuity is implied by `:bind`.

### 2.3 Mutate sketch (openCypher-shaped)

Illustrative create patterns (gated mutate; not unbounded DBA script). **Ground ids** for the canonical netlist (MERGE / known `id`). Do **not** mint these devices with goldfish `NEW`.

```cypher
CREATE (vin:CST {
  id: 'CST_Vin', name: 'Vin', Vin: 1.0,
  ports: {p: {direc: 'out', V: '@vin', I: '@iin'}},
  law: '$@vin=Vin$'
})
CREATE (rin:CST {
  id: 'CST_Rin', name: 'Rin', R: 10000,
  ports: {
    a: {direc: 'inout', V: '@va_r', I: '@ia_r'},
    b: {direc: 'inout', V: '@vb_r', I: '@ib_r'}
  },
  law: '$@va_r-@vb_r=@ia_r*R$,$@ia_r=-@ib_r$'
})
CREATE (rf:CST {
  id: 'CST_Rf', name: 'Rf', R: 100000,
  ports: {
    a: {direc: 'inout', V: '@va_f', I: '@ia_f'},
    b: {direc: 'inout', V: '@vb_f', I: '@ib_f'}
  },
  law: '$@va_f-@vb_f=@ia_f*R$,$@ia_f=-@ib_f$'
})
CREATE (u1:CST {
  id: 'CST_U1', name: 'opamp', a_s: 1000000,
  ports: {
    inp: {direc: 'in', V: '@vp', I: '@ip'},
    inm: {direc: 'in', V: '@vm', I: '@im'},
    out: {direc: 'out', V: '@vo', I: '@io'}
  },
  law: '$@ip=0$,$@im=0$,$@vo=a_s*(@vp-@vm)$'
})
CREATE (gnd:CST {
  id: 'CST_Gnd', name: 'VGND',
  ports: {a: {direc: 'inout', V: '@vg', I: '@ig'}},
  law: '$@vg=0$'
})
CREATE (cl:CST {
  id: 'CST_A', name: 'closed_loop',
  a_s: 1000000, Rin: 10000, Rf: 100000,
  A_s: -10.0, A_s_lim: -10.0, Vin: 1.0, Vout: -10.0,
  ports: {
    in: {direc: 'in', V: '@vin_a'},
    out: {direc: 'out', V: '@vout_a'}
  },
  law: '$@vout_a=@vin_a*A_s$,$A_s=-(Rf/Rin)*a_s/(a_s+1+Rf/Rin)$,$A_s_lim=-(Rf/Rin)$'
})

MATCH (vin:CST {id:'CST_Vin'}), (rin:CST {id:'CST_Rin'})
CREATE (vin)-[:bind {id:'E_vin', fromPort:'p', toPort:'a', carries:'I'}]->(rin)

MATCH (rin:CST {id:'CST_Rin'}), (u1:CST {id:'CST_U1'})
CREATE (rin)-[:bind {id:'E_sum_r', fromPort:'b', toPort:'inm', carries:'I'}]->(u1)

MATCH (rf:CST {id:'CST_Rf'}), (u1:CST {id:'CST_U1'})
CREATE (rf)-[:bind {id:'E_sum_f', fromPort:'b', toPort:'inm', carries:'I'}]->(u1)

MATCH (u1:CST {id:'CST_U1'}), (rf:CST {id:'CST_Rf'})
CREATE (u1)-[:bind {id:'E_out_f', fromPort:'out', toPort:'a', carries:'I'}]->(rf)

MATCH (u1:CST {id:'CST_U1'}), (gnd:CST {id:'CST_Gnd'})
CREATE (u1)-[:bind {id:'E_inp', fromPort:'inp', toPort:'a', carries:'I'}]->(gnd)

MATCH (vin:CST {id:'CST_Vin'}), (cl:CST {id:'CST_A'})
CREATE (vin)-[:bind {id:'E_A_in', fromPort:'p', toPort:'in'}]->(cl)

MATCH (u1:CST {id:'CST_U1'}), (cl:CST {id:'CST_A'})
CREATE (u1)-[:bind {id:'E_A_out', fromPort:'out', toPort:'out'}]->(cl)
```

Optional **relation** grain (not copper) — e.g. a task about the closed-loop result:

```cypher
CREATE (tsk:TSK {id:'NEW', status:'active', title:'Confirm A_s limit'})
# copy minted TSK id, then:
MATCH (tsk:TSK {id:'TSK_inv_gain'}), (cl:CST {id:'CST_A'})
CREATE (tsk)-[:about {id:'NEW'}]->(cl)
```

---

## 3. Shaped `pin_map` read (Write = display redefined)

Agent goldfish read is **not** a raw binding table such as:

```text
// NON-GOAL as primary read
MATCH (n)-[r]->(m) RETURN n, r, m
```

Instead, `pin_map(anchor='CST_U1', depth=2, view='shell')` wraps GQL internally and returns a **bounded shaped subgraph** — openCypher-family graph lines the agent can copy when mutating:

```cypher
// shaped emit (illustrative — same family as mutate, ego-bounded)
(:CST {id:'CST_U1', name:'opamp', a_s:1000000, law:'$@ip=0$,$@im=0$,$@vo=a_s*(@vp-@vm)$', ...})
(:CST {id:'CST_Rin', name:'Rin', R:10000, ...})
(:CST {id:'CST_Rf', name:'Rf', R:100000, ...})
(:CST {id:'CST_Gnd', name:'VGND', ...})
(:CST {id:'CST_A', name:'closed_loop', A_s:-10.0, ...})
(:CST {id:'CST_U1'})-[:bind {id:'E_sum_r', fromPort:'b', toPort:'inm'}]->(:CST {id:'CST_Rin'})
(:CST {id:'CST_U1'})-[:bind {id:'E_sum_f', fromPort:'b', toPort:'inm'}]->(:CST {id:'CST_Rf'})
(:CST {id:'CST_U1'})-[:bind {id:'E_out_f', fromPort:'out', toPort:'a'}]->(:CST {id:'CST_Rf'})
(:CST {id:'CST_U1'})-[:bind {id:'E_inp', fromPort:'inp', toPort:'a'}]->(:CST {id:'CST_Gnd'})
(:CST {id:'CST_U1'})-[:bind {id:'E_A_out', fromPort:'out', toPort:'out'}]->(:CST {id:'CST_A'})
```

Engine-law rows may prepend when present. Recyclable / out-of-budget neighbours stay hidden (MN-REQ-04).

---

## 4. Where concerns live in the model

| Concern | Location |
|---------|----------|
| Device constitutive law | Node property `law` on `:CST` |
| Port bags (V/I, direc) | Node property `ports` (`PortIncidence`) |
| Copper | Relationship type `:bind` + port endpoint properties |
| Chart / mission links | Other relationship types on bare node ids (`:about`) — **not** `derives` as law |
| Goldfish budget | `PinMapShapedRead` / `pin_map` view+depth+max_rows |
| Durable AgensGraph | Optional later; same GQL family — not this sketch |

Maps to SysML: `GqlCodec`, `PinMapShapedRead`, `GraphStore`, items in `MemNetConnections`.

---

## 5. Historical seed aside (not teach)

Older ASCII Layer-shaped seeds for the same circuit live under derivation notes and [`../../grammar/archive/examples-layer/`](../../grammar/archive/examples-layer/) — **quarantine only**. **1.x teach:** GQL patterns + shaped `pin_map` above.

---

## 6. Related

| Path | Role |
|------|------|
| [`../../SHAPE.md`](../../SHAPE.md) | Product shape |
| [`inverting-amplifier-memnet.md`](inverting-amplifier-memnet.md) | Full derivation (math) |
| [`../llm-circuit-schematic.md`](../llm-circuit-schematic.md) | Circuit doctrine (body M3) |
| [`../../grammar/gql-wire-profile.md`](../../grammar/gql-wire-profile.md) | M1 wire SSOT |
| [`../../grammar/gql-model-exam.md`](../../grammar/gql-model-exam.md) | GQL-wire paradox (historical filename) |
| [`../../../sysml-models/README.md`](../../../sysml-models/README.md) | Nested SysML outline |
