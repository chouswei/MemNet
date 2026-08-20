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
| Authoritative “what calls X?” | **No** — ripgrep / LSP first; optionally **mutate** an edge after verify |

**Open a coding session** at the start of a non-trivial task. One session per repo/task. Cue by path/name/goal. Use `session_save` / `session_load` for multi-day work.

## Kinds (session)

| Kind | Purpose | Typical fields |
|------|---------|----------------|
| `CFG` | Repo root | `repo`, `anchor`, `version`, `notes` |
| `MOD` | File or package | `path`, `summary`, `status`, `recycle` |
| `SYM` | Function, class, … | `name`, `kind`, `path`, `line`, `sig`, `status`, `recycle` |
| `TSK` | Active coding mission | `goal`, `status`, `recycle` |
| `USR` | User constraints | `topic`, `content`, `status`, `recycle` |
| `DEC` | Open fork | `task`, `question`, `options`, `chosen`, `recycle` |
| Edge | Relations | typed rel + optional `note`, `recycle` |

Edge rels: `imports`, `calls`, `tests`, `implements`, `owns`, `constrained_by`, `related`, `defines`.

## Cue properties (not a store key)

| Kind | Cue on | Example |
|------|--------|---------|
| Module | `path` | `parts/common/memnet/memnet/cli.py` |
| Symbol | `name` + `path` | `session_load` |
| Task | `goal` | `Expose session_load on memnet-mcp` |
| User constraint | `topic` | `api` |
| Decision | `question` | `keep_id default` |

leftover nickname `id` / `MOD_*` mint is leftover.

## Goldfish loop (coding)

1. `pin_map` on the current `TSK` (`kind` + `goal`) or `MOD` / `SYM` (`path` / `name`).
2. **grep/LSP** if you need fresh truth on disk.
3. **`mutate`** when path/line/signature or task status changes. leftover `add`/`update` named leftover.
4. **`session_save`** after substantive turns.
5. Settle task (`status=done`, `recycle=delete_on_settle`) when finished.

## MCP examples

### Start task + record a function

```cypher
CREATE (:TSK {goal: 'Expose session_load on memnet-mcp', status: 'in_progress'})
CREATE (:MOD {path: 'parts/common/memnet/memnet/cli.py', summary: 'Typer CLI session commands', status: 'active'})
CREATE (:SYM {name: 'session_load', kind: 'fn', path: 'parts/common/memnet/memnet/cli.py', line: '387'})
CREATE (:USR {topic: 'api', content: 'MCP session_load keep_id default true', status: 'active'})
CREATE (:DEC {question: 'keep_id default', options: 'MCP true / CLI false'})
MATCH (t:TSK {goal: 'Expose session_load on memnet-mcp'}), (m:MOD {path: 'parts/common/memnet/memnet/cli.py'})
CREATE (t)-[:owns {note: 'task scope'}]->(m)
MATCH (m:MOD {path: 'parts/common/memnet/memnet/cli.py'}), (s:SYM {name: 'session_load'})
CREATE (m)-[:defines {note: 'handler'}]->(s)
MATCH (t:TSK {goal: 'Expose session_load on memnet-mcp'}), (u:USR {topic: 'api'})
CREATE (t)-[:constrained_by {note: 'user stated'}]->(u)
```

### Settle decision + task

```cypher
MATCH (d:DEC {question: 'keep_id default'}) SET d.chosen = 'MCP true', d.recycle = 'delete_on_settle'
MATCH (t:TSK {goal: 'Expose session_load on memnet-mcp'}) SET t.status = 'done', t.recycle = 'delete_on_settle'
```

### Next turn — where is that function?

```text
pin_map(kind='TSK', locators=['goal=Expose session_load on memnet-mcp'], depth=2)
```

Returns LAW + connected task/module/symbol/user/decision/edge atoms — small slice, not the whole repo.

### File moved after refactor

```cypher
MATCH (s:SYM {name: 'session_load', path: 'parts/common/memnet/memnet/cli.py'})
SET s.line = '390'
```

## Cues to prefer

| Cue | Pin-map slice |
|-----|---------------|
| `kind=TSK` + `goal=` | Task + owned modules/symbols/decisions/constraints |
| `kind=MOD` + `path=` | File + symbols defined there + callers |
| `kind=SYM` + `name=` | Symbol + module + call graph neighbours |

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
