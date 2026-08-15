# Host search (design)

**Status:** design only — **not** shipped. No `rag_query` MCP; no embeddings in the engine.  
**Research:** [#77](https://github.com/chouswei/MemNet/issues/77) (below the product math).  
**Math SSOT (above this nest):** [`math-skeleton.md`](math-skeleton.md).  
**Walk:** [`../../sysml-models/outputs/host-search-nest-case-study.md`](../../sysml-models/outputs/host-search-nest-case-study.md).  
**Dialect:** GQL ([`gql-wire-profile.md`](gql-wire-profile.md)). British English.

MN-REQ-00: MemNet is mission working memory, **not** the search corpus. Host retrieval MAY propose **locators**; **MutateGate** (or Path-B ingest) commits them. Skip is valid.

**Absorb is precise.** `ImportAbsorb` is Path-B only: a member `WorkingMemorySlice` into the lead session under `id_policy` (`keep` / `reject` / `remint`). Host search does **not** absorb. It does not invent a second absorb-shaped leaf.

| Verb | What moves | Hard owner |
|------|------------|------------|
| **mutate** | GQL in the *current* session | `MutateGate` |
| **ingest** | Artefact → deterministic locator pins | `PinMapIngest_*` |
| **absorb** | Member *slice* → lead SSOT + id policy | `ImportAbsorb` |

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

## In-session retrieve: kinds as cues (human memory)

Corpus RAG stays on the host. Inside the session, SCHEMA kinds/tags are an **open cue vocabulary**. Recall is like working memory in a person: a **keyword** cues a cluster, then a **neighbourhood** is reconstructed. House prefixes (`TSK_*`, `MOD_*`, `KYWD`, …) are conventions, not a DBA taxonomy. `KYWD` hubs (daily-news) are one idiom, not a second product.

```text
session scope
  -->  lexical / kind cue (#73)
  -->  pin_map(center = hit, depth, max_rows)
  -->  recycle settled TSK
```

Serial, not fused. A hit becomes the ego; then the neighbourhood is the reconstruct. Empty cue → skip / grep / host — not a second ranker.

Graph-memory products often **run lexical, vector, and BFS in parallel and fuse ranks** (Graphiti RRF). That is a **corpus hybrid**. Goldfish stays **cue then walk**: encoding specificity (the token must already be on the pin) plus ecphory (bounded reconstruct). HippoRAG is serial too, but the walk is Personalized PageRank over an OpenIE graph seeded by fact embeddings — that is **host RAG**, not `pin_map`.

### First principles

| Principle | What it licenses | What it forbids |
|-----------|------------------|-----------------|
| **IB / rate–distortion** | A short token as cue; then a bounded reconstruct (`depth`, `max_rows`) | Dumping the session; embedding the session “to be sure” |
| **Discrete codebook** | Kinds/tags/ids/locators *are* the code — overlapping cues, like human categories | A second ANN index as the “real” memory |
| **k-hop reconstruct** | After a hit, ego walk is the polynomial stand-in for “spread of activation” | Unbounded association; Steiner “optimal memory subgraph” |
| **Empty cue** | Miss → skip / grep / host retrieve | Inventing a node because the keyword felt right |
| **Working memory ≠ LTM** | Recycle / settle is forgetting on purpose | Growing a session thesaurus into a cabinet |
| **Jobs stay unfused** | Fuzzy overlap is for **recall keys** only | Blurring kind for **identity** (one primary label) or **ACL** (`labels=` write-scope) or **Absorb** |

So: **no clear boundary among cues** (a pin may answer to `SYM` and to `session`). **Hard boundary among jobs** (retrieve ≠ mutate-scope ≠ absorb). Human LTM (years, interference, false memory) is not the product — goldfish is.

| Cue | Then |
|-----|------|
| Token matches a kind, id, or locator | Leftover [#73](https://github.com/chouswei/MemNet/issues/73) bounded find |
| A hit id is in hand | `pin_map` — dimension of the net |

Engine today: one primary GQL label; `tagmap` lists kinds, it is not a topic ontology. Layer `@TAG` pipe stays retired.

## Cousins (code, not README)

Read the retrieve functions. Steal the *shape*; reject the *haystack*.

| Code | What it actually does | Steal | Reject |
|------|------------------------|-------|--------|
| [HippoRAG 2](https://github.com/OSU-NLP-Group/HippoRAG) `retrieve` | Embed query → score facts → LLM “recognition” rerank → **if no facts, DPR** else seed igraph **PPR** (entity weight ÷ chunk fan-in + small passage weight) → return **chunk bodies**. `index` = OpenIE + three embedding stores. | Empty facts → fallback (our skip / grep / host). Fan-in as a budget (our `max_rows` / fanout — not PPR damping). Write entities **at atomise** or find misses. | OpenIE, three vector stores, PPR, IRCoT merge-docs loop, chunks as the memory surface. |
| [Graphiti](https://github.com/getzep/graphiti) `search` | Parallel **BM25 \|\| cosine \|\| BFS** on edges/nodes/episodes/communities; fuse with **RRF** (optional MMR / cross-encoder / **node_distance** given `center_node_uuid`). Empty query → empty. BFS with no origins expands from first-pass hit sources. | **Center + hop distance** = `pin_map(ego)`. Lexical cue then expand from hits (serialise that; do not RRF it). Episodes as **provenance** ≈ locators. `group_ids` ≈ session scope. | Neo4j/FalkorDB goldfish, default embeddings, community nodes, cross-encoder in-engine, bi-temporal LTM as session. |
| [mem0](https://github.com/mem0ai/mem0) `Memory.search` | Require `user_id` / `agent_id` / `run_id` → **vector store** → optional rerank → `{memory, score}` for the **system prompt**. | Scope filter **before** cue. Threshold as skip. | Vector store as memory; dumping prose into chat; metadata-operator soup as goldfish. |
| [HiAgent](https://github.com/HiAgent2024/HiAgent) (ACL’25) | In-trial **working** vs cross-trial LTM. Subgoal as the live chunk; **replace** finished subgoals with a summary; keep only current-subgoal action–observation pairs. | Current `TSK_*` as ego. Recycle / settle = forget on purpose (not Graphiti invalidate-as-LTM). | Prompt-only hierarchy with no graph; AgentBoard env loop in the engine. |

Closest working-memory cousin in Awesome-GraphMemory is HiAgent, not HippoRAG. Graphiti’s **node_distance reranker** is the closest *algorithm* to `pin_map`; their **RRF of BM25+cosine+BFS** is the closest *temptation* to fuse with host RAG.

## Math (product SSOT above this nest)

Product equations and the two-operator cut live in [`math-skeleton.md`](math-skeleton.md) — **above** this research note and [#77](https://github.com/chouswei/MemNet/issues/77). Do not thicken this file with a paper pile. Citations stay on #77. **MUST NOT** train IB, run Steiner, or ANN-index the session because a paper did.

| Principle | In MemNet (pointer) |
|-----------|---------------------|
| **Information bottleneck** | `Recall` compresses the session given cue \(q\). Skip = empty extra retrieve. |
| **Ego \(k\)-hop** | Optimal evidence subgraph is NP-hard; `depth` from a seed is the polynomial stand-in. |
| **Cardinality / diameter** | `max_rows` and `depth` are the budget. Metric is hops, not cosine. |

## Nest (application; not product)

Do **not** copy ImportGuard leaf-for-leaf. ImportGuard’s hard leaf is **Absorb** — that verb does not apply here.

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
- Call host locator commit **absorb** (that word is `ImportAbsorb` only).
- Fuse overlapping **recall cues** with identity (primary label), ACL `labels=`, or Absorb.
- Run Graphiti-style **RRF** (lexical || vector || BFS) or HippoRAG **PPR** / OpenIE **inside** the engine.
- Treat mem0 `search` → system-prompt memories as goldfish.

## Related

| Path | Role |
|------|------|
| [#77](https://github.com/chouswei/MemNet/issues/77) | Research (steal/reject vs Neo4j / RAGFlow / graph-memory code) |
| [`math-skeleton.md`](math-skeleton.md) | Product math (above #77) |
| [`gql-wire-profile.md`](gql-wire-profile.md) | Goldfish = `pin_map` / Recall |
| [`../application-notes/llm-daily-news.md`](../application-notes/llm-daily-news.md) | `KYWD` as one overlapping cue idiom |
| [`../../sysml-models/outputs/host-search-nest-case-study.md`](../../sysml-models/outputs/host-search-nest-case-study.md) | Evidence walk |
