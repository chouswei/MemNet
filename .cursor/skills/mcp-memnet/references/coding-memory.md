# MemNet for coding memory

Use MemNet when the agent must **remember where things are across turns** — function locations, modules touched, refactor plans — without stuffing paths into chat history.

**Atomise first:** one `MOD` per file, one `SYM` per symbol, edges for relationships — see [atomisation.md](atomisation.md). Short field values only ([wire-format.md](wire-format.md)). GQL wire only (shaped pin_map + openCypher-shaped mutate).

MemNet is **agent-maintained index + task graph**, not a substitute for `grep`, LSP, or semantic search. **Verify** on disk; **store** confirmed atoms.

## When to use (coding)

| Situation | Use MemNet? |
|-----------|-------------|
| Multi-file refactor spanning many chat turns | **Yes** — anchor on `TSK` or `MOD` |
| “Where is `send_command`?” after you already found it once | **Yes** — `SYM` + pin map |
| Tracking files/modules touched for current task | **Yes** — `MOD` + edges |
| User-stated API/style constraints | **Yes** — `USR` + `constrained_by` from `TSK` |
| Open design fork (default value, naming) | **Yes** — `DEC`; settle with `chosen` |
| One-shot symbol lookup, never referenced again | **No** — grep / Go to definition |
| Authoritative “what calls X?” | **No** — ripgrep / LSP first; optionally **add** edge after verify |

**Open a coding session** at the start of a non-trivial task. One session per repo/task; reuse ids. Use `session_save` / `session_load` for multi-day work.

## Kinds (session)

| Kind | Purpose | Typical fields |
|------|---------|----------------|
| `CFG` | Repo root | `repo`, `anchor`, `version`, `notes` |
| `MOD` | File or package | `path`, `summary`, `status`, `recycle` |
| `SYM` | Function, class, … | `name`, `kind`, `path`, `line`, `sig`, `status`, `recycle` |
| `TSK` | Active coding mission | `goal`, `status`, `recycle` |
| `USR` | User constraints | `topic`, `content`, `status`, `recycle` |
| `DEC` | Open fork | `task`, `question`, `options`, `chosen`, `recycle` |
| Edge | Relations | `--(rel)-->` + optional `note`, `recycle` |

Edge rels: `imports`, `calls`, `tests`, `implements`, `owns`, `constrained_by`, `related`, `defines`.

## ID conventions

| Entity | ID pattern | Example |
|--------|------------|---------|
| Module | `MOD_` + slug from path | `MOD_mcp_server` |
| Symbol | `SYM_` + layer prefix | `SYM_cli_session_load` |
| Task | `TSK_` + short name | `TSK_mcp_session_load` |
| User constraint | `USR_` + topic slug | `USR_keep_id` |
| Decision | `DEC_` + slug | `DEC_mcp_keep_id` |
| Edge | `E` + slug or number | `E_mcp_impl_load` |

Copy ids from the pin map — never retype from memory.

## Goldfish loop (coding)

1. Pin map (`query_warm`) on current `TSK` (or `MOD` / `SYM` if task unset).
2. **grep/LSP** if you need fresh truth on disk.
3. **`add`** / **`update`** shared-dialect lines when path/line/signature or task status changes.
4. **`session_save`** after substantive turns.
5. Settle task (`status=done`, `recycle=delete_on_settle`) when finished.

## MCP examples

### Start task + record a function

```text
## Nodes
+ TSK [NEW] ; goal=Expose session_load on memnet-mcp ; status=in_progress ; recycle=persistent
+ MOD [NEW] ; path=src/memnet/cli.py ; summary=Typer CLI session commands ; status=active ; recycle=persistent
+ SYM [NEW] ; name=session_load ; kind=fn ; path=src/memnet/cli.py ; line=351 ; sig=def session_load(...) ; status=active ; recycle=persistent
+ USR [NEW] ; topic=api ; content=keep_id default true on session_load ; status=active ; recycle=persistent
+ DEC [NEW] ; question=keep_id default ; options=true / false ; recycle=persistent

## Edges
+ E01 [NEW] --(owns)--> [MOD_cli] ; note=task scope ; recycle=persistent
+ E02 [NEW] --(defines)--> [SYM_cli_session_load] ; note=handler ; recycle=persistent
+ E03 [NEW] --(constrained_by)--> [USR_keep_id] ; note=user stated ; recycle=persistent
```

Copy assigned ids from the mutate / pin-map response (replace `NEW` placeholders above with real ids on follow-up).

### Settle decision + task

```text
## Nodes
~ [DEC_mcp_keep_id] ; chosen=true ; recycle=delete_on_settle
~ [TSK_mcp_session_load] ; status=done ; recycle=delete_on_settle
```

### Next turn — where is that function?

```text
pin_map(anchor="TSK_mcp_session_load", depth=2)
```

Returns LAW + connected task/module/symbol/user/decision/edge atoms — small slice, not the whole repo.

### File moved after refactor

```text
## Nodes
~ [SYM_cli_session_load] ; path=src/memnet/cli.py ; line=352 ; recycle=persistent
```

## Anchors to prefer

| Anchor | Pin-map slice |
|--------|---------------|
| `TSK_*` | Task + owned modules/symbols/decisions/constraints |
| `MOD_*` | File + symbols defined there + callers |
| `SYM_*` | Symbol + module + call graph neighbours |
| `MOD_repo_root` | CFG anchor — repo context |

## Limits

- Rows are **not** auto-synced from git — **update** after moves/renames.
- Do not store whole files — store **path, line, short signature, summary**.
- Prefer **one `TSK` in_progress** per session; settle before starting unrelated work.
- Respect cap warnings; run `housekeep_stats` if rows grow.

## Pair with codebase tools

```text
Turn N:   pin map(TSK) → grep/LSP → add/update MOD/SYM
Turn N+1: pin map(TSK) → edit file → update SYM line if shifted
```

Do not skip verification on the first discovery turn; MemNet remembers **confirmed** atoms.

Cross-ref: [atomisation.md](atomisation.md) · [mcp-policy.md](mcp-policy.md) · [user-input-memory.md](user-input-memory.md)
