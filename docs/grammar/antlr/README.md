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

`generated/` and `.tool/` are gitignored. Core package does **not** require `antlr4-python3-runtime`.

## Covered shapes

- NODE present / `+` create / `~` patch
- EDGE three binds with qualified endpoints: `[Node.port] --(bind)--> [Node.port]`
- Fields: `ports=name{side=…, q=…}`, `law=$eq$,$eq$`, generic `key=value`, patch `+=` / `-=`
- Drop: `- Eid`

Port entry: brace attr bag `name{side=…, …}` (braces required). EDGE binds ports via `[NodeId.PortName]`. Core syntax domain-generic; electronics `V`/`I` only in instance examples.

British English.
