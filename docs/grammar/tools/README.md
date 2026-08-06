# Shared-dialect grammar tools

Package / file names keep `tier_a` for harness continuity; they implement the **shared dialect** (Write = display). **Keep** the twin, fixtures, and golden tests — they are the formal benefit of this folder.

| Path | Role |
|------|------|
| `tier_a.py` | Pure-Python parse / emit / soft lint mirroring `MemNet.g4` (R1 atoms-only) |
| `layer_soft_validate.py` | ANTLR `MemNetLayer` parse + soft-validate (proposed 1.x; not in 0.3 engine) |
| `../MemNet.g4` | ANTLR4 stub (teaching / future codegen) |
| `../antlr/MemNetLayer.g4` | Proposed 1.x multi-layer grammar |
| `../examples/` | Golden fixtures — see `examples/README.md` |
| `../examples/layer/` | MemNetLayer golden fixtures (`layer_*.txt`) |

## Run golden tests

From repo root (PowerShell):

```powershell
python -m pytest tests/grammar -q
```

Round-trip check for pin-map fixtures is included (`01_`, `04_`).

Tier A twin does **not** require `antlr4-python3-runtime`. Layer soft-validate / `test_memnet_layer_golden.py` need the `dev` extra (`antlr4-python3-runtime`) and committed `docs/grammar/antlr/generated/*.py`.
