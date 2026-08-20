# Grammar (agent teach)

**GQL only.** This folder is wire + math + openCypher spelling — not cabinet, extras, or Multitask ops.

| Doc | Role |
|-----|------|
| [`gql-wire-profile.md`](gql-wire-profile.md) | **M1 SSOT** |
| [`math-skeleton.md`](math-skeleton.md) | **0.5** Recall / Commit |
| [`openCypher.bnf`](openCypher.bnf) | Official BNF (Apache-2.0; [`NOTICE-openCypher.md`](NOTICE-openCypher.md)) |

Decision: [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md).

Do **not** teach Layer, Tier A, `@TAG` pipe, leftover `id:'NEW'`, or line-codec `+/~/-` as agent wire. Those sources are **dropped** from this tree. Engine leftover codecs stay in `parts/common/memnet/memnet/tier_a.py` / `layer.py` and are **rejected** on product mutate.

Cabinet: [`../cabinet/`](../cabinet/). Extras: [`../extras/`](../extras/). Index: [`../README.md`](../README.md).
