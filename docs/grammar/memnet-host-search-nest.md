# Host search (design)

**Status:** design only — **not** shipped. No `rag_query` MCP; no embeddings in the engine.  
**Research:** [#77](https://github.com/chouswei/MemNet/issues/77).  
**Walk:** [`../../sysml-models/outputs/host-search-nest-case-study.md`](../../sysml-models/outputs/host-search-nest-case-study.md).  
**Dialect:** GQL ([`gql-wire-profile.md`](gql-wire-profile.md)). British English.

MN-REQ-00: MemNet is mission working memory, **not** the search corpus. Host retrieval MAY propose **locators**; **MutateGate** (or Path-B ingest) commits them. Skip is valid.

**Absorb is precise.** `ImportAbsorb` is Path-B only: a member `WorkingMemorySlice` into the lead session under `id_policy` (`keep` / `reject` / `remint`). Host search does **not** absorb. It does not invent a second absorb-shaped leaf.

| Verb | What moves | Hard owner |
|------|------------|------------|
| **mutate** | GQL in the *current* session | `MutateGate` |
| **ingest** | Artefact → deterministic locator pins | `PinMapIngest_*` |
| **absorb** | Member *slice* → lead SSOT + id policy | `ImportAbsorb` |

## Cut

An LLM turn needs two bounded contexts. Do not fuse them.

| Need | Mechanism |
|------|-----------|
| Mission working memory | Atomised NODE\|EDGE → shaped **`pin_map`** |
| Corpus lookup | Host index / grep / sibling RAG MCP → **locators**, then MutateGate |

Retrieve, generate, and remember all “put less text in the prompt”. Only the third is MemNet. Symptoms of fusion: `rag_query` on `memnet-mcp`, chunks on `note=`, `pin_map.generate(prompt)`.

```text
corpus --(host retrieve)--> locators --MutateGate--> session --pin_map--> goldfish
```

Skip the host hop when grep, ingest, or existing pins suffice.

## Role (pinned)

Working set for **a few technical documents** (atoms and locators; PDF/HTML stay on disk) **plus** live `TSK`/`USR`/`MOD`, re-read **fast** (`pin_map`, depth ~2 / 50 rows). Tens of MiB typical; **hundreds of MiB still in role**; gigabytes = RAG/cabinet.

The session itself is already too big to dump: same *shape* as RAG (which slice this turn?), different haystack. Owner = **`pin_map`** (and leftover [#73](https://github.com/chouswei/MemNet/issues/73) bounded find when there is no ego) — **not** a second vector index.

| Haystack | Owner |
|----------|--------|
| Library / PDFs / web | Host RAG, grep, ingest |
| Live session graph | MemNet `pin_map` |

If the graph becomes the library, it has left this role.

## In-session retrieve: kinds as cues (human memory)

Corpus RAG stays on the host. Inside the session, SCHEMA kinds/tags are an **open cue vocabulary**. Recall is like working memory in a person: a **keyword** cues a cluster, then a **neighbourhood** is reconstructed. House prefixes (`TSK_*`, `MOD_*`, `KYWD`, …) are conventions, not a DBA taxonomy. `KYWD` hubs (daily-news) are one idiom, not a second product.

```text
keyword cue  -->  find (kind / id / locator)  -->  pin_map(ego)
```

### First principles

| Principle | What it licenses | What it forbids |
|-----------|------------------|-----------------|
| **IB / rate–distortion** | A short token as cue; then a bounded reconstruct (`depth`, `max_rows`) | Dumping the session; embedding the session “to be sure” |
| **Discrete codebook** | Kinds/tags/ids/locators *are* the code — overlapping cues, like human categories | A second ANN index as the “real” memory |
| **k-hop reconstruct** | After a hit, ego walk is the polynomial stand-in for “spread of activation” | Unbounded association; Steiner “optimal memory subgraph” |
| **Empty cue** | Miss → skip / grep / host retrieve | Inventing a node because the keyword felt right |
| **Working memory ≠ LTM** | Recycle / settle is forgetting on purpose | Growing a session thesaurus into a cabinet |
| **Jobs stay unfused** | Fuzzy overlap is for **recall keys** only | Blurring kind for **identity** (one primary label) or **ACL** (`labels=` write-scope) or **Absorb** |

So: **no clear boundary among cues** (a pin may answer to `SYM` and to `session`). **Hard boundary among jobs** (retrieve ≠ mutate-scope ≠ absorb). Human LTM (years, interference, false memory) is not the product — goldfish is.

| Cue | Then |
|-----|------|
| Token matches a kind, id, or locator | Leftover [#73](https://github.com/chouswei/MemNet/issues/73) bounded find |
| A hit id is in hand | `pin_map` — dimension of the net |

Engine today: one primary GQL label; `tagmap` lists kinds, it is not a topic ontology. Layer `@TAG` pipe stays retired.

## Math (keep three)

Citations on [#77](https://github.com/chouswei/MemNet/issues/77). **MUST NOT** train IB, run Steiner, or ANN-index the session because a paper did.

| Principle | In MemNet |
|-----------|-----------|
| **Information bottleneck** | `pin_map` compresses the session given an anchor. Skip = empty extra retrieve. |
| **Ego \(k\)-hop** | Optimal evidence subgraph is NP-hard; `depth` from a known id is the polynomial stand-in. |
| **Cardinality / diameter** | `max_rows` and `depth` are the budget. Relations are the metric, not cosine. |

## Nest (application; not product)

Do **not** copy ImportGuard leaf-for-leaf. ImportGuard’s hard leaf is **Absorb** — that verb does not apply here.

```text
HostSearchBridge          // MUST NOT nest under MemNetSystem
└── RagHostHook           // optional, implemented=false, fail-open
    // skip → pin_map + grep
    // propose locators → existing MutateGate / PinMapIngest
```

**Hook in:** `session_id` (capability; do not log), `anchor`, short question, `max_hits`, timeout. Not the whole session or source artefact.

**Hook out:** locators only (`path=` / `line=` / `qname=` / `document_id`). **MUST NOT** emit chunk bodies. Host or agent then writes GQL; ground ids for source pins (no client `NEW` on artefact nodes). Next turn: `pin_map`.

Fail-open: missing adapter / timeout / parse → skip; **MUST NOT** fail `pin_map` / `add`. Adapter **MUST NOT** mutate the session.

`BoundedMatchFind` (#73) is unanchored **graph** lookup. Host search is **corpus** lookup. Do not merge them.

## MUST NOT

- Add `rag_query` (or equivalent) to `memnet-mcp`.
- Nest this under `MemNetSystem`.
- Store embeddings or chunk text as the memory surface (MN-REQ-11.13).
- Teach RAG emit as shaped `pin_map`, or `generate` *on* MemNet.
- Dual-write a vector index and MutateGate.
- Claim this shipped because ImportGuard or ingest shipped.
- Call host locator commit **absorb** (that word is `ImportAbsorb` only).
- Fuse overlapping **recall cues** with identity (primary label), ACL `labels=`, or Absorb.

## Related

| Path | Role |
|------|------|
| [#77](https://github.com/chouswei/MemNet/issues/77) | Research (steal/reject vs Neo4j / RAGFlow / math) |
| [`gql-wire-profile.md`](gql-wire-profile.md) | Goldfish = `pin_map` |
| [`../application-notes/llm-daily-news.md`](../application-notes/llm-daily-news.md) | `KYWD` as one overlapping cue idiom |
| [`../../sysml-models/outputs/host-search-nest-case-study.md`](../../sysml-models/outputs/host-search-nest-case-study.md) | Evidence walk |
