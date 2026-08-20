# Shared-dialect grammar tools (as-is harness)

Package / file names keep `tier_a` for **as-is engine harness** continuity (M2 shipped; this path is rejected on product mutate).  
**Agent teach = GQL only:** [`../gql-wire-profile.md`](../gql-wire-profile.md). Do **not** teach Tier A / Layer as wire.

| Path | Role |
|------|------|
| `tier_a.py` | As-is pure-Python parse / emit (legacy line dialect; rejected on product mutate) |
| `../examples/` | Golden fixtures for as-is harness |
| [`../archive/antlr/MemNet.g4`](../archive/antlr/MemNet.g4) | Unused ANTLR stub (quarantine; do not generate) |
| [`../archive/tools/layer_soft_validate.py`](../archive/tools/layer_soft_validate.py) | Quarantined Layer soft-validate |

## Run golden tests

```powershell
python -m pytest tests/grammar -q
```

`tests/grammar/archive/` is **not** part of the default teach path; do not re-add Layer golden as product CI without an explicit revive decision.
