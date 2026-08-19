# Case study: durable hydrate / flush (M2.5)

**Shelf:** product canon

Evidence walk against SysML under `sysml-models/models/`.  
Companions: [company-memory-case-study.md](company-memory-case-study.md), [snapshot-passport-case-study.md](snapshot-passport-case-study.md).

**Wire:** GQL / shaped `pin_map` only. **Status:** M2.5 **0.7** Agens live hydrate/flush proven; optional Neo4j client not live-claimed; cabinets external / not vendored.

## 1. Purpose

Show how a mission or company ego **survives process death**: settled / durable pins flush into `DurableBuffer` / `AgensGraphAdapter`, then hydrate into a **new** live session under pin/depth/view budget. Session id remains the agent handoff handle; the LLM talks to **MemNet**, never to the store as primary.

## 2. Model locus

| Concern | Model element |
|---------|----------------|
| Parts | `DurableBuffer`, `DurableSyncOwner`, `AgensGraphAdapter`, `Neo4jAdapter`, `DurableCabinet` (`Neo4jCabinetServer` / `AgensGraphCabinetServer`), `OperatorDurableSites`, `SessionLifecycle` hydrate/flush ports |
| Connections | `DurableHydrateFlow`, `DurableFlushFlow` |
| Behaviour | `DurableHydrateFlushRoadmap` (`EvHydrateFromDurable`, `EvFlushToDurable`) |
| Items | `DurableGraphStore` (connections), `MissionWorkingSet` / `SharedLlmMemory` |
| Requirement | MN-REQ-06.4 (`DurableStoreBehindMemNet`); MN-REQ-06.5 / 06.6 (external cabinet / evidence ≠ claim) |
| Contrast | `SnapshotStore` (session file save/load) - see [snapshot-passport-case-study.md](snapshot-passport-case-study.md) |

## 3. Scenario

**Title:** Company analytical ego outlives the MCP process

**Premise:** Role D pins (`COM_*`) and a settled mission task live in session `sess_mission_42`. The host process dies. A new process opens a **new** session and hydrates the durable ego under budget.

### Steps

| Step | Action | Model |
|------|--------|--------|
| 1 | Agents work via MemNet MCP / pin_map / mutate | `SharedLlmMemory` / `AgentMemory` |
| 2 | Settle durable facts; mark flush candidates | `HousekeepSettle` / settled `TSK_*` |
| 3 | Flush session subgraph -> durable store | `EvFlushToDurable` -> `flushing` |
| 4 | Process exit | live `GraphStore` gone |
| 5 | New process; open **new** session id | `EvOpenSession` (new handle) |
| 6 | Hydrate under pin/depth/view budget | `EvHydrateFromDurable` -> `hydrating` |
| 7 | Lead/worker handoff by **new** session id | `SessionHandoff` - not store credentials |

### Illustrative GQL (live session after hydrate)

```cypher
// Hydrated under budget - ego slice, not whole store dump
CREATE (c:Company {id: 'COM_acme', name: 'Acme'})
CREATE (t:Task {id: 'TSK_mission_q3', status: 'settled'})
CREATE (t)-[:ABOUT]->(c)
```

Agents continue with `pin_map(anchor='COM_acme', depth=2, max_rows=50)` on the **new** session. They do **not** open a direct AgensGraph or Neo4j/Bolt client.

```mermaid
flowchart LR
  LLM[LLM agents] --> MemNet[SharedLlmMemory / SessionLifecycle]
  MemNet -->|EvFlushToDurable| DB[DurableBuffer / cabinet adapter]
  DB -->|EvHydrateFromDurable| MemNet
  LLM -.->|MUST NOT primary| DB
```

## 4. Gates

| MUST | MUST NOT |
|------|----------|
| MemNet sole agent-facing memory | LLM <-> DurableGraphStore as teach path |
| One sync owner for hydrate/flush | Dual-write without owner |
| Budget hydrate (pin/depth/view) | Unbounded whole-store load into context |
| Session id as handoff handle | Hand store connection strings in chat as SSOT |

## 5. As-is vs to-be

| | As-is | Target / leftover |
|--|-------|-------------------|
| Client adapter | **Landed** — `DurableStoreAdapter`, `FakeDurableAdapter`, optional `AgensGraphAdapter` (`memnet-llm[agensgraph]`; `liveCabinetClaimed=true` in 0.7), optional `Neo4jAdapter` (`memnet-llm[neo4j]`; `liveNeo4jClaimed=false`), `DurableSyncOwner`, `SessionLifecycle.hydrate_from_durable` / `flush_to_durable` | Keep Fake as CI seam |
| External server part | **Modelled** — `DurableCabinet` (Neo4j on Pi operator host; AgensGraph still a possible kind); not in wheel; not on 2 GiB droplet; **no graph id on the server part** | Operator soak ≠ product live Neo4j claim; edge `id` is present MERGE key |
| `company_ego_fixture` leftover | Only COM ego id is parameterised; neighbour `TSK_mission_q3` / edge `E_about_q3` are global MERGE keys | Two egos not isolated (`COM_soak_pi` then `COM_droplet_pi`); per-ego live proof **not** green; do not patch fixture in this cut |
| Live cabinet | Agens external / operator-proven (0.7); Neo4j client not live-claimed; **not** vendored; skip live marks unless URL | Not a hosted product service |
| Satisfy | MN-REQ-06.4 on `DurableBuffer`; 06.5 / 06.6 on `DurableCabinet` + operator sites | Live Neo4j claim stays false |

## 6. Related

| Study | Distinction |
|-------|-------------|
| [snapshot-passport-case-study.md](snapshot-passport-case-study.md) | Named session **file** save/load (MN-REQ-01.4/01.5) |
| [company-memory-case-study.md](company-memory-case-study.md) | `COM_*` pattern that would flush/hydrate |
| [async-parallel-conflict-case-study.md](async-parallel-conflict-case-study.md) | Live Multitask; durable is orthogonal |
