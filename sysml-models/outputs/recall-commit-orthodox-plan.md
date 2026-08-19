# Recall / Commit — orthodox review and plan

**Status:** plan (docs). **0.5 leftover (find + multi-ego + paradox pytest) shipped.** Extra **0.17** HostSearch locators. Extra **0.18** Peak_L last-resort shipped this cut (untagged). Remaining Later is N-server / hosted cabinet — not 1.0.
**Audience:** product developers. British English.  
**Math SSOT:** [`docs/grammar/math-skeleton.md`](../../docs/grammar/math-skeleton.md).  
**Playbook:** [`docs/LLM-GUIDE.md`](../../docs/LLM-GUIDE.md).  
**Research:** [#77](https://github.com/chouswei/MemNet/issues/77) (notes 22–28 on `master`).  
**Model honesty:** MN-VER-13-S01. Live cabinet is **0.7** (`liveCabinetClaimed=true`). **1.0** = 0.5–0.8 claimed — this file is not a bid to invent extra 1.0 engine.

Orthodox = a theorem you can **build from**. Paradox = **all** examination and test after the build (pytest, MN-VER, V-cases, cousin papers). Resolve by **scope**, not a third operator / `rag_query` / Snap-on-session. There is **no** third kind of work called “exam”. Filename `gql-model-exam.md` is historical paradox, not a second orthodox.

---

## Design review (what is already erected)

| Orthodox (build from) | Erected in MemNet | As-is honesty |
|-----------------------|-------------------|---------------|
| Rate–distortion | `max_rows`, `depth`, `MEMNET_MAX_FANOUT`, hide recycled, LAW prepend | Shipped (`context_pack` / `PinMapComposer`) |
| Discrete codebook | id ∪ kind ∪ locator ∪ keyword; one primary GQL label | Shipped mutate + schema; [#73](https://github.com/chouswei/MemNet/issues/73) `find` **shipped** (seed-only) |
| Encoding specificity | Token must be written before it retrieves | Shipped: miss ≠ invent a node. Agent still mints cues via Commit |
| Ecphory (cue then reconstruct) | Recall = seed then Shape | Seed = known id (`pin_map`) **or** kind/keyword `find` then `pin_map` (`implemented=true`) |
| Polynomial \(k\)-hop (not GST) | Ego walk + fan-out clamp | Shipped; metric = hops (`cosineMetric=false`) |
| Empty retrieve | `SessionOutline` empty-q census of \(S\) | TARGET modelled (MN-REQ-04.9); leftover `emptySeedSkip` / `no_anchor` leftover 0.10 |
| Same alphabet | Shaped GQL emit = mutate family | Shipped M2 |
| Incremental coding | Sparse Δ: `add`/`update`; `id_exists` on echo | Shipped strict mutate; playbook must not echo \(\tilde{X}\) |
| One working chunk | Live `TSK` as default ego; settle / `delete_on_settle` | Shipped recycle hide; playbook after [#84](https://github.com/chouswei/MemNet/pull/84) |
| Two rate budgets | Snap (host corpus) vs Shape (session) | Extra **0.17**: `RagHostHook.implemented=true` outside `MemNetSystem`; skip valid |
| Path-B ≠ goldfish writeback | Goldfish Δ is Commit, not Absorb-named writeback. `ImportAbsorb` = Path-B slice + leftover `id_policy` only. `SameThingAbsorb` = distinct in-session Commit rule (not Recall) | Shipped Path-B; MUST NOT send goldfish Δ to ImportAbsorb; SameThingAbsorb modelled |

Load-bearing orthodox: rate, codebook, \(k\)-hop, skip-after-probe, same alphabet, sparse Δ, two budgets. Names-only (do not erect a solver): IB Lagrangian, DPI-as-proof, Pearl blanket, Miller 7±2. Hilbert IR / QQL / ZX-on-Cypher / Gremlin quantum walks are **paradox cousins** (stress), not GQL semantics and not a Hilbert store.

---

## Paradox (scope, not a new product)

Every test below is paradox. Each **must pass on the orthodox base**. Fail = wrong resolution (ANN \(S\), RRF, third API).

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
| **V9** | Raw degree peak = `contains` parent | Ingest tree: PKG/MOD is local max. Live TSK preferred; \(\rho^*\) last (0.18 Peak_L) | Default goldfish = Peak_L; Leiden |
| **V10** | Host Snap vs Shape | Locators only; chunk body not on `note=` | Nest HostSearch under `MemNetSystem` |

Pytest covering part of this (still paradox): `tests/test_goldfish_paradox.py` (V1/V3/V4/V6 + **V9**), `tests/test_peak_l.py` (Peak last-resort; never default), `tests/test_pin_map_view.py` (V2 grain / fan), `tests/test_add_update.py` (V6), `tests/test_mem_store.py` / `test_mission_warm.py` (recycle hide). GQL-wire paradox: [`docs/grammar/gql-model-exam.md`](../../docs/grammar/gql-model-exam.md).

---

## Development sequence

Goldfish leftover for **0.5 is shipped**. Extra **0.18** Peak_L last-resort is shipped this cut. Do **not** hold **1.0** for HostSearch.

### Already done (do not rebuild)

M2 `pin_map` / mutate / fan-out / `view=shell` / recycle / Path-B ingest and Absorb / RSV. **0.5** BoundedMatchFind + multi-ego `pin_map` + paradox pytest. **0.7** live cabinet. **0.8** GQL teach. Playbook goldfish loop (one TSK, sparse Δ). Design Snap vs Shape, Peak_L last (0.18 extra), HostSearch outside.

### Leftover **paradox** (tests first)

| Order | Work | Stresses |
|-------|------|----------|
| — | V1, V3, V4, V6 pytest | **Shipped** in 0.5 (`tests/test_goldfish_paradox.py`) |

### Leftover **erect** (orthodox construction)

| Order | Work | Orthodox it erects | Paradox gate |
|-------|------|--------------------|--------------|
| — | [#73](https://github.com/chouswei/MemNet/issues/73) `BoundedMatchFind` | Codebook find when no ego; hard LIMIT \(L\); seed nodes not RETURN | **Shipped** `implemented=true` |
| — | Multi-ego union-under-**one** \(M\) | Fan / one rate; V2 | **Shipped** in 0.5 |
| — | Optional `Peak_L` on \(\rho^*\) | Last-resort topology cue only | **Shipped** extra 0.18 (untagged): codebook miss only; never default; no cluster assignment; V9 pytest |

### Must not erect (abandons orthodox)

`rag_query` on `memnet-mcp`; ANN / PPR / RRF / GST in-engine; HostSearch under `MemNetSystem`; goldfish Δ via ImportAbsorb; Peak_L as default goldfish; Layer teach; Hilbert / QQL store; Gremlin-walk goldfish.

### Host Snap (application; outside MemNetSystem)

`RagHostHook.implemented=true` extra **0.17** — locator-only adapter **outside** `MemNetSystem`. Skip is valid. Validate V10 in the host-search case study, not by fusing retrieve into `pin_map`.

---

## Paradox mapping (all of these are tests)

| Check | Stresses |
|-------|----------|
| MN-VER-13-S01 | Two operators, find **shipped** seed-only, skip flag, hops not cosine |
| V1–V10 | Cases above (pytest where engine already exists; playbook for the rest) |
| [`gql-model-exam.md`](../../docs/grammar/gql-model-exam.md) | GQL-only wire; M2/M3 done |
| MN-REQ-10.2 / 10.3 | Pin map fits context; no \(N\)-map LAW burn |
| MN-REQ-11.13 | No chunk bodies as memory surface |

Done for **the 0.5 leftover track** when: V1/V3/V4/V6 have pytest (**yes**); playbook still one-TSK; #73 claimed as seed-only find then `pin_map` (**yes**). HostSearch locators extra **0.17**. Done for **Peak_L** when V9 \(\rho^*\) pytest exists and Peak is not default goldfish (**yes**, extra 0.18). Do **not** claim **1.0**.

---

## Related

| Path | Role |
|------|------|
| [`docs/grammar/math-skeleton.md`](../../docs/grammar/math-skeleton.md) | Product math (orthodox names) |
| [`docs/grammar/gql-model-exam.md`](../../docs/grammar/gql-model-exam.md) | GQL-wire paradox (historical filename) |
| [`docs/grammar/memnet-host-search-nest.md`](../../docs/grammar/memnet-host-search-nest.md) | Snap/Shape; after #84 status |
| [`host-search-nest-case-study.md`](host-search-nest-case-study.md) | Paths A–E |
| [`docs/ROADMAP.md`](../../docs/ROADMAP.md) | SemVer SSOT; 0.5–0.8 shipped; 1.0 = claim |
| [#73](https://github.com/chouswei/MemNet/issues/73) | Bounded find (**shipped** seed-only) |
| [#77](https://github.com/chouswei/MemNet/issues/77) | Research (citations) |
