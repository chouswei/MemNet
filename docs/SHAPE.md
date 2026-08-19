# Product shape (from the problem)

**Status:** identity SSOT (0.8 teach). British English.  
**Not** the same word as **Recall Shape** \(\tilde{X}\) (the `pin_map` neighbourhood of a session). This file is the **form of the product**. Operator math stays in [`grammar/math-skeleton.md`](grammar/math-skeleton.md). Versions stay in [`ROADMAP-0.5.md`](ROADMAP-0.5.md). Mission contract: **MN-REQ-00** in `sysml-models/models/requirements.sysml`.

---

## The problem

An LLM call is **goldfish**. The next call does not remember the last graph, the last constraint, or which file the worker already settled.

Three common substitutes fail the mission:

| Substitute | What goes wrong |
|------------|-----------------|
| **Chat as memory** | Transcript is not a named graph. Peers cannot re-read the same facts. Tokens grow with every dump. Chat is never SSOT. |
| **Dump the whole session \(S\)** | Burns the token budget MN-REQ-00 exists to save. The model still has to pick what matters. |
| **Search the corpus (RAG / GraphRAG)** | That haystack is **documents**, not **this mission’s working facts**. Retrieval may help the host; it does not replace a session. |

The job is **system, programme, software, firmware, hardware, and documentation** work: live `TSK` / `USR` / `MOD`, a few technical documents as **atoms and locators** (not PDF bytes), handoff between agents. Aims: save **wall-clock** and **tokens**, keep **factual accuracy**.

So MemNet must sit **between** LLM call pipelines and data search — not as the notepad, and not as the library.

---

## Necessary form

From that problem, the product **must** be this shape:

1. **Named session \(S\)** — a labelled property graph (GQL **node**/vertex, **edge**/relationship, **property**). The handle you pass is the **session id** (plus anchors / write scope). Peers **re-`pin_map`**. They do not receive a graph dump in chat.

2. **Goldfish read** — each turn the agent sees only a bounded **Recall Shape** \(\tilde{X} = \mathrm{Recall}(q)\), not raw \(S\). Cue first (id / kind / locator / keyword / `find`), then neighbourhood. Skip is valid when the seed is empty.

3. **Sparse write** — \(\mathrm{Commit}(\Delta)\) gated mutate. Same **GQL (openCypher-shaped)** alphabet as the read. **Write = display**: the live pin map is a shaped subgraph emit, not a second language.

4. **Two budgets, two jobs**
   - **Session Shape** — compress \(S\) for the next LLM call (`max_rows` \(M\), hop \(k\)).
   - **Host Snap** — optional corpus → **locators** only. MUST NOT Snap-on-session (no ANN / `rag_query` of \(S\)).

5. **Durable cabinet behind, not instead** — an AgensGraph-class store may hydrate/flush \(S\). It is not the handoff handle and not the default teach surface. **0.7** proved live AgensGraph hydrate/flush; the server is not vendored. An optional Neo4j client sits on the same seam and is **not** live-claimed. Fake-alone is not a durable claim.

6. **This repo** — engine + generic `memnet-mcp` only. Novel-writer stays dropped. Transport: in-process first (single agent); **Multitask** uses TCP serve or streamable-http so workers share one \(S\).

That is the shape. Versions **fill** it. They do **not** invent a different product.

---

## Two uses of “shape”

| Name | Object | Operator |
|------|--------|----------|
| **Product shape** (this file) | What MemNet **is** | — |
| **Recall Shape** \(\tilde{X}\) | Bounded neighbourhood of \(S\) | \(\mathrm{Recall}(q)\) → `pin_map` |
| **Snap** (not Shape) | Host corpus topics → locators | Host search **outside** `MemNetSystem` |

Do not call MemNet a “shaped RAG” or a “shaped Cypher proxy”.

---

## What this shape forbids

- Chat or a pasted transcript as SSOT
- `rag_query` / embeddings / GraphRAG **as** MemNet
- HostSearch nested under `MemNetSystem`
- Layer / Tier A as accept or teach
- LLM talking to the durable store directly
- Claiming goldfish from `pin_map` alone when there is no ego — use bounded `find` then `pin_map`
- Claiming the live cabinet on Fake alone

---

## People (0.8 teach; 1.0 claim)

**0.8.0** is this shape **taught for people** in-repo: this file, GQL-only playbook, application-note contract, Multitask honesty (RSV + Path-B ingest shipped; full ACL modes still to-be).

**1.0.0** is **0.5 + 0.6 + 0.7 + 0.8** claimed — the shape is mature for people: one GQL dialect, goldfish `pin_map`, gated mutate, cue-then-shape (including find when there is no ego), optional **proven** cabinet so \(S\) can outlive a process. Not GraphRAG. Not cabinet-only. Map: [`ROADMAP-0.5.md`](ROADMAP-0.5.md). **Honest install:** PyPI `memnet-llm` is still **0.4.6**; do not claim `pip install memnet-llm` yields 0.8 until that release is published. Use this repo until then.

---

## SysML (application vs product)

The shape **applies** to SysML work; it is not a SysML clone.

| Kind | Path | Role |
|------|------|------|
| **Application note** | [`application-notes/llm-sysml-v2-modeling.md`](application-notes/llm-sysml-v2-modeling.md) | Use MemNet as session memory while modelling **someone else's** SysML v2 tree (atoms + locators; `.sysml` stays structural SSOT) |
| **Application note (Multitask)** | [`application-notes/llm-system-dev-multitask.md`](application-notes/llm-system-dev-multitask.md) | Same two-store cut in `modelbasedPrj-*`: shared session goldfish vs product `sysml-models/` |
| **Product model** | [`../sysml-models/`](../sysml-models/) | MemNet **itself** (MN-REQ-00…13). Not an application note |

Do **not** import `MemNetRequirements` into a downstream load tree. User pack: `sysml-memnet-documentation` / `sysml-memnet-cache`.
