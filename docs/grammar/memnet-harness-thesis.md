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

**Token law (MN-REQ-00).** Use **very few LLM tokens** to (1) **fetch** facts and (2) **maintain** \(S\).

**Relevant** here means the emit **co-responds to the input cue** \(q\) — a codebook token (id / kind / locator / keyword). \(\tilde{X}=\mathrm{Recall}(q)\) is that token’s bounded neighbourhood (or **skip** if the seed is empty). Same \(q\) → same Shape. It is **not** RAG “nearest passages to a sentence,” and not a scored pick from a pool.

Fetch: Shape of \(q\), clamp \(M\approx 50\). Maintain: sparse \(\Delta\), settle, Absorb a **slice**. Do not dump \(S\), echo \(\tilde{X}\), or stuff chunks. Typical goldfish prompt **≲ 4k** LLM tokens; **≳ 8k** from one `pin_map` is alarm. The 4 MiB frame is **not** a token budget. Cabinet Bolt uses **zero** LLM tokens.

**Many small calls, not one stuffed call.** A Shape-sized context is cheap enough that the harness can **re-`pin_map` every turn** (goldfish). That favours **Flash-class** models (fast, small context, low $/token) over a single frontier completion stuffed with RAG or a dump of \(S\). GraphRAG global (tens–hundreds of completions × fat prompts) is the opposite spend. Wall-clock in MN-REQ-00 is this loop: **ms** Shape + **one** Flash-class generate per turn, not map-reduce.

If that plane is missing, harnesses fall back to chat dumps, linear trajectories, or corpus retrieve — all of which violate this law on **agentic** turns.

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

**C2. Substrate.** The memory medium is a **labelled property graph**. Cue \(q\) is a codebook **token**. Emit \(\tilde{X}\) **co-responds** to \(q\) (serial Recall, \(M\approx 50\), Write = display). **Few LLM tokens in, sparse Δ out** — so the harness can afford **many** goldfish completions. **Flash-class** (fast, small-context) models are the intended consumer; a stuffed frontier call is the anti-pattern. Not embeddings of \(S\); not Letta prose blocks; not a condenser of the transcript.

**C3. Composition.** RAG **Snaps** a library to locators. Absorb **joins** a member **slice** into the lead session (Path-B, shipped). Hydrate/flush **persists** one named \(S\). Mixing those verbs is the fuse this product forbids (option C in the rethink).

Falsifiers (any one kills the thesis as product doctrine):

- `rag_query` / ANN of mission \(S\) as goldfish
- LLM↔Bolt as the miss path
- Absorb used for host chunks or cabinet ego
- Chat or the cabinet URI as handoff handle
- Dump \(S\), echo \(\tilde{X}\), or stuff library chunks to “maintain memory”
- Design goldfish as **one** fat completion (GraphRAG global / paste the library) instead of **N** Shape-sized Flash-class calls
- Stuff `pin_map` into an ever-growing `messages` list (no goldfish caller)
- Put env blobs (test logs, screenshots) on \(S\) and call that Shape

---

## 3. Related work: what “harness” means in papers and code

Huang et al. (*Harness the Memory*, 2026) define an **agent harness** as scaffolding that decomposes tasks, manages context across sessions, and evaluates outputs — often a **larger lever than the backbone**. They treat **memory as a substrate family inside that harness**, and find **no single substrate dominates**: broad retrieve helps dialogue QA; extra retrieved rows **hurt** sequential decisions because attention leaves the live observation. That is MN-REQ-00 on agentic turns, stated empirically by others.

| System | What the harness is | What it uses as “memory” | Cut vs MemNet |
|--------|---------------------|---------------------------|---------------|
| **SWE-agent** (Yang et al., NeurIPS 2024) | Agent–computer interface; linear trajectory | Full history, optionally **elided** | No named \(S\); goldfish = dump |
| **mini-SWE-agent** | ~bash-only loop | `self.messages` grows every `query()` | Same |
| **OpenHands** / SDK (Wang et al., 2024–2025) | Event-sourced loop, Docker, MCP tools | Event `View` + **condenser** (LLM summary) | Transcript compression ≠ `pin_map` |
| **Inspect AI** (UK AISI) | **Eval** harness (ReAct, MCP, checkpoint) | Chat list + **compaction** / `trim_messages` | Eval, not mission SSOT |
| **HiAgent** (ACL 2025) | Paper cousin; GitHub is AgentBoard eval | Subgoal replace (paper); repo is SAS scores | Steal: live `TSK_*`, settle. Reject: prompt-only |
| **Letta / MemGPT** | Now `letta-code` harness + MemFS | Prose **blocks** + `$MEMORY_DIR` files | Steal: working vs cabinet. Reject: blocks as Shape |
| **Graphiti / GraphRAG** | Often Neo4j | Hybrid search + generate / communities | Library Snap cousins; not goldfish |
| **This repo (as-is)** | Cursor / MCP caller | `memnet-llm` + `memnet-mcp` | Engine + tools only; novel-writer dropped |

**Not this review.** `parts/memnet-mcp/` is MemNet’s **generic MCP**, not an outer harness. The GitHub harnesses below own bash, sandbox, eval, and the completion API.

### 3.1 GitHub harness codebases (fetched)

As-is on GitHub. None of these ships a GQL session id as the peer handoff. Memory is the **transcript**, a **summary of the transcript**, or **prose files in the prompt**.

**SWE-agent** ([`SWE-agent/SWE-agent`](https://github.com/SWE-agent/SWE-agent)). `AbstractAgent.messages` chains `history_processors` over `self.history` (`sweagent/agent/agents.py`). Classic processor: `LastNObservations` in `sweagent/agent/history_processors.py` — keep last \(n\) env observations (paper \(n=5\)), replace the rest with `Old environment output: (n lines omitted)`. Comments now say large windows often make this **optional**, and that elision **breaks prompt cache** unless `polling` batches the rewrite. Other processors: closed file-windows, regex strip, Anthropic cache marks. That is **lossy trajectory edit**, not \(\mathrm{Recall}(q)\). Same \(q\) next turn does not re-Shape a named neighbourhood; omitted lines are gone.

**mini-SWE-agent** ([`SWE-agent/mini-swe-agent`](https://github.com/SWE-agent/mini-swe-agent)). `DefaultAgent.query()` always calls `self.model.query(self.messages)` then `add_messages` (`src/minisweagent/agents/default.py`). Cost / step / wall-clock **stop** the loop; they do not bound the prompt to a codebook ego. Memory **is** the message list.

**OpenHands** — two repos. [`OpenHands/OpenHands`](https://github.com/OpenHands/OpenHands) is now the **TypeScript UI** (`src/` React). The Python condenser lives in [`OpenHands/software-agent-sdk`](https://github.com/OpenHands/software-agent-sdk): `openhands/sdk/context/condenser/`. `CondenserBase.condense(view)` returns a smaller `View` **or** a `Condensation` the agent must emit instead of an action. `LLMSummarizingCondenser` (default `max_size=80`, `keep_first=4`) fires on event count, token cap, or explicit request; it **LLM-summarises forgotten events** (`summarizing_prompt.j2`) and inserts the summary. Token pressure is **HARD** (next generate would fail); event-count is **SOFT**. That spends an extra completion to shrink **chat**, not to Shape \(S\). Steal: separate summariser LLM from the actor. Reject: fuse that summariser into `pin_map`.

**Inspect AI** ([`UKGovernmentBEIS/inspect_ai`](https://github.com/UKGovernmentBEIS/inspect_ai)). `react()` is a ReAct `while` with tools, MCP, and a checkpointer (`src/inspect_ai/agent/_react.py`). Overflow: `compaction` first, then `truncation="auto"` → `trim_messages`. Trim (`src/inspect_ai/model/_trim.py`) keeps system + sample input, then a **ratio** of remaining conversation (default preserve \(0.7\)–\(0.8\)), repairing tool_call / tool_result pairs. `CompactionTrim` can also `clear_memory_content` on preserved turns. Checkpoint tracks `messages`, not a session graph. Inspect **can** call MemNet as just another MCP tool; it does not **be** MemNet.

**Letta** — landing page [`letta-ai/letta`](https://github.com/letta-ai/letta) points at [`letta-ai/letta-code`](https://github.com/letta-ai/letta-code); V1 Python server is the `archive` branch. Live harness: default blocks `persona` / `human` from `.mdx` (`src/agent/memory.ts`); `memory` tool edits `$MEMORY_DIR` (`str_replace` / `insert` / files under `system/` always in the prompt — `src/tools/descriptions/Memory.md`). MemFS is a backend capability (`memory-runtime.ts`). That is **editable prose + a filesystem**, not labelled property graph Shape. Steal: working files vs remote MemFS. Reject: archival search **inside** `memnet-mcp`.

**HiAgent** ([`HiAgent2024/HiAgent`](https://github.com/HiAgent2024/HiAgent)). Public tree is **AgentBoard** eval (`agentboard/`, `evaluate_model.sh`), not a reusable memory library. The **paper** (subgoal replace) is the cousin; do not cite this repo as shipped hierarchical \(S\).

**Pattern.** Every harness still **packs a chat list** for the next generate. When the list grows, they **elide**, **trim a ratio**, or **summarise with another LLM**. MemNet’s law is the opposite: do not grow the list as SSOT; **skip or Shape** from cue \(q\); sparse \(\Delta\). A condenser of omitted bash is not a pin map of `TSK_*` / `USR_*` / `MOD_*`.

### 3.2 Critical objections (harnesses *and* this thesis)

The §3.1 catalogue is true as **mechanism**. It is too neat as **verdict**. Steelman the other side; then say what still stands.

**1. Dump is not a 2024 fossil.** SWE-agent’s own comment on `LastNObservations`: SotA windows often make elision **optional**; elision **breaks prompt cache**. `DefaultHistoryProcessor` is identity. Coding agents **moved toward stuffing** once cache + 100k+ context paid. That is an empirical competitor to the Flash-class goldfish loop, not a confused substitute. If a cached 80k dump is cheaper in wall-clock and dollars than \(N\) Flash calls plus a fresh `pin_map` each turn, MN-REQ-00 can **favour dump**. The thesis has not priced cache-hit dump vs Shape+Flash. Until it does, “they violate the token law” is doctrine, not a measurement.

**2. Two channels, not one plane.** Last-\(n\) observations exist because **pytest logs are not a labelled graph**. \(M\approx 50\) GQL rows is not 50 lines of a failing test. A honest split: **mission names** (`TSK`/`USR`/`MOD`) belong on \(S\); **last env blob** stays in chat (or a condenser of *that* blob). If MemNet tries to eat bash, it becomes a worse condenser. If the thesis pretends one `pin_map` replaces both, SWE-agent is right to ignore it.

**3. The missing operator is Commit, not Recall.** OpenHands summarises **because the event stream was never atomised**. There is nothing to Shape if the actor did not \(\mathrm{Commit}(\Delta)\). Elide / trim / summarise are rational given **write failure**. Citing them as proof that graphs beat condensers skips the adoption problem: no GitHub harness in §3.1 **calls** `pin_map` and **drops** old maps. MCP JSON stuffed into the same `messages` list saves **zero** tokens. C1 (placement *in* the harness) is an **unshipped caller**, not an observed architecture.

**4. Cue \(q\) is the hard step.** “Co-responds to \(q\)” assumes a codebook token. SWE-agent’s actual cue is **instance template + latest observation** — a sentence, not `TSK_*`. `find` then `pin_map` on a keyword is still retrieve; the difference is **deterministic neighbourhood vs scored chunks**, not “not retrieve.” Wrong \(q\) plus \(M=50\) is Huang’s failure mode: extra rows **hurt acting**. Huang is evidence *for* clamping \(M\), and a **falsifier** if agents pin contains-parents or a stale `TSK`.

**5. Named handle ≠ shaped emit.** OpenHands has `ConversationState` / event ids; Inspect checkpoints `messages`; Letta has `agentId` + MemFS. They **do** pass a name. What they lack is **Write = display**: the next generate is a **shaped subgraph**, not the conversation object. Saying “none ship a session id” is a category error. Say: none ship **shaped emit as the goldfish read**.

**6. Letta is closer than the table says.** `system/` files always in the prompt, edit tools, working vs remote MemFS — that *is* a working set with a cabinet. Alphabet is markdown, join is `str_replace`, not gated GQL. Substrate uniqueness is **overclaimed**; the steal (working vs archival, explicit edit) is **underclaimed**. If MemNet cannot beat a small named file in the system prompt on MN-REQ-00, the graph is ceremony.

**7. Inspect must keep a transcript.** Eval scoring and compaction science **require** a reconstructable chat. Replacing SSOT with \(S\) without dual-logging breaks the unit of analysis. Inspect *should* treat MemNet as a tool, not as the log. Do not sell “chat is never SSOT” into an eval harness without a second tape.

**8. Condenser spend can be the right spend.** `LLMSummarizingCondenser` HARD-on-tokens is the same 8k alarm with a different operator. When events are unstructured, summarise is the only compression. Criterion: **if a named ego exists, Shape; if not, do not invent nodes — summarise or skip.** Fusing summarise into `pin_map` stays forbidden. Pretending summarise is always a law violation is false.

**What still stands.** Chat-as-SSOT still fails **peer re-read** and **mission names**. RAG still solves a **library** haystack. None of these repos implement goldfish **replace history with \(\tilde{X}\)**. The thesis is a **caller contract** the outer harness has not signed. Adoption, cache pricing, and the env-blob channel are leftover; they are not solved by GQL wire.

Confucius Code Agent (2025) and OpenHands leaderboard commentary repeat the same moral as Huang: **orchestration and memory handling close gaps** that a stronger backbone alone does not. None of those scaffolds ship **shaped emit** (`pin_map`) as the peer goldfish read.

**Repo homograph (do not confuse).** `tests/grammar/` golden **harness** = codec fixtures. Product teach is GQL (`ADR-001`).

---

## 4. Form of the memory plane

Two operators: \(\mathrm{Recall}(q)\), \(\mathrm{Commit}(\Delta)\).

**Recall.** Seed from a codebook token; empty seed → **skip**; else \(k\)-hop under one \(M\). `find` is the same operator with a different seed rule. ISO GQL *can* `MATCH` a neighbourhood; **showing** a bounded named neighbourhood as the agent read is MemNet `pin_map` (Write = display), not full Cypher as goldfish.

**Commit id rules** (not three goldfish APIs): mutate (`NEW`); ingest (locator from artefact); Absorb (member slice + `keep` / `reject` / `remint`).

**Unknown pin.** \(q\) is not an id → `find` (seed of \(q\)) then `pin_map`, or **skip**. Do not invent a node so the emit “looks relevant.” Optional catalog of `session=` ids (Snap), then **look** or **join** (Absorb a slice).

**Over \(M\).** Do not raise goldfish \(M\). Narrow the ego; `view=shell`; partition into more **sessions** (strata — [`memnet-session-strata.md`](memnet-session-strata.md)). Path-B import payload \(M\times|\mathrm{anchors}|\) is **not** the goldfish budget.

| Leg | Few LLM tokens; high correspondence to \(q\) | Spend instead |
|-----|-----------------------------------------------|---------------|
| **Fetch** | \(\tilde{X}=\mathrm{Recall}(q)\): one `pin_map` (optional `view=shell`); skip if seed empty | Cosine top‑\(k\); \(N\) maps; dump \(S\) |
| **Maintain** | Sparse mutate of what \(q\)’s work changed; Absorb a **slice** on Path B | Echo \(\tilde{X}\); merge sessions; generate-on-retrieve |

Verbs in full: [`memnet-neo4j-rag-rethink.md`](memnet-neo4j-rag-rethink.md). Token budgets: same file, estimates section.

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
- That MemNet **requires** a named Flash SKU. Flash-class = small context, low latency, many turns. A larger model MAY still run; the plane does not grow the prompt to match it.
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
2. Yang et al., *SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering*, NeurIPS 2024. [arXiv:2405.15793](https://arxiv.org/abs/2405.15793). Code: [`SWE-agent/SWE-agent`](https://github.com/SWE-agent/SWE-agent) `history_processors.py`; [`SWE-agent/mini-swe-agent`](https://github.com/SWE-agent/mini-swe-agent) `agents/default.py`.
3. Wang et al., OpenDevin / OpenHands line, 2024; OpenHands Software Agent SDK, 2025. [arXiv:2511.03690](https://arxiv.org/abs/2511.03690). UI: [`OpenHands/OpenHands`](https://github.com/OpenHands/OpenHands). Condenser: [`OpenHands/software-agent-sdk`](https://github.com/OpenHands/software-agent-sdk) `sdk/context/condenser/`.
4. Hu et al., *HiAgent: Hierarchical Working Memory Management…*, ACL 2025. GitHub [`HiAgent2024/HiAgent`](https://github.com/HiAgent2024/HiAgent) is AgentBoard eval, not the memory runtime.
5. Packer et al., *MemGPT* (Letta), 2023–. Live code: [`letta-ai/letta-code`](https://github.com/letta-ai/letta-code); [`letta-ai/letta`](https://github.com/letta-ai/letta) is the landing page (`archive` = V1 server).
6. Huang et al., *Harness the Memory: A Holistic Evaluation of Memory Substrates in Memory Agents*, 2026. [arXiv:2608.15008](https://arxiv.org/abs/2608.15008).
7. UK AISI, *Inspect* — LLM evaluation framework. [inspect.aisi.org.uk](https://inspect.aisi.org.uk/). Code: [`UKGovernmentBEIS/inspect_ai`](https://github.com/UKGovernmentBEIS/inspect_ai) `_react.py`, `_trim.py`.
8. Edge et al., Microsoft GraphRAG; Zep Graphiti `search` / `rrf` (see [`rag-relative-algorithms.md`](rag-relative-algorithms.md)).

---

## Leftover

- Optional one-sentence pointer from [`../SHAPE.md`](../SHAPE.md) §1 **if** this thesis is accepted (“MemNet is the harness memory plane”).
- Do not close live Neo4j or HostSearch from this file.
- Do not rename the grammar **golden harness** — keep the homograph documented.
- Price **prompt-cache dump** vs Shape+Flash (MN-REQ-00). Unmeasured.
- Goldfish **caller**: drop old `pin_map` rows from the chat list. Unshipped in §3.1 harnesses.
- Keep **env blob** (test logs, screenshots) out of \(S\); do not condenser-replace it with GQL theatre.
