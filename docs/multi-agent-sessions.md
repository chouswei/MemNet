# Multitask operating model (as-is 0.4.x)

**Class:** developers — MemNet engine / MCP / agent operating doctrine.  
**Application adoption** (`modelbasedPrj-*`): [`docs/application-notes/llm-system-dev-multitask.md`](application-notes/llm-system-dev-multitask.md). Index: [`docs/README.md`](README.md).

**Status:** enforceable agent doctrine for Cursor Multitask Mode and Task sub-agents. Session ACL, neighbourhood reserve, and ingest engines are **not shipped** — see `docs/grammar/memnet-security-multi-agent.md` and `docs/grammar/memnet-neighbourhood-reserve.md`.

**SysML trail (doctrine ↔ model):** group **MN-REQ-12** (`sysml-models/models/requirements.sysml`) → verify **MN-VER-12-G00** + step cases **S01…S09** (`sysml-models/models/verify.sysml`) → worked scenario [`sysml-models/outputs/multitask-case-study.md`](../sysml-models/outputs/multitask-case-study.md). Downstream **`modelbasedPrj-*`** adoption: [`docs/application-notes/llm-system-dev-multitask.md`](application-notes/llm-system-dev-multitask.md).

## Principle

When Multitask is **on**, one **shared MemNet session** is mission SSOT. Chat is never SSOT. Parent coordinates; workers execute under assigned scope.

## Transport (shared store)

| Transport | Graph store | Multitask |
|-----------|-------------|-----------|
| **MCP in-process** (default) | One graph per host process | **Isolated** per agent process — **MUST NOT** use for shared Multitask missions |
| **CLI + `memnet serve`** (TCP `:18765`) | One shared process | **MUST** use when workers need the same session id |
| **MCP streamable-http** (`:18766/mcp`, opt-in) | Shared remote process | Same as TCP when all agents hit the same server |

Set `MEMNET_MCP_TRANSPORT=tcp` (or streamable-http) so parent and workers share one graph. Default in-process stdio is fine for **single-agent** goldfish loops only.

## Parent agent (coordinator)

### MUST

- Open or load **one** mission `session` id before delegating; pass that id in every worker prompt.
- Mint and own `TSK_*` / `USR_*` lifecycle: create, `status=active`, `status=settled`, optional `led_to_success` edges.
- Give workers **self-contained** prompts: session id, anchor ids, write scope (subgraph or relation types), return shape.
- **End the turn** after spawning background workers — Multitask gate; do not poll or await worker completion in the same turn.
- On the **next** coordinator turn: `pin_map` first; act from the refreshed slice — do not redo worker investigation from chat memory.
- Prefer **one** worker per coherent workstream; parallel workers only for **disjoint** anchors or **separate** session ids.

### MUST NOT

- Treat chat, tool transcripts, or sub-agent prose as durable mission state.
- Settle `TSK_*` / `USR_*` from worker chat — settle from shared-session `pin_map` facts only.
- Spawn parallel workers on the **same** anchor slice without coordination (0.4.x: last-write-wins; no reserve).
- Assume ACL, reserve, or ingest engines — they are design-only.

## Worker agent (background)

### MUST

- Use the **session id** from the parent prompt; `pin_map` **first** every turn (goldfish loop).
- Copy assigned ids from `pin_map` — **MUST NOT** invent ids the parent already minted.
- Mutate only under the **assigned subgraph** (anchors and relation scope in the prompt).
- Return a concise result to the parent — durable facts live in MemNet rows, not chat.

### MUST NOT

- Open a different session id unless the parent explicitly assigned a separate mission session.
- Rely on in-process MCP when the parent uses shared TCP/HTTP — you would write to an isolated graph.
- Settle parent-owned `TSK_*` / `USR_*` unless explicitly delegated.
- Poll, block, or expect the parent to await inline completion.

## Parallel workers (0.4.x)

No neighbourhood reserve or ACL enforcement. Coordination options:

| Pattern | When |
|---------|------|
| **Disjoint anchors** | Parallel workers; each owns a non-overlapping anchor subtree |
| **Separate session ids** | Independent missions; parent merges at settle time if needed |
| **Serial single writer** | Default when scopes overlap |

**MUST NOT** have two writers mutate the same anchor slice without explicit serialisation.

## Anti-patterns

| Anti-pattern | Why it fails |
|--------------|--------------|
| Chat as SSOT for ids / mission state | Workers and parent diverge; re-pin_map is mandatory |
| In-process MCP under Multitask | Each process gets its own graph |
| Parent polls or re-runs worker investigation | Wastes tokens; violates Multitask turn boundary |
| Worker mints duplicate `TSK_*` | Parent owns task lifecycle |
| Teaching ACL / `RSV` / ingest as available | Not enforced in 0.4.x |
| Parallel workers on same anchor | Last-write-wins; silent clobber |

## Not implemented (do not assume)

Product backlog — **deferred** in 0.4.x; gated by **MN-REQ-12.7** and verify **MN-VER-12-S09**:

| Capability | Requirement / verify | Status |
|------------|---------------------|--------|
| Session ACL (`private` / `shared` / `open`), roles, `session_token` | MN-REQ-12.7; design `docs/grammar/memnet-security-multi-agent.md` | **To-be** |
| Neighbourhood reserve (`RSV` rows, `llm_id` + TTL) | MN-REQ-12.7; design `docs/grammar/memnet-neighbourhood-reserve.md` | **To-be** |
| Path-B `PinMapIngest_*` engines (SysML, codebase, PCBA, skills) | MN-REQ-11 stubs; MN-REQ-12.7; MN-VER-12-S09 | **Roadmap** — seed via `session_open` `seed_lines` or `add` with explicit locator ids |
| Engine **WorkerWriteScope** enforcement | MN-REQ-12.4 / 12.5 (doctrine only); MN-VER-12-S09 | **To-be** — 0.4.x last-write-wins |

Also see gaps in [`sysml-models/outputs/system-design-notes.md`](../sysml-models/outputs/system-design-notes.md).

## Related

- [`docs/README.md`](README.md) — docs index (developers vs applications)
- `docs/grammar/memnet-security-multi-agent.md` — target ACL model
- `docs/grammar/memnet-neighbourhood-reserve.md` — target reserve model
- `sysml-models/models/requirements.sysml` — **MN-REQ-12** group + leaves 12.1–12.8
- `sysml-models/models/verify.sysml` — **MN-VER-12-G00** (group) + **S01…S09** (step / 12.7 gate)
- `sysml-models/outputs/multitask-case-study.md` — worked scenario + verify table
- `docs/application-notes/llm-system-dev-multitask.md` — Multitask pattern for `modelbasedPrj-*` system repos
- `.cursor/skills/memnet-reference/SKILL.md` — product development skill
- `~/.cursor/skills/memnet-multitask/` — application Multitask skill (user pack)
- `AGENTS.md` — hub policy
