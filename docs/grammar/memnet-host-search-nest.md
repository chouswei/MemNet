# Host search (design)

**Status:** design only — **not** shipped. No `rag_query` MCP; no embeddings in the engine.  
**Research:** [#77](https://github.com/chouswei/MemNet/issues/77).  
**Walk:** [`../../sysml-models/outputs/host-search-nest-case-study.md`](../../sysml-models/outputs/host-search-nest-case-study.md).  
**Dialect:** GQL ([`gql-wire-profile.md`](gql-wire-profile.md)). British English.

MN-REQ-00: MemNet is mission working memory, **not** the search corpus. Host retrieval MAY propose **locators**; **MutateGate** (or Path-B ingest) commits them. Skip is valid.

## Cut

An LLM turn needs two bounded contexts. Do not fuse them.

| Need | Mechanism |
|------|-----------|
| Mission working memory | Atomised NODE\|EDGE → shaped **`pin_map`** |
| Corpus lookup | Host index / grep / sibling RAG MCP → **locators**, then MutateGate |

Retrieve, generate, and remember all “put less text in the prompt”. Only the third is MemNet. Symptoms of fusion: `rag_query` on `memnet-mcp`, chunks on `note=`, `pin_map.generate(prompt)`.

```text
corpus --(host retrieve)--> locators --MutateGate--> session --pin_map--> goldfish
```

Skip the host hop when grep, ingest, or existing pins suffice.

## Role (pinned)

Working set for **a few technical documents** (atoms and locators; PDF/HTML stay on disk) **plus** live `TSK`/`USR`/`MOD`, re-read **fast** (`pin_map`, depth ~2 / 50 rows). Tens of MiB typical; **hundreds of MiB still in role**; gigabytes = RAG/cabinet.

The session itself is already too big to dump: same *shape* as RAG (which slice this turn?), different haystack. Owner = **`pin_map`** (and leftover [#73](https://github.com/chouswei/MemNet/issues/73) bounded find when there is no ego) — **not** a second vector index.

| Haystack | Owner |
|----------|--------|
| Library / PDFs / web | Host RAG, grep, ingest |
| Live session graph | MemNet `pin_map` |

If the graph becomes the library, it has left this role.

## Math (keep three)

Citations on [#77](https://github.com/chouswei/MemNet/issues/77). **MUST NOT** train IB, run Steiner, or ANN-index the session because a paper did.

| Principle | In MemNet |
|-----------|-----------|
| **Information bottleneck** | `pin_map` compresses the session given an anchor. Skip = empty extra retrieve. |
| **Ego \(k\)-hop** | Optimal evidence subgraph is NP-hard; `depth` from a known id is the polynomial stand-in. |
| **Cardinality / diameter** | `max_rows` and `depth` are the budget. Relations are the metric, not cosine. |

## Nest (application; not product)

Do **not** copy ImportGuard leaf-for-leaf. There is no new hard engine verb.

```text
HostSearchBridge          // MUST NOT nest under MemNetSystem
└── RagHostHook           // optional, implemented=false, fail-open
    // skip → pin_map + grep
    // propose locators → existing MutateGate / PinMapIngest
```

**Hook in:** `session_id` (capability; do not log), `anchor`, short question, `max_hits`, timeout. Not the whole session or source artefact.

**Hook out:** locators only (`path=` / `line=` / `qname=` / `document_id`). **MUST NOT** emit chunk bodies. Host or agent then writes GQL; ground ids for source pins (no client `NEW` on artefact nodes). Next turn: `pin_map`.

Fail-open: missing adapter / timeout / parse → skip; **MUST NOT** fail `pin_map` / `add`. Adapter **MUST NOT** mutate the session.

`BoundedMatchFind` (#73) is unanchored **graph** lookup. Host search is **corpus** lookup. Do not merge them.

## MUST NOT

- Add `rag_query` (or equivalent) to `memnet-mcp`.
- Nest this under `MemNetSystem`.
- Store embeddings or chunk text as the memory surface (MN-REQ-11.13).
- Teach RAG emit as shaped `pin_map`, or `generate` *on* MemNet.
- Dual-write a vector index and MutateGate.
- Claim this shipped because ImportGuard or ingest shipped.

## Related

| Path | Role |
|------|------|
| [#77](https://github.com/chouswei/MemNet/issues/77) | Research (steal/reject vs Neo4j / RAGFlow / math) |
| [`gql-wire-profile.md`](gql-wire-profile.md) | Goldfish = `pin_map` |
| [`../application-notes/llm-software-development.md`](../application-notes/llm-software-development.md) | Cursor index vs locators |
| [`../../sysml-models/outputs/host-search-nest-case-study.md`](../../sysml-models/outputs/host-search-nest-case-study.md) | Evidence walk |
