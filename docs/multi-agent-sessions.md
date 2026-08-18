# Multitask operating model (as-is 0.4.x)

**Class:** developers — MemNet engine / MCP / agent operating doctrine.  
**Product shape:** [`SHAPE.md`](SHAPE.md). **Dialect:** **GQL only** — [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md).  
**Application adoption** (`modelbasedPrj-*`): [`application-notes/llm-system-dev-multitask.md`](application-notes/llm-system-dev-multitask.md). Shared contract: [`application-notes/README.md`](application-notes/README.md). Index: [`README.md`](README.md).

**Status:** enforceable agent doctrine for Cursor Multitask Mode and Task sub-agents.

| Cut | 0.4.x |
|-----|--------|
| CapsPolicy ACL (`who` / `pin_map`-vs-mutate / `WorkerWriteScope` / optional bind) | **Shipped when session ACL is enabled** (`memnet.acl`); **off by default** |
| Full ACL modes (`private` / `shared` / `open`) + `session_token` | **To-be** — [`grammar/memnet-security-multi-agent.md`](grammar/memnet-security-multi-agent.md) |
| Neighbourhood reserve (`RSV`) | **Shipped** — `reserve` / `extend` / `release`; pin-map `## Reserves` |
| Path-B ingest (`ingest_sysml` / `codebase` / `pcba` / `skills`) | **Shipped** |
| Live AgensGraph cabinet | **1.0.0 gate** — client hydrate/flush exists; not the handoff handle |

Privilege grain (TRAVERSE ≈ `pin_map`, WRITE ≈ mutate, label/id GRANT ≈ scope): [`../sysml-models/outputs/system-design-notes.md`](../sysml-models/outputs/system-design-notes.md). Steal grain — not Neo4j/AgensGraph as product.

**SysML trail:** **MN-REQ-12** → verify **MN-VER-12-G00** + **S01…S14** → [`../sysml-models/outputs/multitask-case-study.md`](../sysml-models/outputs/multitask-case-study.md).

---

## Principle

When Multitask is **on**, one **shared MemNet session** \(S\) is mission SSOT. Chat is never SSOT. Parent coordinates; workers execute under assigned scope.

Goldfish: cue then `pin_map` (Recall Shape \(\tilde{X}\)); skip if the seed is empty. Sparse gated mutate. Host search MAY Snap **locators** only — MUST NOT Snap-on-session (`rag_query` / ANN of \(S\)). Durable GQL **backs** \(S\); it is not the handoff handle.

## Inter-module session pipe

Module A → B **MUST** pass **session id only** (`SessionHandoff`) plus anchors / write scope. MCP tool arg is **`session`** (JSON envelope may still *return* `session_id`). B **MUST** cue then `pin_map`. Chat, MissionDock payloads, and HTTP bodies **MUST NOT** carry the graph. Wire is **GQL only**.

`SessionHandoff`: `sessionId`, `caller`, optional `missionId` + `lease` (plus existing optional Multitask `anchors` / `writeScope`). CapsPolicy ACL (when enabled) still governs `pin_map` versus mutate — a handoff is not a mutate waiver.

| Pattern | What happens |
|---------|--------------|
| **Shared session** | Same `sessionId`; B re-`pin_map` (path A) |
| **Separate worker session** | Lead **imports** a bounded slice (`SessionImportReceive` / import_slice; path B) |

EvidenceCentre / MissionDock / `HostSearchBridge` are application patterns — **MUST NOT** nest under `MemNetSystem`.

## Transport (shared store)

| Transport | Graph store | Multitask |
|-----------|-------------|-----------|
| **MCP in-process** (default) | One graph per host process | **Isolated** — **MUST NOT** use for shared missions |
| **CLI + `memnet serve`** (TCP `:18765`) | One shared process | **MUST** when workers share a session |
| **CLI + `memnet serve --ipc`** (`MEMNET_IPC_SOCKET`) | One shared process (AF_UNIX, MN-REQ-06.2) | Prefer on one host when no TCP port is wanted |
| **MCP streamable-http** (`:18766/mcp`, opt-in) | Shared remote process | Same as TCP when all agents hit the same server |

Set `MEMNET_MCP_TRANSPORT=tcp` (or streamable-http) so parent and workers share one graph. Default in-process stdio is fine for **single-agent** goldfish loops only.

When session ACL is enabled, an in-process trusted path MAY skip a configured bind under `MEMNET_SERVE_INTERNAL`; InvestorApi-style / shared boundary paths use `require_bind=true` and enforce the bind.

`session_open` needs a map (`map_file` / `map_lines`) that `SCHEMA`s every kind workers will mutate — else `unknown_tag`. Game `schema.example.txt` is not a SysML/coding map.

## Parent agent (coordinator)

### MUST

- Open or load **one** mission `session` id before delegating; pass that id in every worker prompt.
- Mint and own `TSK_*` / `USR_*` lifecycle: create (`id:'NEW'` then copy), `status=active`, `status=settled`, optional `led_to_success` edges.
- Give workers **self-contained** prompts: session id, cue/anchor ids, write scope (subgraph or relation types), return shape, map kinds they may mint.
- **End the turn** after spawning background workers — Multitask gate; do not poll or await worker completion in the same turn.
- On the **next** coordinator turn: cue then **`pin_map` first**; act from the refreshed slice — do not redo worker investigation from chat.
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

- Use the **session id** from the parent prompt (`session` on tools); **cue then `pin_map` first** every turn.
- Copy assigned ids from `pin_map` — **MUST NOT** invent ids the parent already minted.
- Mutate only under the **assigned subgraph** (anchors and relation scope in the prompt).
- Goldfish creates: `id:'NEW'` then copy. Path-B / locator pins: **no client `NEW`** — `ingest_*` or deterministic locators.
- Return a concise result to the parent — durable facts live in MemNet rows, not chat.

### MUST NOT

- Open a different session id unless the parent explicitly assigned a separate mission session.
- Rely on in-process MCP when the parent uses shared TCP/HTTP — you would write to an isolated graph.
- Settle parent-owned `TSK_*` / `USR_*` unless explicitly delegated.
- Poll, block, or expect the parent to await inline completion.
- Teach Layer / `query_warm` as the primary read.

## Parallel workers (0.4.x)

Overlapping writers without a lease are last-write-wins. **RSV** is shipped (`reserve` / `extend` / `release`). CapsPolicy **`WorkerWriteScope`** hard-rejects out-of-scope mutate **when session ACL is enabled**.

| Pattern | When |
|---------|------|
| **Disjoint anchors** | Parallel workers; each owns a non-overlapping anchor subtree |
| **RSV lease** | Overlapping neighbourhood with explicit `llm_id` + TTL |
| **Separate session ids** | Independent missions; parent **imports** a member slice at settle if needed |
| **Serial single writer** | Default when scopes overlap and no RSV |

**MUST NOT** have two writers mutate the same anchor slice without serialisation or a live reserve.

## Anti-patterns

| Anti-pattern | Why it fails |
|--------------|--------------|
| Chat as SSOT for ids / mission state | Workers and parent diverge; re-`pin_map` is mandatory |
| In-process MCP under Multitask | Each process gets its own graph |
| Parent polls or re-runs worker investigation | Wastes tokens; violates Multitask turn boundary |
| Worker mints duplicate `TSK_*` | Parent owns task lifecycle |
| Client `NEW` on ingest pins | Locators are ground; `unknown` / duplicate ids |
| Teaching full ACL modes/token as available | Modes are to-be; CapsPolicy when ACL on; RSV + ingest shipped |
| Snap-on-session / `rag_query` | Wrong haystack; product shape forbids it |
| Parallel workers on same anchor with no RSV | Last-write-wins; silent clobber |

## Shipped vs deferred

Gated by **MN-REQ-12.7** / **MN-VER-12-S09** where noted. Verify package: **S01…S14**.

| Capability | Requirement / verify | Status |
|------------|---------------------|--------|
| CapsPolicy ACL (`who` / `pin_map`-vs-mutate / `WorkerWriteScope` / optional bind) | MN-REQ-12.7; MN-VER-12-S09; `memnet.acl` | **Shipped when session ACL is enabled** |
| Full session ACL (`private` / `shared` / `open`), roles, `session_token` | MN-REQ-12.7; design `grammar/memnet-security-multi-agent.md` | **To-be** |
| Neighbourhood reserve (`RSV` rows, `llm_id` + TTL) | MN-REQ-12.13; `grammar/memnet-neighbourhood-reserve.md` | **Shipped** |
| Path-B `PinMapIngest_Sysml` | MN-REQ-11.16; MN-REQ-12.7; MN-VER-12-S09 | **Shipped** — `ingest_sysml` (`path=`, `qname=`, `requirementId=`) |
| Path-B `PinMapIngest_Codebase` | MN-REQ-11.6–11.8, 11.16; #64 | **Shipped** — `ingest_codebase` |
| Path-B `PinMapIngest_PcbaAto` | MN-REQ-11.9, 11.14–11.15, 11.16; #64 | **Shipped** — `ingest_pcba` |
| Path-B `PinMapIngest_SkillsRules` | MN-REQ-11.10–11.12, 11.16; #64 | **Shipped** — `ingest_skills` |

Also see gaps in [`../sysml-models/outputs/system-design-notes.md`](../sysml-models/outputs/system-design-notes.md).

## Related

- [`SHAPE.md`](SHAPE.md) — product shape (session goldfish vs corpus)
- [`README.md`](README.md) — docs index
- [`LLM-GUIDE.md`](LLM-GUIDE.md) — goldfish loop / Path-B table
- `docs/grammar/memnet-security-multi-agent.md` — target ACL model
- `docs/grammar/memnet-neighbourhood-reserve.md` — reserve (engine shipped; grammar is the design note)
- `sysml-models/models/requirements.sysml` — **MN-REQ-12**
- `sysml-models/models/verify.sysml` — **MN-VER-12-G00** + **S01…S14**
- `sysml-models/outputs/multitask-case-study.md` — worked scenario
- `docs/application-notes/llm-system-dev-multitask.md` — `modelbasedPrj-*` pattern
- `.cursor/skills/memnet-reference/SKILL.md` — product development skill
- `~/.cursor/skills/memnet-multitask/` — application Multitask skill (user pack)
- `AGENTS.md` — hub policy
