# SysML + MemNet -- pipeline handoffs

**Audience:** LLM agents. Structured state **between pipeline steps** uses MemNet **GQL / openCypher-shaped** wire when MemNet MCP is up -- not TOON/TRON in chat. Wire: [memnet-format](../../memnet-format/SKILL.md), [mcp-memnet](../../mcp-memnet/SKILL.md). Thin SysML bridge: [sysml-gql](../../sysml-gql/SKILL.md).

Pair with [sysml-memnet-snap.md](sysml-memnet-snap.md) (6-step turn).

---

## Tiered handoff (mandatory)

| Situation | Format | Where it lives |
|-----------|--------|----------------|
| **SysML modeling turn** (steps 1-6) | openCypher-shaped mutate; step `code` = `sN:payload` | `mutate` each step |
| **Report generate/maintain** (G/M steps) | Same + ART/SEC when prose settles | Server graph |
| **Skill routing** (`order[]`, picks) | Task + claim atoms + `led_to_success` edges | Server graph |
| **Serve down** | Plain Markdown tables or short prose | Ephemeral -- not durable |
| **MCP / CLI tool boundary** | JSON envelope | Tool response only |

**Rule:** If MemNet is up and the handoff must survive context shrink -> **atoms on server**, not Markdown-only scratch in chat.

---

## Step atoms (openCypher-shaped)

Mutate after each step (or batch s1-s2, then s3, then s4-s6). Pin map is the shaped present; mutate keeps ops.

```cypher
CREATE (t:TSK {goal: $goal, phase: 'turn', status: 'in_progress', recycle: 'delete_on_settle'})
CREATE (c1:CLM {type: 'decision', code: 's1:up', recycle: 'delete_on_settle'})
CREATE (c2:CLM {type: 'decision', code: 's2:hit', recycle: 'delete_on_settle'})
CREATE (t)-[:CHILDOF {note: 'turn', recycle: 'delete_on_settle'}]->(:TSK {id: $modelTid})
```

Copy assigned ids from the pin map / mutate response. Settle with:

```cypher
MATCH (t:TSK {id: $tid}) SET t.status = 'settled'
```

### Step `code` vocabulary

| Step | `code` prefix | Example `code` |
|------|---------------|----------------|
| s1 serve | `s1:` | `s1:up` · `s1:down` |
| s2 warm | `s2:` | `s2:hit` · `s2:miss` |
| s3 edit | `s3:` | `s3:SYM_mcuHeaderHarness` · `s3:skip` |
| s4 validate | `s4:` | `s4:pass` · `s4:fail` |
| s5 sync | `s5:` | `s5:done` · `s5:skip` · `s5:report_delta` |
| s6 delta | `s6:` | `s6:Nrows` · `s6:skip` · `s6:stale` |

**Step 2 skip** (serve down): `s1:down`, omit s2 or `s2:skip`, note `s6:stale` if no delta.

**Step 5 skip** (no outputs): `s5:skip`.

**Step 6 skip** (comment-only): `s6:skip` + settle turn.

**Resume next turn:** pin map on `TSK_model_<short>` -- latest in-progress turn or last step atoms; **do not** re-derive from chat.

### Six-step template

```cypher
CREATE (t:TSK {goal: $goal, phase: 'turn', status: 'in_progress', recycle: 'delete_on_settle'})
CREATE (c1:CLM {type: 'decision', code: 's1:up', recycle: 'delete_on_settle'})
CREATE (c2:CLM {type: 'decision', code: 's2:hit', recycle: 'delete_on_settle'})
CREATE (c3:CLM {type: 'decision', code: 's3:SYM_<symbol>', recycle: 'delete_on_settle'})
CREATE (c4:CLM {type: 'decision', code: 's4:pass', recycle: 'delete_on_settle'})
CREATE (c5:CLM {type: 'decision', code: 's5:sync:done', recycle: 'delete_on_settle'})
CREATE (c6:CLM {type: 'decision', code: 's6:24rows', recycle: 'delete_on_settle'})
CREATE (t)-[:CHILDOF {note: 'turn', recycle: 'delete_on_settle'}]->(:TSK {id: $modelTid})
```

### Router / skill pick

```cypher
CREATE (t:TSK {goal: $intent, phase: 'route', status: 'in_progress', recycle: 'delete_on_settle'})
CREATE (c1:CLM {type: 'decision', code: 'pick:sysml-modeling-workflow', recycle: 'delete_on_settle'})
CREATE (c2:CLM {type: 'decision', code: 'pick:sysml-memnet-documentation', recycle: 'delete_on_settle'})
CREATE (t)-[:LED_TO_SUCCESS {note: 'pass', recycle: 'persistent'}]->(:SKL {id: 'sysml-modeling-workflow'})
```

Phase-4 learning: `led_to_success` edges are **`persistent`**; route task is **`delete_on_settle`**.

---

## Report pipeline -- G / M steps

Parent: `TSK_model_<short>` or `TSK_report_<short>` (`phase=report`, `delete_on_settle`).

| Phase | Step | `code` |
|-------|------|--------|
| Generate | G0-G7 | `G0:serve` … `G7:done` |
| Maintain | M1-M5 | `M1:warm` … `M5:clm_delta` |

```cypher
CREATE (t:TSK {goal: 'Sync relay section', phase: 'report', status: 'in_progress', recycle: 'delete_on_settle'})
CREATE (c1:CLM {type: 'decision', code: 'M1:warm', recycle: 'delete_on_settle'})
CREATE (c2:CLM {type: 'decision', code: 'M2:sec_S05-relay', recycle: 'delete_on_settle'})
CREATE (c3:CLM {type: 'decision', code: 'M5:8clm', recycle: 'delete_on_settle'})
```

Link report atoms with edges (`mentions` -> CON/PRT) in the same batch as model delta.

---

## Diagram placement task

Use when building or updating **interconnection Mermaid** in `outputs/**/*.md`. Full algorithm: [mermaid/references/mermaid-placement-by-degree.md](../../mermaid/references/mermaid-placement-by-degree.md).

**Parent:** `TSK_diagram_<figureId>` `childOf` -> `TSK_model_<short>` · `documents` -> section atom · `delete_on_settle` until `p6:settle`.

| Code | Action | Touches `.md`? |
|------|--------|----------------|
| `p0:types` | typedBy histogram -> intent bucket | No |
| `p1:scope` | figure_includes / figure_uses edges | No |
| `p2:place` | Ranks, anchor, adjacent_to, claim stats | No |
| `p2b:bary` | Barycenter lane iteration <=2 | No |
| `p2c:spans` | Per-CON rank_span | No |
| `p3:edges` | Ordered CON_* | No |
| `p4:materialise` | Patch section `.md`; mmdc | **Yes** |
| `p5:review` | Visual check; ok / adjust | Re-p4 only |
| `p6:settle` | Method claim on section; settle | No |

**Serve down:** Markdown `DiagramPlan` tables in-prompt; backfill MemNet before `p4`.

---

## Between-step execution (goldfish)

```
step N:   pin map on TSK_model_* OR TSK_turn_*
          -> act
          -> add/update step atom for step N
step N+1: pin map (same anchor) -- read step atoms, not chat
```

**MUST NOT** paste pipeline state only as chat Markdown when MemNet is up.

**MAY** echo a **single-line** summary for the user (`Turn settled: s4:pass s6:24rows`).

---

## Serve down fallback

When `s1:down`:

1. Use plain Markdown tables or short prose for in-turn scratch only.
2. Set `s6:stale` on the turn if you would have written delta.
3. On next session with MemNet up: run incremental delta from disk before relying on the pin map.

---

## Anti-patterns

| Bad | Good |
|-----|------|
| Markdown-only scratch in chat for s1-s6 state | Step atoms on server |
| Re-read deploy because pipeline state was only in chat | Pin map on turn task |
| One fat note for whole turn | One claim per step |
| Skip settle -> `settled` | Settle so the pin map stays lean |
| Pipe `@TAG` or Layer line dialect as mutate | openCypher-shaped `CREATE` / `MATCH`/`SET` |

---

## Quick checklist

- [ ] MemNet up -> GQL wire; down -> Markdown
- [ ] Opened turn task or attached to `TSK_model_*` via `childOf`
- [ ] Each completed step has a step atom (`code` = `sN:…`)
- [ ] Turn `settled` when done
- [ ] Next step starts with pin map, not chat memory
