# Cabinet (durable store) — retired

MemNet no longer ships a durable cabinet. Removed:

- the `memnet.durable` package (Fake and AgensGraph adapters, `DurableSyncOwner`, factory);
- the startup bind in serve, the local IPC gateway and the MCP main;
- the `memnet-llm[agensgraph]` extra and the `agensgraph_live` pytest marker;
- the old cabinet docs (AgensGraph buffer, Neo4j buffer, storage-role picture).

Neo4j was retired earlier (#187); `MEMNET_NEO4J_*` is ignored. The 0.7 adapter never had a runtime caller.

The durable copy is the **file snapshot**: `session save` / `session load` (MCP `session_save` / `session_load`).

History: [`../../CHANGELOG.md`](../../CHANGELOG.md). Wire: [`../grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md). Index: [`../README.md`](../README.md).
