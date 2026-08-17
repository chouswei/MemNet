# Recall / Commit — orthodox review and plan

**Status:** plan (docs). **MUST NOT** treat leftover engine as shipped.  
**Audience:** product developers. British English.  
**Math SSOT:** [`docs/grammar/math-skeleton.md`](../../docs/grammar/math-skeleton.md).  
**Playbook:** [`docs/LLM-GUIDE.md`](../../docs/LLM-GUIDE.md).  
**Research:** [#77](https://github.com/chouswei/MemNet/issues/77) (notes 22–28 on `master`).  
**Model honesty:** MN-VER-13-S01. **0.5 engine next notch remains live M2.5 cabinet** ([`docs/ROADMAP-0.5.md`](../../docs/ROADMAP-0.5.md)) — this plan is a leftover **goldfish** track, not a bid to replace that notch.

Orthodox = a theorem you can **build from**. Paradox = stress after the build; resolve by **scope**, not a third operator / `rag_query` / Snap-on-session.

---

## Design review (what is already erected)

| Orthodox (build from) | Erected in MemNet | As-is honesty |
|-----------------------|-------------------|---------------|
| Rate–distortion | `max_rows`, `depth`, `MEMNET_MAX_FANOUT`, hide recycled, LAW prepend | Shipped (`context_pack` / `PinMapComposer`) |
| Discrete codebook | id ∪ kind ∪ locator ∪ keyword; one primary GQL label | Shipped mutate + schema; leftover [#73](https://github.com/chouswei/MemNet/issues/73) find |
| Encoding specificity | Token must be written before it retrieves | Shipped: miss ≠ invent a node. Agent still mints cues via Commit |
| Ecphory (cue then reconstruct) | Recall = seed then Shape | Seed = known id (`pin_map`). Kind/keyword seed = #73 `implemented=false` |
| Polynomial \(k\)-hop (not GST) | Ego walk + fan-out clamp | Shipped; metric = hops (`cosineMetric=false`) |
| Empty retrieve | `emptySeedSkip` | Modelled skip; engine today errors `no_anchor` if pin_map has no ego — probe is `read_list` / known id |
| Same alphabet | Shaped GQL emit = mutate family | Shipped M2 |
| Incremental coding | Sparse Δ: `add`/`update`; `id_exists` on echo | Shipped strict mutate; playbook must not echo \(\tilde{X}\) |
| One working chunk | Live `TSK` as default ego; settle / `delete_on_settle` | Shipped recycle hide; playbook after [#84](https://github.com/chouswei/MemNet/pull/84) |
| Two rate budgets | Snap (host corpus) vs Shape (session) | Design-locked; `RagHostHook.implemented=false` |
| Path-B ≠ goldfish writeback | Absorb = `ImportAbsorb` + `id_policy` only | Shipped Path-B; MUST NOT send goldfish Δ there |

Load-bearing orthodox: rate, codebook, \(k\)-hop, skip-after-probe, same alphabet, sparse Δ, two budgets. Names-only (do not erect a solver): IB Lagrangian, DPI-as-proof, Pearl blanket, Miller 7±2.

---

## Paradox validation (scope, not a new product)

Each case **must pass on the orthodox base**. Fail = wrong resolution (ANN \(S\), RRF, third API).

| Id | Paradox | Probe (given / do / expect) | Wrong fix |
|----|---------|-----------------------------|-----------|
| **V1** | Isolated `TSK`: Shape is LAW + that node | Graph with `TSK_x` and unlinked `MOD_*`. `pin_map(TSK_x)` → no MOD. Commit `:owns`/`:next`, `pin_map` again → MOD present | Snap-on-session; invent Peak as ego |
| **V2** | One ego misses a second component | Two unlinked stars. One interior map on TSK misses the other. One `view=shell` on hub **or** leftover union-under-one-\(M\) still \(\lvert\tilde{X}\rvert\le M\) | \(N\) full maps; RRF; \(M\times\|Q\|\) |
| **V3** | Skip without probe under-recalls | Unknown ego. `read_list(tag=TSK, active_only=True)` then `pin_map`. Empty list → skip / grep / host Snap, **not** silent success | Skip instead of `read_list` |
| **V4** | Sparse Δ omits a fact that next Shape needs | After pin_map, `add` only the new edge (not the whole slice). Re-`pin_map` shows the edge. Chat-only fact is absent (correct) | Echo full \(\tilde{X}\) (`id_exists`); Absorb |
| **V5** | \(N\) maps waste rate | Same session, five interior `pin_map`s on overlapping egos → LAW×5. Prefer one TSK map | Treat Path-B \(M\times\)anchors as goldfish budget |
| **V6** | `add` of an id already in \(\tilde{X}\) | `id_exists` / use `update` | Upsert; Letta-style rewrite of the slice |
| **V7** | Session too large | Caps truncate; no embedding store in engine | `rag_query` / ANN of \(S\) |
| **V8** | Colloquial “absorb the slice” | Goldfish Δ → MutateGate. Member export → ImportAbsorb only | `LocatorCommit`; goldfish through ImportGuard |
| **V9** | Raw degree peak = `contains` parent | Ingest tree: PKG/MOD is local max. Live TSK preferred; \(\rho^*\) last (not shipped) | Default goldfish = Peak_L; Leiden |
| **V10** | Host Snap vs Shape | Locators only; chunk body not on `note=` | Nest HostSearch under `MemNetSystem` |

Runtime tests already covering part of this: `tests/test_pin_map_view.py` (V2 grain / fan), `tests/test_add_update.py` (V6), `tests/test_mem_store.py` / `test_mission_warm.py` (recycle hide). **Gaps:** V1 fixture, V3 `read_list`→`pin_map` chain, V4 sparse re-pin, V5 LAW-count, V9 \(\rho^*\) (defer with Peak_L).

---

## Development sequence

Do **not** reorder ahead of live M2.5 cabinet for 0.5.0 claim. Goldfish leftover is **after or beside** that notch, not instead.

### Already done (do not rebuild)

M2 `pin_map` / mutate / fan-out / `view=shell` / recycle / Path-B ingest and Absorb / RSV. Playbook goldfish loop (one TSK, sparse Δ). Design Snap vs Shape, Peak_L last, HostSearch outside.

### Next that **builds from orthodox** (leftover engine)

| Order | Work | Orthodox it erects | Gate |
|-------|------|--------------------|------|
| 1 | Pytest for V1, V3, V4, V6 (fixtures; no new MCP) | Isolated ego; probe then Shape; sparse Δ; `id_exists` | CI green; no `rag_query` |
| 2 | Leftover [#73](https://github.com/chouswei/MemNet/issues/73) `BoundedMatchFind` | Codebook find when no ego; hard LIMIT \(L\); shaped emit not RETURN | `implemented=true` only with LIMIT tests; MN-VER-13 honesty flips find flag |
| 3 | Multi-ego union-under-**one** \(M\) | Fan / one rate; V2 | Must **not** copy Path-B \(M\times\)anchors. Single LAW prepend |
| 4 | Optional `Peak_L` on \(\rho^*\) | Last-resort topology cue only | Behind explicit cue; never default; no cluster assignment |

### Must not erect (abandons orthodox)

`rag_query` on `memnet-mcp`; ANN / PPR / RRF / GST in-engine; HostSearch under `MemNetSystem`; goldfish Δ via ImportAbsorb; Peak_L as default goldfish; Layer teach.

### Host Snap (application; not this engine)

`RagHostHook` stays `implemented=false` until a **locator-only** adapter lives **outside** `MemNetSystem`. Validate V10 in the host-search case study, not in `memnet-llm` retrieve.

---

## Verification mapping

| Check | Kind |
|-------|------|
| MN-VER-13-S01 | Model: two operators, find not shipped, skip flag, hops not cosine |
| V1–V10 | Paradox cases above (pytest where engine already exists; playbook for the rest) |
| MN-REQ-10.2 / 10.3 | Pin map fits context; no \(N\)-map LAW burn |
| MN-REQ-11.13 | No chunk bodies as memory surface |

Done for **this leftover track** when: V1/V3/V4/V6 have pytest; playbook still one-TSK; #73 still not claimed from pin_map alone. Done for **#77** when HostSearch ship / #73 / Peak_L are decided — not when this plan exists.

---

## Related

| Path | Role |
|------|------|
| [`docs/grammar/math-skeleton.md`](../../docs/grammar/math-skeleton.md) | Product math (names only) |
| [`docs/grammar/memnet-host-search-nest.md`](../../docs/grammar/memnet-host-search-nest.md) | Snap/Shape; after #84 status |
| [`host-search-nest-case-study.md`](host-search-nest-case-study.md) | Paths A–E |
| [`docs/ROADMAP-0.5.md`](../../docs/ROADMAP-0.5.md) | 0.5 one path; leftover vs M2.5 |
| [#73](https://github.com/chouswei/MemNet/issues/73) | Bounded find leftover |
| [#77](https://github.com/chouswei/MemNet/issues/77) | Research (citations) |
