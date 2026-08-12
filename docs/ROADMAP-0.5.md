# Roadmap 0.5.0 — one path

**Status:** plan only (docs). **MUST NOT** treat this as shipped behaviour.  
**Audience:** product developers. Agent ops still follow [`LLM-GUIDE.md`](LLM-GUIDE.md) / [`multi-agent-sessions.md`](multi-agent-sessions.md).

**Problem (0.4.x):** dual remote MCP entries, dual dialect stories (Tier A vs Layer), and on Pi a risk of **two graph writers** (HTTP MCP `InProcessEngine` ≠ TCP `memnet serve`).

---

## Locked priorities

### 1. One remote entry

| MUST | MUST NOT |
|------|----------|
| Teach Cursor remote as **`memnet-pi`** via `"url"` → streamable-http (`:18766/mcp`) | Treat project **`memnet-local`** (stdio) as the default remote/shared path |
| Keep stdio local MCP **optional / dev-only** (disabled or omitted by default in examples) | Document stdio and HTTP as equal “primary” remotes |

Local single-agent may still use in-process stdio when no shared graph is needed. Multitask / shared graph → HTTP or TCP only.

### 2. One dialect teach

| MUST | MUST NOT |
|------|----------|
| Teach **Layer** as the **1.x** shared dialect (Write = display; dual EDGE; law on NODE) | Teach Tier A and Layer as two peer stories |
| Keep **Tier A** as a **legacy alias** / accept path through 0.5.x | Invent a third wire dialect |

Engine unification (single codec path) may land after teach docs; teach order does not wait for full merge.

### 3. One graph owner on Pi

| MUST | MUST NOT |
|------|----------|
| Bridge HTTP MCP to **`memnet serve`** (TCP `:18765`) so one process owns the store | Run HTTP MCP with a separate `InProcessEngine` **and** TCP serve as two writers |
| Default remote HTTP so tools share the serve graph (`MEMNET_MCP_TRANSPORT=tcp` or equivalent bridge) | Dual-write the same mission across two engines |

CLI clients and Cursor `url` clients **MUST** see one session graph.

### 4. Footguns (Cursor just works)

| Concern | Default / gate |
|---------|----------------|
| Host | LAN bind + `MEMNET_MCP_HTTP_TRUSTED_HOSTS` (or specific host bind) so Cursor does not hit `Invalid Host header` |
| Token | Non-empty `MEMNET_MCP_HTTP_TOKEN`; Cursor `Authorization: Bearer …` |
| `view=` | Teach omit → shell-safe default; document `shell` / `interior` only as first grains |

**MUST NOT** advertise empty-token LAN MCP as safe.

---

## Out of 0.5.0 (stay deferred)

Neighbourhood reserve, session ACL / WorkerWriteScope, Path-B ingest as available, first-class `PORT` NODE, SCHEMA vocab freeze — see grammar Open items and MN-REQ-12 backlog. Not blocked by one-path, not claimed here.

**GQL (ISO/IEC 39075):** **consider / map, not teach as wire.** Crosswalk SSOT: [`grammar/gql-consideration.md`](grammar/gql-consideration.md). Verdict for 0.5 = **map** (later selective borrow only). **MUST NOT** add GQL/`MATCH`/`RETURN` as a third dialect beside Layer.

---

## Related

| Path | Role |
|------|------|
| [`../README.md`](../README.md) | How to run (one path) + gaps pointer |
| [`grammar/memnet-multi-layer.md`](grammar/memnet-multi-layer.md) §8 Open | Dialect / grain deferred bullets |
| [`grammar/gql-consideration.md`](grammar/gql-consideration.md) | GQL vs Layer: map, not teach as wire |
| [`../parts/memnet-mcp/README.md`](../parts/memnet-mcp/README.md) | HTTP env / Pi paste |
| [`multi-agent-sessions.md`](multi-agent-sessions.md) | Multitask transport MUST |
| [`../.cursor/mcp.json.example`](../.cursor/mcp.json.example) | `memnet-pi` primary; local optional |
