# Rethink: RAG, `memnet-llm`, and the Neo4j cabinet

**Status:** design proposal — **not** shipped. Does **not** amend [`../SHAPE.md`](../SHAPE.md) until accepted.  
**Decision proposed:** option **B** (two ports, one Neo4j process) **plus** a **session-catalog Snap** (RAG grain = session id, then `pin_map`). Reject **C**. Keep **A** only as the as-is teach until B is accepted.  
**Audience:** product developers. British English.

**Pressure:** operators ask how RAG works *between* `memnet-llm` and Neo4j. As-is the answer is “it doesn’t” (cabinet = hydrate/flush only). That job cut is right; as an **operator** architecture it fails: GraphRAG / Graphiti / FTS already run **on Neo4j**. If MemNet forbids every retrieve on that server, they bypass MemNet (LLM↔Bolt).

**Locked (do not rethink these):** MN-REQ-00 (wall-clock **and** tokens); two operators Recall/Commit ([`math-skeleton.md`](math-skeleton.md)); GQL `pin_map` / mutate (ADR-001); HostSearch **outside** `MemNetSystem` (MN-REQ-13.1); locators not chunk bodies; no `rag_query` / `pin_map.generate`; no ANN of session \(S\); one `DurableSyncOwner` for **cabinet** hydrate/flush; live Neo4j still unclaimed.

| Pointer | Role |
|---------|------|
| [`rag-relative-algorithms.md`](rag-relative-algorithms.md) | Why RAG was hot; retrieve functions from source |
| [`neo4j-buffer.md`](neo4j-buffer.md) | As-is MemNet ↔ Neo4j seam; RAG relatives on Snap / Shape / cabinet |
| [`memnet-host-search-nest.md`](memnet-host-search-nest.md) | Host Snap steal/reject |
| [`../multi-agent-sessions.md`](../multi-agent-sessions.md) | Many sessions in the engine; **one** shared \(S\) per Multitask mission; Path-B import |

---

## Two problems (do not fuse)

RAG got hot because **weights do not contain the operator’s library**. MemNet exists because **the next LLM call does not contain the mission graph**. Same symptom (too much text for the prompt); **two haystacks**. Detail: [`rag-relative-algorithms.md`](rag-relative-algorithms.md) § “Why RAG became a hot topic”.

| | RAG (library Snap) | MemNet (session Shape) |
|--|--------------------|-------------------------|
| **Problem** | Parametric ignorance: freeze, no private PDFs, fine-tune too dear, paste-the-corpus blows the window, fluent hallucination on corpus QA | Goldfish call: forgets `TSK`/`USR`/settled files; chat is not a named graph; dump \(S\) burns tokens |
| **Move** | Index library → retrieve few passages → **generate** | Cue → bounded `pin_map` → sparse Commit; **no** generate on the wire |
| **Hot after** | ChatGPT-era “chat with our docs” (Lewis et al. 2020 → 2023 stacks) | Agents / Multitask that must **re-`pin_map`**, not re-read the PDF |
| **On Neo4j today** | GraphRAG local/global, Graphiti RRF, FTS/vector, GraphQL `generate` | `Neo4jAdapter` MERGE/MATCH ego under `HydrateBudget` only |

GraphRAG-class products are **fancier retrieve for the first problem**. They do not become MemNet. The rethink is: **(B)** may the same Neo4j process host the library port without becoming goldfish, and **(session catalog)** may RAG pick a **session** rather than a chunk?

---

## What is wrong with the as-is design

As-is we taught **two haystacks** but **three stores**, then wired Neo4j only to the cabinet:

| Store | Haystack | As-is owner | As-is Neo4j role |
|-------|----------|-------------|------------------|
| Library | RAG’s | Host Snap (unshipped) | **Unused** — vector/FTS/GraphQL listed as “not on this seam” |
| Live \(S\) | MemNet’s | `memnet-llm` Shape | Not on Neo4j except via flush |
| Durable \(S\) | still MemNet’s | `Neo4jAdapter` cabinet | Ego MERGE/MATCH only |

Live and durable \(S\) are **one** haystack (the mission graph) with two persistence forms. Treating the cabinet as a third haystack is how operators paste Graphiti onto `_memnet_tag`. Three failures follow:

1. **Naming gap.** Cabinet hydrate *is* a graph retrieve of durable \(S\) (k-hop, `LIMIT`). It is not RAG (no ranker, no generate). Operators still hear “graph retrieve on Neo4j” and paste Graphiti RRF onto `_memnet_tag` nodes.
2. **Single-server gravity.** One Neo4j process is cheap. GraphRAG local, LightRAG entity-ANN, and Graphiti already live there. A doctrine that says “RAG never touches Neo4j” does not move the corpus; it moves the **LLM off MemNet**.
3. **Miss path is mute.** Goldfish skip-on-empty-seed is right. The next hop (grep / host Snap) has **no** first-class port onto the cabinet’s server, so the practical miss path is Bolt Browser.

As-is MUST NOTs stay. What we rethink is **“Neo4j = cabinet only, retrieve is someone else’s laptop.”** We do **not** rethink “RAG solved session memory.”

---

## Options (do not mix)

| Option | Idea | Keep | Cost |
|--------|------|------|------|
| **A. Firewall** (as-is) | RAG never uses the MemNet Neo4j URL. Host Snap is a sibling MCP (RAGFlow, Cursor index). | Simplest engine. Honest “no RAG hop.” | Operators fuse on the same URI anyway; MemNet becomes optional. Extra chunk prompt (**2–8k tokens**) beside Shape. |
| **B. Two ports, one server** (propose) | Same Neo4j **process**; **two namespaces**. Cabinet port = hydrate/flush of \(S\). Library port = `RagHostHook` adapter → **locators only**. | Jobs unfused. LLM still never talks Bolt. Goldfish **1–4k** tokens, Snap **0** LLM. | Need namespace law, fail-open, no generate. HostSearch remains Later to ship. |
| **C. Fuse** (reject) | `pin_map` / hydrate runs RRF, PPR, Leiden, or GraphQL `generate` on the cabinet. | Matches Graphiti/GraphRAG products. | Contradicts MN-REQ-00 / 13.1. Session becomes the library. Tokens ×N communities. |
| **D. Session-catalog Snap** (propose, with B) | Host RAG ranks **library session ids** (or a directory session of `session=` locators). Next hop is `pin_map` / Path-B **import**, not generate. | Uses MemNet’s existing multiplicity. Answers “no pin” and “>50 rows” without ANN of mission \(S\). | Catalog must stay locator-sized. Must not merge/RRF sessions into one prompt. Multitask mission SSOT stays **one** \(S\). |

**Reject C.** That is Graphiti-as-MemNet — RAG’s problem wearing MemNet’s name.

**D is not C.** Ranking **which named graph** to open is Snap. Ranking **pins inside** the mission graph, or stuffing \(N\) sessions into one completion, is C.

**Do not pick A as the long-term operator story** unless we also tell them to run a *second* graph server for the corpus. Most will not.

---

## Proposed design (option B)

```text
                    LLM  <-->  memnet-llm   (GQL pin_map / mutate only)
                                 |
            +--------------------+--------------------+
            | cabinet port       | library port       |
            | DurableSyncOwner   | RagHostHook        |
            | hydrate / flush    | locators, fail-open|
            v                    v
         Neo4j db/label          Neo4j db/label
         MEMNET_NEO4J_DATABASE   MEMNET_NEO4J_LIBRARY_DATABASE
         nodes with _memnet_tag  corpus KG / FTS / vector
         (session S durable)     (library — RAG’s haystack)
```

Same Bolt URL **may** be used. Library is **not** a second `DurableStoreAdapter`. Factory today errors two *cabinet* URLs (Agens + Neo4j); that rule stays.

### Namespace law (the whole of option B)

Preferred: **two named databases** on one process — `MEMNET_NEO4J_DATABASE` (cabinet, default `neo4j`) vs `MEMNET_NEO4J_LIBRARY_DATABASE` (library; **not** shipped). Fallback on Community single-db: **label split** — cabinet MERGE only writes `_memnet_tag`; library MATCH **MUST NOT** return those nodes.

| Port | Writes | Reads |
|------|--------|-------|
| Cabinet | `MERGE` nodes/edges with `_memnet_tag` under `HydrateBudget` | Ego `{id}` `[*0..depth]` `LIMIT` — never FTS/ANN |
| Library | **None** from MemNet (host / GraphRAG / Graphiti own ingest) | FTS / vector / 1-hop corpus walk → **locators** only |

**MUST NOT** dual-write the same Neo4j node as both a mission pin and a corpus chunk. If the operator has only one database and one label set, they are on **C** whether they meant to be.

### Library port — steal retrieve, reject generate

Algorithms from source: [`rag-relative-algorithms.md`](rag-relative-algorithms.md). Graphiti `node_distance` is **one hop** of `RELATES_TO` to `center_node_uuid`, not a \(k\)-hop shortest path and not MemNet depth-2 Recall.

| Relative | Steal on library port | Reject (cabinet / goldfish) |
|----------|----------------------|-----------------------------|
| GraphRAG **local** | Entity access points + neighbour **tables as locators** | Mixed-context **generate**; global Leiden **map-reduce** |
| GraphRAG **global** | Nothing on the goldfish turn | Community reports as `pin_map` |
| LightRAG **local** | 1-hop entity ids as locators | hl/ll **keyword LLM**; chunk JSON as Shape |
| Graphiti | `center_node_uuid` → next `pin_map` **anchor**; `group_ids` ≈ session | RRF (\(k=1\)) of BM25\|\|cosine\|\|BFS; 1-hop distance **as** Recall; `add_episode` onto `_memnet_tag` |
| HippoRAG 2 | Passage **ids** after host PPR | PPR / fact-ANN **on** \(S\); chunk bodies in the prompt |
| RAGFlow / mem0 | Host MCP; emit paths / memory **ids** | Weighted chunk fusion or `{memory, score}` stuffing through MemNet |
| Neo4j GraphQL `generate` | GraphQL **retrieve** of corpus types | Resolver `generate` as goldfish |

### Serial miss path (goldfish I/O, already designed)

```text
cue in mission S → find / pin_map
  seed hit     → Shape \(\tilde{X}\) → sparse Δ → Commit
  seed empty   → skip OR session-catalog Snap → session= locators
               → pin_map that library session
                 OR Path-B import slice into mission → pin_map
```

Emit `session=` / `path=` / `document_id=` / `qname=` only. Adapter **MUST NOT** mutate mission \(S\). Fail-open: timeout / miss → skip; **MUST NOT** fail `pin_map`. Skip Snap when grep / ingest / existing pins suffice. Multitask workers **MUST NOT** open a library session unless the parent assigned it.

### What hydrate is (still not RAG)

Cabinet hydrate remains: ego `{id}` → `[*0..depth]` → `LIMIT` → upsert into a **new** session. No embedding of \(S\), no RRF, no community reports, no `generate`. **Zero LLM tokens.** If the operator enabled a vector index on cabinet labels, MemNet **MUST NOT** use it on this port (Snap-on-session).

### What the LLM sees

Still one goldfish: shaped GQL from `memnet-llm` (**≲ 4k tokens** typical). Never Neo4j Browser, never GraphQL `generate`, never `{memory, score}` prompt stuffing from the cabinet. Never chunk bodies from the library port. Never \(N\) sessions pasted into one prompt.

---

## RAG process on multiple sessions (option D)

The engine **already** holds many sessions (each `session_open` mints an id). Multitask still uses **one shared mission \(S\)**. Those are compatible: extra sessions are **library / member / directory** graphs, not a second SSOT for the same mission.

RAG’s retrieve grain in this design is **which session**, not which pin and not which chunk.

```text
                    LLM  <-->  memnet-llm
                                 |
              mission S (goldfish pin_map, M≈50)
                                 |
              Snap (host) ranks catalog of session ids
                                 |
         +-----------+-----------+-----------+
         |           |           |           |
      S_lib_a     S_lib_b     S_dir      S_member
      (topic A)   (topic B)   (session=) (Path-B worker)
```

| Kind of session | Role | RAG? |
|-----------------|------|------|
| **Mission** \(S\) | SSOT for this job. Cue → `pin_map`. Workers share **this** id. | **No** — Shape only. MUST NOT ANN. |
| **Library** \(S_{\mathrm{lib}}\) | One topic / package / ingest that must stay Shape-sized. Host owns ingest; MemNet goldfish if opened. | Snap **picks the id**; Shape **inside**. |
| **Directory** \(S_{\mathrm{dir}}\) | Pins that *are* locators: `session=mn_…`, keyword, path. \(M=50\) **sessions listed**, not 50 chunks. No new SCHEMA kind required. | Catalog for Snap; still `pin_map`, not generate. |
| **Member** (Path-B) | Separate worker session; lead **imports** a bounded slice. Shipped. | Not RAG. Import ≠ host Snap. |

**Unknown pin (question 1).** `find` in mission \(S\). Empty → Snap the **directory** (or host index of session ids + keywords) → emit `session=` locators → either `pin_map` that library session **or** Path-B import a slice into mission \(S\) → `pin_map`. Still skip if the catalog misses. Do not invent a pin; do not rank mission pins by embedding.

**Larger than 50 rows (question 2).** Do not raise \(M\). **Partition** the library into more sessions so each graph is goldfish-sized. A fat `PKG` is a sign to split sessions, not to fuse. Path-B import still uses a **slice** (\(M\times|\mathrm{anchors}|\) is import payload, not goldfish).

Steal / reject vs relatives:

| Relative | Steal | Reject |
|----------|-------|--------|
| Graphiti `group_ids` | One group ≈ one session id | RRF groups into one search hit list |
| GraphRAG communities | One community ≈ one library session (id, not report prose) | Map-reduce reports as goldfish |
| LightRAG dual-level | Directory = shell; library session = interior | Keyword LLM + chunk JSON |
| MemNet Path-B | Import slice into lead \(S\) | Absorb host RAG hits; merge whole sessions |

**MUST NOT:** one session per chunk; RRF / union of \(N\) `pin_map` dumps in chat; workers opening library sessions as a shadow mission SSOT; ANN of mission \(S\) “because we have many sessions.”

Cabinet (B): hydrate/flush **the session id you named**. Library Neo4j namespace may back **library** sessions; cabinet labels stay `_memnet_tag` per session, never a cross-session vector index used as goldfish.

---

## SHAPE delta (only if this note is accepted)

[`../SHAPE.md`](../SHAPE.md) §4–5 stay two jobs (Shape vs Snap) and cabinet-behind. Add: **Snap MAY use the same Neo4j process as the cabinet iff the library namespace is disjoint; Snap MUST NOT read `_memnet_tag` / cabinet database as a corpus.** Add: **Snap MAY return `session=` locators (library / directory sessions); goldfish remains `pin_map` of one named \(S\); Multitask mission SSOT remains one session.** § forbids still: `rag_query` as MemNet; GraphRAG **as** MemNet; LLM↔store direct; ranking pins inside mission \(S\).

MN-REQ-13.1 already allows `RagHostHook` outside `MemNetSystem`. This rethink only **binds** that hook to a namespaced Neo4j as one allowed backend — it does not nest HostSearch under `MemNetSystem` and does not ship the hook.

---

## MUST / MUST NOT (proposal)

**MUST**

- Keep cabinet and library as **two ports** even on one Bolt URL (named database preferred; else `_memnet_tag` vs corpus labels).
- Locator-only host emit (`session=` / `path=` / `document_id=` / `qname=`); next goldfish is `pin_map` of **one** named session.
- Partition a fat library into **more sessions**, not a larger \(M\).
- Fail-open skip on host miss.
- One `DurableSyncOwner` for cabinet writes.
- Flush cabinet on **settle / process death**, not every `pin_map` (N auto-commit MERGEs).
- Keep goldfish prompt **≲ 4k tokens** typical; treat **≳ 8k** from one `pin_map` as alarm.
- Keep **one** mission session under Multitask; library sessions are extra ids, not a second SSOT.

**MUST NOT**

- Rank/generate inside `pin_map` or hydrate (option C).
- ANN / FTS **mission** \(S\) or **cabinet** labels as goldfish (Snap-on-session).
- RRF or paste \(N\) sessions into one completion.
- Dual-write the same node id as both mission pin and corpus chunk.
- Teach LLM↔Neo4j as the miss path.
- Treat the **4 MiB** serve frame as a token budget.
- Hold **1.0** for this (HostSearch ship remains **Later**).

---

## Estimates (order of magnitude, not a benchmark)

These are **design budgets** so option A/B/C can be compared. They are **not** measured SLAs and **not** a live-Neo4j claim. Caps from the engine: `pin_map` default depth 2 / `max_rows` 50 (`DEFAULT_QUERY_*`); `HydrateBudget` 50 nodes / 100 edges / depth 2; TCP/IPC frame **4 MiB** (`MEMNET_SERVE_MAX_FRAME_BYTES`); session store cap `MEMNET_MAX_ROWS` default 5000. Role size: tens of MiB typical, hundreds still in role, gigabytes = library/cabinet ([`memnet-host-search-nest.md`](memnet-host-search-nest.md)).

**RTT** = one request/response on that hop. **Local** = same host or LAN under 1 ms. **WAN** = 20–80 ms class. **LLM** = one chat completion (0.5–30 s, dominates everything else).

### Network (latency / bytes on the wire)

| Hop | Bytes / turn (typical) | RTT count | Wall-clock (local) | Wall-clock (WAN) |
|-----|------------------------|-----------|--------------------|------------------|
| **Shape** `pin_map` in-process | 10–100 KiB shaped GQL (~50 rows × 0.2–2 KiB) | 0 (same process) | **0.1–5 ms** CPU, no NIC | n/a |
| **Shape** via `memnet serve` / MCP | Same payload; frame ≤ 4 MiB | 1 | **1–10 ms** | **20–100 ms** |
| **Cabinet hydrate** | Two Cypher reads; ≤50 nodes + ≤100 edges ≈ 20–200 KiB | **2** Bolt | **1–20 ms** | **40–200 ms** |
| **Cabinet flush** | One `MERGE` **per** node then per edge (`session.run` auto-commit) | **≤150** Bolt | **50–500 ms** local (chatty) | **seconds** on WAN — avoid remote flush every turn |
| **Library Snap (B, locators only)** | 1–3 Cypher or ANN queries; emit a few locators (bytes, not chunks) | 1–3 Bolt | **2–30 ms** (+ ANN) | **50–250 ms** |
| **Option A sibling RAG MCP** | Chunk bodies often 2–20 KiB × top‑\(k\) | 1 HTTP | **10–100 ms** + embed | **100 ms–2 s** |
| **Graphiti RRF (C / bypass)** | 3–4 parallel searches × `2×limit` candidates | 3–8 Bolt | **10–80 ms** | **100–400 ms** |
| **GraphRAG local generate** | Mixed tables stuffed into prompt (often 4–16 KiB) | 1 LLM | **LLM-bound** | LLM-bound |
| **GraphRAG global map-reduce** | One LLM call **per** community-report chunk, then reduce | **tens–hundreds** LLM | **tens of seconds–minutes** | same |
| **Neo4j GraphQL `generate`** | GraphQL retrieve + 1 LLM per field | 1 Bolt-ish + 1 LLM | **LLM-bound** | LLM-bound |

**Design rule.** Goldfish must stay **milliseconds** without an LLM. Cabinet flush is the expensive MemNet hop (N round-trips); do it on **settle / process death**, not every `pin_map`. Library Snap must stay **locator-sized** or it becomes RAGFlow on the goldfish path. Any path that calls **generate** leaves the millisecond budget.

### Size of memory (RAM / store)

| Store | Working set | Notes |
|-------|-------------|--------|
| **Live \(S\)** (`memnet-llm` GraphStore) | **Tens of MiB** typical; **hundreds of MiB** still in role; hard row cap 5000 (default) | Atoms + locators; PDF bytes stay on disk. Goldfish **sees** ~50 rows, not all of \(S\). |
| **`pin_map` / hydrate slice** | **~10–200 KiB** in RAM + prompt | Bound by \(M\) and 4 MiB frame — not by Neo4j heap. |
| **Cabinet namespace** (option B) | Same order as \(S\) (flushed ego balls, not the whole library) | Neo4j page cache: plan **0.5–2 GiB** for a mission cabinet; not a corpus. |
| **Library namespace** (option B) | **Gigabytes–terabytes** class (docs, KG, vectors) | Operator’s GraphRAG/FTS heap/index. MemNet must not load this into \(S\). |
| **Embedding index** (library only) | ~1–4 KiB × vectors (e.g. 768-d float32 ≈ 3 KiB) × chunks | 1 M chunks ≈ **3 GiB** vectors **plus** graph. Forbidden on cabinet labels. |
| **GraphRAG Leiden + reports** | Graph + **LLM-sized** report text per community | Index-time disk/RAM; query-time still prompt-bound. |
| **HippoRAG three stores + igraph** | Facts + entities + passages **all** in RAM for PPR | Fine for QA benchmarks; not a goldfish working set. |
| **Option C fused** | Library **plus** \(S\) in one hot graph | RAM follows the **library**; goldfish budget is lost. |

**Design rule.** If it does not fit in **hundreds of MiB**, it is library or cabinet-of-library, not live Shape. Option B keeps two heaps conceptually even when one `java` process holds both databases.

### CPU effort (one turn, no LLM unless stated)

| Work | Complexity (sketch) | Effort class |
|------|---------------------|--------------|
| **`find` + `pin_map`** | Scan/index by kind + BFS ≤ depth 2, clamp \(M=50\), fan-out clamp | **µs–ms**, one core. Deterministic. |
| **MutateGate** | Parse + mint + SCHEMA | **µs–ms**. |
| **Hydrate Cypher** `[*0..2]` LIMIT 50 | Planner + expand; bounded | **ms** on cabinet-sized graphs; **degrades** if cabinet was stuffed with the corpus (then you already fused). |
| **Flush N MERGE** | \(O(N)\) commits | **CPU cheap**; **network/fsync** dominate (see table above). |
| **Library FTS / Lucene** | Inverted index | **ms** for locator top‑\(k\). |
| **Library vector KNN** | HNSW/ANN | **ms–tens of ms**; extra **embed query** CPU/GPU ~1–10 ms local model, or a network embed call. |
| **Graphiti RRF \(k=1\)** | 3 lists + \(O(\sum r)\) | **Cheap vs Bolt**. Cross-encoder rerank = **GPU/LLM**. |
| **LightRAG hl/ll keywords** | **1 LLM** before any graph | Leaves the ms budget immediately. |
| **HippoRAG PPR** | ~sparse \(|V|\) with damping 0.5 on the **whole** graph | **10 ms–seconds** as \(|V|\) grows; plus fact ANN + optional LLM fact filter. |
| **GraphRAG Leiden** | Index-time community detection | **Seconds–hours** once per corpus, not per goldfish turn. |
| **GraphRAG global map** | LLM × report chunks | **Dominant cost** of that product. |
| **Option C on cabinet** | RRF/PPR/Leiden/**generate** on \(S\) | Pays **library** CPU **every turn**; contradicts MN-REQ-00 wall-clock. |

**Design rule.** Option **B** library port is allowed to spend **ANN/FTS milliseconds** (and must **timeout** / fail-open). It is **not** allowed to spend **LLM seconds** on the goldfish turn. Keyword extraction and generate stay host-side and **off** the default miss path, or the miss path is skipped.

### LLM token usage (MN-REQ-00 boundary)

Tokens here are **chat-completion** tokens (prompt + completion), not embedding dimensions and not MemNet `id` codebook tokens. Conversion for estimates: **~4 characters / token** on shaped GQL and English (order of magnitude, not a tiktoken claim).

**The 4 MiB serve frame is not a goldfish token budget.** 4 MiB ≈ \(10^6\) tokens — stuffing that would violate MN-REQ-00. The live bound is `max_rows` \(M=50\) (and `view=shell` ≤8 NODE / ≤12 EDGE). Hydrate/flush use **zero** LLM tokens.

| Path (one agent turn) | Prompt in (est.) | Completion out (est.) | Calls | Notes |
|-----------------------|------------------|------------------------|-------|--------|
| **Shape** `pin_map` interior, \(M=50\) | **1–4k** typical; **~8k** alarm; **~25k** if every row is a 2 KiB blob | Sparse \(\Delta\): **50–400** | **1** (the agent’s own call) | 50 × ~80–300 chars/line. MUST NOT echo \(\tilde{X}\) back through mutate. |
| **Shape** `view=shell` | **200–800** | same sparse \(\Delta\) | 1 | Survey then one interior — not \(N\) full maps (duplicate LAW). |
| **`find` only** | **tens–200** (hit ids) | — | 0 extra | Then `pin_map`; do not dump hits as prose. |
| **Commit \(\Delta\)** | counted in the same call as Shape | **50–400** | 0 extra | NEW/SET only. |
| **Cabinet hydrate / flush** | **0** | **0** | 0 | Bolt only. |
| **Library Snap locators (B)** | **0–200** if locators are committed, not pasted | **0** on the hook | 0 on goldfish | Hook MUST NOT emit chunk bodies. Pasting \(k\) chunks into chat is option A/C leakage. |
| **Option A RAG MCP** (top‑\(k\) chunks in the prompt) | **2–8k** (\(k=8\) × ~400–800 tok/chunk) | **200–2k** | 1 | Plus the `pin_map` call if they also goldfish — **two** stuffed contexts. |
| **LightRAG keywords** | **0.5–2k** | **50–200** (hl/ll lists) | **+1 LLM before retrieve** | Then a **second** generate on chunks. |
| **HippoRAG fact “recognition”** | facts × filter prompt | short list | **+1** | Then QA generate on **chunk bodies**. |
| **Graphiti + generate** | facts/episodes often **1–4k** | **200–2k** | 1 | Cross-encoder may be a **second** model. |
| **Neo4j GraphQL `generate`** | retrieved records + prompt | **200–1k** / field | **1 per generate field** | \(N\) movies ⇒ \(N\) completions. |
| **GraphRAG local** | mixed tables **1–4k** (4–16 KiB) | **500–2k** | 1 | Retrieve-then-generate on the **library**. |
| **GraphRAG global map-reduce** | report chunk **1–4k each** | **200–1k** each map; reduce **1–4k** | **tens–hundreds** | Token cost ≈ communities × (in+out). Dominates. |
| **Dump live \(S\)** (forbidden) | **10k–100k+** (thousands of rows) | wasted | 1 | Why \(M\) exists. |
| **Option C** (RRF + generate on cabinet \(S\)) | **library-sized** prompt every turn | full answer | 1+ | Pays global-RAG tokens **and** loses Shape. |

**Boundary (design)**

| Bound | Value | Why |
|-------|--------|-----|
| Goldfish **typical** prompt from MemNet | **≲ 4k tokens** | \(M=50\) dense GQL lines + one LAW |
| Goldfish **alarm** | **≳ 8k tokens** from one `pin_map` | Rows too fat (`note=` blobs) or \(N\) serial maps |
| Goldfish **hard stop (teach)** | Do not use the **4 MiB** frame; do not dump \(S\) | Network cap ≠ token cap |
| Host Snap on the **same** turn | **0 LLM tokens** on the default miss path | Locators via mutate; skip if pins suffice |
| Generate / keyword-LLM / map-reduce | **Off** `pin_map` / hydrate | Host only; not the cabinet port |

**Design rule.** MN-REQ-00 counts **tokens as well as wall-clock**. Option B keeps **one** completion per goldfish turn, context ≈ Shape only. A sibling RAG that **also** stuffs chunks **doubles** prompt tokens (A). Fuse (C) or GraphRAG global spends **orders of magnitude** more tokens per question than `pin_map`.

### Option A / B / C / D scored on these budgets

| | Network | Memory | CPU / turn | LLM tokens / question |
|--|---------|--------|------------|------------------------|
| **A Firewall** | Goldfish ms; corpus RAG is another MCP (chunky). Two servers if they obey. | \(S\) small; library elsewhere | Shape ms; RAG MCP extra | Shape **1–4k** **plus** chunk prompt **2–8k** if they RAG |
| **B Two ports** | Shape ms; hydrate 2 RTT; flush batched/offline; Snap 1–3 RTT locators | Two namespaces; cabinet hundreds of MiB; library GiB **not** in \(S\) | Shape ms; Snap ms–tens of ms; **no** generate | **1–4k** Shape; Snap **0**; hydrate **0** |
| **C Fuse** | Every turn looks like Graphiti/GraphRAG (parallel Bolt + prompt) | One hot heap = library | PPR/Leiden/LLM — **seconds+** | **1–4k+** stuffed graph **plus** generate; global = **×N communities** |
| **D Catalog** (with B) | Same as B; Snap returns a few `session=` ids | Many small \(S_{\mathrm{lib}}\); mission \(S\) stays tens of MiB | Catalog rank on **ids**, then one Shape | **1–4k** one `pin_map`; **not** \(N\times\) maps |

MN-REQ-00 (wall-clock + tokens) **selects B+D** when one Neo4j process is a given and the engine already has many sessions: keep the millisecond goldfish, pay Bolt only for bounded hydrate and rare flush, pay library ANN only on **miss** and only to pick a **session id**, never pay map-reduce on `pin_map`. One completion, Shape-sized context. RAG still solves the **library** problem; MemNet still solves the **session** problem.

---

## Leftover if accepted

1. Spec `MEMNET_NEO4J_LIBRARY_DATABASE` (or label law) in the Neo4j extra — docs first; adapter Later with HostSearch. Same URL as `MEMNET_NEO4J_URL` is allowed; **different database name** (or labels).
2. SysML: `RagHostHook` backend `Neo4jLibraryAdapter` `implemented=false`; emit type `session=` (directory / library ids) beside path locators.
3. Teach: catalog Snap vs Path-B import (already shipped) — do not invent a second absorb for host hits.
4. Do not close live Neo4j cabinet leftover from this note.

Until accepted, as-is teaching stays: no RAG hop on the **cabinet** seam; host Snap unshipped; operators who fuse on one graph do so **outside** MemNet.
