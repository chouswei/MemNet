# Math skeleton (Recall / Commit)

**Status:** product math SSOT for 0.5 — modelled; **no engine cut**.  
**Audience:** product developers. **British English.**  
**Below this file:** host-search research [#77](https://github.com/chouswei/MemNet/issues/77) and [`memnet-host-search-nest.md`](memnet-host-search-nest.md). Citations stay on #77.  
**Model:** `RecallCommit` in `sysml-models/models/deploy.sysml` (MN-REQ-13.1).

Do **not** train an IB, run a Steiner solver, or ANN-index the session because a paper did.

---

## Session and cue

Session \(S\) is a labelled property graph (NODE | EDGE) with rate cap \(R\) (rows / bytes).

Cue \(q\) is a **discrete codebook token**: \(\mathrm{id} \cup \mathrm{kind} \cup \mathrm{locator} \cup \mathrm{keyword}\), plus an optional **topology** token (local degree peak; deferred, [#77](https://github.com/chouswei/MemNet/issues/77) note 23).

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

**Peak (deferred, names only).** Let \(\rho(v)=\) degree of \(v\) (incident edges; isolates \(\rho=0\)). A **strict local maximum** is \(\rho(v)>\rho(u)\) for every neighbour \(u\). Relative height \(r(v)=\rho(v)/(1+\max_{u\in N(v)}\rho(u))\) ranks peaks when several exist. \(\mathrm{Peak}_{L}\) returns at most \(L\) such ids (hide recycled). Regular / plateau graphs \(\Rightarrow\) empty \(\Rightarrow\) skip. Then the same \(k\)-hop reconstruct as any other seed. **MUST NOT** assign every node to a peak (that is clustering / GraphRAG). Fan-out clamp on reconstruct stays (a star centre is a peak).

**Reconstruct** \(\tilde{X}\): \(k\)-hop ego from the seed, diameter \(\le k\), \(|\tilde{X}| \le M\) (`max_rows`). Hide recycled rows. Emit the **same** shaped GQL subgraph family as mutate — not a tabular `RETURN`.

`pin_map` and leftover [#73](https://github.com/chouswei/MemNet/issues/73) `BoundedMatchFind` are the **same** Recall; seed rule differs. Honesty: `PinMapShapedRead.implemented=true`; `BoundedMatchFind.implemented=false` until #73.

### Named maths (names only)

| Name | In MemNet |
|------|-----------|
| **Information bottleneck** | \(\tilde{X}\) compresses \(S\) given \(q\). Skip = empty extra retrieve. |
| **Ego \(k\)-hop** | Optimal evidence subgraph is NP-hard; ego from a seed is the polynomial stand-in. |
| **Cardinality / diameter** | \(M\) and \(k\) are the budget. Metric is **hops**, not cosine. |
| **Local degree peak** (deferred) | Topology cue: relative local max of \(\rho\), then ego hop. Not PageRank, not ANN. |

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

- `rag_query`, embeddings, PPR, RRF, GST/Steiner, ANN on the session.
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
