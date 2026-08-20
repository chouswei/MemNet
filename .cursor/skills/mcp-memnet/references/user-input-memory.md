# MemNet for user input and preferences

When the agent **must recall what the user said** across turns — atomise each constraint as its own **`USR`** row (one fact, short `content`), link to `TSK` via an edge. See [atomisation.md](atomisation.md), [wire-format.md](wire-format.md). GQL wire only.

MemNet is **not** a chat log. Store **distilled atoms**, not messages.

## When to write user input to MemNet

| User said | Store? | Example |
|-----------|--------|---------|
| Hard constraint ("never force push", "British English") | **Yes** — `USR`, `persistent` | `topic=git ; content=never force push main` |
| Scope decision ("only touch MCP files") | **Yes** — edge from `TSK` | |
| One-off clarification for this message only | **No** — act immediately | |
| Preference that affects many turns | **Yes** | `topic=style ; content=concise technical blog` |
| Pipeline input | **Yes** — `USR` + edge to `TSK` | |

**Rule:** If forgetting it in 5 turns would cause wrong behaviour → **`add` `USR`** after the user message.

## Fields

| Field | Use |
|-------|-----|
| `topic` | Short key: `git`, `scope`, `style`, `decision`, `requirement` |
| `content` | Distilled fact — short phrase, not a paragraph |
| `status` | `active` while in force; `superseded` when user changes mind |
| `recycle` | `persistent` for long-lived prefs; `delete_on_settle` for step-local input |

## MCP examples

**Teach GQL** (pipe `+ TAG` samples below are legacy import only — do not emit as agent I/O):

### Capture user constraint at start of task

```text
## Nodes
+ TSK [NEW] ; goal=Implement MCP docs ; status=in_progress ; recycle=persistent
+ USR [NEW] ; topic=files ; content=only src/memnet_mcp and docs ; status=active ; recycle=persistent
+ USR [NEW] ; topic=style ; content=British English in replies ; status=active ; recycle=persistent

## Edges
+ E01 [NEW] --(constrained_by)--> [USR_scope] ; note=user stated ; recycle=persistent
+ E02 [NEW] --(constrained_by)--> [USR_lang] ; note=user stated ; recycle=persistent
```

### Next turn — recall before acting

```text
pin_map(anchor="TSK_current", depth=2)
```

Pin map includes `USR` rows linked to the task.

### User changes mind

```text
## Nodes
~ [USR_scope] ; content=memnet repo only, no user-pack edits ; status=active ; recycle=persistent
```

Same id — **update**, not add.

## Anchors

| Anchor | Recalls |
|--------|---------|
| `TSK_*` | Task + linked `USR` constraints |
| `USR_*` | Single preference + edges to tasks |

## vs chat history

| Chat history | MemNet `USR` |
|--------------|--------------|
| May scroll away | Stays until settled or updated |
| Mixed with agent text | User-sourced facts only |
| Hard to query by task | Pin map from `TSK` pulls relevant `USR` |

## Pair with goldfish loop

Each turn: **pin map** first (includes user constraints) → act → **`add`/`update`** if the user said something new that must persist.

Cross-ref: [atomisation.md](atomisation.md) · [coding-memory.md](coding-memory.md) · [mcp-policy.md](mcp-policy.md)
