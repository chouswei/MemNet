# Grammar (agent teach)

**GQL only.** Wire SSOT: [`gql-wire-profile.md`](gql-wire-profile.md). Math: [`math-skeleton.md`](math-skeleton.md). Decision: [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md).

Do **not** teach Layer, Tier A, `@TAG` pipe, leftover `id:'NEW'`, or line-codec `+/~/-` as agent wire. Those sources are **dropped** from this tree (not an archive folder). Engine leftover codecs stay in `parts/common/memnet/memnet/tier_a.py` / `layer.py` and are **rejected** on product mutate.

Index: [`../README.md`](../README.md).
