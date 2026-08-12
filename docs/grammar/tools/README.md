# Shared-dialect grammar tools (as-is harness)

Package / file names keep `tier_a` for **as-is engine harness** continuity until **M2**.  
**Agent teach = GQL only:** [`../gql-wire-profile.md`](../gql-wire-profile.md). Do **not** teach Tier A / Layer as wire.

| Path | Role |
|------|------|
| `tier_a.py` | As-is pure-Python parse / emit (legacy line dialect in engine) |
| `../MemNet.g4` | ANTLR4 stub for that harness |
| `../examples/` | Golden fixtures for as-is harness |
| [`../archive/tools/layer_soft_validate.py`](../archive/tools/layer_soft_validate.py) | Quarantined Layer soft-validate |

## Run golden tests

```powershell
python -m pytest tests/grammar -q
```

`tests/grammar/archive/` is **not** part of the default teach path; do not re-add Layer golden as product CI without an explicit revive decision.
