# SysML + MemNet atomisation patterns (user pack)

Use with [atomisation.md](../../mcp-memnet/references/atomisation.md), [sysml-memnet-snap.md](sysml-memnet-snap.md), and [sysml-memnet-cookbook-bridge.md](sysml-memnet-cookbook-bridge.md).

**Core discipline:** one row = one fact/link/status. Short fields. Explicit edges. Stable ids from the pin map. **MUST NOT** create nodes labelled PARTD, PORTD, BEHD, or TASK (old aliases -- re-snap to unified kinds on warm miss).

Agent I/O: MemNet **GQL / openCypher-shaped** wire only ([memnet-format](../../memnet-format/SKILL.md)). Do not teach pipe `@TAG:|` rows. pin_map returns a shaped subgraph.

## Canonical kinds

ART, SEC, CLM, ENT, PKG, PRT, POR, CON, BEH, ITM, REQ, MOD, SYM, CONV, DEC, ISSUE, TSK, USR, plus edges.

| Field | Notes |
|-------|-------|
| PRT.role | short domain tag (`power`, `compute`, `deploy`); empty if N/A |
| POR.dir | `in` / `out` / `inout` for port usages |
| POR.typeRef | typed port/protocol name (for `typedBy` edge) |
| CON.ends | endA / endB usage path |
| BEH.owner | owning PRT usage id or package qname |
| DEC.task | parent TSK id; short options; chosen when decided |
| ISSUE.code | <=15 words backlog item |

## Stable id rules

| Kind | Id pattern | Example |
|------|------------|---------|
| TSK | `TSK_model_<short>` / `TSK_diagram_<figureId>` | `TSK_model_vfdl2` |
| PKG | `PKG_<packageSuffix>` | `PKG_FoamLiteVer2Deploy` |
| MOD | `MOD_<file_slug>` | `MOD_deploy_vfdl2` |
| PRT / POR / CON / BEH / ITM | `PRT_<name>` etc. | `PRT_edgePc` |
| REQ | `REQ_<requirementId>` | `REQ_VFDL2-MQTT-RELAY` |
| SYM | `SYM_<name>` | `SYM_edgePc` |
| CONV / DEC / ISSUE | `CONV_<topic>` / `DEC_<nn>` / `ISS_<nn>` | `DEC_01` |

## kind enums (closed lists)

| Kind | Allowed `kind` values |
|------|------------------------|
| PRT | partDef, partUsage |
| POR | portDef, portUsage |
| CON | connectionDef, connectionUsage, linkUsage |
| BEH | stateMachine, action, calculation |
| ITM | itemDef, flowItem |
| SYM | partDef, partUsage, portDef, portUsage, requirement, connection, behaviour, satisfy, allocate, package |
| PKG | deploy, requirements, connections, behaviour, root, library, common |
| ART | report, interconnection, behaviour, requirements, traceability |
| CLM.type | fact, decision, assumption, convention, conclusion, stat |
| TSK.phase | model, sync, audit, refactor, report, verify, turn, route |

## ITM is a node

`ITM` is a **NODE only**: an item definition or flow item. It is never an edge. Use `declaredIn` to link an ITM to its package and optionally `flowOf` to link a flow item to its item definition. Ports and connections remain `POR` and `CON`; do not model them as ITM edges.

```cypher
CREATE (i:ITM {id: 'ITM_LaserFrame', name: 'LaserFrame', kind: 'itemDef', recycle: 'persistent'})
CREATE (f:ITM {id: 'ITM_LaserFrameFlow', name: 'LaserFrameFlow', kind: 'flowItem', recycle: 'persistent'})
CREATE (i)-[:DECLAREDIN {id: 'E01', recycle: 'persistent'}]->(:PKG {id: 'PKG_LaserComm'})
CREATE (f)-[:FLOWOF {id: 'E02', recycle: 'persistent'}]->(i)
```

## Recycle

- `persistent` -- structure, claims, campaign TSK
- `delete_on_settle` -- DEC, ISSUE, sync/refactor sub-tasks

## SysML construct -> MemNet

| SysML v2 | MemNet | Same-batch edges (required) |
|----------|--------|------------------------------|
| part def / usage | PRT + SYM | declaredIn -> PKG; inFile -> MOD |
| port def / usage | POR + SYM | declaredIn; parent PRT hasPort -> POR; typedBy if typed |
| connection / link | CON + SYM | declaredIn; typedBy -> CONDEF_* |
| requirement | REQ + SYM | declaredIn -> requirements PKG |
| satisfy | edge only `satisfies` | PRT/BEH -> REQ |
| allocate | edge only `allocates` | BEH/PRT -> PRT |
| state / action | BEH + SYM | declaredIn |
| item / flow | ITM | declaredIn; optional flowOf |
| convention | CONV | TSK constrained_by -> CONV |
| open fork | DEC | TSK owns -> DEC |
| backlog | ISSUE or CLM assumption | TSK/SEC contains |

**Batch rule:** every new PRT / POR / CON MUST include `declaredIn` + `inFile` in the same `mutate`. Cross-package types MUST include `typedBy`.

## Edge relations (closed list)

Copy these spellings exactly (session registry). Engine-generic new edges outside this list prefer English verb / snake tokens (MemNet `docs/grammar/`); do not dual-spell the same link.

`satisfies`, `allocates`, `declaredIn`, `hasPort`, `typedBy`, `connects`, `realizes`, `owns`, `inFile`, `contains`, `mentions`, `constrained_by`, `dependsOn`, `audits`, `flowOf`, `declaredAs`

Diagram placement (`TSK_diagram_*`): `figure_includes`, `figure_uses`, `anchor_of`, `adjacent_to`, `documents` -- see [sysml-memnet-pipeline.md](sysml-memnet-pipeline.md).

## Example (GQL / openCypher-shaped)

```cypher
CREATE (t:TSK {goal: 'Model 6U CubeSat PDU', phase: 'model', status: 'in_progress', recycle: 'persistent'})
CREATE (pkg:PKG {qname: 'project/pdu-controller', kind: 'deploy', status: 'active', recycle: 'persistent'})
CREATE (m:MOD {path: 'models/deploy-pdu.sysml', role: 'deploy', status: 'active', recycle: 'persistent'})
CREATE (p:PRT {name: 'PDUController', kind: 'partUsage', role: 'power', status: 'active', recycle: 'persistent'})
CREATE (por:POR {name: 'pwr_in_28v', kind: 'portUsage', dir: 'in', typeRef: 'Power28V', status: 'active', recycle: 'persistent'})
CREATE (r:REQ {requirementId: 'REQ-01', text: 'Total output 15 W avg 20 W peak', status: 'active', recycle: 'persistent'})
CREATE (s:SYM {name: 'PDUController', kind: 'partUsage', path: 'models/deploy-pdu.sysml', line: 42, recycle: 'persistent'})
CREATE (t)-[:OWNS {note: 'scope', recycle: 'persistent'}]->(m)
CREATE (p)-[:DECLAREDIN {recycle: 'persistent'}]->(pkg)
CREATE (p)-[:INFILE {note: 'loc', recycle: 'persistent'}]->(m)
CREATE (p)-[:HASPORT {recycle: 'persistent'}]->(por)
CREATE (p)-[:SATISFIES {recycle: 'persistent'}]->(r)
```

Copy assigned ids from the pin_map / mutate response. Port-port links use BIND; node-node use typed rels ([memnet-format](../../memnet-format/SKILL.md)).

## Anchor strategy

- Campaign -> `TSK_model_<short>`
- Mermaid figure -> `TSK_diagram_<figureId>`
- Part/port under edit -> `PRT_<name>` / `POR_<name>` / `SYM_<name>`
- Requirement audit -> `REQ_<requirementId>`
- Pending choice -> `DEC_<nn>`
- Convention -> `CONV_<topic>`
- Outputs section -> SEC id

Pin-map depth 2 default; increase only when needed.

## Quick kind reference

| Kind | Purpose |
|------|---------|
| PKG / MOD | Package / `.sysml` file |
| PRT / POR / CON / BEH / ITM / REQ | Model structure |
| SYM | Edit locator (path + line) |
| CONV / DEC / ISSUE | Convention / fork / backlog |
| ART / SEC / CLM | Outputs / claims |
| TSK | Campaign anchor |
| Edge | Typed relation |

Cross-ref: [mcp-memnet](../../mcp-memnet/SKILL.md) · [memnet-format](../../memnet-format/SKILL.md)
