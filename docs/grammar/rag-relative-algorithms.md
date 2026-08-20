# RAG-relative algorithms (read from retrieve, not from README)

**Status:** research / design — **not** shipped. No `rag_query`; no embeddings in the engine.  
**Audience:** product developers placing GraphRAG-class retrieve against MemNet Recall.  
**Placement SSOT:** [`neo4j-buffer.md`](neo4j-buffer.md) (Snap / Shape / cabinet).  
**Steal/reject SSOT:** [`memnet-host-search-nest.md`](memnet-host-search-nest.md) + [#77](https://github.com/chouswei/MemNet/issues/77).  
**Product math (above this file):** [`math-skeleton.md`](math-skeleton.md). British English.

Classic RAG is **retrieve a ranked list from a corpus, stuff it, generate**. MemNet goldfish is **discrete cue → bounded reconstruct of session \(S\) → shaped GQL**; generate stays off the wire. The relatives below all implement some mix of (1) embed, (2) lexical rank, (3) graph walk / community, (4) fuse, (5) generate. This note records **what the retrieve functions actually do**, then the MemNet cut.

**Between `memnet-llm` and Neo4j (as-is):** RAG does **not** run on the **cabinet** seam. `memnet-llm[neo4j]` is hydrate/flush only. Host Snap (if any) is a **third** hop over the library — locators into MutateGate, never chunks through Bolt. **Rethink (B+D, not shipped):** library port disjoint from cabinet; join sessions with **Absorb**, not generate. [`memnet-neo4j-rag-rethink.md`](memnet-neo4j-rag-rethink.md). Walk: [`neo4j-buffer.md`](neo4j-buffer.md) § “How RAG sits between `memnet-llm` and the Neo4j cabinet”.

---

## Why RAG became a hot topic

**The problem it solved** is **parametric ignorance of a private or changing corpus** — not goldfish mission memory.

A pretrained LLM stores facts in **weights**. Those weights (1) freeze at train time, (2) do not contain the operator’s PDFs / tickets / SysML, (3) are expensive to update (fine-tune), and (4) **hallucinate** a fluent answer when the fact was never in the weights. Stuffing the *whole* corpus into the prompt hits the **context window** and the **token bill** (the same MN-REQ-00 pressure, different haystack).

**RAG** (Lewis et al., 2020; then every ChatGPT-era stack) is the cheap third path besides “retrain” and “paste the library”:

1. Index the **library** (chunks, later a KG).
2. At question time, **retrieve** a few passages (BM25 / ANN / hybrid).
3. **Generate** conditioned on those passages.

That is why it went hot after late 2022: every product suddenly had an LLM **and** a pile of documents, and RAG shipped “use our docs” in days, not a training run. GraphRAG, LightRAG, RAGFlow, Neo4j `generate`, Graphiti hybrid search are **the same problem with a fancier retrieve** (themes over a corpus, incremental docs, chunk MCP, graph-as-retriever, LTM episodes). They still retrieve-then-generate over a **library**.

| It solved | It did **not** solve |
|-----------|---------------------|
| Ground answers in **this organisation’s files** without fine-tune | Named **session** \(S\) across agent turns (handoff, `TSK`/`USR`) |
| Fresh / private facts vs train cutoff | Token dump of **chunks** still burns the window (hence \(k\), rerank, GraphRAG reports) |
| Some hallucination on **corpus QA** | Global “what are the themes?” (vanilla RAG fails → GraphRAG map-reduce) |
| One question → one retrieve → one generate | Next call is still a goldfish unless you **also** keep working memory |

MemNet’s problem is the **other** goldfish: the next LLM call forgets the **mission graph**, not the PDF shelf. RAG remains the right **host Snap** of the library. Using RAG **as** MemNet (or as Neo4j goldfish) mixes haystacks — [`../SHAPE.md`](../SHAPE.md). Token/wall-clock budgets: [`memnet-neo4j-rag-rethink.md`](memnet-neo4j-rag-rethink.md).

---

## Shared RAG skeleton vs MemNet Recall

| Step | Typical RAG relative | MemNet \(\mathrm{Recall}(q)\) |
|------|----------------------|-------------------------------|
| Haystack | Documents / OpenIE KG / LTM graph | Live session \(S\) (already a graph) |
| Cue | Free-text query (often embedded) | Discrete codebook: id / kind / locator / keyword |
| Retrieve | Ranked chunks or mixed tables | Seed then \(k\)-hop under one \(M\) |
| Fuse | RRF / weighted sum / PPR / Leiden reports | **Serial** — no RRF of lexical \|\| vector \|\| BFS |
| Emit | Prose + citations; often **generate** in the same call | Shaped GQL subgraph; **no** `generate` |
| Empty | Fallback DPR / fail string / empty list | **Skip** (do not invent a node) |

---

## 1. Neo4j GraphQL RAG (Cowley, Apr 2024)

**Haystack:** whatever `@neo4j/graphql` already returned for `Movie` / `Actor` (`where` / relationships).  
**Code shape:** custom resolver on the GraphQL field; LangChain `PromptTemplate` → `ChatOpenAI` → `StringOutputParser`.  
**Source:** [Adding RAG to your GraphQL API](https://neo4j.com/blog/graphql/rag-graphql-api/) · [adam-cowley/neo4j-graphql-genai](https://github.com/adam-cowley/neo4j-graphql-genai).

**Algorithm**

1. GraphQL **retrieve:** `movies(where: …) { title plot … }` (Cypher under `@neo4j/graphql`).
2. **Generate on the same field:** `generate(prompt)` or restricted `generateReview(stars)`.
3. Resolver `invoke`s `{ …source, …args }` — retrieved **records are the RAG context**.
4. Weaviate-style `generate` on a collection is the same pattern: retrieve then LLM **inside** the query API.

**MemNet:** steal “graph retrieve then (host) generate”. Reject LLM **inside** `pin_map` / Bolt / GraphQL as goldfish. Restricted vs open prompt is a host policy, not an MCP field.

---

## 2. Microsoft GraphRAG (`LocalSearch` / `global_search`)

**Haystack:** corpus → LLM entity/relationship extract → **Leiden** community hierarchy → LLM **community reports** + text units.  
**Sources:** [docs/query/local_search.md](https://github.com/microsoft/graphrag/blob/main/docs/query/local_search.md), [docs/query/global_search.md](https://github.com/microsoft/graphrag/blob/main/docs/query/global_search.md), `packages/graphrag/graphrag/query/structured_search/`.

**Index (once)**

1. Extract entities and relationships from text units.
2. Leiden (recursive, `max_cluster_size`) → nested communities.
3. Bottom-up LLM summaries (community reports).

**Local search (entity questions)**

1. Embed query (+ optional conversation history) → **semantically similar entities** (access points).
2. Fan-out maps: entity→text units, entity→community reports, entity→neighbours, entity→relationships, entity→covariates.
3. **Rank + filter** each candidate table to one context-window budget.
4. **Generate** a response from the mixed tables (`mixed_context` + system prompt).

**Global search (corpus themes)**

1. Pick a Leiden **level**.
2. **Map:** chunk community reports → LLM intermediate answers (points + importance scores).
3. **Reduce:** keep high-importance points → LLM final answer.

Also: **DRIFT** (global primer then local follow-ups) and **basic** top-\(k\) vector search.

**MemNet:** local *shape* (ego + neighbours + related text) is a host Snap cousin. Leiden / map-reduce / community reports / generate-on-retrieve are **not** Recall. Do not treat the corpus KG as session \(S\).

---

## 3. LightRAG (`kg_query` / `aquery`)

**Haystack:** incremental document KG + entity VDB + relationship VDB + chunk store.  
**Source:** `lightrag/operate.py` (`kg_query`, `_perform_kg_search`, `_build_query_context`).

**Algorithm**

1. LLM extracts **high-level** keywords (themes) and **low-level** keywords (entities). Empty both: if `len(query)<50`, force `ll_keywords=[query]`; else fail string.
2. Mode:
   - `local`: embed **ll** → entity VDB `query(top_k)` → load nodes + **degrees** → `_find_most_related_edges_from_entities` (1-hop gather).
   - `global`: embed **hl** → relationship VDB → related entities.
   - `hybrid`: both, then **round-robin merge** of entity lists and relation lists (local slot then global slot, de-dupe).
   - `mix`: hybrid plus **chunk** vector search (`source: "C"`).
   - `naive`: `naive_query` — chunks only, no entities/relations.
   - `bypass`: skip retrieve (prompt only).
3. Truncate to token budget → merge chunks from surviving entities/relations → **default path generates**. `aquery_data` / `only_need_context` can return entities, relationships, **chunk bodies**.

**MemNet:** steal dual-level *grain* (`view=shell` then TSK `interior`) and empty-keyword skip. Reject hybrid/mix/naive **in** `memnet-llm`; locators from `file_path`, not chunk JSON as `pin_map`.

---

## 4. RAGFlow (`rag/nlp/search.py`)

**Haystack:** chunk index (Infinity/ES-class) with full-text + dense vectors.  
**Source:** `rag/nlp/search.py` (`retrieval`, `rerank`, `hybrid_similarity`).

**Algorithm**

1. Query → keywords + query vector.
2. Backend **weighted_sum fusion** of match-text and match-dense. Default `vector_similarity_weight ≈ 0.3` ⇒ full-text weight \(1-w\) (or near-pure vector if no text match).
3. Fetch a ~64-candidate **window**, then **rerank:**  
   \(\mathrm{sim} = w_{\mathrm{tk}}\,\mathrm{token\_sim} + w_{\mathrm{vt}}\,\mathrm{vec\_sim} + \mathrm{rank\_feature}\).  
   Token side boosts title / `important_kwd` / question tokens (×2 / ×5 / ×6). Optional external reranker replaces the vector term (scores in \([0,1]\)).
4. Threshold + page slice. MCP `ragflow_retrieval` returns **chunks**.

**MemNet:** host Snap of the library. Steal skip-when-pins-suffice. Reject chunks on `note=` and nesting under `MemNetSystem`.

---

## 5. Graphiti (`graphiti_core/search/search.py`)

**Haystack:** temporal KG on Neo4j / FalkorDB (nodes, edges/facts, episodes, communities).  
**Sources:** `search.py`, `search_utils.py` (`rrf`, `node_distance_reranker`).

**Algorithm**

1. Empty `query.strip()` → **empty** `SearchResults` (no fallback walk).
2. If any cosine/MMR method is on, embed the query; else a dummy vector.
3. **Four scopes in parallel** (`semaphore_gather`): edges, nodes, episodes, communities — each with its `SearchConfig`.
4. Per scope, run configured methods **concurrently**, each at `2×limit` candidates:
   - `bm25` → Lucene/TF-IDF full-text (Graphiti blog: fuzzy Levenshtein on the store).
   - `cosine_similarity` → vector KNN, `sim_min_score`.
   - `bfs` → `bfs_max_depth`. If **no** `bfs_origin_node_uuids`, **two-pass:** first BM25/cosine hits become BFS origins, then a second BFS list is appended.
5. **Rerank** (config enum):
   - **RRF:** `score[uuid] += 1 / (i + rank_const)` with default `rank_const=1` (Cormack often uses \(k=60\); this is \(k=1\)).
   - **MMR:** diversity vs query vector (`mmr_lambda`).
   - **cross_encoder:** RRF seed then LLM/encoder rank of facts/names/contents.
   - **episode_mentions:** frequency of unique episodes (edges: `len(edge.episodes)`; nodes: store query).
   - **node_distance:** requires `center_node_uuid`. **Not a \(k\)-hop shortest path.** Cypher is one hop:  
     `MATCH (center:Entity {uuid})-[:RELATES_TO]-(n:Entity {uuid})` → adjacent score `1`, others `inf`, centre `0.1` if present; emit `1/score`. Edges: RRF first, then rerank **source** nodes by that adjacency.
6. Truncate to `limit`. Caller typically **generates** from facts + episode text (outside this function).

**MemNet:** steal serialise “lexical cue then expand from hits” and centre bias **as** `pin_map` from a cue (true \(k\)-hop under budget). leftover `pin_map(anchor)` is leftover. Reject parallel RRF as goldfish; reject Neo4j as the agent memory; do not copy 1-hop `RELATES_TO` as Recall (MemNet depth default is 2, undirected, `max_rows`).

---

## 6. HippoRAG 2 (`HippoRAG.retrieve`)

**Haystack:** OpenIE triples + **three** embedding stores (facts, entities, passages) + igraph.  
**Source:** `src/hipporag/HippoRAG.py`.

**Algorithm** (per query)

1. Embed query for fact-space and passage-space.
2. **Fact scores:** cosine (`np.dot`) vs fact embeddings, min-max normalise.
3. Top facts → LLM **recognition** rerank (`rerank_filter`). If **no facts survive** → **DPR** (`dense_passage_retrieval`) and return chunk bodies.
4. Else **graph_search_with_fact_entities:**
   - Phrase (entity) reset mass = average fact score **÷ chunk fan-in** (`len(ent_node_to_chunk_ids)`).
   - Passage nodes get a **small** DPR mass (`passage_node_weight`, default ~0.05).
   - **Personalized PageRank** (`damping=0.5`, undirected, `prpack`) on the whole graph.
   - Rank **passage** vertices by PPR; return **chunk bodies**.
5. Optional **IRCoT:** loop retrieve → one reasoning step → merge doc scores → retrieve again.

**MemNet:** steal empty-facts → skip/grep/host (their DPR fallback). Fan-in as a **budget**, not PPR damping. Reject OpenIE, three vector stores, PPR, IRCoT, chunks as the memory surface.

---

## 7. mem0 (`Memory.search`)

**Haystack:** vector store of `{memory, score}` rows.  
**Source:** `mem0/memory/main.py`.

**Algorithm**

1. **Require** `filters` containing `user_id` and/or `agent_id` and/or `run_id` (else `ValueError`).
2. Optional metadata operators (`eq` / `in` / `AND` / `OR` / …).
3. `_search_vector_store(query, filters, top_k, threshold)` — default `threshold=0.1`, `top_k=20`.
4. Optional `reranker.rerank`; on failure keep original.
5. Return `{"results": [{id, memory, score, …}]}` for the **system prompt**.

**MemNet:** steal scope-before-cue and threshold-as-skip. Reject vector store as memory and prose dump as SSOT.

---

## 8. Letta (core vs archival) and HiAgent

**Letta:** core = **prose blocks in the prompt**; archival = a second retrieve hop (typically vectors). Cousin of working-set vs cabinet *idea* only — cabinet is hydrate/flush of a graph, not a prompt rewrite.

**HiAgent:** not RAG. In-trial working memory = current **subgoal** chunk; finished subgoals are **replaced** by a summary. Steal live `TSK_*` ego and settle/`delete_on_settle`. Reject prompt-only hierarchy as `pin_map`.

---

## Comparison (operator, not brand)

| Relative | Seed | Walk / fuse | Output | Generate in retrieve? |
|----------|------|-------------|--------|------------------------|
| Neo4j GraphQL RAG | GraphQL `where` | None (already retrieved) | Records + LLM text | **Yes** (resolver) |
| GraphRAG local | Entity ANN | Fan-out tables + budget | Mixed tables | **Yes** |
| GraphRAG global | Leiden level | Map-reduce reports | Points → answer | **Yes** |
| LightRAG local | ll-keyword ANN | 1-hop edges | Entities + rels + chunks | Default **yes** |
| LightRAG hybrid/mix | ll + hl | Round-robin (+ chunk ANN) | Same | Default **yes** |
| RAGFlow | Query tokens + vector | Weighted sum + rerank | Chunks | Host / agent |
| Graphiti | Query string | Parallel BM25\|\|cosine\|\|BFS → RRF/MMR/CE/1-hop centre | Facts/nodes/episodes | Caller |
| HippoRAG 2 | Fact ANN + LLM filter | PPR (entity÷fan-in + ε DPR) | Chunks | QA separately / IRCoT |
| mem0 | Embedded query | Vector top-\(k\) + threshold | Memory strings | Prompt stuffing |
| **MemNet** | Discrete cue | Serial \(k\)-hop, one \(M\) | Shaped GQL | **No** |

**Rule.** If the algorithm’s last mile is **chunk bodies + generate**, it is host Snap (or LTM), not goldfish. If it **fuses** lexical, vector, and BFS in one ranker, it is Graphiti-class hybrid — serialise to cue-then-`pin_map` or leave it on the host. If it **ANN-indexes \(S\)**, that is Snap-on-session (forbidden).
