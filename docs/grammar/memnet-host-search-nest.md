# Host search (design)

**Status:** extra **0.17** hook shipped (untagged; package stays 0.9.0) — `RagHostHook.implemented=true` **outside** `MemNetSystem`. Skip is valid. No `rag_query` MCP; no embeddings in the engine.  
**Research:** [#77](https://github.com/chouswei/MemNet/issues/77) (below the product math). Notes 22–28 landed on `master` via [#84](https://github.com/chouswei/MemNet/pull/84).  
**Math SSOT (above this nest):** [`math-skeleton.md`](math-skeleton.md).  
**Retrieve algorithms (what the functions do):** [`rag-relative-algorithms.md`](rag-relative-algorithms.md).  
**Walk:** [`../../sysml-models/outputs/host-search-nest-case-study.md`](../../sysml-models/outputs/host-search-nest-case-study.md).  
**Dialect:** GQL ([`gql-wire-profile.md`](gql-wire-profile.md)). British English.

### After 0.17 (hook shipped)

Note 13 remains the close bar for the original Neo4j / RAGFlow / Meilisearch questions. Notes 22–28 lock the **session** side. The **locator hook** is extra **0.17** (`memnet.rag_host_hook`); skip remains valid.

| Locked on `master` | Still leftover |
|--------------------|----------------|
| Four jobs (corpus GraphRAG / LightRAG / Letta archival / session goldfish) | Multi-ego union-under-one-\(M\) as a later goldfish validate |
| Snap (host corpus) vs Shape (`pin_map`) — MUST NOT ANN \(S\) | |
| Goldfish: one live `TSK` `pin_map`; optional `view=shell` survey; sparse Commit Δ | |
| Writeback = mutate, not Path-B Absorb | |
| `RagHostHook` locators outside `MemNetSystem` (0.17) | |
| `Peak_L` last-resort residual cue (0.18; never default goldfish) | |

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
corpus --(host Snap)--> locators --MutateGate--> session
live TSK --(one Shape pin_map)--> goldfish
  (blocked: at most one view=shell survey, then TSK interior)
goldfish sparse Δ --Commit--> session
```

Skip the host hop when grep, ingest, or existing pins suffice. **Snap** is host compression of the **library**. **Shape** is Recall \(\tilde{X}\) of the **session**. Goldfish **in** = one slice (not \(N\) full maps); **out** = sparse \(\Delta\) via Commit (not Path-B Absorb). Do not Snap-on-session (no ANN of \(S\)). Detail: [`math-skeleton.md`](math-skeleton.md) and [#77](https://github.com/chouswei/MemNet/issues/77) notes 26–28.

## Role (pinned)

Working set for **a few technical documents** (atoms and locators; PDF/HTML stay on disk) **plus** live `TSK`/`USR`/`MOD`, re-read **fast** (`pin_map`, depth ~2 / 50 rows). Tens of MiB typical; **hundreds of MiB still in role**; gigabytes = RAG/cabinet.

The session itself is already too big to dump: same *symptom* as RAG (which slice this turn?), different haystack. Owner = **Shape** via **`pin_map`** (and leftover [#73](https://github.com/chouswei/MemNet/issues/73) bounded find when there is no ego) — **not** a second vector index on \(S\).

| Haystack | Compression | Owner |
|----------|-------------|--------|
| Library / PDFs / web | **Snap** (host RAG / grep / ingest → locators) | `RagHostHook` (outside) |
| Live session graph | **Shape** (`Recall` → \(\tilde{X}\)) | `PinMapShapedRead` |

The 2026 GraphRAG market is **three other jobs**. MemNet is none of them. Detail: [#77](https://github.com/chouswei/MemNet/issues/77) note 22.

| Job | Typical stack | MemNet |
|-----|----------------|--------|
| Global themes over a **static corpus** | Microsoft GraphRAG Leiden + community-report map-reduce | Host only |
| Incremental **document** Q&A | LightRAG dual-level / RAGFlow chunks | Host locators |
| Cross-session **LTM** (facts expire) | Graphiti / Letta archival | Cabinet / host, not goldfish |
| Mission **session** working memory | — | `pin_map` + shipped #73 `find` (seed-only) |

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

**Pin topics, then fetch slices.** Prefer **one** `pin_map` on the live `TSK`. Extra topics: at most one `view=shell` survey, then interior on the task — not \(N\) serial full maps (duplicate LAW / overlap). Seed set \(|Q|\le L\) unions under **one** \(M\) (0.5 multi-ego `pin_map`). Goldfish then emits a **sparse** \(\Delta\) (`add`/`update`); the session takes it via **Commit**. Do **not** call that Absorb. Do **not** echo the fetched slice.

**New work already in the session.** Find the id (`read_list(tag=TSK, active_only=True)`, hub `:owns`/`:next`, `find` / #73, or a known id) then `pin_map`. Isolated `TSK` ⇒ LAW + that node only — Commit edges if pins exist but are unlinked. **Switch task:** settle the old `TSK` (`delete_on_settle`); next ego from hub / list / mint — **not** peaks. Host RAG **snaps topics** in the corpus; `pin_map` **shapes** the neighbourhood.

Graph-memory products often **run lexical, vector, and BFS in parallel and fuse ranks** (Graphiti RRF). That is a **corpus hybrid**. Goldfish stays **cue then walk**: encoding specificity (the token must already be on the pin) plus ecphory (bounded reconstruct). HippoRAG is serial too, but the walk is Personalized PageRank over an OpenIE graph seeded by fact embeddings — that is **host RAG**, not `pin_map`.

### First principles

| Principle | What it licenses | What it forbids |
|-----------|------------------|-----------------|
| **IB / rate–distortion** | A short token as cue; then a bounded reconstruct (`depth`, `max_rows`) | Dumping the session; embedding the session “to be sure” |
| **Discrete codebook** | Kinds/tags/ids/locators *are* the code — overlapping cues, like human categories | A second ANN index as the “real” memory |
| **k-hop reconstruct** | After a hit, ego walk is the polynomial stand-in for “spread of activation” | Unbounded association; Steiner “optimal memory subgraph” |
| **Empty cue** | Miss → skip / grep / host retrieve | Inventing a node because the keyword felt right |
| **Local degree peak** (deferred) | Topology cue when there is no id/keyword: pick nodes whose degree is a **local maximum relative to neighbours**, then `pin_map` | Global top-k degree; PageRank; assigning the whole session to peaks (clustering) |
| **Working memory ≠ LTM** | Recycle / settle is forgetting on purpose | Growing a session thesaurus into a cabinet |
| **Jobs stay unfused** | Fuzzy overlap is for **recall keys** only | Blurring kind for **identity** (one primary label) or **ACL** (`labels=` write-scope) or **Absorb** |

So: **no clear boundary among cues** (a pin may answer to `SYM` and to `session`). **Hard boundary among jobs** (retrieve ≠ mutate-scope ≠ absorb). Human LTM (years, interference, false memory) is not the product — goldfish is.

| Cue | Then |
|-----|------|
| Token matches a kind, id, or locator | Leftover [#73](https://github.com/chouswei/MemNet/issues/73) bounded find |
| No id/keyword | Unsettled `TSK_*` / RSV / last mutate (HiAgent current subgoal) |
| Still empty; want cluster representatives | Last-resort **typed residual** local max (strip `contains`) — not raw degree — [#77](https://github.com/chouswei/MemNet/issues/77) notes 23–25 |
| A hit id is in hand | `pin_map` — dimension of the net |

Engine today: one primary GQL label; `tagmap` lists kinds, it is not a topic ontology. Layer `@TAG` pipe stays retired.

## Cousins (code, not README)

Read the retrieve functions. Steal the *shape*; reject the *haystack*.

| Code | What it actually does | Steal | Reject |
|------|------------------------|-------|--------|
| [HippoRAG 2](https://github.com/OSU-NLP-Group/HippoRAG) `retrieve` | Embed query → score facts → LLM “recognition” rerank → **if no facts, DPR** else seed igraph **PPR** (entity weight ÷ chunk fan-in + small passage weight) → return **chunk bodies**. `index` = OpenIE + three embedding stores. | Empty facts → fallback (our skip / grep / host). Fan-in as a budget (our `max_rows` / fanout — not PPR damping). Write entities **at atomise** or find misses. | OpenIE, three vector stores, PPR, IRCoT merge-docs loop, chunks as the memory surface. |
| [Graphiti](https://github.com/getzep/graphiti) `search` | Parallel **BM25 \|\| cosine \|\| BFS** on edges/nodes/episodes/communities; fuse with **RRF** (\(k=1\)). Optional MMR / cross-encoder / **node_distance** (1-hop `RELATES_TO` to `center_node_uuid`, not Dijkstra). Empty query → empty. BFS with no origins expands from first-pass hit sources. | Serialise cue then walk (do not RRF). Centre id ≈ `pin_map` **anchor** (MemNet still does true \(k\)-hop). Episodes ≈ locators. `group_ids` ≈ session scope. | Neo4j/FalkorDB goldfish, default embeddings, community nodes, cross-encoder in-engine, bi-temporal LTM as session. |
| [mem0](https://github.com/mem0ai/mem0) `Memory.search` | Require `user_id` / `agent_id` / `run_id` → **vector store** → optional rerank → `{memory, score}` for the **system prompt**. | Scope filter **before** cue. Threshold as skip. | Vector store as memory; dumping prose into chat; metadata-operator soup as goldfish. |
| [HiAgent](https://github.com/HiAgent2024/HiAgent) (ACL’25) | In-trial **working** vs cross-trial LTM. Subgoal as the live chunk; **replace** finished subgoals with a summary; keep only current-subgoal action–observation pairs. | Current `TSK_*` as ego. Recycle / settle = forget on purpose (not Graphiti invalidate-as-LTM). | Prompt-only hierarchy with no graph; AgentBoard env loop in the engine. |
| [microsoft/graphrag](https://github.com/microsoft/graphrag) `LocalSearch` / `global_search` | Index extracts entities + Leiden communities + LLM community reports. **Local:** mix entity / relationship / text-unit / community tables into a prompt, then **generate**. **Global:** map-reduce over community reports. Also DRIFT + basic vector. | Local *shape* ≈ ego neighbourhood — keep as **host** retrieve. Skip extra hop when pins suffice. | Leiden / map-reduce / community reports as goldfish; `pin_map.generate`; corpus KG as the session. |
| [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) `aquery` / `aquery_data` | Modes `local` / `global` / `hybrid` (round-robin) / `mix` (KG + chunks) / `naive` (chunks only) / `bypass`. Default path **generates**; `aquery_data` returns entities, relationships, **chunk bodies**. | Dual-level keywords as a host cue. Empty keywords → skip. Locators from `file_path`, not chunks. | Hybrid/mix/naive **in** `memnet-llm`; chunk JSON as `pin_map`. |
| Letta (f.k.a. MemGPT) core vs archival | Core memory is **prose in the prompt**; archival is a second retrieve hop (typically vectors). | Working set vs cabinet (HiAgent cousin). Recycle keeps goldfish small. | Core-memory blocks as MemNet; archival search on `memnet-mcp`. |
| LICOD `compute_node_leaders` ([MUNA](https://github.com/Issamfalih/MUNA/blob/master/R/Licod.R)) | Leader iff centrality beats **most** neighbours (paper σ). Then **assign** every node to a leader (community detection). | σ-relative local max as `Peak_L` seeds. Empty leaders → skip. | Vote/Borda assignment; modularity communities as goldfish. Copy the public R inequality blindly (it counts *higher* neighbours). |
| [k-peak](https://github.com/priyagovindan/kpeak) `get_kpeak_decomposition` (WWW’17) | Repeated degeneracy/`k_core` peel; every node gets a peak number (“mountains”). | Local *regions* not global top-k degree. | Assign the whole session; `nx.k_core` as goldfish; mountain plots in-engine. |
| [pytorch_geometric `NeighborLoader`](https://pytorch-geometric.readthedocs.io/en/latest/tutorial/neighbor_loader.html) | Seed batch \(B\); sample ≤k neighbours / hop; directed L-hop around **the set**. | Seed **set** + fan-out cap + one reconstruct. | Stochastic sample; GNN aggregators; embeddings as memory. |
| Graphiti `add_episode` / `bfs_origin_node_uuids` | Incremental episode ingest; optional multi-origin BFS; hybrid search then `node_distance` rerank; `update_communities` / episode-mentions rerank. | Incremental write (sparse Δ). Multi-origin as seed set. Distance **is** `pin_map`. | Hybrid/RRF first; community update; mention-frequency as goldfish. |
| LightRAG dual-level keywords | LLM extracts high-level (themes) + low-level (entities); vector match; 1-hop gather; hybrid/mix generate. | Two **grains**: shell survey then TSK interior. Empty keywords → skip. | Keyword embeddings; hybrid/mix **in** engine; chunks as `pin_map`. |

Closest working-memory cousin in Awesome-GraphMemory is HiAgent, not HippoRAG. Graphiti’s **centre id** is the closest *handle* to `pin_map(anchor)`; their **`node_distance` is 1-hop adjacency**, not MemNet depth-2 reconstruct; their **RRF of BM25+cosine+BFS** is the closest *temptation* to fuse with host RAG. Microsoft GraphRAG **local** search is the closest *corpus* cousin to ego walk — still generate-on-retrieve, still the library haystack. Algorithms: [`rag-relative-algorithms.md`](rag-relative-algorithms.md).

## Math (product SSOT above this nest)

Product equations and the two-operator cut live in [`math-skeleton.md`](math-skeleton.md) — **above** this research note and [#77](https://github.com/chouswei/MemNet/issues/77). Do not thicken this file with a paper pile. Citations stay on #77. **MUST NOT** train IB, run Steiner, or ANN-index the session because a paper did.

| Principle | In MemNet (pointer) |
|-----------|---------------------|
| **Information bottleneck** | `Recall` **Shapes** the session given cue \(q\). Skip = empty extra retrieve. |
| **Ego \(k\)-hop** | Optimal evidence subgraph is NP-hard; `depth` from a seed is the polynomial stand-in. |
| **Cardinality / diameter** | `max_rows` and `depth` are the budget. Metric is hops, not cosine. |
| **Snap vs Shape** | Host Snap = corpus locators. Shape = `pin_map`. MUST NOT ANN \(S\). |
| **Slice I/O** | Goldfish in = \(\tilde{X}\); out = sparse \(\Delta\) via Commit. One \(M\); live `TSK` first. Not Absorb. |

## Nest (application; not product)

Do **not** copy ImportGuard leaf-for-leaf. ImportGuard’s hard leaf is **Absorb** — that verb does not apply here.

```text
HostSearchBridge          // MUST NOT nest under MemNetSystem
└── RagHostHook           // optional, implemented=true, fail-open
    locatorIn  ← library / host locators (LibraryLocator; optional line=)
    locatorOut → existing MutateGate / PinMapIngest
    // skip → pin_map + grep
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
- Claim this shipped because ImportGuard or ingest shipped (0.17 ships the hook; it still does not absorb).
- Call host locator commit **absorb** (that word is `ImportAbsorb` only).
- Fuse overlapping **recall cues** with identity (primary label), ACL `labels=`, or Absorb.
- Run Graphiti-style **RRF** (lexical || vector || BFS) or HippoRAG **PPR** / OpenIE **inside** the engine.
- Treat mem0 `search` → system-prompt memories as goldfish.
- Run Microsoft GraphRAG Leiden / community-report map-reduce, LightRAG hybrid/mix, or Letta archival search **inside** the engine.
- Treat Letta core-memory prompt blocks as shaped `pin_map`.
- Treat local degree peaks as GraphRAG / density-peak **clustering**, or as a default goldfish instead of anchored `pin_map`.
- Snap-on-session (embed / ANN \(S\); RAG “to snap topics” *inside* the goldfish).
- Call goldfish \(\Delta\) **absorb** (that word is `ImportAbsorb` only). Fuse several topic slices with RRF.
- Serial \(N\) full `pin_map`s as the default (duplicate LAW / overlap). Goldfish budget \(M\times|Q|\). Echo \(\tilde{X}\) through mutate.

## Related

| Path | Role |
|------|------|
| [#77](https://github.com/chouswei/MemNet/issues/77) | Research (steal/reject vs Neo4j / RAGFlow / graph-memory code) |
| [`neo4j-buffer.md`](neo4j-buffer.md) | Places those relatives on Snap / Shape / Neo4j cabinet (not a second steal/reject SSOT) |
| [`rag-relative-algorithms.md`](rag-relative-algorithms.md) | Retrieve pipelines from source |
| [`memnet-neo4j-rag-rethink.md`](memnet-neo4j-rag-rethink.md) | Two ports; catalog Snap; join by Absorb (proposal) |
| [`memnet-harness-thesis.md`](memnet-harness-thesis.md) | MemNet as harness memory plane (design thesis) |
| [`math-skeleton.md`](math-skeleton.md) | Product math (above #77) |
| [`gql-wire-profile.md`](gql-wire-profile.md) | Goldfish = `pin_map` / Recall |
| [`../application-notes/llm-daily-news.md`](../application-notes/llm-daily-news.md) | `KYWD` as one overlapping cue idiom |
| [`../../sysml-models/outputs/host-search-nest-case-study.md`](../../sysml-models/outputs/host-search-nest-case-study.md) | Evidence walk |
| [`../../sysml-models/outputs/recall-commit-orthodox-plan.md`](../../sysml-models/outputs/recall-commit-orthodox-plan.md) | Orthodox; all tests are paradox |
