# Host search (retired design note)

**Status: retired.** The extra **0.17** `RagHostHook` code is removed. The hook never had a product caller. MemNet ships **no** host-search hook: a host runs its own search (grep, index, RAG) and commits **locators** through the normal mutate path (`MutateGate`) or Path-B ingest. Skip is valid. No `rag_query` MCP; no embeddings in the engine. History: [`../../CHANGELOG.md`](../../CHANGELOG.md).  
**Research:** [#77](https://github.com/chouswei/MemNet/issues/77) (cousin code, steal/reject detail).  
**Math SSOT:** [`math-skeleton.md`](../grammar/math-skeleton.md).  
**Dialect:** GQL ([`gql-wire-profile.md`](../grammar/gql-wire-profile.md)). British English.

## The cut (still holds)

MN-REQ-00: MemNet is mission working memory, **not** the search corpus. An LLM turn needs two bounded contexts. Do not fuse them.

| Need | Mechanism |
|------|-----------|
| Mission working memory | Atomised NODE\|EDGE → shaped **`pin_map`** (**Shape**) |
| Corpus lookup | Host index / grep / sibling RAG MCP → **locators** (**Snap**), then mutate |

```text
corpus --(host's own search)--> locators --mutate (MutateGate)--> session
live TSK --(one pin_map)--> goldfish
goldfish sparse Δ --Commit--> session
```

Locators only (`path=` / `line=` / `qname=` / `document_id`), never chunk bodies. Locator commit is **mutate**, not absorb (`ImportAbsorb` is Path-B slices only). `BoundedMatchFind` (#73) is graph lookup; host search is corpus lookup.

In the SysML model, `HostSearchBridgePart` stays an outside application nest with `hookShipped=false`.

## MUST NOT

- Add `rag_query` (or equivalent) to `memnet-mcp`.
- Nest host search under `MemNetSystem`.
- Store embeddings or chunk text as the memory surface (MN-REQ-11.13).
- Teach RAG emit as shaped `pin_map`, or `generate` *on* MemNet.
- Dual-write a vector index and MutateGate.
- Run RRF / PPR / Leiden / ANN **inside** the engine, or Snap-on-session (ANN \(S\)).
- Call locator commit or goldfish \(\Delta\) **absorb**.

## Related

| Path | Role |
|------|------|
| [#77](https://github.com/chouswei/MemNet/issues/77) | Research |
| [`math-skeleton.md`](../grammar/math-skeleton.md) | Product math |
| [`gql-wire-profile.md`](../grammar/gql-wire-profile.md) | Goldfish = `pin_map` / Recall |
| [`../../sysml-models/outputs/host-search-nest-case-study.md`](../../sysml-models/outputs/host-search-nest-case-study.md) | Retired evidence walk |
