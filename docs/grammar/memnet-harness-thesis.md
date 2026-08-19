# Thesis: MemNet as the memory plane of an agent harness

**Status:** design thesis — **not** a measured claim, **not** a SemVer gate, **not** an amendment of [`../SHAPE.md`](../SHAPE.md).  
**Audience:** product developers. British English.  
**Product:** MemNet 0.9.0 (Hatch); PyPI `memnet-llm` still 0.4.6; live Neo4j unclaimed.

This note states a **thesis**, then argues it from in-repo doctrine and from public harness / memory papers and codebases. It does not invent SWE-Bench numbers, train an information bottleneck, or ship HostSearch.

**Companion proposals (not this file):** two Neo4j ports, catalog Snap, Path-B Absorb — [`memnet-neo4j-rag-rethink.md`](memnet-neo4j-rag-rethink.md). Math: [`math-skeleton.md`](math-skeleton.md). Wire: [`gql-wire-profile.md`](gql-wire-profile.md). Steal/reject: [`memnet-host-search-nest.md`](memnet-host-search-nest.md).

**Homograph.** In this repository, *harness* also means the **golden line-codec tests** (`memnet-grammar-design.md`). That is **not** the subject here. Below, **harness** = agent scaffolding around a model (loop, tools, context packing, eval).

---

## Abstract

An LLM call is goldfish. The industry answered **parametric ignorance of a library** with RAG (retrieve then generate). Coding and system agents instead fail because the **next call lacks this mission’s named facts**. Those are two haystacks.

**Thesis.** MemNet is not a RAG engine, not a graph database, and not the full agent. It is the **memory plane of a harness**: a named session graph \(S\) that the scaffold **re-Shapes** (`pin_map`) and **sparsely Commits** (mutate), with **Absorb** only as session-to-session join, and a durable cabinet **behind** the session id.

If that plane is missing, harnesses fall back to chat dumps, linear trajectories, or corpus retrieve — all of which violate MN-REQ-00 (wall-clock and tokens) on **agentic** turns.

---

## 1. Problem

[`../SHAPE.md`](../SHAPE.md) states the failure modes:

| Substitute | What goes wrong |
|------------|-----------------|
| Chat as memory | Not a named graph; peers cannot re-read; tokens grow |
| Dump session \(S\) | Burns the window; the model still picks |
| RAG / GraphRAG | Haystack is **documents**, not **this mission** |

The work is system, programme, software, firmware, hardware, and documentation: live `TSK` / `USR` / `MOD`, locators not PDF bytes, handoff between agents. The contract is MN-REQ-00: save **time** and **tokens**, keep **facts**.

Lewis et al. (2020) solved a different problem: freeze, private files, dear fine-tune, paste-the-corpus. GraphRAG, LightRAG, Graphiti, Neo4j GraphQL `generate` are **that** problem with a fancier retrieve. They still end in **generate**. Detail: [`rag-relative-algorithms.md`](rag-relative-algorithms.md).

---

## 2. Thesis statement (three claims)

**C1. Placement.** MemNet sits **in the harness**, between LLM call pipelines and data search — as MCP tools (`pin_map`, mutate, `find`, `import_slice`) plus an in-process engine. The outer harness (Cursor, OpenHands, SWE-agent, Inspect, Claude Code) owns bash, sandbox, eval, and the completion API.

**C2. Substrate.** The memory medium is a **labelled property graph** with codebook cues (id / kind / locator / keyword), serial Recall, clamp \(M\approx 50\), **Write = display** (shaped GQL, not tabular `RETURN`). It is not embeddings of \(S\), not Letta core-memory **prose blocks**, not an OpenHands condenser of the transcript.

**C3. Composition.** RAG **Snaps** a library to locators. Absorb **joins** a member **slice** into the lead session (Path-B, shipped). Hydrate/flush **persists** one named \(S\). Mixing those verbs is the fuse this product forbids (option C in the rethink).

Falsifiers (any one kills the thesis as product doctrine):

- `rag_query` / ANN of mission \(S\) as goldfish
- LLM↔Bolt as the miss path
- Absorb used for host chunks or cabinet ego
- Chat or the cabinet URI as handoff handle

---

## 3. Related work: what “harness” means in papers and code

Huang et al. (*Harness the Memory*, 2026) define an **agent harness** as scaffolding that decomposes tasks, manages context across sessions, and evaluates outputs — often a **larger lever than the backbone**. They treat **memory as a substrate family inside that harness**, and find **no single substrate dominates**: broad retrieve helps dialogue QA; extra retrieved rows **hurt** sequential decisions because attention leaves the live observation. That is MN-REQ-00 on agentic turns, stated empirically by others.

| System | What the harness is | What it uses as “memory” | Cut vs MemNet |
|--------|---------------------|---------------------------|---------------|
| **SWE-agent** (Yang et al., NeurIPS 2024) | Agent–computer interface; linear trajectory | Full history in the prompt | No named \(S\); goldfish = dump |
| **mini-SWE-agent** | ~bash-only loop | Linear messages = trajectory | Same |
| **OpenHands** / SDK (Wang et al., 2024–2025) | Event-sourced loop, Docker, MCP tools | Event history + **condenser** | Transcript compression ≠ `pin_map` |
| **Inspect AI** (UK AISI) | **Eval** harness (ReAct, deep agents, bridge) | Task state / transcripts | Eval, not mission SSOT |
| **HiAgent** (ACL 2025) | Env loop + subgoal chunks | Replace finished subgoal with a summary | Steal: live `TSK_*`, settle. Reject: prompt-only, no graph |
| **Letta / MemGPT** | Tool-edited tiers | Core = prose in the prompt; archival = vectors | Steal: working vs cabinet. Reject: core blocks as Shape; archival **inside** `memnet-mcp` |
| **Graphiti / GraphRAG** | Often Neo4j | Hybrid search + generate / communities | Library Snap cousins; not goldfish |
| **This repo (as-is)** | Cursor / MCP caller | `memnet-llm` + `memnet-mcp` | Engine + tools only; novel-writer dropped |

Confucius Code Agent (2025) and OpenHands leaderboard commentary repeat the same moral as Huang: **orchestration and memory handling close gaps** that a stronger backbone alone does not. None of those scaffolds ship a **GQL session id** as the peer handoff.

**Repo homograph (do not confuse).** `tests/grammar/` golden **harness** = codec fixtures. Product teach is GQL (`ADR-001`).

---

## 4. Form of the memory plane

Two operators: \(\mathrm{Recall}(q)\), \(\mathrm{Commit}(\Delta)\).

**Recall.** Seed from a codebook token; empty seed → **skip**; else \(k\)-hop under one \(M\). `find` is the same operator with a different seed rule. ISO GQL *can* `MATCH` a neighbourhood; **showing** a bounded named neighbourhood as the agent read is MemNet `pin_map` (Write = display), not full Cypher as goldfish.

**Commit id rules** (not three goldfish APIs): mutate (`NEW`); ingest (locator from artefact); Absorb (member slice + `keep` / `reject` / `remint`).

**Unknown pin.** `find`, then skip — not “most relevant pin.” Optional catalog of `session=` ids (Snap), then **look** (`pin_map`) or **join** (Absorb a slice).

**Over \(M\).** Do not raise goldfish \(M\). Narrow the ego; `view=shell`; partition into more sessions. Path-B import payload \(M\times|\mathrm{anchors}|\) is **not** the goldfish budget.

Verbs in full: [`memnet-neo4j-rag-rethink.md`](memnet-neo4j-rag-rethink.md).

---

## 5. Where the plane plugs into a harness

```text
  completion API, bash, sandbox, eval     ← outer harness (not this repo)
                    |
                    | MCP / CLI  (session id, anchors, write scope)
                    v
              memnet-llm  /  memnet-mcp
              Recall Shape  +  Commit Δ
                    |
         +----------+------------------+
         |                             |
    host Snap (RAG)              cabinet Bolt
    locators only                hydrate / flush
    outside MemNetSystem         one DurableSyncOwner
```

**Single agent.** In-process MCP is allowed (one graph per process).

**Multitask.** Isolated in-process graphs are **not** a shared mission. TCP serve or streamable-http; **one** mission session (Path A: re-`pin_map`, no Absorb). Path B: separate member session, Absorb a slice. Chat is never SSOT ([`../multi-agent-sessions.md`](../multi-agent-sessions.md)).

The security note already says spoofing `llm_id` in-process is a **trust-the-harness** problem. That sentence is the same cut: MemNet enforces graph ACL **when enabled**; the outer harness still owns process identity.

---

## 6. Neo4j and RAG (so the harness does not bypass)

As-is, `memnet-llm[neo4j]` is cabinet only. Honest, and operator-hostile: GraphRAG already lives on Neo4j, so the LLM leaves the harness memory plane for Browser.

**Proposal (not shipped):** one Neo4j **process**, two **namespaces** (cabinet `_memnet_tag` vs library corpus). Library port emits locators, never `generate`. Catalog Snap may return `session=` ids. Join remains Absorb, not RAG. Live Neo4j still unclaimed. Estimates: rethink note (design budgets, not SLAs).

---

## 7. What this thesis does not claim

- That MemNet wins SWE-Bench without an outer harness.
- That a graph substrate always beats condensers (Huang: **regime-dependent**; graphs can win QA and lose acting if you retrieve too broadly — hence \(M\)).
- That HostSearch, Peak_L, or live Neo4j are shipped.
- That “harness” in `docs/grammar/examples/` is this architecture.

---

## 8. Consequences if accepted

1. Teach MemNet as **harness memory plane**, not “graph RAG.”
2. Keep HostSearch **outside** `MemNetSystem`; locators through mutate.
3. Prefer Path A; Absorb only for member slices.
4. Do not hold **1.0** for catalog Snap or a second Neo4j database name.
5. User-pack skills (`mcp-memnet`) remain how a **specific** harness (Cursor) calls the plane.

---

## References (selected)

Doctrine (this repo): [`../SHAPE.md`](../SHAPE.md), [`math-skeleton.md`](math-skeleton.md), [`gql-wire-profile.md`](gql-wire-profile.md), [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md), [`memnet-neo4j-rag-rethink.md`](memnet-neo4j-rag-rethink.md), MN-REQ-00 in `sysml-models/models/requirements.sysml`.

1. Lewis et al., *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*, 2020.
2. Yang et al., *SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering*, NeurIPS 2024. [arXiv:2405.15793](https://arxiv.org/abs/2405.15793).
3. Wang et al., OpenDevin / OpenHands line, 2024; OpenHands Software Agent SDK, 2025. [arXiv:2511.03690](https://arxiv.org/abs/2511.03690).
4. Hu et al., *HiAgent: Hierarchical Working Memory Management…*, ACL 2025. [HiAgent2024/HiAgent](https://github.com/HiAgent2024/HiAgent).
5. Packer et al., *MemGPT* (Letta), 2023–.
6. Huang et al., *Harness the Memory: A Holistic Evaluation of Memory Substrates in Memory Agents*, 2026. [arXiv:2608.15008](https://arxiv.org/abs/2608.15008).
7. UK AISI, *Inspect* — LLM evaluation framework. [inspect.aisi.org.uk](https://inspect.aisi.org.uk/).
8. Edge et al., Microsoft GraphRAG; Zep Graphiti `search` / `rrf` (see [`rag-relative-algorithms.md`](rag-relative-algorithms.md)).

---

## Leftover

- Optional one-sentence pointer from [`../SHAPE.md`](../SHAPE.md) §1 **if** this thesis is accepted (“MemNet is the harness memory plane”).
- Do not close live Neo4j or HostSearch from this file.
- Do not rename the grammar **golden harness** — keep the homograph documented.
