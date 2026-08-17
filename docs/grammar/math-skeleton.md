# Math skeleton (Recall / Commit)

**Status:** product math SSOT for 0.5 — modelled; **no engine cut**.  
**Audience:** product developers. **British English.**  
**Below this file:** host-search research [#77](https://github.com/chouswei/MemNet/issues/77) and [`memnet-host-search-nest.md`](memnet-host-search-nest.md). Citations stay on #77. Notes 22–28 are on `master` ([#84](https://github.com/chouswei/MemNet/pull/84)).  
**Model:** `RecallCommit` in `sysml-models/models/deploy.sysml` (MN-REQ-13.1).

Do **not** train an IB, run a Steiner solver, or ANN-index the session because a paper did.

---

## Session and cue

Session \(S\) is a labelled property graph (NODE | EDGE) with rate cap \(R\) (rows / bytes).

Cue \(q\) is a **discrete codebook token**: \(\mathrm{id} \cup \mathrm{kind} \cup \mathrm{locator} \cup \mathrm{keyword}\). Topology (local degree peak) is a **last-resort** optional token — prefer live `TSK` / last mutate; if a peak test is used, count **typed residual** degree (strip `contains`), not raw edge count ([#77](https://github.com/chouswei/MemNet/issues/77) notes 23–25).

Two operators only: \(\mathrm{Recall}(q)\) and \(\mathrm{Commit}(\Delta)\). RSV is a **lease** under Commit, not a third API. Host search stays **outside** `MemNetSystem`.

---

## Recall(\(q\))

**Seed**

\[
\mathrm{seed}(q,S)=\begin{cases}
\{q\} & \text{if } q \text{ is already a node id}\\
\mathrm{MATCH}_{L}(q,S) & \text{if } q \text{ is kind / locator / keyword (hard LIMIT } L\text{)}\\
\mathrm{Peak}_{L}(S) & \text{if } q \text{ is the topology cue (deferred; note 23)}
\end{cases}
\]

Empty seed \(\Rightarrow\) **skip** (do not invent a node). Topology cue is **not** empty \(q\): it is an explicit codebook token.

**Peak (deferred, last resort).** Raw degree local-max is a **footgun** on ingest trees: `contains` parents (`PKG` / `MOD`) look like peaks (fan effect). Prefer: id → kind/keyword MATCH → unsettled `TSK_*` / RSV / last mutate. If a topology cue is still wanted: \(\rho^\*(v)=\) incident edges **except** hierarchical `contains` (hide recycled); then the same strict / relative local-max and \(\mathrm{Peak}_L\). **MUST NOT** assign every node to a peak. Fan-out clamp stays.

**Reconstruct** \(\tilde{X}\): \(k\)-hop from a **seed set** \(Q\) (\(|Q|\le L\)), diameter \(\le k\), \(|\tilde{X}| \le M\) (`max_rows`) — **one** \(M\), not \(M\times|Q|\). Hide recycled rows. Emit the **same** shaped GQL subgraph family as mutate — not a tabular `RETURN`.

Engine honesty: `PinMapComposer.compose` / `context_pack` today take **one** `anchor`. Multi-ego union-under-\(M\) is the same Recall leftover as [#73](https://github.com/chouswei/MemNet/issues/73) (do not claim shipped). Path-B `export_working_memory_slice` unions by id but budgets \(M\times|\mathrm{anchors}|\) — that is import payload, **not** goldfish.

`pin_map` and leftover `BoundedMatchFind` are the **same** Recall; seed rule differs. Honesty: `PinMapShapedRead.implemented=true`; `BoundedMatchFind.implemented=false` until #73. \(\mathrm{Peak}_L\) is deferred (same LIMIT honesty; not a third operator).

**In-session task already on \(S\).** The work is in MemNet; \(S\) is still too large to dump. That is Shape, not Snap. Seed from a known id, `read_list(tag=TSK, active_only)`, a hub `:owns`/`:next`, or leftover #73 — then `pin_map`. Isolated `TSK` ⇒ LAW + that node only; attach edges via Commit if pins exist but are unlinked. **Switch task:** settle the old `TSK` (`delete_on_settle`); next ego from hub / list / mint — **not** \(\mathrm{Peak}_L\).

---

## Two compressions (Snap vs Shape)

Same symptom (haystack too large for the LLM). Different owners. [#77](https://github.com/chouswei/MemNet/issues/77) note 26.

| Compression | Haystack | Mechanism | Owner |
|-------------|----------|-----------|--------|
| **Snap** | Corpus / library | Host retrieve → locators (ANN / BM25 / corpus GraphRAG *on the library*) | `RagHostHook` **outside** `MemNetSystem` |
| **Shape** | Session \(S\) | \(\mathrm{Recall}(q)\rightarrow\tilde{X}\) (`pin_map`, depth \(\approx 2\), \(M\approx 50\), fan-out clamp, hide recycled) | `PinMapShapedRead` |

The LLM **never** sees raw \(S\). Goldfish = Shape. Host Snap MAY feed Commit (locators), then Shape. **MUST NOT** Snap-on-session (no embeddings / ANN of \(S\)).

---

## Goldfish I/O (slice in, \(\Delta\) out)

Goldfish talks only to **relevant slices** of \(S\), never to \(S\) whole. [#77](https://github.com/chouswei/MemNet/issues/77) notes 27–28.

```text
live TSK (+ ≤L−1 topic pins) --Recall/Shape, one M--> slice X̃
    --(LLM)--> sparse Δ  --Commit--> S
```

| Leg | Object | Operator | Honesty |
|-----|--------|----------|---------|
| **In** | One neighbourhood \(\tilde{X}\) | \(\mathrm{Recall}(Q)\) / `pin_map` | Caps + hide recycled; **one** \(M\) |
| **Out** | Sparse shaped \(\Delta\) | \(\mathrm{Commit}(\Delta)\) / `add`/`update` | NEW/SET only; do not echo \(\tilde{X}\) |

**Optimisation (note 28).** Serial \(N\) `pin_map` calls duplicate LAW rows and overlapping neighbourhoods (MN-REQ-10.3). Prefer:

1. **One primary ego** — unsettled `TSK_*` (HiAgent current subgoal). Skip extra topic pins when that neighbourhood already covers them.
2. **Topic survey is shell** — at most one extra `pin_map(..., view=shell)` on a `KYWD`/kind hub (composer: ≤8 NODE / ≤12 EDGE). Then `view=interior` on the live `TSK`. Steal LightRAG dual-level *grain*; reject keyword embeddings / hybrid/mix.
3. **Seed set, not a ranker** — \(|Q|\le L\); union \(k\)-hop under **one** \(M\). Steal PyG `NeighborLoader` seed batch \(B\); keep deterministic fan-out clamp (not GraphSAGE random sample). MUST NOT copy Path-B \(M\times|\mathrm{anchors}|\). MUST NOT RRF slices (Graphiti `EDGE_HYBRID_SEARCH_NODE_DISTANCE` still hybrid-first).
4. **Sparse \(\Delta\)** — mint/update only what changed. Steal Graphiti `add_episode` *incremental* write; HiAgent **replace** finished subgoal (settle + `delete_on_settle`). Reject Letta rewrite of the whole core block; reject echoing the fetched slice (`id_exists`).

**Pin the topics, then fetch slices.** Topic tokens are already on the graph. Empty topic cue ⇒ skip / grep / host Snap. Engine today: one `anchor` per `pin_map` — default **one** call on the live `TSK`; a second shell call only when blocked.

**Writeback is Commit, not Absorb.** Colloquial “the session absorbs the new slice” = MutateGate in the *current* session. Product **absorb** stays Path-B only (`ImportAbsorb` + member `WorkingMemorySlice` + `id_policy`). Goldfish \(\Delta\) MUST NOT travel `WorkingMemorySliceExport` / ImportGuard unless this turn *is* Multitask Path-B.

### Named maths (names only)

| Name | In MemNet |
|------|-----------|
| **Information bottleneck** | \(\tilde{X}\) compresses \(S\) given \(q\). Skip = empty extra retrieve. |
| **Ego \(k\)-hop** | Optimal evidence subgraph is NP-hard; ego from a seed is the polynomial stand-in. |
| **Cardinality / diameter** | \(M\) and \(k\) are the budget. Metric is **hops**, not cosine. |
| **Snap vs Shape** | Host Snap compresses the corpus; Recall Shape compresses \(S\). Do not embed \(S\). |
| **Slice I/O** | Goldfish in = \(\tilde{X}\); out = sparse \(\Delta\) via Commit. One \(M\); pin live `TSK` first. |
| **Local degree peak** (deferred, last) | Typed residual local max of \(\rho^\*\), then ego hop. Not raw `contains`-tree degree. |

Hierarchical reconstruct \(\neq\) Layer dialect. Layer / Tier A stay REJECTED on accept (retire-from-wheel leftover; `layer.py` not deleted in this PR).

---

## Commit(\(\Delta\))

**One gate.** `mutate` / `ingest` / `absorb` are **id-mint rules**, not three product verbs.

| Rule | Id |
|------|----|
| Default mutate | Client `NEW` \(\rightarrow\) engine id |
| Ingest | Deterministic locator id from the artefact (`PinMapIngest_*`) |
| Absorb | Path-B only: member `WorkingMemorySlice` + `id_policy` keep / reject / remint |

Optional `ImportGuard` / `CheapLlmImportGuard` stay Path-B **soft**, fail-open. RSV nests under Commit / `SessionLifecycle`.

---

## MUST NOT

- `rag_query`, embeddings, PPR, RRF, GST/Steiner, ANN on the session (Snap-on-session).
- Goldfish writeback via `ImportAbsorb` / a second absorb-shaped leaf (that verb is Path-B only).
- Dumping \(S\); fusing several topic slices with RRF / cosine.
- Goldfish budget \(M\times|Q|\) (that is Path-B import); echoing \(\tilde{X}\) through mutate.
- Density-peak **cluster assignment**, Leiden from peaks, or global top-\(k\) degree as goldfish.
- New `HostSearchBridge` leaves, HIT rows, `RagDecision` envelopes.
- Dual-teach GraphQL / LangChain / HiGram as agent wire.
- Claim #73 shipped; free `MATCH`/`RETURN` as goldfish.
- A literature pile in this file (that stays on #77).

---

## Related

| Path | Role |
|------|------|
| [`gql-wire-profile.md`](gql-wire-profile.md) | Shaped GQL wire; `pin_map` vs find honesty |
| [`memnet-host-search-nest.md`](memnet-host-search-nest.md) | Application nest **below** this math |
| [`../../sysml-models/models/deploy.sysml`](../../sysml-models/models/deploy.sysml) | `RecallCommit` nest |
| [#77](https://github.com/chouswei/MemNet/issues/77) | Research notes (not product SSOT) |
| [#73](https://github.com/chouswei/MemNet/issues/73) | Bounded MATCH find leftover |
