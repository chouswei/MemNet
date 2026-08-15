# Case study: Host search (outside MemNetSystem)

**Shelf:** application example (on SharedLlmMemory)

Host corpus lookup MAY propose **locators**; MemNet **MutateGate** commits them. Skip is valid. Not a product MCP tool.  
Design: [`docs/grammar/memnet-host-search-nest.md`](../../docs/grammar/memnet-host-search-nest.md). Product math (above #77): [`docs/grammar/math-skeleton.md`](../../docs/grammar/math-skeleton.md). Research: [#77](https://github.com/chouswei/MemNet/issues/77).

## Binding

**Host looks up the corpus; MemNet keeps locators the agent will re-`pin_map`.**

| Path | When | What |
|------|------|------|
| A (prefer) | Pins already there, or grep/LSP suffices | Skip the hook — goldfish only |
| B | Fuzzy find in docs/repo | `RagHostHook` proposes locators → **existing** MutateGate / ingest |

| Term | Meaning |
|------|---------|
| **`HostSearchBridge`** | Application nest — **MUST NOT** sit under `MemNetSystem` |
| **`RagHostHook`** | Optional host plug-in (`implemented=false`) |

Do not invent `LocatorCommit` / `HostSearchReceive` / passthrough leaves, and do **not** call the hard path Absorb — that word is `ImportAbsorb` (member slice + `id_policy`) only. Host locators go through existing MutateGate. ImportGuard shipped ≠ this nest shipped. Do not teach `rag_query` on `memnet-mcp`.

```text
HostSearchBridgePart              // MUST NOT nest under MemNetSystem
└── RagHostHook   implemented=false  fail-open  locator-only
```

## Fake mission

**Anchor:** `TSK_mcp_session`. Find `session_open` and pin it.

**Path A:** `MOD_server_py` already on the pin map → grep line → edit. No host retrieve.

**Path B (illustrative):** host returns `path=parts/memnet-mcp/software/memnet_mcp/server.py line=59`. Agent commits locators via MutateGate, discards any chunk text, `pin_map` again, grep before trusting `line=`. Timeout → same as Path A.

## Counter-examples

| Fault | Why it fails |
|-------|----------------|
| Nest under `MemNetSystem` | MN-REQ-00 — search corpus is not MemNet |
| MCP `rag_query` on `memnet-mcp` | Tool SSOT is session / pin_map / mutate / ingest |
| Chunk body on `note=` | MN-REQ-11.13 |
| Merge with `BoundedMatchFind` (#73) | Graph lookup ≠ corpus lookup |
| Adapter writes the graph | Two writers |
| Graphiti RRF or HippoRAG PPR on the session | Corpus hybrid / OpenIE RAG — goldfish is serial cue then `pin_map` |

## Related

| Path | Role |
|------|------|
| [`docs/grammar/memnet-host-search-nest.md`](../../docs/grammar/memnet-host-search-nest.md) | Design SSOT |
| [session-import-case-study.md](session-import-case-study.md) | Product ImportGuard (different nest) |
| [`docs/application-notes/llm-software-development.md`](../../docs/application-notes/llm-software-development.md) | Cursor index vs locators |
| [`docs/application-notes/llm-daily-news.md`](../../docs/application-notes/llm-daily-news.md) | `KYWD` as one overlapping cue idiom |
