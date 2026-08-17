# Case study: Host search (outside MemNetSystem)

**Shelf:** application example (on SharedLlmMemory)

Host corpus lookup MAY propose **locators**; MemNet **MutateGate** commits them. Skip is valid. Not a product MCP tool.  
Design: [`docs/grammar/memnet-host-search-nest.md`](../../docs/grammar/memnet-host-search-nest.md). Product math (above #77): [`docs/grammar/math-skeleton.md`](../../docs/grammar/math-skeleton.md). Research: [#77](https://github.com/chouswei/MemNet/issues/77).

## Binding

**Host Snaps the corpus; MemNet Shapes locators the agent will re-`pin_map`.**

| Path | When | What |
|------|------|------|
| A (prefer) | Pins already there, or grep/LSP suffices | Skip the hook — goldfish only |
| B | Fuzzy find in docs/repo | `RagHostHook` proposes locators → **existing** MutateGate / ingest |

| Term | Meaning |
|------|---------|
| **`HostSearchBridge`** | Application nest — **MUST NOT** sit under `MemNetSystem` |
| **`RagHostHook`** | Optional host Snap (`implemented=false`) — locators, not chunks |

Do not invent `LocatorCommit` / `HostSearchReceive` / passthrough leaves, and do **not** call the hard path Absorb — that word is `ImportAbsorb` (member slice + `id_policy`) only. Host locators go through existing MutateGate. ImportGuard shipped ≠ this nest shipped. Do not teach `rag_query` on `memnet-mcp`. Do not ANN-index the session (Snap-on-session).

```text
HostSearchBridgePart              // MUST NOT nest under MemNetSystem
└── RagHostHook   implemented=false  fail-open  locator-only
```

## Fake mission

**Anchor:** `TSK_mcp_session`. Find `session_open` and pin it.

**Path A:** `MOD_server_py` already on the pin map → grep line → edit. No host retrieve.

**Path B (illustrative):** host Snaps `path=parts/memnet-mcp/software/memnet_mcp/server.py line=59`. Agent commits locators via MutateGate, discards any chunk text, Shape (`pin_map`) again, grep before trusting `line=`. Timeout → same as Path A.

**Path C (in-session TSK; graph too large to dump):** the “new” task is already a `TSK` on \(S\). Do not Snap \(S\). `read_list(tag=TSK, active_only=True)` or hub `:owns`/`:next` → `pin_map(anchor=TSK_…, depth=2, max_rows=50)`. Isolated node ⇒ LAW + that `TSK` only — Commit edges if pins exist but are unlinked. Switch: settle the old `TSK` (`delete_on_settle`), then Shape the next ego.

**Path D (pin topics, fetch slices, Commit Δ):** goldfish never sees raw \(S\). Default: one `pin_map` on `TSK_mcp_session`. Blocked: one `view=shell` on a `KYWD`/kind hub, then interior on the `TSK`. Emit sparse GQL `add`/`update` (do not echo the slice; do not `ImportAbsorb`).

**Path E (anti-optimisation):** five full `pin_map`s on overlapping topics → LAW prepended five times, shared neighbours five times. That is the fault note 28 removes. Path-B `M×anchors` is import payload, not goldfish.

## Counter-examples

| Fault | Why it fails |
|-------|----------------|
| Nest under `MemNetSystem` | MN-REQ-00 — search corpus is not MemNet |
| MCP `rag_query` on `memnet-mcp` | Tool SSOT is session / pin_map / mutate / ingest |
| Chunk body on `note=` | MN-REQ-11.13 |
| Merge with `BoundedMatchFind` (#73) | Graph lookup ≠ corpus lookup |
| Adapter writes the graph | Two writers |
| Graphiti RRF or HippoRAG PPR on the session | Corpus hybrid / OpenIE RAG — goldfish is serial cue then `pin_map` |
| Microsoft GraphRAG global / LightRAG mix in-engine | Static-corpus GraphRAG — library haystack, generate-on-retrieve |
| Local degree peaks as the default goldfish / cluster assignment | Topology cue only (deferred); then `pin_map` with fanout clamp — not Leiden |
| RAG “snaps topics” *on the session* (embed \(S\)) | Snap is corpus-only; Shape is `pin_map`. Same symptom, different haystack |
| Goldfish Δ via `ImportAbsorb` | Absorb is Path-B member `WorkingMemorySlice` only; goldfish writeback is Commit |
| Fuse several topic `pin_map`s with RRF | One \(M\); distance *is* reconstruct; goldfish is not a ranker |
| \(N\) serial full maps / \(M\times|Q|\) goldfish budget | Duplicate LAW + overlap; Path-B import budget is not goldfish |
| Echo fetched \(\tilde{X}\) through `add` | `id_exists`; sparse Δ only (Graphiti incremental, not Letta core rewrite) |

## Related

| Path | Role |
|------|------|
| [`docs/grammar/memnet-host-search-nest.md`](../../docs/grammar/memnet-host-search-nest.md) | Design SSOT |
| [session-import-case-study.md](session-import-case-study.md) | Product ImportGuard (different nest) |
| [`docs/application-notes/llm-software-development.md`](../../docs/application-notes/llm-software-development.md) | Cursor index vs locators |
| [`docs/application-notes/llm-daily-news.md`](../../docs/application-notes/llm-daily-news.md) | `KYWD` as one overlapping cue idiom |
