# Roadmap 0.5.0 — one path

**Status:** plan only (docs). **MUST NOT** treat this as shipped behaviour.  
**Audience:** product developers. Agent ops: [`LLM-GUIDE.md`](LLM-GUIDE.md) / [`multi-agent-sessions.md`](multi-agent-sessions.md) — dialect teach = **GQL** ([`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md)).

**Product:** MemNet is **shared working memory for LLMs** — multi-agent / Multitask sessions, goldfish re-read via shaped `pin_map`, gated mutate. A MemNet **session** can be SSOT for a mission / that shared memory: LLM handoff = deliver **session id** (+ anchors / write scope); peers **re-pin_map** — **MUST NOT** pass a graph dump in chat. Chat is never SSOT ([`multi-agent-sessions.md`](multi-agent-sessions.md)). A durable online GQL store (M2.5) **backs** sessions; it does **not** replace the session handle for agent handoff, and is not the default agent teach surface. **MUST NOT** reframe MemNet as a Cypher proxy to AgensGraph.

**Model:** SysML + grammar for **GQL wire** (`GqlCodec` / `PinMapShapedRead`). Exam: [`grammar/gql-model-exam.md`](grammar/gql-model-exam.md). Case study: [`application-notes/examples/inverting-amplifier-gql-case-study.md`](application-notes/examples/inverting-amplifier-gql-case-study.md).  
**M1 done (docs):** GQL wire profile + shaped-read contract + Layer doctrine purge / archive. **M2 done (engine/MCP):** GQL accept + shaped `pin_map` emit; Layer/Tier A retired from product accept. **M2.5 in progress:** durable-store client hydrate/flush landed; Fake always-on; **live AgensGraph path not verified** (external cabinet not installed). **M3 done (docs scope):** in-repo `LLM-GUIDE` + application-notes bodies teach GQL + shaped `pin_map` + gated mutate.

**Problem (0.4.x):** dual remote MCP entries, dual dialect stories, and on Pi a risk of **two graph writers** (HTTP MCP `InProcessEngine` ≠ TCP `memnet serve`).

---

## Phase order (locked)

| Phase | Owns | Shipped? |
|-------|------|----------|
| **M1** | GQL wire profile SSOT; Layer archive; no Layer teach | **Done** (docs) |
| **M2** | Engine/MCP: GQL accept + shaped `pin_map` emit; retire Layer/Tier A codec from product path | **Done** |
| **M2.5** | Durable online GQL store adapter behind shared LLM memory (MemNet ↔ AgensGraph hydrate/flush; one sync owner) | **In progress** — client hydrate/flush landed; Fake always-on; live path needs external AgensGraph |
| **M3** | In-repo `LLM-GUIDE` + application-notes bodies → GQL examples | **Done (docs)** |

**Order:** M1 → M2 → **M2.5** → M3. M2.5 does **not** wait on M3. User promotion (2026-08-13): durable store adapter sits **immediately after M2**, not deferred past all of 0.5.

**0.5 one-path vs M2.5:** 0.5.0 one-path locks (remote entry, dialect teach, Pi graph owner, footguns) are **M1–M2** product gates. **M2.5** is the scheduled **next notch after M2** — same GQL family; client hydrate/flush is in tree, but **MUST NOT** claim complete without a proven external cabinet. Sketch: [`grammar/agensgraph-buffer.md`](grammar/agensgraph-buffer.md).

User-pack MemNet skills → GQL-only is **in flight separately** (`chouswei/cursor-user-skills`).

---

## Locked priorities

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

---

## Out of 0.5.0 (stay deferred)

Neighbourhood reserve, session ACL / WorkerWriteScope, Path-B ingest as available, first-class `PORT` NODE, SCHEMA vocab freeze — see grammar Open items and MN-REQ-12 backlog.

**GQL:** agent teach/wire only. Profile: [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md). **MUST NOT** revive Layer teach. **M2** accept/emit done; **M2.5** client landed (live cabinet deferred); **M3** in-repo playbook / app-note bodies rewritten to GQL (docs scope).

**AgensGraph / durable GQL store:** **not** deferred forever past 0.5 — scheduled as **M2.5** (right after M2). Backing graph for MemNet sessions / shared LLM working memory — **not** a MemNet substitute and **not** the agent handoff handle (handoff = session id). **MUST NOT** claim fully shipped until the live external-cabinet path is proven; client adapter alone is not enough. **MUST NOT** dual-write without a single sync owner. **MUST NOT** teach LLM ↔ store direct, chat-as-SSOT, or MemNet-as-Cypher-proxy as default agent path.

---

## Related

| Path | Role |
|------|------|
| [`../README.md`](../README.md) | How to run (one path) |
| [`adr/ADR-001-gql-agent-wire.md`](adr/ADR-001-gql-agent-wire.md) | GQL wire; no Layer |
| [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md) | **M1 SSOT** |
| [`grammar/agensgraph-buffer.md`](grammar/agensgraph-buffer.md) | Durable GQL store adapter sketch (**M2.5**) |
| [`grammar/gql-model-exam.md`](grammar/gql-model-exam.md) | Model exam |
| [`application-notes/examples/inverting-amplifier-gql-case-study.md`](application-notes/examples/inverting-amplifier-gql-case-study.md) | InvAmp GQL case study |
| [`../sysml-models/README.md`](../sysml-models/README.md) | Nested SysML outline |
| [`../parts/memnet-mcp/README.md`](../parts/memnet-mcp/README.md) | HTTP env / Pi paste |
| [`multi-agent-sessions.md`](multi-agent-sessions.md) | Multitask transport MUST |
| [`../.cursor/mcp.json.example`](../.cursor/mcp.json.example) | `memnet-pi` primary |
