# Goldfish-loop efficiency gap (0.19.c plan)

**Status:** unshipped / not a SemVer claim / not TARGET until measured.

**Cut:** Hatch package stays **0.19.3**. This plan is **`0.19.c`** — same usage method (`cue → pin_map → mutate → pin_map`). It does **not** invent a **0.20**. It does **not** claim **1.0**.

**SSOT for this cut.** Later engine work follows this note. ROADMAP already names pure efficiency as `0.19.c`; this file is the gap plan that ROADMAP points at.

Wire: GQL only. Two operators: Recall = `pin_map` (bounded `find` when the seed is unknown); Commit = `mutate`. Absorb / ingest are rules, not verbs.

---

## 1. Frame

A goldfish turn is:

```text
cue  →  pin_map  →  mutate  →  pin_map
```

Efficiency owns **wall-clock** and **token waste** on that loop (engine + MCP façade + optional Snap / cabinet behind the session). It does **not** own a new agent step.

**MN-REQ-00** (cache-hit dump vs Shape+Flash) stays **unmeasured**. This plan does **not** ship a dump SKU. Measure dump vs Shape if needed for honesty; do not productise dump.

**1.0** does not wait on this cut. **N-server (#47)** stays Later research.

Until a loop timer exists, ranks below are **mechanism cites**, not millisecond claims.

---

## 2. As-is costs (this checkout)

Cites are `file:function` under `parts/common/memnet/memnet/` unless noted.

### 2.1 Recall — `pin_map`

| Cost | Cite | What happens |
|------|------|----------------|
| Cue then k-hop | `pin_map_composer.py` `PinMapComposer.compose` | Kind/locator/keyword → `bounded_match_find`; leftover nicknames; else empty-q outline. Seeded Shape: `MemStore.context_pack` BFS, then `view=shell` truncates **after** the walk (`apply_shell_soft_cap`, 8 nodes / 12 edges). Default MCP `depth=2`, `max_rows=50`. |
| Shaped emit lookups | `record_to_gql_line` / `_endpoint_shaped` / `emit_gql` | Each **edge** re-resolves both ends (`store.resolve_one`) and emits full shaped node patterns again. Nodes already listed as their own lines are rebuilt on the edge line. |
| Empty-q outline | `compose_session_outline` | `list_records` of all non-EDG rows, bucket by kind, LIMIT exemplars (`OUTLINE_EXEMPLAR_LIMIT` = 3 in `config.py`). No edges; SHALL NOT absorb. |
| Bounded find | `bounded_match_find` | `list_records(kind)` or all non-LAW/EDG, then Python locator + keyword filters, then `hits[:limit]` while `total=len(hits)` (full pass). |
| Codebook miss | `peak_l.py` `peak_l` (from `compose` on non-empty miss) | Last-resort residual cue (0.18). Another full `list_records` + incident walks. Not default goldfish. |

`Caps.max_depth` = 4, `max_fanout` = 256 (`config.py`). Raising \(M\) / `max_rows` is **out** of this cut.

### 2.2 Commit — `mutate` (double parse + leftover lower)

| Cost | Cite | What happens |
|------|------|----------------|
| Product mutate | `mutate_gate.py` `MutateGate.apply` → `_apply_gql` | Joins lines; `self.codec.parse(text)`; then pattern MATCH / MERGE / absorb / upsert. |
| Codec | `gql_codec.py` `GqlCodec.parse` | Delegates to `gql.parse`. |
| GraphGlot front | `gql.py` `_accept_parse` → `gql_parse_front.py` `parse_program` | Per statement: `quote_reserved_idents` then GraphGlot `Dialect.parse`. |
| ProductGqlGate | `gql_parse_front.py` `gate_programs` | ROADMAP Later name **ProductGqlGate**. Forbids WITH / UNWIND / CALL / RETURN after GraphGlot parse. **Does not lower.** |
| Leftover lower | `gql.py` `parse` then `parse_statement` | Second, hand parser that actually yields `NodeRec` / `EdgeRec`. Every Commit statement is parsed **twice**. |
| Pattern scan | `MutateGate._pattern_hits` | Hid shortcut, else `store.match_nodes` (kind index then property loop). Absorb retargets via `list_records("EDG")` of **all** edges. |

Path-B ingest pays the same Commit stack: `pin_map_ingest.py` `PinMapIngestBase.commit` builds GQL then `MutateGate.apply(..., mode="add")`.

### 2.3 Snap — session mint + ingest-as-mutate

`catalog_snap.py` `snap_model`: one `open_session` for the catalog, then **one `open_session` per interior**, then `PinMapIngest_Sysml.commit` (full GQL mutate of projected CREATE/MATCH lines). Interiors stay **live** in the registry (rollback closes only on exception). Look is later `pin_map` with `session=`. Join is slice absorb, not Absorb of whole \(S\).

`Caps.max_sessions` default **1024**. TTL default 60 minutes, **sliding on every `get_session`** (`session.py`).

### 2.4 Cabinet — hydrate/flush (ego slice, not a mutate delta)

| Cost | Cite | What happens |
|------|------|----------------|
| Hydrate | `durable/agensgraph.py` / `neo4j.py` `hydrate` | Loop `_HYDRATE_MATCH_KEYS = (_memnet_hid, "id")` — leftover **nickname `id` after hid miss**. Then a second query for edges among hydrated hids. Agens node walk is `OPTIONAL MATCH (ego)-[*0..depth]-(n)`. |
| Flush | `flush` in both adapters | **One MERGE per node and per edge**, keyed on `_memnet_hid` (not `{id}`). Agens: one transaction of N statements. Neo4j: **auto-commit each** `session.run`. |
| Slice rebuild | `durable/sync.py` `DurableSyncOwner.flush_from_session` | Rebuilds the slice with `context_pack` (ego neighbourhood), **not** a Commit delta. Hydrate upserts every returned record into the live session. |

Default cabinet AgensGraph; Neo4j is the second adapter. **Do not vendor a server.** LLM ↔ Bolt stays forbidden.

This is **not** a dump of whole \(S\) on every goldfish turn unless the host calls hydrate/flush. When called, it is **ego-bounded neighbourhood**, still rebuilt rather than a mutate delta.

### 2.5 MCP / in-process façade

Default MCP stdio is in-process, but every tool still builds **CLI argv**:

- `parts/memnet-mcp/software/memnet_mcp/server.py` `_run` → leftover `query_warm` / `add` / `update` / `query_walk` / `read_list` still registered beside product `pin_map` / `find` / `mutate`
- `client.py` `run_memnet` → `in_process_engine.py` `run_argv` (Typer `cli.app`, stdio capture)
- TCP (`MEMNET_MCP_TRANSPORT=tcp`) adds a serve hop. Streamable-HTTP is a further process hop.

Leftover tools are **token / teach noise** on the goldfish turn if the model lists or calls them. Unregistering them would change the tool surface (**`b`** — excluded).

### 2.6 In-memory session (no copy-on-pin)

| Fact | Cite |
|------|------|
| Same RAM graph | `session.py` `get_session` returns `SessionStore` over the registry entry; **no copy-on-pin** |
| Cap / TTL | `Caps.max_sessions` 1024; sliding TTL on access; `purge_expired` on get/open/list |
| Whole-\(S\) file | `snapshot.py` `snapshot_text` dumps map + relations + `write_order` records (MN-REQ-01.4), not goldfish |
| Deepcopy | `import_absorb.py` copies records on absorb — Path-B join, not every `pin_map` |

### 2.7 What is already measured

| Artefact | Times | Goldfish loop? |
|----------|--------|----------------|
| `tests/test_efficiency.py` | Leftover `list_records` / `neighbors` (soft ms, not CI gates) | **No** |
| `scripts/benchmark_efficiency.py` | Leftover parse / `context_pack` / CLI `add` / `query warm` | **No** |
| `scripts/load_test_mud.py` | Leftover `warm` + `update` | **No** |
| CI | `ruff` + `pytest` correctness | **No** |
| ROADMAP | MN-REQ-00 dump vs Shape+Flash | **Unmeasured** |

---

## 3. Gap table

| ID | As-is | Wanted | `c` or exclude |
|----|--------|--------|----------------|
| **M0** | No timer on cue → `pin_map` → `mutate` → `pin_map` | In-process (+ optional MCP argv) wall-clock; token estimate of leftover tool list vs product-only | **`c`** — measure only; not a SKU |
| **P0-a** | MCP `pin_map`/`mutate`/`find` go through Typer argv (`run_argv`) | Same tools bind `PinMapComposer` / `MutateGate` / `bounded_match_find` in-process; CLI stays for humans | **`c`** — no new agent step |
| **P0-b** | GraphGlot `parse_program` then leftover `parse_statement` per Commit line | One parse that gates **and** lowers; ProductGqlGate still forbids WITH/UNWIND/CALL/RETURN | **`c`** if CREATE / MATCH…SET / DELETE wire is unchanged |
| **P0-c** | Edge emit re-resolves endpoints; shell cap after BFS | Cache endpoint records in `emit_gql`; apply shell caps **during** BFS | **`c`** — still one bounded Shape |
| **P0-d** | `find` / outline / Peak_L linear-scan \(S\) | Kind/locator indexes; outline stops after per-kind LIMIT | **`c`** if empty-q stays outline and find stays seed-only |
| **P1-a** | `snap_model`: 1+N `open_session` + ingest via `MutateGate` GQL | Reuse map parse; commit interiors through the store without a second GQL parse; interiors still `session=` look | **`c`** if Snap API and look loop stay the same |
| **P1-b** | Flush N MERGEs; hydrate hid-then-`id`; `flush_from_session` rebuilds via `context_pack` | Batched MERGE; skip nickname query on hid hit; flush **touched** hids from Commit | **`c`** — still hydrate/flush behind \(S\), not LLM↔Bolt |
| **P1-c** | Absorb lists all EDG | Use incident-edge indexes already on the store | **`c`** — absorb stays agent-gated (0.12) |
| **P2-a** | Leftover MCP `query_warm` / `add` / `update` / `query_walk` / `read_list` still registered | Teach: product-first descriptions; benches aim at `pin_map`+`mutate` | **`c`** if tools remain callable |
| **P2-x** | Same leftover tools | Unregister leftover MCP tools | **`b` — exclude** (agents must drop names) |
| **X-dump** | MN-REQ-00 unmeasured | Ship dump-as-Recall SKU | **exclude** (not this cut; not a SKU) |
| **X-M** | `max_rows` 50 / `max_fanout` 256 | Raise \(M\) as a speed fix | **exclude** |
| **X-rag** | No `rag_query` | Add RAG / Snap-on-session | **exclude** |
| **X-47** | N-server Later | Reopen #47 as efficiency | **exclude** (not a `b`; not this cut) |

---

## 4. Order

Measure first, then cheapest **same-loop** wins. Do not implement from this note until M0 numbers exist.

1. **M0 (must first).** Time in-process `pin_map` + `mutate` + second `pin_map` on a fixture session (and one `snap_model` separately). Optional: same loop via MCP argv vs direct bind. Optional: leftover tool-list tokens vs product-only. MN-REQ-00 dump vs Shape+Flash may be measured **without** shipping dump.
2. **P0** — if M0 shows façade or parse on the goldfish path: **P0-a** (MCP bind), **P0-b** (single parse), **P0-c** (emit/walk), **P0-d** (MATCH_L indexes). Pick by measured share, not by this guess order.
3. **P1** — only if interiors or cabinet are on the timed path: **P1-a** Snap mint/ingest, **P1-b** cabinet batch/delta, **P1-c** absorb edges.
4. **P2** — leftover teach/bench honesty (**P2-a**). Do **not** unregister leftover tools in this cut (**P2-x**).

Package remains **0.19.3** until a later `c` that actually ships code. This extras note is the plan, not the bump.

---

## 5. MUST NOT

- Invent **0.20** or a new extra row for efficiency.
- Claim **1.0**.
- Change usage method (new required step, new product tool, cue/loop change) — that would be a `b`, not this cut.
- Raise \(M\) / `max_rows` / dump whole \(S\) as a speed fix.
- Add `rag_query` or Snap-on-session.
- Vendor AgensGraph or Neo4j.
- Teach LLM ↔ Bolt as the miss path.
- Silent MERGE-by-name; invent a store key; put hid on the wire.
- Revive Layer / Tier A.
- Reopen N-server (#47).
- Treat leftover `add`/`update`/`query_warm` tests as the goldfish SLO.
- Implement engine changes from this note before M0.

---

## Related

- Version law: [`../ROADMAP.md`](../ROADMAP.md) (`a.b.c`; efficiency = `0.19.c`)
- Shape: [`../SHAPE.md`](../SHAPE.md)
- Wire: [`../grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md)
