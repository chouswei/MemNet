# Sessions as strata (not Layer)

**Status:** design — **not** shipped, **not** a SemVer gate, **not** Layer / Tier A.  
**Audience:** product developers. British English.  
**Homograph.** *Layer* in this repo means the **archived dialect** (ADR-001). Do **not** teach it. Below, a **stratum** is a **named session** \(S_i\), not a wire tier and not `view=shell`.

**Locked:** one GQL dialect; Write = display; chat never SSOT; no `rag_query`; Absorb = Path-B slice only; do not raise goldfish \(M\). Wire: [`gql-wire-profile.md`](gql-wire-profile.md). Join: [`memnet-neo4j-rag-rethink.md`](memnet-neo4j-rag-rethink.md). Multitask: [`../multi-agent-sessions.md`](../multi-agent-sessions.md). Thesis: [`memnet-harness-thesis.md`](memnet-harness-thesis.md).

---

## Thesis

The old instinct (one fat \(S\), strata *inside* the dialect) is how Layer happened. The replacement is already in doctrine and under-taught:

**Partition the haystack into more sessions. Goldfish one session at a time. Join with Absorb (slice), not merge, not ANN.**

That *is* “sessions as layers”: each stratum has a **session id**, a schema map, a budget \(M\), and a Shape. The catalog of ids is itself a small session (or a Snap of `session=` locators). The lead mission stays Path A until a second haystack or a second writer earns a new id.

---

## What a stratum is

| Kind | Session | Goldfish read | Write | Join |
|------|---------|---------------|-------|------|
| **Mission** | Lead \(S\) (Path A) | `pin_map` on live `TSK`/`USR` | Mutate Δ | Default; peers re-`pin_map` |
| **Member** | Worker \(S_w\) (Path B) | Same, under write scope | Mutate in \(S_w\) | Absorb a **slice** into lead |
| **Library pins** | \(S_{\mathrm{lib}}\) | `pin_map` of locators | Mutate locators only | Snap from corpus **into** \(S_{\mathrm{lib}}\); do not Absorb Neo4j library nodes |
| **Catalog** | Index of `session=` ids | `view=shell` on the index, then one interior map | Parent mints/settles session rows | Look = `pin_map(session=…)`; join = Absorb slice |

Cabinet hydrate/flush is **not** a stratum. It is persistence of **one** named \(S\). Neo4j **library namespace** (option B) is **not** a session; Snap may emit locators into \(S_{\mathrm{lib}}\).

`view=shell` / `interior` is **grain inside one \(S\)**, not a second session. RSV is a **lease inside one \(S\)**, not a stratum. Env blobs stay in the outer harness.

---

## When to mint a new session

Mint \(S_{i+1}\) when **at least one** holds:

1. **Different haystack** — library locators vs this mission’s `TSK`/`USR`.
2. **Different writer** that must not share Path A (Path B member; Absorb later).
3. **Over \(M\)** after narrowing ego and `view=shell` — partition, do not raise \(M\).

**MUST NOT** mint a session per `TSK` (HiAgent subgoal replace is **settle in \(S\)**, not a new id). **MUST NOT** mint a session per source **file** as a coding habit (`MOD_*` stay nodes in the mission). **Exception:** a **model Snap** (below) **does** mint several sessions — those are partitions of **one** model, not one session per disk file. **MUST NOT** mint a session so the catalog “looks like RAG.” Empty catalog seed → skip.

V5 still holds: \(N\) interior maps on overlapping egos waste LAW. Across strata, the goldfish is **one** catalog shell (or skip) **then** **one** `pin_map` on the chosen `session=`. Not \(N\) maps in one generate.

---

## Goldfish across strata

```text
q  →  catalog Shape (session= ids, M≈50)
       empty → skip
       hit   → pin_map(session=S*, anchor=…)     # one interior
                mutate Δ on S* only
                Path B: Absorb slice → lead
```

Same token law as one session: few LLM tokens; emit **co-responds** to \(q\). The catalog is a codebook of **session ids**, not passages. Ranking catalogs with cosine is Snap-on-sessions (forbidden). `find` on the catalog is seed-only, then Shape.

**Path A first.** One shared mission id is the cheap stratum. Path B and \(S_{\mathrm{lib}}\) are the expensive ones. Workers **MUST NOT** open a library session unless the parent assigned it.

---

## Steal / reject

| Cousin | Steal | Reject |
|--------|-------|--------|
| Archived **Layer** dialect | Nothing on the wire | Dual teach; strata as syntax |
| HiAgent subgoal replace | Settle finished `TSK_*` in **the same** \(S\) | One session per subgoal |
| Letta `system/` vs `$MEMORY_DIR` | Working vs cabinet **files** ≈ mission vs hydrate | Prose blocks as Shape; archival **inside** `pin_map` |
| OpenHands condenser | Summarise **env events** in the harness | Summarise as a MemNet stratum |
| GraphRAG communities | Partition a fat **library** into more \(S_{\mathrm{lib}}\) | Community reports as goldfish; Leiden in-engine |
| `view=shell` | Dual grain **inside** \(S\) | Calling shell a “layer session” |

---

## Critical objections

**1. Name.** If we say “layer” in teach, agents revive Layer. Product word = **session** / **stratum**. Catalog rows are `session=` locators.

**2. Explosion.** Unbounded session mint is GraphRAG global with extra ids. The mint rule above is the rate cap. Catalog \(M\) is the same \(M\).

**3. Absorb of whole \(S\)** is option C (forbidden). Slice only. Merging strata in chat is dump.

**4. Catalog as RAG.** A directory of sessions is still **named**. `find` then skip. Do not RRF session ids.

**5. 0.10 caller.** Stuffing maps from **every** stratum into one chat list is worse than one fat \(S\). Goldfish **drops** the previous map, including catalog rows, unless \(q\) still names that session.

**6. ACL.** CapsPolicy is per session when enabled. A stratum stack is not a privilege ladder unless GRANT says so. Do not invent Layer-like clearance in GQL labels.

---

## SysML: Snap **one model** into multiple sessions

The Snap is of **one model** (a load tree / root package). The sessions are **strata of that Snap**, not a pile of unrelated library stores.

**As-is (too thin).** `ingest_sysml` Commits one `.sysml` **path** into the **current** session (MN-REQ-11.16): PKG/PRT/REQ/POR with `qname=` / `requirementId=` / `path=` (no client `NEW`). Map: `schema.sysml.example.txt`. Ingest `max_nodes` default 200. `requirements.sysml` alone is ~193 nodes. **`.sysml` stays structural SSOT.**

**Wrong reading of “strata”.** Opening a new session for each file on disk and calling that Snap. That is N ingests, not **one model Snap**. Files are how this repo **stores** packages; they are not the Snap cardinality.

**Right reading.** `Snap(model) → (S_{\mathrm{cat}}, S_1, \ldots, S_k)`. One catalogue plus \(k\) interiors, all **about the same model**. Goldfish still **one** \(S\) per generate. Join interiors with catalog look or Absorb a **slice** into the mission — not one `pin_map` across stores, not session merge.

**Two budgets.** Ingest `max_nodes` = Commit into **that interior**. Goldfish \(M\approx 50\) = Shape. A 193-pin requirements package in **one** interior still cannot shell the whole package under \(M\). Then split **that package** again (kind band or child package), still under the **same model Snap**. Do not raise goldfish \(M\). Do not `rag_query` `.sysml` bytes.

### Interior grain (of the model)

Prefer **SysML package** (the `package` / `private import` tree), not “whatever `.sysml` files exist.” Optional **kind band** (REQ vs PRT vs verification) when a package still exceeds ~2\(M\) pins.

Worked example — **this product model** (`ProjectMemNet` / `root.sysml` imports):

| Interior of **one** Snap | Package haystack |
|--------------------------|------------------|
| \(S_{\mathrm{req}}\) | `MemNetRequirements` |
| \(S_{\mathrm{ver}}\) | `MemNetVerification` |
| \(S_{\mathrm{dep}}\) | `MemNet` (deploy nest) |
| \(S_{\mathrm{beh}}\) | `MemNetBehaviour` |
| \(S_{\mathrm{con}}\) | `MemNetConnections` |
| \(S_{\mathrm{cat}}\) | Root: `session=` + `qname=` of those packages (not the atoms) |

Mission \(S\) is **not** an interior of the model Snap. It holds `TSK_model_*` and locators into the catalog. The model Snap’s output is the **stack** \((S_{\mathrm{cat}}, S_{\mathrm{req}}, \ldots)\).

**MUST NOT** one session per `requirement def`. **MUST NOT** dump the whole model into the mission or into a single library session. **MUST NOT** Layer dialect.

### Snap loop (one model)

```text
Snap(ProjectMemNet)
  mint S_cat, S_req, S_ver, …          # one stack, one model
  project each package → Commit into its S_i   # locators, idempotent
  S_cat := session= + qname= of package roots

q = REQ_MN_REQ_00
  → pin_map(S_cat) or skip
  → pin_map(session=S_req, anchor=REQ_MN_REQ_00)   # one interior
  → edit the .sysml SSOT
  → re-Snap that package into S_req
  → mission Δ: TSK / TOUCHES only
```

`satisfy` from requirements to verify: two interiors of the **same** Snap. Second look, or Absorb a slice into the mission. No edge that points at another session’s store.

**Engine leftover (0.12).** Today `ingest_sysml(path, session=current)` is 1→1. Model Snap is 1→k: walk the root, mint the stack, partition, Commit. Caller 0.10 still drops old maps so the stack does not refill the prompt.

### Steal / reject (SysML)

| Cousin | Steal | Reject |
|--------|-------|--------|
| `root.sysml` imports | One model, several packages | Treating each file as an independent Snap |
| Package tree | Interior grain | One session per requirement; Leiden on the model |
| 6-step modelling note | Cue TSK → edit SSOT → delta | Chat as SSOT for `qname=` |
| Product vs application ([`../SHAPE.md`](../SHAPE.md)) | Same Snap-model grain downstream | Import `MemNetRequirements` into a customer load tree |

---

## SemVer

Fits **0.12 Catalog Snap**. **SysML model Snap** = one model → session stack (worked application). **0.10** owns the caller that does not keep the stack in one prompt. **1.0 MUST NOT** wait.

**MUST NOT** ship: Layer accept; `SessionMerge*`; ANN of the catalog; a `layer=` property as wire; HostSearch nested under `MemNetSystem`.

---

## Related

| Path | Role |
|------|------|
| [`gql-wire-profile.md`](gql-wire-profile.md) | `view=` grain **inside** one \(S\) |
| [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md) | No Layer |
| [`../multi-agent-sessions.md`](../multi-agent-sessions.md) | Path A / Path B |
| [`memnet-neo4j-rag-rethink.md`](memnet-neo4j-rag-rethink.md) | \(S_{\mathrm{lib}}\) vs Neo4j library namespace; more sessions when over \(M\) |
| [`../application-notes/llm-sysml-v2-modeling.md`](../application-notes/llm-sysml-v2-modeling.md) | Application: Snap **one** SysML model into many sessions |
