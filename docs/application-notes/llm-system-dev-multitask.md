# System development with Multitask — A MemNet application note

**Class:** applications — downstream `modelbasedPrj-*` system repos.  
**Operational doctrine (developers):** [`docs/multi-agent-sessions.md`](../multi-agent-sessions.md).  
**Application skill:** `~/.cursor/skills/memnet-multitask/`. Index: [`docs/README.md`](../README.md).

**Application example (documentation only).** Pattern for a downstream **`modelbasedPrj-*` system repository** when Cursor **Multitask Mode** (or Task sub-agents) runs multi-step system, software, or SysML work. MemNet holds **mission goldfish state**; the product **`sysml-models/`** tree remains **structural SSOT** for the system under design.

**Dialect:** workers mutate **Write = display** / **Layer** (`pin_map` first). Electrical law leaves use `ports=` / `law=` / `--bind-->` — see [`llm-circuit-schematic.md`](llm-circuit-schematic.md). Do not teach `@TAG` pipe as the agent surface.

This note complements:

- [`docs/multi-agent-sessions.md`](../multi-agent-sessions.md) — enforceable Multitask doctrine (as-is 0.4.x)
- [`sysml-models/outputs/multitask-case-study.md`](../../sysml-models/outputs/multitask-case-study.md) — MemNet product SysML walk-through (MN-REQ-12)
- [`llm-sysml-v2-modeling.md`](llm-sysml-v2-modeling.md) — single-agent SysML memory (no Multitask transport)
- [`llm-software-development.md`](llm-software-development.md) — single-agent coding memory

**Doctrine pointer:** adopt **MN-REQ-12** via a short local requirement mirror or doc link — do **not** import `MemNetRequirements` from the MemNet product repo into the system project's SysML load tree.

---

## 1. Two stores of truth

| Store | Role | SSOT for |
|-------|------|----------|
| **MemNet session** (shared TCP/HTTP) | Turn-facing goldfish: `TSK_*`, `USR_*`, scoped `MOD_*` / `SYM_*`, `CLM_*` / `DEC_*` | Mission ids, paths, task status, agent-verified locators |
| **Product `sysml-models/`** | Versioned structural model (requirements, deploy, behaviour) | System architecture, interfaces, satisfy/trace to product reqs |
| **Source tree** (`parts/`, firmware, docs) | Git history | Code and artefacts on disk |

Chat and sub-agent prose are **never** mission SSOT (MN-REQ-12.1; extends MN-REQ-10.1).

```mermaid
flowchart TB
  subgraph mission [Shared MemNet session TCP/HTTP]
    TSK[TSK_* parent task]
    USR[USR_* constraints]
    MOD[MOD_* / SYM_* under scope]
  end
  subgraph structural [Product sysml-models/ git]
    REQ[requirements.sysml]
    DEP[deploy.sysml]
    BEH[behaviour.sysml]
  end
  subgraph workers [Multitask workers]
    W1[Worker scoped mutate]
  end
  PARENT[Parent coordinator] --> TSK
  PARENT -->|delegate + end turn| W1
  W1 -->|pin_map first| mission
  PARENT -->|pin_map reconcile| mission
  W1 -.->|edit when in scope| structural
  structural -.->|Path-B seed_lines / add| mission
```

---

## 2. Transport (non-negotiable under Multitask)

Parent and every worker **MUST** bind to the **same** GraphStore via **TCP serve** (`MEMNET_MCP_TRANSPORT=tcp`, `:18765`) or **streamable-http** MCP (`:18766/mcp`). Default **in-process** MCP gives each process an isolated graph — **MUST NOT** use for shared missions (MN-REQ-12.2).

| Pattern | When |
|---------|------|
| **One mission session id** | Default: parent passes `session` in every worker prompt |
| **Separate session ids** | Independent missions only; parent merges at settle if needed |

Probe with `serve_status` before delegating if transport is uncertain.

---

## 3. Parent coordinator

### MUST

- `session_open` / `session_load` **one** mission id before spawn; pass it in worker prompts.
- Mint and own **`TSK_*`** / **`USR_*`**: `status=active` → `status=settled`; optional `led_to_success` edges.
- Assign **write scope** (anchor ids + allowed relation types) in self-contained worker prompts.
- **End the turn** after background spawn — no poll, no await (MN-REQ-12.6).
- Next coordinator turn: **`pin_map` first**; act from refreshed slice — do not redo worker investigation from chat.
- Prefer **one worker** per coherent workstream; parallel only with **disjoint** anchors or **separate** sessions (MN-REQ-12.5).

### MUST NOT

- Settle parent `TSK_*` from worker chat — only from shared-session pin-map facts.
- Assume session ACL, neighbourhood reserve (`RSV`), or `PinMapIngest_*` engines (MN-REQ-12.7; verified by MN-VER-12-S09).

---

## 4. Worker agent

### MUST

- Use the parent's **session id**; **`pin_map` first** every turn.
- Copy assigned ids from pin map — **MUST NOT** invent ids the parent already minted.
- Mutate only under the **assigned subgraph** (anchors + relations in the prompt).
- Return a concise result; durable facts live in MemNet rows.

### MUST NOT

- Open a different session unless explicitly assigned.
- Settle parent-owned `TSK_*` / `USR_*` unless delegated.
- Use in-process MCP when the parent uses shared TCP/HTTP.

---

## 5. Serial SysML then code (recommended)

When work touches both **`sysml-models/`** and implementation files:

| Order | Worker | Scope | Rationale |
|-------|--------|-------|-----------|
| **1** | SysML worker | `MOD_*` under `sysml-models/`, product `REQ_*` / `SYM_*` | Structural decisions land in git SSOT first |
| **2** | Code worker | `parts/`, tests, firmware | Implementation follows model; disjoint `MOD_*` anchors |

**Alternative:** one worker if the mission is small and files do not overlap.

**MUST NOT** run two workers on the **same** anchor slice without serialisation (0.4.x last-write-wins; no neighbourhood reserve).

---

## 6. Adopting MN-REQ-12 in a system repo

The MemNet **product** models Multitask in `MemNetRequirements::MN_REQ_12_*` and `MemNetVerification` (MN-VER-12-G00, S01…S09). A **`modelbasedPrj-*` repo** should:

| Approach | Use |
|----------|-----|
| **Doc pointer** | Link `docs/multi-agent-sessions.md` + this note in `AGENTS.md` / project rules |
| **Thin local mirror** | e.g. `SYS_REQ_MT_*` leaves in *product* `requirements.sysml` that restate operational SHALLs — **not** a git submodule of MemNet SysML |
| **Verify (optional)** | Product-specific verify cases that `verify` local reqs and reference MemNet case study — do not duplicate the full MemNet verify package |

Do **not** add `import MemNetRequirements::*` from the MemNet engine repo into the system load tree unless the project explicitly owns a merged model (rare).

---

## 7. Path-B pin seed (manual)

Path-B **`PinMapIngest_*`** (SysML, codebase, PCBA, skills) is **roadmap only** in 0.4.x (MN-REQ-11 stubs; MN-REQ-12.7). Seed external locators explicitly:

| Method | When |
|--------|------|
| `session_open` **`seed_lines`** | Mission start: `MOD_*`, `SYM_*` with `path=`, `qname=`, `loc=` |
| **`add`** with deterministic ids | Incremental locators after grep/LSP confirm |
| **LLM `NEW`** | Goldfish-authored `CLM_*`, `DEC_*`, mission annotations only — not for re-creating source pins |

Re-`pin_map` after seeding; workers copy ids from the slice.

---

## 8. Pin taxonomy (system-dev missions)

| Prefix | Owner | Typical use |
|--------|-------|-------------|
| `TSK_*`, `USR_*` | **Parent** | Mission task, user constraints |
| `MOD_*`, `SYM_*`, `REQ_*`, `PRT_*` | Worker under scope | Files, symbols, product requirements, parts |
| `CLM_*`, `DEC_*` | Worker (**NEW** OK) | Findings, open decisions |

Edges: `owns`, `about`, `constrained_by`, `led_to_success` (parent settle), domain relations from product grammar.

---

## 9. Failure modes

| Failure | Symptom | Mitigation |
|---------|---------|------------|
| In-process MCP under Multitask | Worker writes invisible to parent | TCP/HTTP shared store; `serve_status` |
| Chat as SSOT | Duplicate ids, stale paths | `pin_map` every turn; parent reconcile from session |
| Parent polls / re-investigates | Token waste; gate violation | End turn after spawn; next turn pin_map only |
| Parallel same-anchor writers | Silent clobber | Serial worker or disjoint scopes |
| Assuming ACL / `RSV` / ingest | False confidence in isolation | MN-REQ-12.7; seed Path-B manually |
| SysML vs MemNet drift | Model and pins disagree | SysML in git wins for structure; MemNet holds locators + mission state |
| Worker settles parent `TSK_*` | Lifecycle violation | Parent-only settle unless delegated |

---

## 10. Open decisions (record in `DEC_*`)

- Local IPC vs TCP when `LocalIpcGateway` ships (MN-REQ-06.2).
- Whether to add product-specific `SYS_REQ_MT_*` leaves or doc-only adoption.
- Single worker vs SysML-then-code split per mission class.
- When engine **WorkerWriteScope** enforcement lands (currently doctrine-only; MN-VER-12-S09 gate).

---

## 11. Related

| Topic | Path |
|-------|------|
| Enforceable Multitask doctrine | [`docs/multi-agent-sessions.md`](../multi-agent-sessions.md) |
| MemNet product MN-REQ-12 model | [`sysml-models/models/requirements.sysml`](../../sysml-models/models/requirements.sysml) |
| Verify package | [`sysml-models/models/verify.sysml`](../../sysml-models/models/verify.sysml) (MN-VER-12-G00, S01…S09) |
| Case study | [`sysml-models/outputs/multitask-case-study.md`](../../sysml-models/outputs/multitask-case-study.md) |
| ACL / reserve (design) | [`docs/grammar/memnet-security-multi-agent.md`](../grammar/memnet-security-multi-agent.md), [`memnet-neighbourhood-reserve.md`](../grammar/memnet-neighbourhood-reserve.md) |
| SysML modeling (single-agent) | [`llm-sysml-v2-modeling.md`](llm-sysml-v2-modeling.md) |
