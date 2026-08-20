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

**Rule:** If forgetting it in 5 turns would cause wrong behaviour → **`mutate` `USR`** after the user message.

## Fields

| Field | Use |
|-------|-----|
| `topic` | Short key: `git`, `scope`, `style`, `decision`, `requirement` |
| `content` | Distilled fact — short phrase, not a paragraph |
| `status` | `active` while in force; `superseded` when user changes mind |
| `recycle` | `persistent` for long-lived prefs; `delete_on_settle` for step-local input |

## MCP examples

**Teach GQL:**

### Capture user constraint at start of task

```cypher
CREATE (:TSK {goal: 'Implement MCP docs', status: 'in_progress'})
CREATE (:USR {topic: 'files', content: 'only src/memnet_mcp and docs', status: 'active'})
CREATE (:USR {topic: 'style', content: 'British English in replies', status: 'active'})
MATCH (t:TSK {goal: 'Implement MCP docs'}), (u:USR {topic: 'files'})
CREATE (t)-[:constrained_by {note: 'user stated'}]->(u)
MATCH (t:TSK {goal: 'Implement MCP docs'}), (u:USR {topic: 'style'})
CREATE (t)-[:constrained_by {note: 'user stated'}]->(u)
```

### Next turn — recall before acting

```text
pin_map(kind='TSK', locators=['goal=Implement MCP docs'], depth=2)
```

Pin map includes `USR` rows linked to the task.

### User changes mind

```cypher
MATCH (u:USR {topic: 'files'}) SET u.content = 'memnet repo only, no user-pack edits'
```

MATCH the same labels+properties — leftover nickname `id` is leftover.

## Cues

| Cue | Recalls |
|-----|---------|
| `kind=TSK` + `goal=` | Task + linked `USR` constraints |
| `kind=USR` + `topic=` | Single preference + edges to tasks |

## vs chat history

| Chat history | MemNet `USR` |
|--------------|--------------|
| May scroll away | Stays until settled or updated |
| Mixed with agent text | User-sourced facts only |
| Hard to query by task | Pin map from `TSK` pulls relevant `USR` |

## Pair with goldfish loop

Each turn: **pin_map** first → act → **`mutate`** if the user said something that must persist.

Cross-ref: [atomisation.md](atomisation.md) · [coding-memory.md](coding-memory.md) · [mcp-policy.md](mcp-policy.md)
