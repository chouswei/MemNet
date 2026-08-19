# Rethink: RAG, `memnet-llm`, and the Neo4j cabinet

**Status:** design proposal — **not** shipped. Does **not** amend [`../SHAPE.md`](../SHAPE.md) until accepted.  
**Audience:** product developers. British English.  
**Pressure:** after placing RAG relatives and stating there is no RAG hop on Bolt, the remaining question is “how does RAG work *between* `memnet-llm` and Neo4j?” The honest as-is answer is “it doesn’t.” That answer is **correct as a job cut** and **wrong as an operator architecture**: the same people who run MemNet already run GraphRAG / Graphiti / FTS **on Neo4j**. If MemNet forbids every retrieve on that server, they bypass MemNet (LLM↔Bolt) and the session dies.

**Locked (do not rethink these):** MN-REQ-00; two operators Recall/Commit ([`math-skeleton.md`](math-skeleton.md)); GQL `pin_map` / mutate as agent wire (ADR-001); HostSearch **outside** `MemNetSystem` (MN-REQ-13.1); locators not chunk bodies; no `rag_query` / `pin_map.generate`; no ANN of session \(S\); one `DurableSyncOwner` for **cabinet** hydrate/flush; live Neo4j still unclaimed.

**Algorithms:** [`rag-relative-algorithms.md`](rag-relative-algorithms.md). **As-is placement:** [`neo4j-buffer.md`](neo4j-buffer.md). **Host nest:** [`memnet-host-search-nest.md`](memnet-host-search-nest.md).

---

## What is wrong with the as-is design

As-is we taught **three haystacks** and then wired only two of them to Neo4j’s absence:

| Haystack | As-is owner | As-is Neo4j role |
|----------|-------------|------------------|
| Library | Host Snap (unshipped) | **Unused** — vector/FTS/GraphQL listed as “not on this seam” |
| Session \(S\) | `memnet-llm` Shape | Not stored on Neo4j except via flush |
| Durable \(S\) | `Neo4jAdapter` cabinet | Ego MERGE/MATCH only |

Three failures follow:

1. **Naming gap.** Cabinet hydrate *is* a graph retrieve of durable \(S\) (k-hop, `LIMIT`). It is not RAG (no ranker, no generate). Operators still hear “graph retrieve on Neo4j” and paste Graphiti RRF onto `_memnet_tag` nodes.
2. **Single-server gravity.** One Neo4j process is cheap. GraphRAG local, LightRAG entity-ANN, and Graphiti already live there. A doctrine that says “RAG never touches Neo4j” does not move the corpus; it moves the **LLM off MemNet**.
3. **Miss path is mute.** Goldfish skip-on-empty-seed is right. The next hop (grep / host Snap) has **no** first-class port onto the cabinet’s server, so the practical miss path is Bolt Browser.

As-is MUST NOTs stay. What we rethink is **“Neo4j = cabinet only, retrieve is someone else’s laptop.”**

---

## Options (do not mix)

| Option | Idea | Keep | Cost |
|--------|------|------|------|
| **A. Firewall** (as-is) | RAG never uses the MemNet Neo4j URL. Host Snap is a sibling MCP (RAGFlow, Cursor index). | Simplest engine. Honest “no RAG hop.” | Operators fuse on the same URI anyway; MemNet becomes optional. |
| **B. Two ports, one server** (propose) | Same Neo4j **process**; **two namespaces**. Cabinet port = hydrate/flush of \(S\). Library port = `RagHostHook` adapter → **locators only**. | Jobs unfused. LLM still never talks Bolt. | Need namespace law, fail-open, no generate. HostSearch remains Later to ship. |
| **C. Fuse** (reject) | `pin_map` / hydrate runs RRF, PPR, Leiden, or GraphQL `generate` on the cabinet. | Matches Graphiti/GraphRAG products. | Contradicts MN-REQ-00 / 13.1. Session becomes the library. |

**Reject C.** That is Graphiti-as-MemNet.

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
         (session S durable)     (library — not S)
```

Same Bolt URL **may** be used. **MUST** distinguish namespace: named database (preferred) or a reserved label/prefix that cabinet MERGE will **never** write (e.g. library graph `Corpus` vs cabinet `_memnet_tag`). Factory today errors two *cabinet* URLs (Agens + Neo4j); that rule stays. Library is **not** a second `DurableStoreAdapter`.

### Serial miss path (goldfish I/O, already designed)

```text
cue → find / pin_map
  seed hit     → Shape \(\tilde{X}\) → sparse Δ → Commit
  seed empty   → skip OR host Snap (library port) → locators → Commit → pin_map
```

Host Snap **MAY** call GraphRAG-*local shape* (entity access points + neighbour tables) or LightRAG-local 1-hop or Neo4j FTS — **strip generate and chunk bodies**. Emit `path=` / `document_id=` / `qname=` only. Adapter **MUST NOT** mutate \(S\). Fail-open: timeout / miss → skip; **MUST NOT** fail `pin_map`.

Steal from relatives (shape only): GraphRAG local fan-out **without** the LLM response; LightRAG dual-level as `shell` then TSK `interior`; Graphiti **centre uuid** as `pin_map` anchor, **not** their RRF or 1-hop-as-Recall. Algorithms stay in [`rag-relative-algorithms.md`](rag-relative-algorithms.md).

### What hydrate is (still not RAG)

Cabinet hydrate remains: ego `{id}` → `[*0..depth]` → `LIMIT` → upsert into a **new** session. No embedding of \(S\), no RRF, no community reports, no `generate`. If the operator enabled a vector index on cabinet labels, MemNet **MUST NOT** use it on this port (Snap-on-session).

### What the LLM sees

Still one goldfish: shaped GQL from `memnet-llm`. Never Neo4j Browser, never GraphQL `generate`, never `{memory, score}` prompt stuffing from the cabinet.

---

## SHAPE delta (only if this note is accepted)

[`../SHAPE.md`](../SHAPE.md) §4–5 stay two jobs (Shape vs Snap) and cabinet-behind. Add one sentence: **Snap MAY use the same Neo4j process as the cabinet iff the library namespace is disjoint; Snap MUST NOT read `_memnet_tag` / cabinet database as a corpus.** § forbids still: `rag_query` as MemNet; GraphRAG **as** MemNet; LLM↔store direct.

MN-REQ-13.1 already allows `RagHostHook` outside `MemNetSystem`. This rethink only **binds** that hook to a namespaced Neo4j as one allowed backend — it does not nest HostSearch under `MemNetSystem` and does not ship the hook.

---

## MUST / MUST NOT (proposal)

**MUST**

- Keep cabinet and library as **two ports** even on one Bolt URL.
- Locator-only host emit; next goldfish is `pin_map`.
- Fail-open skip on host miss.
- One `DurableSyncOwner` for cabinet writes.

**MUST NOT**

- Rank/generate inside `pin_map` or hydrate (option C).
- ANN / FTS **cabinet** labels as goldfish (Snap-on-session).
- Dual-write the same node id as both mission pin and corpus chunk.
- Teach LLM↔Neo4j as the miss path.
- Hold **1.0** for this (HostSearch ship remains **Later**).

---

## Leftover if accepted

1. Spec `MEMNET_NEO4J_LIBRARY_DATABASE` (or label law) in the Neo4j extra — docs first; adapter Later with HostSearch.
2. SysML: `RagHostHook` backend `Neo4jLibraryAdapter` `implemented=false`.
3. Do not close live Neo4j cabinet leftover from this note.

Until accepted, as-is teaching stays: no RAG hop on the cabinet seam; host Snap unshipped; operators who fuse on one graph do so **outside** MemNet.

---

## Estimates (order of magnitude, not a benchmark)

These are **design budgets** so option A/B/C can be compared. They are **not** measured SLAs and **not** a live-Neo4j claim. Caps from the engine: `pin_map` default depth 2 / `max_rows` 50 (`DEFAULT_QUERY_*`); `HydrateBudget` 50 nodes / 100 edges / depth 2; TCP/IPC frame **4 MiB** (`MEMNET_SERVE_MAX_FRAME_BYTES`); session store cap `MEMNET_MAX_ROWS` default 5000. Role size: tens of MiB typical, hundreds still in role, gigabytes = library/cabinet ([`memnet-host-search-nest.md`](memnet-host-search-nest.md)).

**RTT** = one request/response on that hop. **Local** = same host or LAN &lt;1 ms. **WAN** = 20–80 ms class. **LLM** = one chat completion (0.5–30 s, dominates everything else).

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
| **GraphRAG local generate** | Mixed tables stuffed into prompt (often 4–16 KiB+ tokens) | 1 LLM | **LLM-bound** | LLM-bound |
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

### Option A / B / C scored on these budgets

| | Network | Memory | CPU / turn |
|--|---------|--------|------------|
| **A Firewall** | Goldfish ms; corpus RAG is another MCP (chunky). Two servers if they obey. | \(S\) small; library elsewhere | Shape ms; RAG MCP extra |
| **B Two ports** | Shape ms; hydrate 2 RTT; flush batched/offline; Snap 1–3 RTT locators | Two namespaces; cabinet hundreds of MiB; library GiB **not** in \(S\) | Shape ms; Snap ms–tens of ms; **no** generate |
| **C Fuse** | Every turn looks like Graphiti/GraphRAG (parallel Bolt + prompt) | One hot heap = library | PPR/Leiden/LLM — **seconds+** |

MN-REQ-00 (wall-clock + tokens) **selects B** when one Neo4j process is a given: keep the millisecond goldfish, pay Bolt only for bounded hydrate and rare flush, pay library ANN only on **miss**, never pay map-reduce on `pin_map`.

