# Roadmap 0.5.0 — one path

**Status:** version map below is the SemVer SSOT. Product shape: [`SHAPE.md`](SHAPE.md). Package **0.9.0** = Neo4j cabinet-client extra (`liveNeo4jClaimed=false`).  
**Audience:** product developers. Agent ops: [`LLM-GUIDE.md`](LLM-GUIDE.md) / [`multi-agent-sessions.md`](multi-agent-sessions.md) — dialect teach = **GQL** ([`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md)).

**Product:** MemNet is **mission working memory for LLMs** — not the search corpus, not GraphRAG. Multi-agent / Multitask sessions, goldfish re-read via shaped `pin_map`, gated mutate. In-session recall is serial cue then neighbourhood. A MemNet **session** can be SSOT for a mission / that shared memory: LLM handoff = deliver **session id** (+ anchors / write scope); peers **re-pin_map** — **MUST NOT** pass a graph dump in chat. Chat is never SSOT ([`multi-agent-sessions.md`](multi-agent-sessions.md)). A durable online GQL store (M2.5) **backs** sessions; it does **not** replace the session handle for agent handoff, and is not the default agent teach surface. **MUST NOT** reframe MemNet as a Cypher proxy to AgensGraph.

**Model:** SysML + grammar for **GQL wire** (`GqlCodec` / `PinMapShapedRead`). Paradox (GQL wire): [`grammar/gql-model-exam.md`](grammar/gql-model-exam.md) (historical filename). Case study: [`application-notes/examples/inverting-amplifier-gql-case-study.md`](application-notes/examples/inverting-amplifier-gql-case-study.md).

---

## Version map (locked)

| Version | Owns | Status |
|---------|------|--------|
| **0.5.0** | Leftover goldfish: paradox V1/V3/V4/V6, BoundedMatchFind (#73) seed-only `find`, multi-ego `pin_map` under one \(M\) + one LAW | **Shipped** (`v0.5.0`) |
| **0.6.0** | Honesty: V5 LAW×N pytest, snapshot as offered durable, version-map docs | **Shipped** (`v0.6.0`) |
| **0.7.0** | Live AgensGraph hydrate/flush; `liveCabinetClaimed=true`. Server not vendored. Fake + skip unless `MEMNET_AGENSGRAPH_URL` | **Shipped** (`v0.7.0`) |
| **0.8.0** | GQL-only **teach** + product **shape for people** (`docs/SHAPE.md`, playbook, application-note contract, Multitask honesty). Docs only. **No** engine cut. Rebase of identity [#87](https://github.com/chouswei/MemNet/pull/87) on 0.7 — cabinet stays claimed | **Shipped** (`v0.8.0`) |
| **0.9.0** | Neo4j `DurableStoreAdapter` client (`memnet-llm[neo4j]`), factory both-URL rule (`MEMNET_DURABLE_BACKEND`), [`grammar/neo4j-buffer.md`](grammar/neo4j-buffer.md). Live round-trip **unclaimed** (`liveNeo4jClaimed=false`). Cabinet extra, not a 1.0 gate | **Shipped** (package 0.9.0; tag by coordinator) |
| **1.0.0** | **0.5 + 0.6 + 0.7 + 0.8** claimed. Product shape mature for people. Not GraphRAG. Not cabinet-only. Not a new engine; Later items stay Later | **Claim next** — PyPI still 0.4.6 |
| **Later** | `Peak_L`, HostSearch ship, N-server (#47), pin-map export (#66), hosted AgensGraph as a product service, live Neo4j round-trip (`liveNeo4jClaimed`) | **Out** — do not hold 0.9 or 1.0 |

**0.8 MUST:** one dialect teach (GQL only; Layer archive only); Write = display = bounded shaped `pin_map`; session id = handoff handle; working memory ≠ corpus (no `rag_query`). Wire SSOT stays [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md). User-pack GQL rewrite is **sibling** (`chouswei/cursor-user-skills`), not this engine repo.

**0.8 MUST NOT:** Peak_L / HostSearch / N-server / export / `rag_query`; second **live** cabinet claim; vendor AgensGraph/Neo4j servers; restore Layer teach or novel-writer; merge stale #87 text that unclaims the Agens cabinet. Optional Neo4j **client** landed in **0.9** with `liveNeo4jClaimed=false`.

**0.9 MUST NOT:** claim `liveNeo4jClaimed`; vendor a Neo4j server; hold **1.0** for live Neo4j, HostSearch, N-server, or Peak_L.

**1.0 MUST NOT** wait on the Later row.

---

## Where we are (M-phases)

| Phase | Owns | Shipped? |
|-------|------|----------|
| **M1** | GQL wire profile SSOT; Layer archive; no Layer teach | **Done** (docs) |
| **M2** | Engine/MCP: GQL accept + shaped `pin_map` emit; retire Layer/Tier A from product accept | **Done** |
| **M3** | In-repo `LLM-GUIDE` + application-notes bodies → GQL examples | **Done** (docs) |
| **M2.5** | Durable online GQL store **behind** mission working memory (MemNet ↔ AgensGraph hydrate/flush; one sync owner) | **Done** (0.7) — Agens client + live hydrate/flush proven; optional Neo4j client (not live-claimed); Fake always-on CI; skip live marks unless URL exported |

**Next SemVer:** **1.0.0** = **claim** of 0.5–0.8 (no extra engine; 0.9 is not a 1.0 gate). One-path gates below stay the teach/ops lock. Durable: [`grammar/agensgraph-buffer.md`](grammar/agensgraph-buffer.md), [`grammar/neo4j-buffer.md`](grammar/neo4j-buffer.md). Do **not** wait on Later (Peak_L, HostSearch ship, N-server, export, hosted cabinet, live Neo4j).

User-pack MemNet skills → GQL-only is **in flight separately** (`chouswei/cursor-user-skills`).

### Already shipped (from 0.4.x — do not list as deferred)

CapsPolicy ACL (off by default), neighbourhood reserve (RSV), Path-B ingest domains (#64), ImportAbsorb + ImportGuard / CheapLlmImportGuard, LocalIpcGateway. See [`../CHANGELOG.md`](../CHANGELOG.md) and [`../README.md`](../README.md).

---

## Locked priorities (0.5 teach / ops)

### 1. One remote entry

| MUST | MUST NOT |
|------|----------|
| Teach Cursor remote as **`memnet-pi`** via `"url"` → streamable-http (`:18766/mcp`) | Treat project **`memnet-local`** (stdio) as the default remote/shared path |
| Keep stdio local MCP **optional / dev-only** | Document stdio and HTTP as equal “primary” remotes |

Local single-agent may still use in-process stdio when no shared graph is needed. Multitask / shared graph → HTTP or TCP only.

### 2. One dialect teach

| MUST | MUST NOT |
|------|----------|
| Teach **GQL (openCypher-shaped)** as the **only** agent wire ([`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md); family authority = openCypher CIP / oC9) | Teach Layer / Tier A as wire, peer, or accept path |
| Redefine **Write = display** as **bounded shaped GQL subgraph** via `pin_map`-class tool | Ship unbounded tabular `MATCH`/`RETURN` as primary goldfish read |
| Point historical Layer sources only at [`grammar/archive/`](grammar/archive/) | Invent a third peer dialect |

Decision SSOT: [`adr/ADR-001-gql-agent-wire.md`](adr/ADR-001-gql-agent-wire.md) (supersession: no Layer).

### 3. One graph owner on Pi

| MUST | MUST NOT |
|------|----------|
| Bridge HTTP MCP to **`memnet serve`** (TCP `:18765`) so one process owns the store | Run HTTP MCP with a separate `InProcessEngine` **and** TCP serve as two writers |
| Default remote HTTP so tools share the serve graph | Dual-write the same mission across two engines |

### 4. Footguns (Cursor just works)

| Concern | Default / gate |
|---------|----------------|
| Host | LAN bind + `MEMNET_MCP_HTTP_TRUSTED_HOSTS` |
| Token | Non-empty `MEMNET_MCP_HTTP_TOKEN`; Cursor `Authorization: Bearer …` |
| `view=` | Omit → shell-safe default; teach `shell` / `interior` first |

**MUST NOT** advertise empty-token LAN MCP as safe.

### 5. Working memory ≠ corpus

| MUST | MUST NOT |
|------|----------|
| Keep retrieve / generate / remember unfused. Goldfish = serial cue then `pin_map` | Add `rag_query` (or equivalent) to `memnet-mcp` |
| Host search MAY propose **locators** into MutateGate / ingest; skip is valid | Store embeddings or chunk bodies as the memory surface |
| [#73](https://github.com/chouswei/MemNet/issues/73) `find` is **graph** lookup (seed nodes only; then `pin_map`), not corpus RAG | Run HippoRAG PPR / Graphiti RRF / OpenIE / ANN **inside** the engine |

Design: [`grammar/memnet-host-search-nest.md`](grammar/memnet-host-search-nest.md). Math (above #77): [`grammar/math-skeleton.md`](grammar/math-skeleton.md). Research: [#77](https://github.com/chouswei/MemNet/issues/77).

---

## Out of 0.5.0 (and still Later than 1.0 unless noted)

Stay out of the 0.5 engine/MCP ship unless a later row already claimed it. **MUST NOT** treat design docs as implemented.

| Item | Notes |
|------|--------|
| Live AgensGraph as **claimed** complete | **0.7 shipped** — live hydrate/flush proven; `liveCabinetClaimed` true. Not a hosted product service; server not vendored. Do not claim the cabinet on Fake alone. Hosted cabinet = **Later**. |
| Host search / RAG nest | **Later.** Application `HostSearchBridge` **outside** `MemNetSystem`; locators only. Goldfish I/O (Snap/Shape, one `TSK` map, sparse Δ) is **design-locked** on `master` ([#84](https://github.com/chouswei/MemNet/pull/84)); not an engine cut |
| BoundedMatchFind | **0.5 shipped** (`implemented=true`; #73). Seed nodes only — **not** GraphRAG |
| N-server session pipe | [#47](https://github.com/chouswei/MemNet/issues/47) |
| Pin-map export / round-trip | MN-REQ-11.1–11.5 / [#66](https://github.com/chouswei/MemNet/issues/66); ingest ≠ export |
| First-class `PORT` NODE; SCHEMA vocab freeze | Grammar Open; ports stay properties |
| Full ACL modes / roles / `session_token` | CapsPolicy cut already ships when enabled; the rest stays design |

**GQL:** agent teach/wire only. **MUST NOT** revive Layer teach.

**AgensGraph / Neo4j:** backing graphs for sessions — **not** a MemNet substitute and **not** the agent handoff handle (handoff = session id). **MUST NOT** dual-write without a single sync owner. **MUST NOT** teach LLM ↔ store direct (Bolt), chat-as-SSOT, or MemNet-as-Cypher-proxy as default agent path. Between MemNet and Neo4j: [`grammar/neo4j-buffer.md`](grammar/neo4j-buffer.md).

---

## Related

| Path | Role |
|------|------|
| [`SHAPE.md`](SHAPE.md) | Product shape from the problem |
| [`../README.md`](../README.md) | Doctrine / how to run |
| [`adr/ADR-001-gql-agent-wire.md`](adr/ADR-001-gql-agent-wire.md) | GQL wire; no Layer |
| [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md) | **M1 SSOT** |
| [`grammar/agensgraph-buffer.md`](grammar/agensgraph-buffer.md) | Durable GQL store adapter (**M2.5**) |
| [`grammar/neo4j-buffer.md`](grammar/neo4j-buffer.md) | Second cabinet client (not live-claimed) |
| [`grammar/math-skeleton.md`](grammar/math-skeleton.md) | 0.5 Recall/Commit math (no engine cut) |
| [`../sysml-models/outputs/recall-commit-orthodox-plan.md`](../sysml-models/outputs/recall-commit-orthodox-plan.md) | Orthodox build-from; 0.5 leftover shipped; Peak_L Later |
| [`grammar/memnet-host-search-nest.md`](grammar/memnet-host-search-nest.md) | Host search nest (design; not 0.5 engine) |
| [`grammar/gql-model-exam.md`](grammar/gql-model-exam.md) | GQL-wire paradox (historical filename) |
| [`application-notes/examples/inverting-amplifier-gql-case-study.md`](application-notes/examples/inverting-amplifier-gql-case-study.md) | InvAmp GQL case study |
| [`../sysml-models/README.md`](../sysml-models/README.md) | Nested SysML outline |
| [`../parts/memnet-mcp/README.md`](../parts/memnet-mcp/README.md) | HTTP env / Pi paste |
| [`multi-agent-sessions.md`](multi-agent-sessions.md) | Multitask transport MUST |
| [`../.cursor/mcp.json.example`](../.cursor/mcp.json.example) | `memnet-pi` primary |
