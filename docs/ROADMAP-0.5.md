# Roadmap 0.5.0 — one path

**Status:** plan only (docs). **MUST NOT** treat this as shipped behaviour.  
**Audience:** product developers. Agent ops: [`LLM-GUIDE.md`](LLM-GUIDE.md) / [`multi-agent-sessions.md`](multi-agent-sessions.md) — dialect teach = **GQL** ([`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md)).

**Model:** SysML + grammar for **GQL wire** (`GqlCodec` / `PinMapShapedRead`). Exam: [`grammar/gql-model-exam.md`](grammar/gql-model-exam.md). Case study: [`application-notes/examples/inverting-amplifier-gql-case-study.md`](application-notes/examples/inverting-amplifier-gql-case-study.md).  
**M1 done (docs):** GQL wire profile + shaped-read contract + Layer doctrine purge / archive. **Next: M2** (engine/MCP GQL accept + shaped emit).

**Problem (0.4.x):** dual remote MCP entries, dual dialect stories, and on Pi a risk of **two graph writers** (HTTP MCP `InProcessEngine` ≠ TCP `memnet serve`).

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
| Teach **GQL (openCypher-shaped)** as the **only** agent wire ([`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md)) | Teach Layer / Tier A as wire, peer, or accept path |
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

**GQL:** agent teach/wire only. Profile: [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md). **MUST NOT** revive Layer teach. **M2** implements accept/emit; **M3** rewrites in-repo playbook / app-note bodies. User-pack MemNet skills → GQL-only is **in flight separately** (`chouswei/cursor-user-skills`).

**AgensGraph (durable buffer thesis):** deferred past one-path. Sketch: [`grammar/agensgraph-buffer.md`](grammar/agensgraph-buffer.md). **MUST NOT** dual-write without a single sync owner.

---

## Related

| Path | Role |
|------|------|
| [`../README.md`](../README.md) | How to run (one path) |
| [`adr/ADR-001-gql-agent-wire.md`](adr/ADR-001-gql-agent-wire.md) | GQL wire; no Layer |
| [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md) | **M1 SSOT** |
| [`grammar/agensgraph-buffer.md`](grammar/agensgraph-buffer.md) | AgensGraph buffer sketch |
| [`grammar/gql-model-exam.md`](grammar/gql-model-exam.md) | Model exam |
| [`application-notes/examples/inverting-amplifier-gql-case-study.md`](application-notes/examples/inverting-amplifier-gql-case-study.md) | InvAmp GQL case study |
| [`../sysml-models/README.md`](../sysml-models/README.md) | Nested SysML outline |
| [`../parts/memnet-mcp/README.md`](../parts/memnet-mcp/README.md) | HTTP env / Pi paste |
| [`multi-agent-sessions.md`](multi-agent-sessions.md) | Multitask transport MUST |
| [`../.cursor/mcp.json.example`](../.cursor/mcp.json.example) | `memnet-pi` primary |
