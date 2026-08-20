# MemNet roadmap

**Status:** SemVer SSOT (claimed vs planned vs Later).

**Audience:** product developers. Dialect teach = **GQL** ([`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md)). Product shape: [`SHAPE.md`](SHAPE.md). British English.

**Package now:** Hatch **0.19.3**. Numbered extras **0.10–0.19** are in this package (unchanged). Git tag `v0.19.3` after this cut. GraphGlot parse front is on master (#109 @ 73a63c9b). Extra **0.14** claims `liveNeo4jClaimed=true`. Last published PyPI **`memnet-llm==0.19.0`** until 0.19.3 upload. **1.0** is still unclaimed (0.5–0.8).

**Last updated:** 2026-08-20 (package **0.19.3**; default `max_sessions` **256**; MCP `session_close` + list `sessions|n/max`; extras **0.10–0.19** unchanged; last PyPI wheel **0.19.0** until upload; extras first packaged as **0.19.0**; GraphGlot parse front #109 @ 73a63c9b; extra **0.19** pin-map export #123 @ 2c460e7d; extra **0.18** Peak_L #128 @ dc464cd4; extra **0.17** HostSearch #129 @ 00e74dfb; extra **0.16** two namespaces #127 @ c32d4c52; extra **0.15** catalog Snap #124 @ 7767ed84; extra **0.14** live Neo4j claimed; do not claim **1.0**).

Patch notes: [`../CHANGELOG.md`](../CHANGELOG.md).


## One picture

MemNet is **mission working memory** — the **memory plane of an agent harness**, not the harness, not the library, not the cabinet.

```text
  outer harness (Cursor, OpenHands, SWE-agent, Inspect, …)
  owns: completion API, bash, sandbox, eval, chat list
                    |
                    |  MCP / CLI   session id + cue / re-pin
                    v
              memnet-llm  /  memnet-mcp     ← this repo (engine + generic MCP)
              Recall  pin_map(q)   Commit Δ
                    |
         +----------+------------------+
         |                             |
    host Snap (RAG)              cabinet Bolt
    locators only                hydrate / flush
    HostSearch locators (0.17)   Agens live claimed (0.7)
    outside MemNetSystem         Neo4j live claimed (0.14)
                                 0.16 library DB (locators)
```

| Layer | Job | This repo? |
|-------|-----|------------|
| Outer harness | Loop, tools, env blob, eval tape | **No** |
| Memory plane | Named session \(S\); goldfish Shape; sparse mutate; Path-B Absorb | **Yes** — engine + `memnet-mcp` |
| Library RAG | Corpus → locators (Snap) | **0.17** HostSearch outside `MemNetSystem` (skip valid) |
| Cabinet | Persist one \(S\) | Agens **0.7 claimed**; Neo4j **0.14 claimed** |

Handoff = **session id** (+ cue / write scope). Peers **re-`pin_map`** from labels+properties (or a kind/keyword cue). Chat is never SSOT. A durable store **backs** \(S\); it is not the handle and not the default teach surface. **MUST NOT** reframe MemNet as a Cypher proxy or as GraphRAG.

**Two operators only.** Recall and Commit. CueConflict is an **emit mark**, not a command. SameThingAbsorb is a **Commit rule**, not a third operator. **MUST NOT** invent a replacement application store key (locator-as-PK, qname-as-PK, minted string-as-PK). GraphElement is identity. Optional property `id` is a nickname.

**Two channels (thesis leftover, not a SemVer gate).** Mission names (`TSK`/`USR`/`MOD`) live on \(S\). Env blobs (test logs, screenshots) stay in the outer harness (or its condenser). Do not put bash on \(S\) and call that Shape.

**Goldfish caller (thesis leftover, not 1.0).** Shape saves tokens only if the harness **drops** old `pin_map` rows from the chat list. Stuffing MCP JSON into growing `messages` saves zero. That caller is **unshipped** in public harnesses; user-pack `mcp-memnet` is how **Cursor** is taught. Do not hold **1.0** for OpenHands/SWE-agent adoption. The contract in this repo is **0.13**.

---

## Version map (locked)

| Version | Owns | Status |
|---------|------|--------|
| **0.5.0** | Goldfish leftover: paradox V1/V3/V4/V6; BoundedMatchFind (#73) seed-only `find`; multi-ego `pin_map` under one \(M\) + one LAW | **Shipped** (`v0.5.0`) |
| **0.6.0** | Honesty: V5 LAW×N pytest; snapshot as offered durable; version-map docs | **Shipped** (`v0.6.0`) |
| **0.7.0** | Live AgensGraph hydrate/flush; `liveCabinetClaimed=true`. Server not vendored. Fake + skip unless `MEMNET_AGENSGRAPH_URL` | **Shipped** (`v0.7.0`) |
| **0.8.0** | GQL-only **teach** + product **shape for people** (`SHAPE.md`, playbook, application-note contract, Multitask honesty). Docs only. **No** engine cut. Cabinet stays claimed | **Shipped** (`v0.8.0`) |
| **0.9.0** | Neo4j `DurableStoreAdapter` client (`memnet-llm[neo4j]`); factory both-URL rule; [`cabinet/neo4j-buffer.md`](cabinet/neo4j-buffer.md). Live round-trip claimed later as extra **0.14**. Cabinet extra, **not** a 1.0 gate | **Shipped** (`v0.9.0` era; extras later packaged as 0.19.0) |
| **0.10–0.19** | Numbered extras (table below). Same pattern as 0.9: **not** 1.0 gates | **Packaged** (Hatch **0.19.3**; extras first shipped as 0.19.0) |
| **1.0.0** | **Claim** of **0.5 + 0.6 + 0.7 + 0.8**. Shape mature for people. Not GraphRAG. Not cabinet-only. Not a new engine | **Claim when coordinator tags** — package **0.19.3** / last PyPI **0.19.0** does not claim 1.0 |
| **Later** | Grammar Open / hosted product / leftover ACL; N-server research (#47). GraphGlot parse-front is **shipped**. If **1.0 tags first**, remaining extras become **1.1, 1.2, …** with the same owns | **Out** of 1.0 |

**1.0 MAY ship from 0.9** (claim only). **0.10+ MAY ship before 1.0** as extras. Do not wait for the other. User-pack GQL rewrite is **sibling** (`chouswei/cursor-user-skills`), not this repo.

**1.0 MUST NOT** wait on 0.10+ — not HostSearch, not live Neo4j, not Peak_L, not catalog Snap, not a second Neo4j database name, not OpenHands/SWE-agent adoption, not GraphGlot, not N-server.

**GraphGlot** ([#109](https://github.com/chouswei/MemNet/issues/109) @ 73a63c9b) is **shipped** as parse-front only. ProductGqlGate still runs after parse. Layer stays retired. HOLD is lifted (0.10 already shipped).

---

## Code vs TARGET (0.9 leftover)

The nest on master (#108–#118) models GraphElement identity, CueConflict on emit, empty-cue **session outline** (MN-REQ-04.9 / `#118`), and SameThingAbsorb (SysML `implemented=false`; 0.12 engine already on master: agent-gated Commit `MATCH (a),(b) SET a += b` after CueConflict). The **0.11** engine cut emits the outline census (in package 0.19.0). leftover empty-seed skip is leftover only. Outline SHALL NOT absorb. Do **not** claim **1.0**. Do not revert the 0.11 nest or the 0.12 Commit rule. Live Neo4j is extra **0.14** (claimed on master); not this leftover-store gap.

The **0.9 engine** still runs leftover invented store. Numbered extras start at **0.10** because this gap is not named in 0.5–0.9:

| Leftover (as-is 0.9) | TARGET (model) |
|----------------------|----------------|
| `by_id` **is** the graph | GraphElement is identity; hidden handle off the wire |
| `gql.py` NEW / require ground `id` / `CREATE ()` illegal | `CREATE ()` legal; MERGE/SET/DELETE by labels+properties; emit does not require `{id}` |
| MCP/CLI `pin_map --anchor`; `require_anchor` as product | `pin_map` from cue; no `require_anchor` as product |
| `find` teaches copy-id then `--anchor` | Seed \(Q\), then `pin_map` from labels+props. When \(|Q|>1\), emit **CueConflict** (do not pick one root; do not absorb) |
| SCHEMA `id_first` | SCHEMA not `id_first` |
| import keep = MERGE-by-id | ImportAbsorb keep = pattern MERGE (labels+props / type+ends) |
| ingest `allocate_from_locator` | Locators are properties, not a PK |
| leftover `read_get` / NEW / AssignedIdMap / `import_slice id_policy` as product commands | Not product commands |
| Application notes still teach leftover 0.9 as law | 0.10 owns the TARGET teach rewrite |

Do **not** treat leftover 0.9 identity as a live-Neo4j claim. Do **not** claim **1.0** from 0.10.

---

## Numbered extras (0.10–0.19)

One concern per minor. Dependency order. **In package 0.19.0** (git tag by coordinator). Skip a row only if the coordinator writes the skip in CHANGELOG; do not fuse two rows into one tag.

| Version | Owns | Depends on | MUST NOT |
|---------|------|------------|----------|
| **0.10.0** | **Identity + leftover façade.** **Done / in package 0.19.0**. Engine: GraphElement identity; hidden handle off the wire; `CREATE ()` legal; MERGE/SET/DELETE by labels+properties; SCHEMA not `id_first`; emit does not require `{id}`. Façade: `pin_map` from cue (no `require_anchor` as product); find emit **CueConflict** when \(|Q|>1\) (do not pick one root; do not absorb); leftover `read_get` / NEW / AssignedIdMap / `import_slice id_policy` / ingest `allocate_from_locator` are not product commands. Tests that lock leftover as success are rewritten. Application-note + LLM-GUIDE example rewrite (TARGET loop; leftover named leftover). SysML README nest sync. | Nest on master (#108–#114); 0.9 package | Invent a new store key; claim live Neo4j; merge GraphGlot into the identity cut (historical fence); third operator; silent MERGE-by-name; Layer |
| **0.11.0** | **Session outline.** **Done / in package 0.19.0**. Empty cue is Recall of \(S\): kinds + hard-LIMIT exemplars (Neo4j Browser / `db.labels` + `LIMIT k` pattern). Model first if not yet in SysML, then code. Still one Recall. Name conflict among exemplars is CueConflict. | 0.10 (need pattern cue, not `--anchor`) | Dump \(S\); `getAllPages`; RAG search; third operator; `view=shell` as the outline (that is grain on a seed) |
| **0.12.0** | **SameThingAbsorb implemented.** **Done / in package 0.19.0**. Agent-gated Commit after CueConflict. Pattern collapse (labels+props), not MERGE-by-id. Distinct from ImportAbsorb. SysML nest flag still `implemented=false` (Sysmler). | 0.10 CueConflict | Silent LLM merge in Recall; name-as-identity; third operator |
| **0.13.0** | **Goldfish caller contract** (old 0.10). **Done / in package 0.19.0**. Playbook + pytest: stuffed history of maps is a fail; drop prior map rows; sparse Δ. | 0.10 teach | Patch OpenHands/SWE-agent; `rag_query`; raise \(M\); claim **1.0** |
| **0.14.0** | **Live Neo4j claimed** (old 0.11). **Done / in package 0.19.0**. Operator proof rpi5-syson @ d23cc71: `live_round_trip` yes; hid flush; leftover-nickname hydrate after hid miss. `liveNeo4jClaimed=true`. Skip unless `MEMNET_NEO4J_URL`. Hid stays off the wire. | 0.10 identity (else live claim cements leftover_MERGE_by_id) | Vendor Neo4j server; LLM↔Bolt; second database name (0.16); claim hydrate-by-hid proven on live |
| **0.15.0** | **Catalog Snap** + session strata + model Snap (old 0.12). **Done / in package 0.19.0** (#124 @ 7767ed84). [`extras/memnet-session-strata.md`](extras/memnet-session-strata.md). Catalog cut's own fence: that extra does not own `liveNeo4jClaimed`. | ImportAbsorb pattern match (0.10); ingest locators as props | ANN rank sessions; Absorb whole \(S\); Layer; one session per REQ |
| **0.16.0** | **Two Neo4j namespaces** (old 0.13). **Done / in package 0.19.0** (#127 @ c32d4c52). Same process; cabinet vs library. Library port emits **locators only**, never `generate`. Skip library unless `MEMNET_NEO4J_LIBRARY_DATABASE`. `liveNeo4jClaimed` stays **true**. | 0.14 live claim | Fuse RRF/PPR into `pin_map`; `rag_query`; Snap-on-session; vendor Neo4j; LLM↔Bolt |
| **0.17.0** | **HostSearch locators** (old 0.14). **Done / in package 0.19.0** (#129 @ 00e74dfb). `RagHostHook.implemented=true` **outside** `MemNetSystem`; locators into MutateGate / ingest; skip is valid. | 0.16 | `rag_query` MCP; Snap-on-session |
| **0.18.0** | **Peak_L** last-resort (old 0.15). **Done / in package 0.19.0** (#128 @ dc464cd4). Topology cue on residual \(\rho^*\) when codebook miss; never default goldfish; V9 paradox pytest. | 0.5 find | Peak as default |
| **0.19.0** | **Pin-map export** (old 0.16 / [#66](https://github.com/chouswei/MemNet/issues/66)). **Done / in package 0.19.0** (#123 @ 2c460e7d). Ingest ≠ export. | Shaped emit | Export as Absorb |

**After 0.19 (still Later, unnumbered until a cut exists):** hosted AgensGraph as a **product service**; first-class `PORT` NODE / SCHEMA vocab freeze; full ACL modes / `session_token` (CapsPolicy already ships when enabled). N-server session pipe stays research (no cut; [#47](https://github.com/chouswei/MemNet/issues/47)).

**Not a `memnet-llm` minor:** cache-hit dump vs Shape+Flash (measure, do not ship a SKU); OpenHands condenser patches; Inspect dual-tape; Letta MemFS. Teach Cursor via user-pack `mcp-memnet`. Sibling skills repo may absorb 0.13 caller text; this engine still owns the **fail-the-stuffed-maps** test.

**0.10 MUST NOT** wait on 0.14. **0.11 MUST NOT** wait on HostSearch. **0.14 MUST NOT** happen before 0.10. Parallel only when the Depends-on cell is already shipped.

**0.8 MUST:** one dialect teach (GQL only; Layer archive only); Write = display = bounded shaped `pin_map`; session id = handoff handle; working memory ≠ corpus (no `rag_query`). Wire SSOT: [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md).

**0.8 MUST NOT:** Peak_L / HostSearch / N-server / export / `rag_query`; second **live** cabinet claim; vendor AgensGraph/Neo4j servers; restore Layer teach or novel-writer.

**0.9 MUST NOT:** vendor a Neo4j server; hold **1.0** for live Neo4j, HostSearch, N-server, Peak_L, catalog Snap, OpenHands adoption, or GraphGlot. Extra **0.14** claimed `liveNeo4jClaimed` while the package was still 0.9.0; coordinated bump is **0.19.0**.

**0.10 MUST NOT:** wait on live Neo4j, HostSearch, Peak_L, catalog Snap, or GraphGlot.

---

## Later (unnumbered remainder)

Numbered fill is **0.10–0.19** above. This list is the overflow. **MUST NOT** treat design docs as implemented.

| Item | Notes |
|------|--------|
| Hosted AgensGraph as a product service | 0.7 proved **client** live; server not vendored |
| First-class `PORT` NODE; SCHEMA vocab freeze | Grammar Open; ports stay properties |
| Full ACL modes / roles / `session_token` | CapsPolicy cut already ships when enabled |
| GraphGlot parse-front (#109 @ 73a63c9b) | **Shipped** as parse-front only on master. ProductGqlGate still runs after parse. Not a store. Layer stays retired. |
| N-server session pipe ([#47](https://github.com/chouswei/MemNet/issues/47)) | **Research** — no cut exists; **MUST NOT** treat the issue as a SemVer owns. Shared \(S\) across serve processes without Snap-on-session stays a research question. Not in 0.8; **1.0 MUST NOT** wait on it. |

### Not this repo’s SemVer (harness leftovers)

| Item | Notes |
|------|--------|
| Goldfish caller in **other** harnesses | 0.13 owns the **contract** in this repo. OpenHands/SWE-agent/Inspect patches are not `memnet-llm` SemVer. |
| Cache-hit dump vs Shape+Flash | MN-REQ-00 unmeasured. Do not pretend dump always loses. |
| Env-blob channel | Harness condenser of pytest logs ≠ MemNet Shape. |
| Eval dual-tape | Inspect (and cousins) keep a transcript for scoring; \(S\) is not that tape. |

**GQL:** agent teach/wire only. **MUST NOT** revive Layer teach.

**AgensGraph / Neo4j:** backing graphs for sessions — **not** a MemNet substitute and **not** the handoff handle. **MUST NOT** dual-write without a single sync owner. **MUST NOT** teach LLM ↔ Bolt as the miss path.

---

## Where we are (M-phases — all done)

| Phase | Owns | Shipped? |
|-------|------|----------|
| **M1** | GQL wire profile SSOT; Layer archive; no Layer teach | **Done** (docs) |
| **M2** | Engine/MCP: GQL accept + shaped `pin_map` emit; retire Layer/Tier A from product accept | **Done** |
| **M3** | In-repo `LLM-GUIDE` + application-notes bodies → GQL examples | **Done** for **Layer retirement**. **0.10** TARGET teach rewrite (in package 0.19.0): cue/`pin_map` + pattern Commit; leftover `--anchor` / `id:'NEW'` named leftover. |
| **M2.5** | Durable store **behind** working memory (MemNet ↔ AgensGraph hydrate/flush; one sync owner) | **Done** (0.7 Agens; extra **0.14** Neo4j live claimed) |

Durable: [`cabinet/agensgraph-buffer.md`](cabinet/agensgraph-buffer.md), [`cabinet/neo4j-buffer.md`](cabinet/neo4j-buffer.md). Numbered extras **0.10–0.19** above (in package **0.19.0**).

### Already shipped (from 0.4.x — do not list as deferred)

CapsPolicy ACL (off by default), neighbourhood reserve (RSV), Path-B ingest domains (#64), ImportAbsorb + ImportGuard / CheapLlmImportGuard, LocalIpcGateway. See [`../CHANGELOG.md`](../CHANGELOG.md) and [`../README.md`](../README.md).

---

## Locks that survive 1.0 (teach / ops)

### 1. One remote entry

| MUST | MUST NOT |
|------|----------|
| Teach Cursor remote as **`memnet-pi`** via `"url"` → streamable-http (`:18766/mcp`) | Treat project **`memnet-local`** (stdio) as the default remote/shared path |
| Keep stdio local MCP **optional / dev-only** | Document stdio and HTTP as equal “primary” remotes |

Local single-agent may still use in-process stdio when no shared graph is needed. Multitask / shared graph → HTTP or TCP only.

### 2. One dialect teach

| MUST | MUST NOT |
|------|----------|
| Teach **GQL (openCypher-shaped)** as the **only** agent wire ([`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md); family authority = openCypher CIP / oC9) | Teach Layer / Tier A as wire, peer, or accept path |
| Redefine **Write = display** as **bounded shaped GQL subgraph** via `pin_map`-class tool | Ship unbounded tabular `MATCH`/`RETURN` as primary goldfish read |
| Do **not** restore Layer / Tier A sources into `docs/` | Invent a third peer dialect |

Decision SSOT: [`adr/ADR-001-gql-agent-wire.md`](adr/ADR-001-gql-agent-wire.md) (supersession: no Layer).

### 3. One graph owner on Pi

| MUST | MUST NOT |
|------|----------|
| Bridge HTTP MCP to **`memnet serve`** (TCP `:18765`) so one process owns the store | Run HTTP MCP with a separate `InProcessEngine` **and** TCP serve as two writers |
| Default remote HTTP so tools share the serve graph | Dual-write the same mission across two engines |

### 4. Footguns (Cursor just works)

| Concern | Default / gate |
|---------|----------------|
| Host | LAN bind + `MEMNET_MCP_HTTP_TRUSTED_HOSTS` |
| Token | Non-empty `MEMNET_MCP_HTTP_TOKEN`; Cursor `Authorization: Bearer …` |
| `view=` | Omit → shell-safe default; teach `shell` / `interior` first |

**MUST NOT** advertise empty-token LAN MCP as safe.

### 5. Working memory ≠ corpus

| MUST | MUST NOT |
|------|----------|
| Keep retrieve / generate / remember unfused. Goldfish = serial cue then `pin_map` | Add `rag_query` (or equivalent) to `memnet-mcp` |
| Host search MAY propose **locators** into MutateGate / ingest; skip is valid | Store embeddings or chunk bodies as the memory surface |
| [#73](https://github.com/chouswei/MemNet/issues/73) `find` is **graph** lookup (seed nodes only; then `pin_map` from labels+props), not corpus RAG. Do **not** teach copy-id then `--anchor`. When \(|Q|>1\), CueConflict on emit (0.10) | Run HippoRAG PPR / Graphiti RRF / OpenIE / ANN **inside** the engine |

Design: [`extras/memnet-host-search-nest.md`](extras/memnet-host-search-nest.md). Math: [`grammar/math-skeleton.md`](grammar/math-skeleton.md). Research: [#77](https://github.com/chouswei/MemNet/issues/77).

---

## Related

| Path | Role |
|------|------|
| [`SHAPE.md`](SHAPE.md) | Product shape from the problem (identity SSOT) |
| [`extras/memnet-session-strata.md`](extras/memnet-session-strata.md) | Sessions as strata (not Layer); 0.15 catalog |
| [`../README.md`](../README.md) | Doctrine / how to run |
| [`adr/ADR-001-gql-agent-wire.md`](adr/ADR-001-gql-agent-wire.md) | GQL wire; no Layer |
| [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md) | **M1 SSOT** |
| [`cabinet/agensgraph-buffer.md`](cabinet/agensgraph-buffer.md) | Durable GQL store adapter (**M2.5**) |
| [`cabinet/neo4j-buffer.md`](cabinet/neo4j-buffer.md) | Second cabinet client (extra **0.14** live claimed) |
| [`grammar/math-skeleton.md`](grammar/math-skeleton.md) | 0.5 Recall/Commit math |
| [`extras/memnet-host-search-nest.md`](extras/memnet-host-search-nest.md) | Host search nest (0.17; skip valid) |
| [`application-notes/examples/inverting-amplifier-gql-case-study.md`](application-notes/examples/inverting-amplifier-gql-case-study.md) | InvAmp GQL case study |
| [`../sysml-models/README.md`](../sysml-models/README.md) | Nested SysML outline |
| [`../parts/memnet-mcp/README.md`](../parts/memnet-mcp/README.md) | HTTP env / Pi paste |
| [`operations/multi-agent-sessions.md`](operations/multi-agent-sessions.md) | Multitask transport MUST |
| [`../.cursor/mcp.json.example`](../.cursor/mcp.json.example) | `memnet-pi` primary |
