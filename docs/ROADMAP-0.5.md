# Roadmap — one path

**Status:** this file is the SemVer SSOT. Product shape: [`SHAPE.md`](SHAPE.md). Placement (design): [`grammar/memnet-harness-thesis.md`](grammar/memnet-harness-thesis.md).  
**Audience:** product developers. Dialect teach = **GQL** ([`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md)). British English.

**Package now:** Hatch **0.9.0** (Neo4j cabinet-client extra; `liveNeo4jClaimed=false`). **PyPI `memnet-llm` is still 0.4.6.**

---

## One picture

MemNet is **mission working memory** — the **memory plane of an agent harness**, not the harness, not the library, not the cabinet.

```text
  outer harness (Cursor, OpenHands, SWE-agent, Inspect, …)
  owns: completion API, bash, sandbox, eval, chat list
                    |
                    |  MCP / CLI   session id + anchors
                    v
              memnet-llm  /  memnet-mcp     ← this repo (engine + generic MCP)
              Recall  pin_map(q)   Commit Δ
                    |
         +----------+------------------+
         |                             |
    host Snap (RAG)              cabinet Bolt
    locators only                hydrate / flush
    HostSearch Later             Agens live claimed (0.7)
    outside MemNetSystem         Neo4j client 0.9, live unclaimed
```

| Layer | Job | This repo? |
|-------|-----|------------|
| Outer harness | Loop, tools, env blob, eval tape | **No** |
| Memory plane | Named session \(S\); goldfish Shape; sparse mutate; Path-B Absorb | **Yes** — engine + `memnet-mcp` |
| Library RAG | Corpus → locators (Snap) | **Later** (HostSearch outside `MemNetSystem`) |
| Cabinet | Persist one \(S\) | Agens **0.7 claimed**; Neo4j **Later** to claim live |

Handoff = **session id** (+ anchors / write scope). Peers **re-`pin_map`**. Chat is never SSOT. A durable store **backs** \(S\); it is not the handle and not the default teach surface. **MUST NOT** reframe MemNet as a Cypher proxy or as GraphRAG.

**Two channels (thesis leftover, not a SemVer gate).** Mission names (`TSK`/`USR`/`MOD`) live on \(S\). Env blobs (test logs, screenshots) stay in the outer harness (or its condenser). Do not put bash on \(S\) and call that Shape.

**Goldfish caller (thesis leftover, not 1.0).** Shape saves tokens only if the harness **drops** old `pin_map` rows from the chat list. Stuffing MCP JSON into growing `messages` saves zero. That caller is **unshipped** in public harnesses; user-pack `mcp-memnet` is how **Cursor** is taught. Do not hold **1.0** for OpenHands/SWE-agent adoption.

---

## Version map (locked)

| Version | Owns | Status |
|---------|------|--------|
| **0.5.0** | Goldfish leftover: paradox V1/V3/V4/V6; BoundedMatchFind (#73) seed-only `find`; multi-ego `pin_map` under one \(M\) + one LAW | **Shipped** (`v0.5.0`) |
| **0.6.0** | Honesty: V5 LAW×N pytest; snapshot as offered durable; version-map docs | **Shipped** (`v0.6.0`) |
| **0.7.0** | Live AgensGraph hydrate/flush; `liveCabinetClaimed=true`. Server not vendored. Fake + skip unless `MEMNET_AGENSGRAPH_URL` | **Shipped** (`v0.7.0`) |
| **0.8.0** | GQL-only **teach** + product **shape for people** (`SHAPE.md`, playbook, application-note contract, Multitask honesty). Docs only. **No** engine cut. Cabinet stays claimed | **Shipped** (`v0.8.0`) |
| **0.9.0** | Neo4j `DurableStoreAdapter` client (`memnet-llm[neo4j]`); factory both-URL rule; [`grammar/neo4j-buffer.md`](grammar/neo4j-buffer.md). Live round-trip **unclaimed**. Cabinet extra, **not** a 1.0 gate | **Shipped** (package 0.9.0; tag by coordinator) |
| **1.0.0** | **Claim** of **0.5 + 0.6 + 0.7 + 0.8**. Shape mature for people. Not GraphRAG. Not cabinet-only. Not a new engine | **Claim next** — PyPI still 0.4.6 |
| **Later** | See table below. Out of 0.9 and 1.0 | **Out** |

**Next SemVer is 1.0.0** = publish the claim (and PyPI when the coordinator tags). No extra engine. User-pack GQL rewrite is **sibling** (`chouswei/cursor-user-skills`), not this repo.

**1.0 MUST NOT** wait on the Later table — not HostSearch, not live Neo4j, not Peak_L, not catalog Snap, not a second Neo4j database name, not a goldfish caller in third-party harnesses.

**0.8 MUST:** one dialect teach (GQL only; Layer archive only); Write = display = bounded shaped `pin_map`; session id = handoff handle; working memory ≠ corpus (no `rag_query`). Wire SSOT: [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md).

**0.8 MUST NOT:** Peak_L / HostSearch / N-server / export / `rag_query`; second **live** cabinet claim; vendor AgensGraph/Neo4j servers; restore Layer teach or novel-writer.

**0.9 MUST NOT:** claim `liveNeo4jClaimed`; vendor a Neo4j server; hold **1.0** for live Neo4j, HostSearch, N-server, or Peak_L.

---

## Later (sorted)

Stay out of 1.0 unless a row already claimed it. **MUST NOT** treat design docs as implemented.

### Engine / product (this repo, after 1.0)

| Item | Notes |
|------|--------|
| Live Neo4j round-trip | Client landed in 0.9; claim `liveNeo4jClaimed` only after an operator cabinet proves flush/hydrate (mirror 0.7). Not a close of [#65](https://github.com/chouswei/MemNet/issues/65). |
| HostSearch ship | Application `HostSearchBridge` **outside** `MemNetSystem`; locators only. No `rag_query`. Design-locked Snap/Shape: [#84](https://github.com/chouswei/MemNet/pull/84), [`grammar/memnet-host-search-nest.md`](grammar/memnet-host-search-nest.md). Two Neo4j **namespaces** (cabinet vs library) = same Later bucket — [`grammar/memnet-neo4j-rag-rethink.md`](grammar/memnet-neo4j-rag-rethink.md) option B. |
| Catalog Snap (`session=` ids) | Option D in the rethink. Join remains Path-B Absorb, not RAG. |
| `Peak_L` | Last-resort Recall seed. Orthodox plan: [`../sysml-models/outputs/recall-commit-orthodox-plan.md`](../sysml-models/outputs/recall-commit-orthodox-plan.md). |
| N-server session pipe | [#47](https://github.com/chouswei/MemNet/issues/47) |
| Pin-map export / round-trip | MN-REQ-11.1–11.5 / [#66](https://github.com/chouswei/MemNet/issues/66); ingest ≠ export |
| Hosted AgensGraph as a product service | 0.7 proved **client** live; server not vendored; hosted = Later |
| First-class `PORT` NODE; SCHEMA vocab freeze | Grammar Open; ports stay properties |
| Full ACL modes / roles / `session_token` | CapsPolicy already ships when enabled; the rest stays design |

### Not this repo’s SemVer (harness leftovers)

| Item | Notes |
|------|--------|
| Goldfish caller | Outer harness drops old `pin_map` from chat. Unshipped in SWE-agent / OpenHands / Inspect / Letta-code. Teach: user-pack `mcp-memnet` (Cursor). |
| Cache-hit dump vs Shape+Flash | MN-REQ-00 unmeasured. Do not pretend dump always loses. |
| Env-blob channel | Harness condenser of pytest logs ≠ MemNet Shape. |
| Eval dual-tape | Inspect (and cousins) keep a transcript for scoring; \(S\) is not that tape. |

**GQL:** agent teach/wire only. **MUST NOT** revive Layer teach.

**AgensGraph / Neo4j:** backing graphs for sessions — **not** a MemNet substitute and **not** the handoff handle. **MUST NOT** dual-write without a single sync owner. **MUST NOT** teach LLM ↔ Bolt as the miss path.

---

## Where we are (M-phases — all done)

| Phase | Owns | Shipped? |
|-------|------|----------|
| **M1** | GQL wire profile SSOT; Layer archive; no Layer teach | **Done** (docs) |
| **M2** | Engine/MCP: GQL accept + shaped `pin_map` emit; retire Layer/Tier A from product accept | **Done** |
| **M3** | In-repo `LLM-GUIDE` + application-notes bodies → GQL examples | **Done** (docs) |
| **M2.5** | Durable store **behind** working memory (MemNet ↔ AgensGraph hydrate/flush; one sync owner) | **Done** (0.7) — optional Neo4j client 0.9, not live-claimed |

Durable: [`grammar/agensgraph-buffer.md`](grammar/agensgraph-buffer.md), [`grammar/neo4j-buffer.md`](grammar/neo4j-buffer.md).

### Already shipped (from 0.4.x — do not list as deferred)

CapsPolicy ACL (off by default), neighbourhood reserve (RSV), Path-B ingest domains (#64), ImportAbsorb + ImportGuard / CheapLlmImportGuard, LocalIpcGateway. See [`../CHANGELOG.md`](../CHANGELOG.md) and [`../README.md`](../README.md).

---

## Locks that survive 1.0 (teach / ops)

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

Design: [`grammar/memnet-host-search-nest.md`](grammar/memnet-host-search-nest.md). Math: [`grammar/math-skeleton.md`](grammar/math-skeleton.md). Research: [#77](https://github.com/chouswei/MemNet/issues/77). Relatives: [`grammar/rag-relative-algorithms.md`](grammar/rag-relative-algorithms.md).

---

## Related

| Path | Role |
|------|------|
| [`SHAPE.md`](SHAPE.md) | Product shape from the problem (identity SSOT) |
| [`grammar/memnet-harness-thesis.md`](grammar/memnet-harness-thesis.md) | Memory plane of a harness (design thesis; not a SemVer gate) |
| [`grammar/memnet-neo4j-rag-rethink.md`](grammar/memnet-neo4j-rag-rethink.md) | Two ports; catalog Snap; Absorb = Path-B (not 1.0) |
| [`../README.md`](../README.md) | Doctrine / how to run |
| [`adr/ADR-001-gql-agent-wire.md`](adr/ADR-001-gql-agent-wire.md) | GQL wire; no Layer |
| [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md) | **M1 SSOT** |
| [`grammar/agensgraph-buffer.md`](grammar/agensgraph-buffer.md) | Durable GQL store adapter (**M2.5**) |
| [`grammar/neo4j-buffer.md`](grammar/neo4j-buffer.md) | Second cabinet client (not live-claimed) |
| [`grammar/math-skeleton.md`](grammar/math-skeleton.md) | 0.5 Recall/Commit math |
| [`../sysml-models/outputs/recall-commit-orthodox-plan.md`](../sysml-models/outputs/recall-commit-orthodox-plan.md) | Orthodox build-from; Peak_L Later |
| [`grammar/memnet-host-search-nest.md`](grammar/memnet-host-search-nest.md) | Host search nest (design; not engine) |
| [`grammar/gql-model-exam.md`](grammar/gql-model-exam.md) | GQL-wire paradox (historical filename) |
| [`application-notes/examples/inverting-amplifier-gql-case-study.md`](application-notes/examples/inverting-amplifier-gql-case-study.md) | InvAmp GQL case study |
| [`../sysml-models/README.md`](../sysml-models/README.md) | Nested SysML outline |
| [`../parts/memnet-mcp/README.md`](../parts/memnet-mcp/README.md) | HTTP env / Pi paste |
| [`multi-agent-sessions.md`](multi-agent-sessions.md) | Multitask transport MUST |
| [`../.cursor/mcp.json.example`](../.cursor/mcp.json.example) | `memnet-pi` primary |
