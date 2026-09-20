# Unsync checkpoint pipeline — a MemNet application note

> **Dialect (product 0.8):** **GQL only** — [`../../grammar/gql-wire-profile.md`](../../grammar/gql-wire-profile.md). Product shape: [`../../SHAPE.md`](../../SHAPE.md). Shared contract: [`../README.md`](../README.md). Do **not** teach Layer / Tier A.

**Class:** applications — coordinator doctrine for unsync Multitask waves.  
**Honesty:** teach-only `c` (same goldfish loop). No new MemNet verbs. No MN-REQ-12 change. Hatch stays **0.19.10**.

**Purpose.** Parent coordinates unsync waves when MemNet is **mission SSOT**. Chat is never mission SSOT. Roles are roles, not nicknames. The next coordinator turn is a **checkpoint**, not a poll.

---

## Cite, do not fork

This note is **not** a second SSOT for transport, shared session, or parent/worker MemNet MUST. Cite these and stop:

| Layer | Owns | Path |
|-------|------|------|
| **This playbook** | Role pipeline, atom positioning, checkpoint gates, soft-pass kills | this file |
| **memnet-multitask** (user pack; this checkout vendors a copy) | Shared-session transport, `pin_map` first, parent/worker MUST | [`.cursor/skills/memnet-multitask/`](../../../.cursor/skills/memnet-multitask/) · optional `~/.cursor/skills/memnet-multitask/` |
| **memnet-format** | GQL wire / shaped `pin_map` | [`.cursor/skills/memnet-format/`](../../../.cursor/skills/memnet-format/) |
| Product ops (`docs/multi-agent-sessions.md` live path) | Multitask operating model | [`docs/operations/multi-agent-sessions.md`](../../operations/multi-agent-sessions.md) |
| System-dev adoption (`docs/application-notes/llm-system-dev-multitask.md` live path) | Two-store pattern + Multitask in `modelbasedPrj-*` / `SysMLEdgePrj-*` | [`llm-system-dev-multitask.md`](llm-system-dev-multitask.md) |
| **User Rules** | Thin pointer: Multitask → this playbook + memnet-multitask. Host prefs (secrets, PowerShell, prompt quality) stay in User Rules | Cursor User Rules — **MUST NOT** paste here |

MUST NOT restate TCP / HTTP / in-process tables or parent-worker MUST tables from memnet-multitask or `multi-agent-sessions.md`.

---

## Roles (roles ≠ nicknames)

| Role | Does | MUST NOT |
|------|------|----------|
| **Architect** | Complex **root plan** or complex **diagnosis** only. Thin I/O. | Emit atoms, waves, patches, or file contents |
| **Bind** | Plan detail. Decompose to positioned, role-tagged atoms. Returns the atom list and **stops**. | Implement those atoms in the same worker |
| **Diagnose** | Name cause + checkable proof | Implement |
| **Implement** | One bound atom (`path`, `qname`, proof) | Plan, diagnose, or deploy |
| **Deploy** | Ship a **committed** change to the live host, verify, state rollback | Author the change |
| **Web / Visual / Prose / Unclear** | Research or review when needed | Replace Bind, Implement, or Deploy |

Parent coordinates. Parent **MUST NOT** do a worker role when that role applies.

---

## Model policy (aging-safe)

- Resolve the **newest live allowlisted slug** for the role family and tier. **State the slug used**.
- MUST NOT hardcode unlisted model versions as **product law**.
- MUST NOT use `*-fast` slugs for Architect, Bind, Diagnose, Deploy, Visual, or Web.
- Session allowlist / Cursor model picker is the live source. Family names in User Rules (for example Opus / Grok / Gemini) are **non-normative examples**, not frozen SSOT.

---

## Architect I/O

**Input (thin):** problem, constraints, `path` / `qname` pointers.  
MUST NOT send `.sysml` bodies, skill stacks, bulk code, atom lists, or patches.

**Output (thin):** purpose, constraints, approach, `path` / `qname` pointers.  
MUST NOT emit atoms, waves, patches, or file contents.

---

## Bind

**Bind ready** = atom list with **position** (`wave`, `order`) and **required role**.

- Same wave = **disjoint scopes** only; else serial.
- MUST NOT collapse disjoint atoms into one worker.
- MUST NOT Bind + Implement in one worker.
- One worker only when Bind emits **one** atom, the step is serial on prior proof, or the answer is a trivial parent call.

---

## Runtime (unsync)

1. Parent mints and settles `TSK_*` / `USR_*` (lifecycle: cite memnet-multitask — do not fork). MUST NOT play the worker role when a role applies.
2. **Complex** → Architect root plan → **Architect accept** → Bind. **Normal** → Bind plans and decomposes. **Unknown cause** → Diagnose → Bind.
3. After Bind ready: spawn **one worker per ready atom** with that atom's **required role**. MUST NOT default every atom to Implement.
4. MUST spawn **unsync** (background / Multitask) and MUST **end the turn** — no poll, no await. Transport and shared `session` id: cite memnet-multitask / [`multi-agent-sessions.md`](../../operations/multi-agent-sessions.md).
5. Next coordinator turn = **checkpoint**: `pin_map` first; settle from graph facts and proofs; spawn the next wave or stop.
6. Multitask Mode governs **spawn-async + end-turn only**. It MUST NOT change atom count or required role.

GQL Commit stays `mutate`. Recall stays `pin_map`. Cite [`memnet-format`](../../../.cursor/skills/memnet-format/SKILL.md).

---

## Checkpoint kinds

| Kind | Ready when |
|------|------------|
| **Architect accept** | Thin root plan exists. Human gate if user-bound. Skip when a plan already exists, the patch is obvious, or Bind planned. |
| **Diagnose proof** | Cause named and checkable. Then Bind. |
| **Bind ready** | Atoms have position and required role. Ready wave may start. |
| **Wave proof** | Wave proof commands produced sane output. |
| **Deploy proof** | Live host shows the change; PIDs / markers recorded; rollback stated. Local test pass is **not** deploy proof. |
| **Review pass** | Visual / Web / Prose / Unclear only when needed; coordinator-auto unless the user asked for review. |

Checkpoint is the **coordinator** turn after a wave. Workers MUST NOT self-declare settle of parent-owned `TSK_*` / `USR_*`.

---

## Soft-pass kills

- Tip / chat as mission SSOT
- Poll / await after spawn
- Bind + Implement in the same worker
- Implement before Bind ready
- Deploy bundled into an Implement atom
- Committee of Implements on one atom
- Invent ids, or settle parent `TSK_*` / `USR_*` from worker chat
- Use Multitask Mode to change atom count or required role

---

## SysML note

Architect I/O gate is unchanged. Bind / parent fills purpose, packages, part / port / `qname`, and paths under the repo SysML SSOT (`sysml-models/`). Implement edits `.sysml` only after Bind ready, then syncs outputs and allocated `parts/**`.

Two-store pattern (MemNet session vs product `sysml-models/` vs source tree): cite [`llm-system-dev-multitask.md`](llm-system-dev-multitask.md). Do not restate that note's transport or parent-worker tables here.

---

## Related

| Topic | Path |
|-------|------|
| Product Multitask ops | [`docs/operations/multi-agent-sessions.md`](../../operations/multi-agent-sessions.md) |
| System-dev two-store + Multitask | [`llm-system-dev-multitask.md`](llm-system-dev-multitask.md) |
| Enforceable Multitask + MemNet skill | [`.cursor/skills/memnet-multitask/`](../../../.cursor/skills/memnet-multitask/) |
| GQL wire | [`.cursor/skills/memnet-format/`](../../../.cursor/skills/memnet-format/) · [`gql-wire-profile.md`](../../grammar/gql-wire-profile.md) |
| MN-REQ-12 case study | [`sysml-models/outputs/multitask-case-study.md`](../../../sysml-models/outputs/multitask-case-study.md) |
