# MemNet 1.x layer dialect — ANTLR4

**Status:** proposed teaching / design grammar for [`../memnet-multi-layer.md`](../memnet-multi-layer.md).  
**Not** in engine 0.3.x. Sibling R1 stub: [`../MemNet.g4`](../MemNet.g4).

| File | Role |
|------|------|
| `MemNetLayer.g4` | Combined lexer+parser for slim 1.x overlays |
| `smoke_parse.py` | Optional local smoke (needs `generated/`) |
| Header comment in `.g4` | Review findings and dialect notes |

## Generate (optional)

Pinned intent: ANTLR **4.13.x**, Python3 target (same family as `third_party/antlr4` docs pin).

```text
cd docs/grammar/antlr
java -jar .tool/antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor -no-listener -o generated MemNetLayer.g4
python smoke_parse.py
```

`.tool/` is gitignored. Commit `generated/*.py` for the layer golden pytest (regenerate when `.g4` changes). Core package does **not** require `antlr4-python3-runtime`; the layer harness / optional smoke do (`dev` extra).

## Covered shapes

- NODE present / `+` create / `~` patch
- Dual EDGE (same three wire forms):
  - **Bind:** teach `[Node.port] --bind--> [Node.port]` only (also `--bind--`, `<--bind-->`); `pipe` is **accept-only** — do not teach; optional `carries=`
  - **Relation:** `[NodeA] --knows--> [NodeB]` (bare ids; label = sense)
- Fields: `ports=name: {direc=…, q=…}` (teach `direc=`; `direction=` accept-only), brace-group values (`meta={…}`; nest OK to depth 2), quantity `@alias` (`V=@va`), `law=$eq$,$eq$` (opaque `@` / `\` inside `$…$`), generic `key=value`, patch `+=` / `-=`
- Drop: `- Eid`

`{…}` = brace-group / record (ports primary teach; other attrs may take bare `{…}`). **Max nesting depth = 2** (grammar: one `nestedRecord` inside outer bag; depth 3+ fails parse). Soft-validate: [`../tools/layer_soft_validate.py`](../tools/layer_soft_validate.py) — same endpoint grain both ends; no `law=` on EDGE; bag denylist on `law`/`pseudo`/`recycle`/`role`/`view`; law `@idents` ⊆ bag aliases. Fixtures: [`../examples/layer/`](../examples/layer/). Core syntax domain-generic; electronics `V`/`I` only in instance examples.

British English.
