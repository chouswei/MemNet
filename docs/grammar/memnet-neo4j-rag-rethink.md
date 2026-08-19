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
