# Tier A grammar tools

| Path | Role |
|------|------|
| `tier_a.py` | Pure-Python parse / emit / soft lint mirroring `MemNet.g4` (R1 atoms-only) |
| `../MemNet.g4` | ANTLR4 stub (teaching / future codegen) |
| `../examples/` | Golden fixtures — see `examples/README.md` |

## Run golden tests

From repo root (PowerShell):

```powershell
python -m pytest tests/grammar -q
```

Round-trip check for warm fixtures is included (`01_`, `04_`).

ANTLR codegen is optional later (`antlr4 -Dlanguage=Python3`); this twin does not require `antlr4-python3-runtime`.
