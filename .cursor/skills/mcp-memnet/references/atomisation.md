# Atomisation -- knowledge graph discipline

MemNet is an **in-memory knowledge graph**: **nodes** + **relationships**. Agent I/O is the **GQL wire** only (shaped pin_map + openCypher-shaped mutate). The pin map (`pin_map`) returns connected **atoms** -- not the whole store.

**Atomisation is the most important step.** Dumping paragraphs or merged facts into one row bloats pin maps and breaks the graph.

## Core rules

1. **One idea per row** -- one function, one constraint, one fact, one task phase
2. **Relations are edges** -- `calls`, `owns`, `constrained_by`, `defines`, ...
3. **Short fields only** -- paths, line numbers, codes; **no prose blobs**
4. **Split compound state** -- if a field needs "and also ...", add another row + edge
5. **Cue by labels+properties** -- MATCH the same pattern; leftover nickname `id` is leftover

Bad: one `MOD` whose summary is a paragraph of architecture.
Good: `MOD` + several `SYM` + edges linking task -> modules -> symbols.

## Why it matters

```text
pin_map(kind='TSK', locators=['goal=Expose send_command'], depth=2)
  -> LAW rows
  -> seed node
  -> edge-linked neighbours up to depth
  -> NOT unrelated atoms elsewhere
```

## Domains (kinds)

| Domain | Node kinds | Edge examples |
|--------|------------|---------------|
| Coding | MOD, SYM, TSK, USR | defines, calls, owns, constrained_by |
| User input | USR | constrained_by from TSK |
| SysML | PKG, PRT, POR, CON, REQ, ... | declaredIn, satisfies, connects |
| Article | ART, SEC, CLM, ENT | contains, part_of, mentions, contradicts |

## MCP write pattern (openCypher-shaped)

Prefer **one `add` call, many atom lines**:

```cypher
CREATE (:TSK {goal: 'Expose send_command', status: 'in_progress', recycle: 'persistent'})
CREATE (:MOD {path: 'parts/common/memnet/memnet/serve.py', summary: 'TCP serve', status: 'active'})
CREATE (:SYM {name: 'send_command', kind: 'fn', path: 'parts/common/memnet/memnet/serve.py', line: '96'})
MATCH (t:TSK {goal: 'Expose send_command'}), (m:MOD {path: 'parts/common/memnet/memnet/serve.py'})
CREATE (t)-[:owns {note: 'scope'}]->(m)
MATCH (m:MOD {path: 'parts/common/memnet/memnet/serve.py'}), (s:SYM {name: 'send_command'})
CREATE (m)-[:defines {note: 'handler'}]->(s)
```

Prefer **one `mutate` call, many statements**. leftover `+ TSK [NEW]` line dialect is leftover.

## Checklist

- [ ] One fact per row?
- [ ] Relations are separate edges?
- [ ] Fields short (no sentences)?
- [ ] Cue by labels+properties (not leftover `id`)?

Cross-ref: [wire-format.md](wire-format.md) · [coding-memory.md](coding-memory.md) · [memnet-format](../../memnet-format/SKILL.md)
