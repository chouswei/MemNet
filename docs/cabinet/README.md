# Cabinet (durable store)

Durable GQL **behind** sessions: hydrate / flush adapter, one sync owner. `agentReachable=false` on AgensGraph and Neo4j: the live claim is the adapter plus the operator round trip, not an MCP/CLI/Commit/TTL path. Not the agent teach surface and not the Multitask handoff handle.

| Doc | Role |
|-----|------|
| [`agensgraph-buffer.md`](agensgraph-buffer.md) | AgensGraph adapter (0.7 round trip; `agentReachable=false`) |
| [`neo4j-buffer.md`](neo4j-buffer.md) | Neo4j client (0.14 round trip; `agentReachable=false`; 0.16 two namespaces) |
| [`storage-roles.d2`](storage-roles.d2) | Storage-role picture (working memory, file snapshot, cabinet ego) |

Wire: [`../grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md). Index: [`../README.md`](../README.md).
