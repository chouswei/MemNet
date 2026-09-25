# Cabinet (durable store)

Durable GQL **behind** sessions: hydrate / flush adapter, one sync owner. `hydrateFlushCallers="tests"`: the live claim is the adapter plus the operator round trip, not an MCP/CLI/Commit/TTL path. Not the agent teach surface and not the Multitask handoff handle.

| Doc | Role |
|-----|------|
| [`agensgraph-buffer.md`](agensgraph-buffer.md) | AgensGraph adapter (0.7 round trip; `hydrateFlushCallers="tests"`) |
| [`neo4j-buffer.md`](neo4j-buffer.md) | Retired Neo4j cabinet (#187). Not a current backend |
| [`storage-roles.d2`](storage-roles.d2) | Storage-role picture (working memory, file snapshot, cabinet ego) |

Wire: [`../grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md). Index: [`../README.md`](../README.md).
