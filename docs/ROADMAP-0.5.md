# Roadmap 0.5.0 — one path

**Status:** plan only (docs). **MUST NOT** treat this as shipped behaviour.  
**Audience:** product developers. Agent ops: [`LLM-GUIDE.md`](LLM-GUIDE.md) / [`multi-agent-sessions.md`](multi-agent-sessions.md) — dialect teach = **GQL** ([`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md)).

**Product:** MemNet is **mission working memory for LLMs** — not the search corpus, not GraphRAG. Multi-agent / Multitask sessions, goldfish re-read via shaped `pin_map`, gated mutate. In-session recall is serial cue then neighbourhood. A MemNet **session** can be SSOT for a mission / that shared memory: LLM handoff = deliver **session id** (+ anchors / write scope); peers **re-pin_map** — **MUST NOT** pass a graph dump in chat. Chat is never SSOT ([`multi-agent-sessions.md`](multi-agent-sessions.md)). A durable online GQL store (M2.5) **backs** sessions; it does **not** replace the session handle for agent handoff, and is not the default agent teach surface. **MUST NOT** reframe MemNet as a Cypher proxy to AgensGraph.

**Model:** SysML + grammar for **GQL wire** (`GqlCodec` / `PinMapShapedRead`). Exam: [`grammar/gql-model-exam.md`](grammar/gql-model-exam.md). Case study: [`application-notes/examples/inverting-amplifier-gql-case-study.md`](application-notes/examples/inverting-amplifier-gql-case-study.md).

---

## Where we are (2026-08-14)

| Phase | Owns | Shipped? |
|-------|------|----------|
| **M1** | GQL wire profile SSOT; Layer archive; no Layer teach | **Done** (docs) |
| **M2** | Engine/MCP: GQL accept + shaped `pin_map` emit; retire Layer/Tier A from product accept | **Done** |
| **M3** | In-repo `LLM-GUIDE` + application-notes bodies → GQL examples | **Done** (docs) |
| **M2.5** | Durable online GQL store **behind** mission working memory (MemNet ↔ AgensGraph hydrate/flush; one sync owner) | **In progress** — client hydrate/flush landed; Fake always-on; **live path needs external AgensGraph** |

**Next notch for 0.5.0:** prove the **live** M2.5 cabinet path. One-path gates below stay the teach/ops lock (remote, dialect, Pi owner, footguns). Sketch: [`grammar/agensgraph-buffer.md`](grammar/agensgraph-buffer.md).

User-pack MemNet skills → GQL-only is **in flight separately** (`chouswei/cursor-user-skills`).

### Already in 0.4.x (do not list as deferred)

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
| Leftover [#73](https://github.com/chouswei/MemNet/issues/73) find is **graph** lookup, not corpus RAG | Run HippoRAG PPR / Graphiti RRF / OpenIE / ANN **inside** the engine |

Design: [`grammar/memnet-host-search-nest.md`](grammar/memnet-host-search-nest.md). Math (above #77): [`grammar/math-skeleton.md`](grammar/math-skeleton.md). Research: [#77](https://github.com/chouswei/MemNet/issues/77).

---

## Out of 0.5.0

Stay out of the 0.5 engine/MCP ship. **MUST NOT** treat design docs as implemented.

| Item | Notes |
|------|--------|
| Live AgensGraph as **claimed** complete | M2.5 client is in tree; live cabinet is the remaining 0.5 notch — do not call 0.5 done on Fake alone |
| Host search / RAG nest | Application `HostSearchBridge` **outside** `MemNetSystem`; locators only. Goldfish I/O (Snap/Shape, one `TSK` map, sparse Δ) is **design-locked** on `master` ([#84](https://github.com/chouswei/MemNet/pull/84)); not an engine cut |
| BoundedMatchFind | Leftover [#73](https://github.com/chouswei/MemNet/issues/73); modelled `implemented=false`. Cue when there is no ego — **not** GraphRAG |
| N-server session pipe | [#47](https://github.com/chouswei/MemNet/issues/47) |
| Pin-map export / round-trip | MN-REQ-11.1–11.5 / [#66](https://github.com/chouswei/MemNet/issues/66); ingest ≠ export |
| First-class `PORT` NODE; SCHEMA vocab freeze | Grammar Open; ports stay properties |
| Full ACL modes / roles / `session_token` | CapsPolicy cut already ships when enabled; the rest stays design |

**GQL:** agent teach/wire only. **MUST NOT** revive Layer teach.

**AgensGraph:** backing graph for sessions — **not** a MemNet substitute and **not** the agent handoff handle (handoff = session id). **MUST NOT** dual-write without a single sync owner. **MUST NOT** teach LLM ↔ store direct, chat-as-SSOT, or MemNet-as-Cypher-proxy as default agent path.

---

## Related

| Path | Role |
|------|------|
| [`../README.md`](../README.md) | Doctrine / how to run |
| [`adr/ADR-001-gql-agent-wire.md`](adr/ADR-001-gql-agent-wire.md) | GQL wire; no Layer |
| [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md) | **M1 SSOT** |
| [`grammar/agensgraph-buffer.md`](grammar/agensgraph-buffer.md) | Durable GQL store adapter (**M2.5**) |
| [`grammar/math-skeleton.md`](grammar/math-skeleton.md) | 0.5 Recall/Commit math (no engine cut) |
| [`../sysml-models/outputs/recall-commit-orthodox-plan.md`](../sysml-models/outputs/recall-commit-orthodox-plan.md) | Orthodox/paradox validate plan (goldfish leftover; not M2.5) |
| [`grammar/memnet-host-search-nest.md`](grammar/memnet-host-search-nest.md) | Host search nest (design; not 0.5 engine) |
| [`grammar/gql-model-exam.md`](grammar/gql-model-exam.md) | Model exam |
| [`application-notes/examples/inverting-amplifier-gql-case-study.md`](application-notes/examples/inverting-amplifier-gql-case-study.md) | InvAmp GQL case study |
| [`../sysml-models/README.md`](../sysml-models/README.md) | Nested SysML outline |
| [`../parts/memnet-mcp/README.md`](../parts/memnet-mcp/README.md) | HTTP env / Pi paste |
| [`multi-agent-sessions.md`](multi-agent-sessions.md) | Multitask transport MUST |
| [`../.cursor/mcp.json.example`](../.cursor/mcp.json.example) | `memnet-pi` primary |
