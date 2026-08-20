# Multitask operating model (as-is 0.8)

**Class:** developers — MemNet engine / MCP / agent operating doctrine.  
**Product shape:** [`SHAPE.md`](../SHAPE.md). **Dialect:** **GQL only** — [`grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md). Handoff = **session id** (module A→B pipe; B cue then `pin_map`); prefer **import** over session merge.
**Application adoption** (`modelbasedPrj-*`): [`application-notes/llm-system-dev-multitask.md`](../application-notes/system/llm-system-dev-multitask.md). Shared contract: [`application-notes/README.md`](../application-notes/README.md). Index: [`README.md`](../README.md).

**Status:** enforceable agent doctrine for Cursor Multitask Mode and Task
sub-agents. The CapsPolicy ACL cut (who / `pin_map`-vs-mutate /
`WorkerWriteScope` hard reject / optional bind) is **shipped when session ACL
is enabled** via `memnet.acl`; ACL remains off by default. Privilege grain
(TRAVERSE≈`pin_map`, WRITE≈mutate, label/id GRANT≈scope) is named once in
[`sysml-models/outputs/system-design-notes.md`](../../sysml-models/outputs/system-design-notes.md)
— steal grain, not Neo4j/AgensGraph as product; GQL only. Full ACL modes,
neighbourhood reserve is shipped; Path-B ingest domains are shipped —
see `docs/extras/memnet-security-multi-agent.md` and
`docs/extras/memnet-neighbourhood-reserve.md`. Full ACL modes remain deferred.

**SysML trail (doctrine ↔ model):** group **MN-REQ-12** (`sysml-models/models/requirements.sysml`) → verify **MN-VER-12-G00** + step cases **S01…S14** (`sysml-models/models/verify.sysml`) → worked scenario [`sysml-models/outputs/multitask-case-study.md`](../../sysml-models/outputs/multitask-case-study.md). Downstream **`modelbasedPrj-*`** adoption: [`application-notes/llm-system-dev-multitask.md`](../application-notes/system/llm-system-dev-multitask.md).

## Principle

When Multitask is **on**, one **shared MemNet session** \(S\) is mission SSOT. Chat is never SSOT. Parent coordinates; workers execute under assigned scope.

Goldfish: cue then `pin_map(q)` (Recall Shape \(\tilde{X}\)); empty cue is session outline (0.11 census of \(S\)). **Drop** prior map rows from the pack each turn (`stuffed_maps`). Sparse gated mutate. Env blobs stay in the harness. leftover `--anchor` is not law. Host search MAY Snap **locators** only — MUST NOT Snap-on-session (`rag_query` / ANN of \(S\)). Durable GQL **backs** \(S\) (0.7 live path); it is not the handoff handle.

## Inter-module session pipe

Module A → B **MUST** pass **session id only** (`SessionHandoff`) plus anchors / write scope. MCP tool arg is **`session`** (JSON envelope may still *return* `session_id`). B **MUST** cue then `pin_map`. Chat, MissionDock payloads, and HTTP bodies **MUST NOT** carry the graph. Wire is **GQL only**.

`SessionHandoff`: `sessionId`, `caller`, optional `missionId` + `lease` (plus existing optional Multitask `anchors` / `writeScope`). The shipped CapsPolicy ACL still governs `pin_map` versus mutate (who / scope / bind) — a handoff is not a mutate waiver.

| Pattern | What happens |
|---------|--------------|
| **Shared session** | Same `sessionId`; B re-`pin_map` (path A) |
| **Separate worker session** | Lead **imports** a bounded slice (`SessionImportReceive` / import_slice; path B) |

EvidenceCentre / MissionDock / `HostSearchBridge` are application patterns — **MUST NOT** nest under `MemNetSystem`.

## Transport (shared store)

| Transport | Graph store | Multitask |
|-----------|-------------|-----------|
| **MCP in-process** (default) | One graph per host process | **Isolated** per agent process — **MUST NOT** use for shared Multitask missions |
| **CLI + `memnet serve`** (TCP `:18765`) | One shared process | **MUST** use when workers need the same session id |
| **CLI + `memnet serve --ipc`** (`MEMNET_IPC_SOCKET`) | One shared process (AF_UNIX, MN-REQ-06.2) | Prefer on one host when no TCP port is wanted |
| **MCP streamable-http** (`:18766/mcp`, opt-in) | Shared remote process | Same as TCP when all agents hit the same server |

Set `MEMNET_MCP_TRANSPORT=tcp` (or streamable-http) so parent and workers share one graph. Default in-process stdio is fine for **single-agent** goldfish loops only.

When session ACL is enabled, an in-process trusted path MAY skip a configured
bind under `MEMNET_SERVE_INTERNAL`; InvestorApi-style / shared boundary paths
use `require_bind=true` and enforce the bind.

`session_open` needs a map (`map_file` / `map_lines`) that `SCHEMA`s every kind workers will mutate — else `unknown_tag`. Game `schema.example.txt` is not a SysML/coding map.

## Parent agent (coordinator)

### MUST

- Open or load **one** mission `session` id before delegating; pass that id in every worker prompt.
- Mint and own `TSK_*` / `USR_*` lifecycle: create, `status=active`, `status=settled`, optional `led_to_success` edges.
- Give workers **self-contained** prompts: session id, cue ids (leftover `anchor=` named leftover), write scope (subgraph or relation types), return shape, map kinds they may mint.
- **End the turn** after spawning background workers — Multitask gate; do not poll or await worker completion in the same turn.
- On the **next** coordinator turn: cue then **`pin_map(q)` first** (or skip); **drop** the previous map from the pack; act from the refreshed slice — do not redo worker investigation from chat.
- Prefer **one** worker per coherent workstream; parallel workers only for **disjoint** anchors, **RSV** leases, or **separate** session ids.

### MUST NOT

- Treat chat, tool transcripts, or sub-agent prose as durable mission state.
- Dump \(S\) into a worker prompt; dump a graph in chat.
- Settle `TSK_*` / `USR_*` from worker chat — settle from shared-session `pin_map` facts only.
- Spawn parallel workers on the **same** anchor slice without serialisation or an **RSV** lease.
- Assume full `private`/`shared`/`open` + `session_token` modes. CapsPolicy ACL applies **only when enabled**. RSV and Path-B ingest **are** shipped — do not treat them as design-only.
- `rag_query` / ANN the session; nest HostSearch under `MemNetSystem`.

## Worker agent (background)

### MUST

- Use the **session id** from the parent prompt; cue then `pin_map(q)` **first** every turn (goldfish loop). Drop prior maps. leftover `--anchor` is not law.
- Copy assigned ids from `pin_map` — **MUST NOT** invent ids the parent already minted.
- Mutate only under the **assigned subgraph** (anchors and relation scope in the prompt).
- Return a concise result to the parent — durable facts live in MemNet rows, not chat.

### MUST NOT

- Open a different session id unless the parent explicitly assigned a separate mission session.
- Rely on in-process MCP when the parent uses shared TCP/HTTP — you would write to an isolated graph.
- Settle parent-owned `TSK_*` / `USR_*` unless explicitly delegated.
- Poll, block, or expect the parent to await inline completion.

## Parallel workers (0.8)

**RSV** is shipped (`reserve` / `extend` / `release`). The shipped CapsPolicy ACL rejects
unauthorised or out-of-scope calls when session ACL is enabled. Prefer an RSV lease
when scopes may overlap:

| Pattern | When |
|---------|------|
| **Disjoint anchors** | Parallel workers; each owns a non-overlapping anchor subtree |
| **Separate session ids** | Independent missions; parent **imports** a member slice at settle if needed |
| **Serial single writer** | Default when scopes overlap |

**MUST NOT** have two writers mutate the same anchor slice without explicit serialisation.

## Anti-patterns

| Anti-pattern | Why it fails |
|--------------|--------------|
| Chat as SSOT for ids / mission state | Workers and parent diverge; re-pin_map is mandatory |
| Stuffing every `pin_map` into worker chat | Drop prior maps; env blobs stay in the harness (`stuffed_maps`) |
| In-process MCP under Multitask | Each process gets its own graph |
| Parent polls or re-runs worker investigation | Wastes tokens; violates Multitask turn boundary |
| Worker mints duplicate `TSK_*` | Parent owns task lifecycle |
| Teaching full ACL modes/token as available | Full private/shared/open + session_token modes are not enforced; CapsPolicy ACL ships when enabled; RSV + Path-B ingest domains are shipped |
| Parallel workers on same anchor | Last-write-wins; silent clobber |

## Honesty (do not assume the to-be row)

Shipped vs to-be. Full ACL modes stay design-only:

| Capability | Requirement / verify | Status |
|------------|---------------------|--------|
| CapsPolicy ACL (`who` / `pin_map`-vs-mutate / `WorkerWriteScope` hard reject / optional bind) | MN-REQ-12.7; MN-VER-12-S09; `memnet.acl` | **Shipped when session ACL is enabled** |
| Full session ACL (`private` / `shared` / `open`), roles, `session_token` | MN-REQ-12.7; design `docs/extras/memnet-security-multi-agent.md` | **To-be** |
| Neighbourhood reserve (`RSV` rows, `llm_id` + TTL) | MN-REQ-12.13; design `docs/extras/memnet-neighbourhood-reserve.md` | **Shipped** — `reserve` / `extend` / `release`; pin-map `## Reserves` |
| Path-B `PinMapIngest_Sysml` | MN-REQ-11.16; MN-REQ-12.7; MN-VER-12-S09; `memnet.pin_map_ingest` | **Shipped** — CLI `ingest sysml` / MCP `ingest_sysml` |
| Path-B `PinMapIngest_Codebase` | MN-REQ-11.6–11.8, 11.16; #64 | **Shipped** — CLI `ingest codebase` / MCP `ingest_codebase` |
| Path-B `PinMapIngest_PcbaAto` | MN-REQ-11.9, 11.14–11.15, 11.16; #64 | **Shipped** — CLI `ingest pcba` / MCP `ingest_pcba` |
| Path-B `PinMapIngest_SkillsRules` | MN-REQ-11.10–11.12, 11.16; #64 | **Shipped** — CLI `ingest skills` / MCP `ingest_skills` |
| Pin-map export | MN-REQ-11.1–11.4; #66 | **Shipped (0.19)** — CLI `export pin-map` / MCP `export_pin_map` (cue GQL; empty q = outline). Re-ingest later. |

Also see gaps in [`sysml-models/outputs/system-design-notes.md`](../../sysml-models/outputs/system-design-notes.md).

## Related

- [`docs/README.md`](../README.md) — docs index (developers vs applications)
- `docs/extras/memnet-security-multi-agent.md` — target ACL model
- `docs/extras/memnet-neighbourhood-reserve.md` — target reserve model
- `sysml-models/models/requirements.sysml` — **MN-REQ-12** group + leaves 12.1–12.8
- `sysml-models/models/verify.sysml` — **MN-VER-12-G00** (group) + **S01…S14**
- `sysml-models/outputs/multitask-case-study.md` — worked scenario + verify table
- `docs/application-notes/system/llm-system-dev-multitask.md` — Multitask pattern for `modelbasedPrj-*` system repos
- `.cursor/skills/memnet-reference/SKILL.md` — product development skill
- `.cursor/skills/memnet-multitask/` — application Multitask skill (vendored in this repo)
- `AGENTS.md` — hub policy
