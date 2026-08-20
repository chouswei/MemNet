---
name: memnet-multitask
description: >-
  Enforceable MemNet doctrine for Cursor Multitask Mode and Task sub-agents:
  one shared session SSOT, TCP or streamable-http transport, parent/worker
  MUST/MUSTNOT, MN-REQ-12 usage, system-dev two-store pattern for modelbasedPrj-*.
  Triggers: Multitask Mode, multitask, multi-agent, Task sub-agent, background
  worker, parent coordinator, delegate worker, shared session, memnet multitask,
  system-dev multitask, modelbasedPrj multitask, MN-REQ-12, parallel workers,
  TSK_* settle, TCP serve, streamable-http MCP.
metadata:
  pattern: pipeline
  version: "2.3"
  domain: memnet
  product: memnet-llm==0.19.3
---

# MemNet + Multitask Mode

This checkout **vendors** the Multitask skill. Pair with [mcp-memnet](../mcp-memnet/SKILL.md) (tools) and [memnet-format](../memnet-format/SKILL.md) (GQL wire / shaped pin_map).

**Product ops SSOT (MemNet repo, developers):** `docs/operations/multi-agent-sessions.md`.
**System-repo adoption (applications):** MemNet `docs/application-notes/system/llm-system-dev-multitask.md`.
**Product shape / 0.8 teach:** MemNet `docs/SHAPE.md`. **Version map:** MemNet `docs/ROADMAP.md` (package **0.19.3**; **1.0** = 0.5–0.8 claimed).
**Docs index:** MemNet `docs/README.md`. Chat is **never** mission SSOT.

## When to load

| Signal | Action |
|--------|--------|
| Multitask Mode on | Follow this skill + MemNet `docs/operations/multi-agent-sessions.md` |
| Spawning Task / background workers | Parent checklist below; pass session id in every worker prompt |
| `modelbasedPrj-*` system repo + Multitask | Also read MemNet `docs/application-notes/system/llm-system-dev-multitask.md` |
| Single-agent goldfish loop | [memnet-use](../memnet-use/SKILL.md) — default in-process MCP |

## Transport (shared store)

| Transport | Multitask |
|-----------|-----------|
| **MCP in-process** (default) | **MUST NOT** -- isolated graph per process |
| **CLI + `memnet serve`** (TCP `:18765`) | **MUST** when workers share one session id |
| **MCP streamable-http** (`:18766/mcp`) | Same as TCP when all agents hit the **same** HTTP process **bridged to that serve** |

Set `MEMNET_MCP_TRANSPORT=tcp` on the shared HTTP MCP (or use TCP CLI). Probe with `serve_status` before delegating if uncertain. Detail: [mcp-memnet](../mcp-memnet/SKILL.md).

## Parent coordinator

### MUST

- `session_open` / `session_load` **one** mission `session` id; pass it in every worker prompt.
- Mint and own **`TSK_*`** / **`USR_*`**: `status=active` -> `status=settled`; optional `led_to_success` edges. Prefer **one live `TSK`** (0.5 V5).
- Self-contained worker prompts: session id, cue locators (`kind` / `goal=` / `path=` / `qname=`), write scope (subgraph or relation types), return shape, **`llm_id`**. leftover nickname `id` is leftover.
- **`reserve`** overlapping neighbourhoods before parallel mutate (shipped RSV); pass matching `llm_id` on worker **`mutate`**.
- **End the turn** after background spawn -- no poll, no await.
- Next coordinator turn: **`pin_map` first** (cue / `find` if ego lost); act from refreshed slice -- do not redo worker investigation from chat.
- Prefer **one worker** per coherent workstream; parallel only when the **parent shell is already clear** and interiors are **disjoint** (or RSV) — [memnet-nested-sessions](../memnet-nested-sessions/SKILL.md).

### MUST NOT

- Treat chat, tool transcripts, or sub-agent prose as durable mission state.
- Settle `TSK_*` / `USR_*` from worker chat -- only from shared-session pin-map facts.
- Use in-process MCP for a shared mission.
- Run parallel writers on the **same** reserved slice with different `llm_id`s.

## Worker agent

### MUST

- Use the parent's **session id**; **`pin_map` first** every turn (or `find` then pin_map).
- Cue locators from the pin map -- **MUST NOT** invent a store key. leftover nickname `id` is leftover.
- Mutate only under the **assigned subgraph** (anchors + relations in the prompt).
- Pass the assigned **`llm_id`** on mutate when RSV is held.
- Return a concise result; durable facts live in MemNet rows.

### MUST NOT

- Open a different session unless explicitly assigned.
- Use in-process MCP when the parent uses shared TCP/HTTP.
- Settle parent-owned `TSK_*` / `USR_*` unless delegated.

## MN-REQ-12 usage (MemNet product repo)

When working **in** the MemNet engine repository:

| Step | Path |
|------|------|
| Requirements group | `sysml-models/models/requirements.sysml` -- **MN-REQ-12** leaves 12.1-12.8 |
| Verify package | `sysml-models/models/verify.sysml` -- **MN-VER-12-G00** + **S01…S14** |
| Worked scenario | `sysml-models/outputs/multitask-case-study.md` |

In downstream **`modelbasedPrj-*`** repos: adopt via doc pointer or thin local mirror -- **do not** import `MemNetRequirements` into the product load tree unless the project owns a merged model. Detail: MemNet `docs/application-notes/system/llm-system-dev-multitask.md` section 6.

## System-dev two-store pattern (`modelbasedPrj-*`)

| Store | SSOT for |
|-------|----------|
| **MemNet session** (TCP/HTTP) | Mission goldfish: `TSK_*`, `USR_*`, scoped `MOD_*` / `SYM_*`, `CLM_*` / `DEC_*` |
| **Product `sysml-models/`** (git) | Structural model: requirements, deploy, behaviour |
| **Source tree** | Code and artefacts on disk |

Recommended order when both SysML and code change: **SysML worker first** (disjoint `MOD_*` under `sysml-models/`), then **code worker** (`parts/`, tests). Full pattern: MemNet `docs/application-notes/system/llm-system-dev-multitask.md`.

Path-B: **`ingest_*`** into the current session (locator ids; **no** leftover NEW). Catalog Snap: **`snap_model`**. Export: **`export_pin_map`**. Ingest is **not** export.

## Shipped vs still design (package 0.19.3)

| Capability | Status |
|------------|--------|
| Neighbourhood RSV | **Shipped** |
| Path-B ingest | **Shipped** |
| CapsPolicy ACL | **Shipped opt-in** (`session_acl_enable`) |
| Live AgensGraph | **Claimed 0.7** when URL set |
| Neo4j live | **Claimed 0.14** |
| HostSearch locators | Extra **0.17** (`RagHostHook`; no `rag_query`) |
| Peak_L | Extra **0.18** (last-resort; not default goldfish) |
| Pin-map export / catalog Snap | Extra **0.19** / **0.15** |
| Session ACL modes / `session_token` | **Design** — `docs/extras/memnet-security-multi-agent.md` |
| N-server | **Research** #47 |
| Write without RSV | Last-write-wins |

## Anti-patterns

| Anti-pattern | Why it fails |
|--------------|--------------|
| Chat as SSOT for ids / mission state | Parent and workers diverge |
| In-process MCP under Multitask | Each process gets its own graph |
| Parent polls or re-runs worker work | Token waste; violates turn boundary |
| Worker mints duplicate `TSK_*` | Parent owns task lifecycle |
| Teaching full ACL modes / `rag_query` as available | Full ACL modes still design; HostSearch is locators only (**0.17**) |
| Skipping RSV on overlapping parallel mutate | Last-write-wins |

## Related (this vendor)

| Skill | Role |
|-------|------|
| [memnet-use](../memnet-use/SKILL.md) | Goldfish hub (single agent) |
| [mcp-memnet](../mcp-memnet/SKILL.md) | MCP tools, transport, session lifecycle |
| [memnet-format](../memnet-format/SKILL.md) | MemNet GQL wire / shaped pin_map |
| [memnet-nested-sessions](../memnet-nested-sessions/SKILL.md) | Look loop / nested `session=` |
| [sysml-memnet-documentation](../sysml-memnet-documentation/SKILL.md) | SysML relatives (pair when SysML + Multitask) |
