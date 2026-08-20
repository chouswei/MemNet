# Atomisation -- knowledge graph discipline

MemNet is an **in-memory knowledge graph**: **nodes** + **relationships**. Agent I/O is the **GQL wire** only (shaped pin_map + openCypher-shaped mutate). The pin map (`pin_map`) returns connected **atoms** -- not the whole store.

**Atomisation is the most important step.** Dumping paragraphs or merged facts into one row bloats pin maps and breaks the graph.

## Core rules

1. **One idea per row** -- one function, one constraint, one fact, one task phase
2. **Relations are edges** -- `calls`, `owns`, `constrained_by`, `defines`, ...
3. **Short fields only** -- ids, paths, line numbers, codes; **no prose blobs**
4. **Split compound state** -- if a field needs "and also ...", add another row + edge
5. **Stable ids** -- reuse forever; `update` when the atom changes

Bad: one `MOD` whose summary is a paragraph of architecture.
Good: `MOD` + several `SYM` + edges linking task -> modules -> symbols.

## Why it matters

```text
pin_map(anchor=TSK_x, depth=2)
  -> LAW rows
  -> anchor node
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

```text
## Nodes
+ TSK [NEW] ; goal=Expose send_command ; status=in_progress ; recycle=persistent
+ MOD [NEW] ; path=src/memnet/serve.py ; summary=TCP serve ; status=active ; recycle=persistent
+ SYM [NEW] ; name=send_command ; kind=fn ; path=src/memnet/serve.py ; line=96 ; recycle=persistent

## Edges
+ E01 [NEW] --(owns)--> [MOD_serve] ; note=scope ; recycle=persistent
+ E02 [NEW] --(defines)--> [SYM_send_command] ; note=handler ; recycle=persistent
```

Copy assigned ids from the mutate / pin-map response.

## Checklist

- [ ] One fact per row?
- [ ] Relations are separate edges?
- [ ] Fields short (no sentences)?
- [ ] Ids from pin map or `NEW` mint (then copy)?

Cross-ref: [wire-format.md](wire-format.md) · [coding-memory.md](coding-memory.md) · [memnet-format](../../memnet-format/SKILL.md)
