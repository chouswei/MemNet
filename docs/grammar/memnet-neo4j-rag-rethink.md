# Rethink: RAG, `memnet-llm`, and the Neo4j cabinet

**Status:** option **B namespaces** shipped as extra **0.16** (untagged; package stays 0.9.0). Host Snap (`RagHostHook.implemented=true`) remains **0.17**. Does **not** amend [`../SHAPE.md`](../SHAPE.md) beyond the 0.16 locator port.  
**Decision:** **B** (two Neo4j ports) **+ D** (catalog `session=` ids; join by **Absorb**). **Reject C.** Keep **A** as as-is teach until B is accepted.  
**Audience:** product developers. British English.

**Pressure:** operators ask how RAG works *between* `memnet-llm` and Neo4j. As-is: it doesn’t (cabinet = hydrate/flush). That job cut is right; as an **operator** architecture it fails — GraphRAG / Graphiti / FTS already run on Neo4j, so they bypass MemNet (LLM↔Bolt).

**Locked:** MN-REQ-00 (wall-clock **and** tokens); Recall/Commit ([`math-skeleton.md`](math-skeleton.md)); GQL `pin_map` / mutate (ADR-001); HostSearch **outside** `MemNetSystem`; locators not chunks; no `rag_query` / `pin_map.generate`; no ANN of mission \(S\); Absorb = Path-B `ImportAbsorb` only; one `DurableSyncOwner` for cabinet; live Neo4j claimed (0.14).

| Pointer | Role |
|---------|------|
| [`rag-relative-algorithms.md`](rag-relative-algorithms.md) | Why RAG was hot; retrieve from source |
| [`neo4j-buffer.md`](neo4j-buffer.md) | As-is MemNet ↔ Neo4j seam |
| [`memnet-host-search-nest.md`](memnet-host-search-nest.md) | Host Snap steal/reject |
| [`memnet-session-strata.md`](memnet-session-strata.md) | Sessions as strata (not Layer); catalog then one Shape |
| [`../multi-agent-sessions.md`](../multi-agent-sessions.md) | One mission SSOT; Path A / B |
| [`../../sysml-models/outputs/session-import-case-study.md`](../../sysml-models/outputs/session-import-case-study.md) | Absorb: slice → lead; `keep` / `reject` / `remint` |

---

## Verbs (do not rename)

Two operators only: \(\mathrm{Recall}(q)\) / \(\mathrm{Commit}(\Delta)\). These names are **id rules or hops**, not extra operators.

| Verb | Haystack | Does | Does not |
|------|----------|------|----------|
| **Shape** | Mission (or named) session \(S\) | Cue → `find` / `pin_map` neighbourhood, clamp \(M\approx 50\) | Rank pins; generate |
| **mutate** | Current \(S\) | Sparse goldfish \(\Delta\) (`NEW`) | Import another session |
| **ingest** | Artefact | Deterministic locator ids | Host ANN |
| **Snap** | **Library** (corpus) | Host retrieve → `session=` / `path=` / `document_id=` / `qname=` | Generate; Absorb |
| **Absorb** | **Other session** | Path-B `import_slice`: member `WorkingMemorySlice` → lead + `id_policy` | Host RAG; goldfish Δ; cabinet; whole \(S\) |
| **hydrate / flush** | Durable copy of **one** named \(S\) | Ego MERGE/MATCH under `HydrateBudget` | RAG; Absorb |

Colloquial “the session absorbed that note” = **mutate**. Product **Absorb** is shipped Path-B only. Host Snap **MUST NOT** grow a second absorb leaf.

**Two “library” words.** Neo4j **library namespace** = corpus KG/FTS/vector (option B). MemNet **library session** \(S_{\mathrm{lib}}\) = a Shape-sized session of pins/locators. Absorb joins **sessions**. Snap reads the **corpus** (or a directory of `session=` ids). Do not Absorb Neo4j library nodes as a member slice.

---

## Two problems (do not fuse)

RAG: weights lack the operator’s **library**. MemNet: the next LLM call lacks the **mission graph**. Same symptom (too much text); **two haystacks**. Detail: [`rag-relative-algorithms.md`](rag-relative-algorithms.md).

| | RAG (Snap) | MemNet (Shape) |
|--|------------|----------------|
| **Pick** | Top‑\(k\) passages (BM25 / ANN / RRF) then **generate** | Named seed then \(k\)-hop; **skip** if empty; **no** generate on the wire |
| **Empty** | Often still generate / fallback retriever | Skip |
| **Over budget** | Smaller \(k\), rerank, GraphRAG reports | Narrow ego; `view=shell`; **more sessions**; do not raise goldfish \(M\) |

GraphRAG-class stacks are fancier retrieve for the **first** problem. Sessions already **join** without RAG (`ImportAbsorb`). Composition: catalog → **look** (`pin_map`) or **join** (Absorb a **slice**) — never retrieve-then-generate on \(S\).

---

## What is wrong with the as-is design

Two haystacks, three stores; Neo4j wired only to the cabinet:

| Store | Haystack | As-is Neo4j |
|-------|----------|-------------|
| Corpus | RAG | Unused on this seam |
| Live \(S\) | MemNet | Only via flush |
| Durable \(S\) | still MemNet | Ego MERGE/MATCH |

Live and durable \(S\) are **one** haystack, two persistence forms. Four failures:

1. **Naming.** Cabinet hydrate is bounded graph **read** of durable \(S\), not RAG. Operators paste Graphiti onto `_memnet_tag`.
2. **Single-server gravity.** Forbidding every retrieve on that process moves the LLM off MemNet (Bolt Browser).
3. **Mute miss path.** Skip-on-empty is right; the next hop has no port, so people use Browser.
4. **Join unused.** `import_slice` already Absorb. RAG talk skipped it and invented “rank pins.”

Rethink **“Neo4j = cabinet only”** and **“RAG will pick the pins.”** Do not rethink “RAG solved session memory.”

---

## Options (do not mix)

| Option | Idea | Keep | Cost |
|--------|------|------|------|
| **A Firewall** (as-is) | RAG never uses the MemNet Bolt URL. Sibling MCP. | Honest “no RAG hop.” | Operators fuse on one URI; extra **2–8k** chunk tokens. |
| **B Two ports** (propose) | One Neo4j **process**; cabinet vs library **namespaces**. Library port → locators only. | Jobs unfused. LLM never Bolt. | Namespace law. HostSearch Later. |
| **C Fuse** (reject) | RRF / PPR / Leiden / `generate` inside `pin_map` or hydrate. | Product-shaped like Graphiti. | MN-REQ-00 / 13.1. Session = library. |
| **D Catalog + Absorb** (propose, with B) | Snap MAY emit `session=`. **Join** = Absorb a **slice**. **Look** = `pin_map` that session. | Absorb shipped. No ANN of mission \(S\). | Do not Absorb whole \(S\) / \(N\) sessions. Path A skips Absorb. |

**C** is Graphiti-as-MemNet. **D is not C:** catalog Snap picks a **named graph**; Absorb copies a **slice** into the lead; ranking pins inside mission \(S\) or stuffing \(N\) sessions is C.

Do not keep **A** as the long-term operator story unless they run a second graph server for the corpus.

---

## B — two ports on one Neo4j process

```text
LLM  <-->  memnet-llm  (GQL pin_map / mutate)
              |
     cabinet port              library port
     DurableSyncOwner          RagHostHook (locators, fail-open)
     hydrate / flush           not a DurableStoreAdapter
              v                         v
     MEMNET_NEO4J_DATABASE     MEMNET_NEO4J_LIBRARY_DATABASE
     _memnet_tag (durable S)   corpus KG / FTS / vector
```

Same Bolt URL **may** be used. Factory still errors two *cabinet* URLs (Agens + Neo4j).

**Namespace.** Two named databases (`MEMNET_NEO4J_DATABASE` default `neo4j` vs `MEMNET_NEO4J_LIBRARY_DATABASE`). Skip the library bind when the library name is unset. Community single-db: do **not** put both jobs in one database (that **is C**).

| Port | Writes | Reads |
|------|--------|-------|
| Cabinet | `_memnet_tag` under `HydrateBudget` | Ego `{id}` `[*0..depth]` `LIMIT` — never FTS/ANN |
| Library | **None** from MemNet | FTS / vector / 1-hop → **locators** only |

Hydrate: ego → `LIMIT` → upsert into a **new** session. **Zero** LLM tokens. Hydrate ≠ Absorb. Vector index on cabinet labels **MUST NOT** be goldfish (Snap-on-session).

**Steal retrieve, reject generate** (algorithms: [`rag-relative-algorithms.md`](rag-relative-algorithms.md)). Graphiti `node_distance` is **one hop** of `RELATES_TO` to `center_node_uuid`, not MemNet depth-2 Recall.

| Relative | Steal | Reject |
|----------|-------|--------|
| GraphRAG local | Neighbour tables as locators | **generate**; global map-reduce |
| GraphRAG global | Nothing on the goldfish turn | Reports as `pin_map` |
| LightRAG local | 1-hop entity **ids** | Keyword LLM; chunk JSON as Shape |
| Graphiti | Centre uuid → `pin_map` **anchor**; `group_ids` ≈ session | RRF (\(k=1\)); 1-hop **as** Recall; `add_episode` onto `_memnet_tag` |
| HippoRAG 2 | Passage **ids** | PPR/ANN **on** \(S\); chunk bodies |
| RAGFlow / mem0 | Paths / memory **ids** | Score stuffing through MemNet |
| Neo4j GraphQL | Retrieve of corpus types | Resolver `generate` |

---

## D — catalog Snap, join Absorb

The engine already holds many sessions. Multitask still uses **one** mission \(S\) (Path **A**: shared id, **no** Absorb). Extra sessions are library / directory / member graphs — not a second SSOT.

```text
cue in mission S → find / pin_map
  hit    → Shape → mutate Δ
  miss   → skip
           OR catalog (directory pin_map / host Snap) → session= locators
              look:  pin_map that session (SSOT unchanged)
              join:  export slice → ImportGuard? → ImportAbsorb → pin_map mission S
```

Host locators into the **current** session = **mutate**. Absorb **only** from another session’s `WorkingMemorySlice`. Fail-open: Snap miss **MUST NOT** fail `pin_map`. Skip Snap when grep / ingest / pins suffice. Workers **MUST NOT** open a library session unless the parent assigned it. No `SessionMerge*`.

| Session | Role | Snap? | Absorb? |
|---------|------|-------|---------|
| **Mission** \(S\) | SSOT; Path A | No (Shape only) | **Lead** |
| **Library** \(S_{\mathrm{lib}}\) | Topic graph, Shape-sized | MAY pick `session=` | **Member** if Path B assigned |
| **Directory** \(S_{\mathrm{dir}}\) | Pins that *are* `session=` ids (\(M=50\) **ids**) | Catalog | No |
| **Member** | Worker / other session | No | **Yes** — shipped Path B |

**Unknown pin.** `find` in mission \(S\). Empty → directory / host catalog. Then look or Absorb a **slice**. Still skip if nothing hits. Do not invent a pin; do not rank mission pins.

**Larger than 50 goldfish rows.** Do not raise \(M\). Split into more sessions. Absorb payload may be \(M\times|\mathrm{anchors}|\) — that is **import**, not goldfish. Absorbing whole \(S\) or \(N\) sessions is C.

`id_policy`: `keep` = MERGE-by-id (not append); `reject` = no lead mutate; `remint` = NEW ids, retarget edges. Micro `merge=true` is **not** Path B.

The LLM still sees **one** goldfish Shape (**≲ 4k** tokens typical): never Browser, GraphQL `generate`, cabinet `{memory, score}`, chunk bodies, or \(N\) `pin_map` dumps.

---

## SHAPE delta (only if accepted)

§4–5 stay Shape vs Snap and cabinet-behind. Add: Snap **MAY** share the Neo4j **process** iff the library namespace is disjoint and **MUST NOT** read `_memnet_tag` as corpus. Snap **MAY** emit `session=`; join is Path-B Absorb of a slice; goldfish is `pin_map` of one named \(S\); Path A skips Absorb. Still forbid: `rag_query` as MemNet; GraphRAG as MemNet; LLM↔store; ranking pins in mission \(S\); calling Snap or hydrate Absorb.

MN-REQ-13.1 already allows `RagHostHook` outside `MemNetSystem`. This note **binds** that hook to a namespaced Neo4j — it does not nest or ship HostSearch.

---

## MUST / MUST NOT (proposal)

**MUST**

- Two ports on one Bolt URL (named database preferred; else `_memnet_tag` vs corpus labels).
- Host emit locators only; next goldfish = `pin_map` of **one** named session.
- Join sessions with Absorb of a **slice**; prefer Path A.
- Partition a fat library into **more sessions**, not a larger goldfish \(M\).
- Fail-open on Snap miss and ImportGuard transport failure.
- One `DurableSyncOwner`; flush on settle / process death, not every `pin_map`.
- Goldfish **≲ 4k** tokens typical; **≳ 8k** from one `pin_map` = alarm.
- One mission session under Multitask.

**MUST NOT**

- Rank/generate inside `pin_map` or hydrate (C).
- ANN/FTS of mission \(S\) or cabinet labels as goldfish.
- Call Snap, mutate Δ, or hydrate **Absorb**.
- Absorb whole \(S\), \(N\) sessions, or Neo4j library nodes.
- A second absorb leaf for RAG hits.
- RRF / paste \(N\) sessions into one completion.
- Dual-write the same node as mission pin and corpus chunk.
- Teach LLM↔Neo4j as the miss path; treat the **4 MiB** frame as a token budget.
- Hold **1.0** for HostSearch (Later).

---

## Estimates (order of magnitude, not a benchmark)

These are **design budgets** so option A/B/C/D can be compared. They are **not** measured SLAs and **not** a live-Neo4j claim. Caps from the engine: `pin_map` default depth 2 / `max_rows` 50 (`DEFAULT_QUERY_*`); `HydrateBudget` 50 nodes / 100 edges / depth 2; TCP/IPC frame **4 MiB** (`MEMNET_SERVE_MAX_FRAME_BYTES`); session store cap `MEMNET_MAX_ROWS` default 5000. Role size: tens of MiB typical, hundreds still in role, gigabytes = library/cabinet ([`memnet-host-search-nest.md`](memnet-host-search-nest.md)).

**RTT** = one request/response on that hop. **Local** = same host or LAN under 1 ms. **WAN** = 20–80 ms class. **LLM** = one chat completion (0.5–30 s, dominates everything else).

### Network (latency / bytes on the wire)

| Hop | Bytes / turn (typical) | RTT count | Wall-clock (local) | Wall-clock (WAN) |
|-----|------------------------|-----------|--------------------|------------------|
| **Shape** `pin_map` in-process | 10–100 KiB shaped GQL (~50 rows × 0.2–2 KiB) | 0 (same process) | **0.1–5 ms** CPU, no NIC | n/a |
| **Shape** via `memnet serve` / MCP | Same payload; frame ≤ 4 MiB | 1 | **1–10 ms** | **20–100 ms** |
| **Cabinet hydrate** | Two Cypher reads; ≤50 nodes + ≤100 edges ≈ 20–200 KiB | **2** Bolt | **1–20 ms** | **40–200 ms** |
| **Cabinet flush** | One `MERGE` **per** node then per edge (`session.run` auto-commit) | **≤150** Bolt | **50–500 ms** local (chatty) | **seconds** on WAN — avoid remote flush every turn |
| **Library Snap (B, locators only)** | 1–3 Cypher or ANN queries; emit a few locators (bytes, not chunks) | 1–3 Bolt | **2–30 ms** (+ ANN) | **50–250 ms** |
| **Absorb** `import_slice` (Path-B, shipped) | Bounded `WorkingMemorySlice` (may be \(M\times|\mathrm{anchors}|\)) | 1 in-process / serve | **ms–tens of ms** | **20–100 ms** if via serve |
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
| **Absorb** `import_slice` | Copy bounded slice + `id_policy` | **ms**; optional guard LLM is **off** by default. |
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
| **Absorb slice (Path-B)** | **0** extra LLM on the default path | **0** | 0 | Guard LLM (#63) is **optional** and off unless keyed; still not RAG generate. |
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
| **D Catalog + Absorb** (with B) | Same as B; Snap returns a few `session=` ids; Absorb is in-process slice | Many small \(S_{\mathrm{lib}}\); mission \(S\) stays tens of MiB | Catalog rank on **ids**; Absorb \(O(\mathrm{slice})\) | **1–4k** one `pin_map`; Absorb **0** LLM unless optional guard |

MN-REQ-00 (wall-clock + tokens) **selects B+D** when one Neo4j process is a given and the engine already has many sessions: keep the millisecond goldfish, **join sessions with shipped Absorb**, pay Bolt only for bounded hydrate and rare flush, pay library ANN only on **miss** and only to pick a **session id**, never pay map-reduce on `pin_map`. One completion, Shape-sized context. RAG still solves the **library** problem; MemNet still solves the **session** problem; Absorb solves **session-to-session**, not corpus-to-prompt.

---

## Leftover if accepted

1. Spec `MEMNET_NEO4J_LIBRARY_DATABASE` (or label law) in the Neo4j extra — docs first; adapter Later with HostSearch. Same URL as `MEMNET_NEO4J_URL` is allowed; **different database name** (or labels).
2. SysML: `RagHostHook` backend `Neo4jLibraryAdapter` `implemented=false`; emit type `session=` beside path locators. **Do not** add an absorb leaf under HostSearch.
3. Playbook: Absorb vs Snap vs hydrate vs mutate (Path A skip; Path B slice only). Absorb is already shipped — this note only places it next to catalog Snap.
4. Do not close live Neo4j cabinet leftover from this note.

Until accepted, as-is teaching stays: no RAG hop on the **cabinet** seam; host Snap unshipped; Absorb stays Path-B only; operators who fuse on one graph do so **outside** MemNet.
