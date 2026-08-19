# ANTLR — historical note

**No live `.g4` on the product path.** Agent teach is GQL only: [`../gql-wire-profile.md`](../gql-wire-profile.md).

Quarantine:

| Path | What it was |
|------|-------------|
| [`../archive/antlr/MemNetLayer.g4`](../archive/antlr/MemNetLayer.g4) | Layer dialect (retired) |
| [`../archive/antlr/MemNet.g4`](../archive/antlr/MemNet.g4) | Unused ANTLR stub for the line dialect; never generated into the engine |

As-is line parse/emit (rejected on product mutate) remains the Python twin `memnet.tier_a` / [`../tools/tier_a.py`](../tools/tier_a.py). **MUST NOT** generate a visitor from `MemNet.g4` as a second accept path.
