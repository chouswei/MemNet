# Math skeleton (Recall / Commit)

**Status:** product math SSOT for 0.5 — modelled; **no engine cut**.  
**Audience:** product developers. **British English.**  
**Below this file:** host-search research [#77](https://github.com/chouswei/MemNet/issues/77) and [`memnet-host-search-nest.md`](memnet-host-search-nest.md). Citations stay on #77.  
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

**Reconstruct** \(\tilde{X}\): \(k\)-hop ego from the seed, diameter \(\le k\), \(|\tilde{X}| \le M\) (`max_rows`). Hide recycled rows. Emit the **same** shaped GQL subgraph family as mutate — not a tabular `RETURN`.

`pin_map` and leftover [#73](https://github.com/chouswei/MemNet/issues/73) `BoundedMatchFind` are the **same** Recall; seed rule differs. Honesty: `PinMapShapedRead.implemented=true`; `BoundedMatchFind.implemented=false` until #73. \(\mathrm{Peak}_L\) is deferred (same LIMIT honesty; not a third operator).

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

Goldfish talks only to **relevant slices** of \(S\), never to \(S\) whole. [#77](https://github.com/chouswei/MemNet/issues/77) note 27.

```text
topics on S --(pin egos)--> seed ids --Recall/Shape--> slices X̃
    --(LLM)--> Δ  --Commit--> S
```

| Leg | Object | Operator | Honesty |
|-----|--------|----------|---------|
| **In** | Bounded neighbourhoods \(\tilde{X}\) | \(\mathrm{Recall}(q)\) / `pin_map` | Caps + hide recycled |
| **Out** | New shaped subgraph \(\Delta\) | \(\mathrm{Commit}(\Delta)\) / `add`/`update` | Same GQL family as pin_map emit |

**Pin the topics, then fetch slices.** Topic tokens are already on the graph (`KYWD`, kind, `TSK`, locator, id). Cue → pin those nodes as egos → Shape each neighbourhood. Several topics ⇒ serial `pin_map` calls under the same row budget — **not** a fused ranker (no RRF of slices). Empty topic cue ⇒ skip / grep / host Snap.

**Writeback is Commit, not Absorb.** Colloquial “the session absorbs the new slice” = MutateGate in the *current* session. Product **absorb** stays Path-B only (`ImportAbsorb` + member `WorkingMemorySlice` + `id_policy`). Goldfish \(\Delta\) MUST NOT travel `WorkingMemorySliceExport` / ImportGuard unless this turn *is* Multitask Path-B.

### Named maths (names only)

| Name | In MemNet |
|------|-----------|
| **Information bottleneck** | \(\tilde{X}\) compresses \(S\) given \(q\). Skip = empty extra retrieve. |
| **Ego \(k\)-hop** | Optimal evidence subgraph is NP-hard; ego from a seed is the polynomial stand-in. |
| **Cardinality / diameter** | \(M\) and \(k\) are the budget. Metric is **hops**, not cosine. |
| **Snap vs Shape** | Host Snap compresses the corpus; Recall Shape compresses \(S\). Do not embed \(S\). |
| **Slice I/O** | Goldfish in = \(\tilde{X}\); out = \(\Delta\) via Commit. Pin topics, then fetch slices. |
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
