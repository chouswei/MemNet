# Math skeleton (Recall / Commit)

**Status:** 0.5 operator math SSOT. Version map [`../ROADMAP.md`](../ROADMAP.md). Product shape [`../SHAPE.md`](../SHAPE.md). **1.0** = 0.5–0.8 claimed. Extra **0.17** = Host Snap locators (`RagHostHook` outside `MemNetSystem`). Extra **0.18** = Peak_L last-resort cue. Later = N-server / hosted cabinet.
**Audience:** product developers. **British English.**  
**Model:** `RecallCommit` in `sysml-models/models/deploy.sysml` (MN-REQ-13.1).  
**Below this file:** host-search research [#77](https://github.com/chouswei/MemNet/issues/77) and [`memnet-host-search-nest.md`](../extras/memnet-host-search-nest.md). Notes 22–28 live on `master` ([#84](https://github.com/chouswei/MemNet/pull/84)). Strata / model Snap: [`memnet-session-strata.md`](../extras/memnet-session-strata.md).

Do **not** train an IB, run a Steiner solver, or ANN-index the session because a paper named a cousin.

---

## Objects

| Symbol | Meaning |
|--------|---------|
| \(S\) | One **named session**: labelled property graph (GQL **node**/vertex, **edge**/relationship, **property**). Rate cap \(R\) (rows / bytes). Handle = session id. |
| \(q\) | Discrete **codebook token**: kind / primary label \(\cup\) properties (locators as properties) \(\cup\) keyword \(\cup\) optional nickname `id` if already set. NOT store-key id, elementId/handle, prose/embedding sentence. Topology (\(\mathrm{Peak}_L\)) is last-resort on codebook miss (0.18), not empty \(q\). |
| \(\tilde{X}\) | **Recall Shape** — bounded neighbourhood of **this** \(S\) given \(q\). |
| \(\Delta\) | Sparse mutate batch (same GQL family as the emit). |
| \(M\) | Goldfish row cap (`max_rows`, default **50**). **One** \(M\) per Shape, not \(M\times|Q|\). |
| \(k\) | Hop diameter of the ego walk (typical interior \(\approx 2\)). Metric is **hops**, not cosine. |
| \(L\) | Hard LIMIT on `find` / seed cardinality (\(|Q|\le L\)). |

**Relevant** means the emit **co-responds to** \(q\): same \(q\) on the same \(S\) → same Shape. It is not “nearest passages to a sentence.” Goldfish query SHALL be codebook tokens. Empty token / empty \(q\) ⇒ **session outline** (0.11 census of \(S\): kinds + LIMIT exemplars). leftover empty-seed skip is leftover, not TARGET.

**Two haystacks.** Library / corpus is **Snap** (host). Mission working memory is **Shape** (this file). Mixing them is the fuse the product forbids.

---

## Operators (domains)

Goldfish APIs are **two**: \(\mathrm{Recall}(q)\) and \(\mathrm{Commit}(\Delta)\). Other verbs have **other domains**. RSV is a **lease** under Commit, not a third API. Host search stays **outside** `MemNetSystem`.

| Verb | Domain | Maps | Goldfish? |
|------|--------|------|-----------|
| **Recall** | One \(S\) | \(q \mapsto \tilde{X}\) (`pin_map`; `find` is seed-only then Shape) | **Yes** (read) |
| **Commit** | One \(S\) | \(\Delta \mapsto S'\) (`mutate` / ingest into current session; leftover `add`/`update` named leftover) | **Yes** (write) |
| **Absorb** | Member **slice** \(\to\) lead | Path-B `import_slice` + `id_policy` keep / reject / remint | **Join**, not goldfish writeback |
| **Host Snap** | Corpus / library | Retrieve \(\to\) locators; Commit locators into some \(S\) | **Outside** engine |
| **hydrate / flush** | Cabinet \(\leftrightarrow\) one named \(S\) | Persist / restore | **Zero** LLM tokens; not Recall |

Colloquial “the session absorbed that note” = **Commit**. Product **Absorb** is Path-B only. Hydrate ≠ Absorb. **MUST NOT** Absorb whole \(S\), host chunks, or cabinet ego.

`mutate` / `ingest` / `absorb` are **id-mint rules** on Commit’s family, not three goldfish verbs.

| Rule | Id |
|------|----|
| Default mutate | Client `NEW` \(\rightarrow\) engine id |
| Ingest | Deterministic locator id from the artefact (`PinMapIngest_*`) |
| Absorb | Member `WorkingMemorySlice` + `id_policy` |

---

## Token law (three budgets)

MN-REQ-00: few **LLM tokens** to fetch and to maintain. Rows, frames, and tokens are not the same knob.

| Budget | Typical | Owns |
|--------|---------|------|
| Goldfish **rows** \(M\) | \(\approx 50\) | Shape (`PinMapComposer`) |
| Goldfish **prompt** | \(\lesssim 4\,\mathrm{k}\) tokens; \(\gtrsim 8\,\mathrm{k}\) from one `pin_map` is alarm | Outer harness + emit |
| Serve **frame** | 4 MiB | Transport — **not** a token budget |
| Cabinet Bolt | **0** LLM tokens | hydrate / flush |

Do **not** raise \(M\) because \(S\) grew. Partition into more sessions ([`memnet-session-strata.md`](../extras/memnet-session-strata.md)). The 0.10 leftover is the **caller**: drop old `pin_map` rows from `messages[]`; stuffing JSON saves zero.

---

## Recall(\(q\))

**Seed** (then reconstruct). Topology cue is explicit, not “no ego.”

\[
\mathrm{seed}(q,S)=\begin{cases}
\mathrm{MATCH}_{L}(q,S) & q \text{ is labels + properties + keyword (hard LIMIT } L\text{); } Q \text{ = relative nodes}\\
\{q\} & \text{leftover 0.9: optional nickname / by\_id copied id (not TARGET; not a store key)}\\
\mathrm{Peak}_{L}(S) & q \text{ is a non-empty codebook miss (MATCH}_L\text{ empty; 0.18 last resort)}
\end{cases}
\]

Empty seed \(\Rightarrow\) **skip** (do not invent a node). Empty \(q\) \(\Rightarrow\) **session outline**, not \(\mathrm{Peak}_L\). \(Q\) elements **are** the walk roots. Prefer MATCH_L on live `TSK` kind before topology. \(\mathrm{Peak}_L\) is not default goldfish.

**Peak (0.18 extra, last resort, inside one \(S\)).** Raw degree is a footgun on ingest trees: `contains` parents (`PKG` / `MOD`) look like peaks. Topology cue on codebook miss: \(\rho^\*(v)=\) incident edges **except** hierarchical `contains` (hide recycled); then \(\mathrm{Peak}_L\). **MUST NOT** assign every node to a peak. **MUST NOT** use \(\mathrm{Peak}_L\) instead of splitting sessions when the nest is model-wide ([`memnet-session-strata.md`](../extras/memnet-session-strata.md)). **MUST NOT** be default goldfish.

**Reconstruct** \(\tilde{X}\): \(k\)-hop from seed set \(Q\) (\(|Q|\le L\)), diameter \(\le k\), \(|\tilde{X}| \le M\) — **one** \(M\), not \(M\times|Q|\). Hide recycled. Emit the **same** shaped GQL family as mutate — not tabular `RETURN`.

Engine leftover: `PinMapComposer.compose` / `context_pack` still take `anchor` plus optional `anchors` (0.9 by_id / require_anchor). TARGET ShapeWalk walks from \(Q\). Path-B `export_working_memory_slice` may budget \(M\times|\mathrm{anchors}|\) — that is **import payload**, not goldfish.

`pin_map` and `BoundedMatchFind` are the **same** Recall (RelativeSeed then ShapeWalk). Honesty: `PinMapShapedRead.implemented=true`; `BoundedMatchFind.implemented=true` (`query find` / MCP `find` — MATCH_L seed elements, hard LIMIT; then ShapeWalk from \(Q\)). leftover 0.9 “copy find id then `pin_map(anchor=id)`” is leftover, not TARGET. \(\mathrm{Peak}_L\) is not a third operator.

**In-session work already on \(S\).** TARGET: RelativeSeed MATCH_L then ShapeWalk. leftover `read_list` / copied id / `--anchor` named leftover. Isolated `TSK` \(\Rightarrow\) LAW + that element only; attach edges via Commit. **Switch task:** settle the old `TSK` (`delete_on_settle`); next ego from MATCH_L — **not** \(\mathrm{Peak}_L\).

---

## Compressions (homographs)

Same symptom (haystack too large). Different owners. [#77](https://github.com/chouswei/MemNet/issues/77) note 26.

| Name | Haystack | Mechanism | Owner |
|------|----------|-----------|--------|
| **Shape** | One session \(S\) | \(\mathrm{Recall}(q)\to\tilde{X}\) (\(k\), \(M\), fan-out clamp, hide recycled). Order of \(\tilde{X}\) is a function of observables (kind + payload), not hid / nickname `id` / CREATE order. | `PinMapShapedRead` |
| **Host Snap** | Corpus / library | Retrieve → locators (ANN / BM25 / corpus GraphRAG *on the library*) | `RagHostHook` **outside** `MemNetSystem` (0.17; skip valid) |
| **Model Snap** (design, 0.12) | One SysML (or design) **model** | \( \mathrm{Snap}(\mathrm{model})\to(S_{\mathrm{cat}},S_1,\ldots,S_k) \) | Session stack; **not** one session per file |

The LLM **never** sees raw \(S\). Goldfish = Shape. Host Snap MAY feed **Commit** (locators), then Shape. Model Snap **partitions** a load tree so each interior stays Shape-sized. **MUST NOT** Snap-on-session (no embeddings / ANN of \(S\)). **MUST NOT** call `pin_map` a Snap.

`view=shell` / `interior` is **grain inside one \(S\)**, not a second session and not a SysML `view def`.

---

## One \(S\) per generate

Goldfish talks to **one** session at a time.

```text
live TSK (+ ≤L−1 topic pins) --Recall/Shape, one M--> X̃
    --(LLM)--> sparse Δ  --Commit--> that S
```

Over \(M\) after narrowing ego and `view=shell`: **mint** \(S_{i+1}\), do not raise \(M\). Catalog of `session=` ids is itself a small session (or Host Snap of locators). Look = `pin_map` **that** id. Join = Absorb a **slice**. Path A (shared mission id, re-`pin_map`) is the cheap stratum. Path B and library-pin sessions are the expensive ones.

**MUST NOT** mint a session per `TSK` (settle in \(S\)). **MUST NOT** mint a session per source file as a habit (`MOD_*` stay nodes). **Exception:** model Snap interiors are partitions of **one** model.

| Leg | Object | Operator | Honesty |
|-----|--------|----------|---------|
| **In** | One neighbourhood \(\tilde{X}\) | \(\mathrm{Recall}(Q)\) / `pin_map` | Caps + hide recycled; **one** \(M\) |
| **Out** | Sparse shaped \(\Delta\) | \(\mathrm{Commit}(\Delta)\) | NEW/SET only; do not echo \(\tilde{X}\) |

**Writeback is Commit, not Absorb.** Goldfish \(\Delta\) MUST NOT travel `WorkingMemorySliceExport` / ImportGuard unless this turn *is* Path-B.

**Optimisation (note 28).** Serial \(N\) `pin_map` calls duplicate LAW (V5). Prefer one primary ego (unsettled `TSK_*`); at most one extra `view=shell` survey; seed set \(|Q|\le L\) under **one** \(M\); sparse \(\Delta\) only. Steal grain, not embeddings: LightRAG dual-level *as view=*; PyG NeighborLoader *as seed batch*; Graphiti incremental write; HiAgent **replace** = settle. Reject RRF, GraphSAGE random sample, Letta rewrite of the core block, Path-B \(M\times|\mathrm{anchors}|\) as goldfish.

**Pin the topics, then fetch slices.** Empty topic cue \(\Rightarrow\) skip / grep / host Snap. Default **one** call on the live `TSK`.

Hierarchical reconstruct \(\neq\) Layer dialect. Layer / Tier A stay **rejected** on accept.

---

## Named maths (names only)

Orthodox = these as a **base to build from**. **All** examination and test is paradox (pytest, MN-VER).

| Name | In MemNet |
|------|-----------|
| **Information bottleneck** | \(\tilde{X}\) compresses \(S\) given \(q\). Skip = empty extra retrieve. |
| **Ego \(k\)-hop** | Optimal evidence subgraph is NP-hard; ego from a seed is the polynomial stand-in. |
| **Cardinality / diameter** | \(M\) and \(k\) are the row budget. Metric is **hops**. |
| **Shape vs Snap** | Host Snap compresses the corpus; Recall Shape compresses **one** \(S\). Model Snap partitions a model into sessions. Do not embed \(S\). |
| **Slice I/O** | Goldfish in = \(\tilde{X}\); out = sparse \(\Delta\) via Commit. One \(M\); pin live `TSK` first. |
| **Strata** | Many \(S_i\); goldfish one; join Absorb a slice. Catalog is codebook of session ids. |
| **Local degree peak** (0.18 extra, last) | Typed residual local max of \(\rho^\*\) **inside one \(S\)**. Not raw `contains`-tree degree; not a nest fix. Not default goldfish. |

Do **not** treat Hilbert IR / QQL / ZX-on-Cypher as GQL semantics.

---

## MUST NOT

- `rag_query`, embeddings, PPR, RRF, GST/Steiner, ANN on the session (Snap-on-session).
- Goldfish writeback via `ImportAbsorb` (that verb is Path-B join only).
- Dump \(S\); fuse several topic slices or several sessions with RRF / cosine.
- Goldfish budget \(M\times|Q|\) (Path-B import); echo \(\tilde{X}\) through mutate; raise \(M\) instead of minting \(S_{i+1}\).
- Density-peak **cluster assignment**, Leiden from peaks, or global top-\(k\) degree as goldfish.
- \(\mathrm{Peak}_L\) as default ego or as the SysML nest encoding.
- New `HostSearchBridge` leaves, HIT rows, `RagDecision` envelopes.
- Dual-teach GraphQL / LangChain / HiGram / Layer as agent wire.
- Free `MATCH`/`RETURN` as goldfish (find is RelativeSeed MATCH_L; then ShapeWalk from \(Q\), not a copied id).
- Absorb whole \(S\); Absorb Neo4j library nodes; hydrate as Absorb.
- A literature pile in this file (that stays on #77).

---

## Related

| Path | Role |
|------|------|
| [`gql-wire-profile.md`](gql-wire-profile.md) | Shaped GQL wire; `pin_map` vs find honesty |
| [`memnet-session-strata.md`](../extras/memnet-session-strata.md) | Many sessions; model Snap; not Layer |
| [`memnet-host-search-nest.md`](../extras/memnet-host-search-nest.md) | Application nest **below** this math |
| [`../../sysml-models/models/deploy.sysml`](../../sysml-models/models/deploy.sysml) | `RecallCommit` nest |
| [#77](https://github.com/chouswei/MemNet/issues/77) | Research notes (not product SSOT) |
| [#73](https://github.com/chouswei/MemNet/issues/73) | Bounded MATCH find (shipped seed-only) |
