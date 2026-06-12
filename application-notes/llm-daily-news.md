# LLM Daily News Digest — A MemNet Application Note

**Application example (documentation only).** This file is a self-contained *pattern* for a **multi-stage RSS digest pipeline** with session-scoped working memory — not part of the MemNet engine. The graph is built incrementally during one run, queried for analysis, and drives final prose synthesis; readers see Markdown/HTML briefings, not raw graph wires.

**Project:** `daily-news` — automated RSS digest with China-source fact-checking  
**Bridge module:** `memnet_bridge.py`  
**Schema map:** `memnet_schema.txt`  
**Orchestrator:** `generate.py`  
**Runtime:** Raspberry Pi 5, Gemma 4 E4B (llama.cpp, port 8081)

This note describes how MemNet is used as the **working memory and knowledge graph** for a multi-stage LLM news pipeline. The graph is built incrementally during one pipeline run, queried for analysis, and then drives final prose synthesis. It is **not** the published output — readers see Markdown/HTML briefings, not raw graph wires.

---

## 1. Problem MemNet solves

Each day the pipeline ingests ~100 RSS articles across six sections. The LLM cannot hold all articles in context at once. MemNet provides:

1. **Structured ingest** — every article becomes graph nodes and edges as it arrives.
2. **Shared vocabulary** — keyword tokens (`@KYWD`) are session-wide; repeated terms reuse one node and accumulate edges.
3. **Cross-article linkage** — the same keyword in two stories joins through one `@KYWD` node plus `ENT --supports-->` edges.
4. **Layered analysis** — theme clusters (`@CLU`) and narrative arcs (`@SYN`) sit above raw readings.
5. **Prompt-safe views** — formatters turn graph state into bounded text blocks for each LLM stage.

MemNet acts as **short-term, run-scoped memory** (TTL 120 minutes), not a permanent archive.

---

## 2. Pipeline overview

```mermaid
flowchart TB
  RSS[RSS fetch] --> S0[Graph skeleton DAY + SEC]
  S0 --> S1[Stage 1: per-article LLM atomise]
  S1 --> KYWD[@KYWD map + EDG edges]
  KYWD --> FIN[finalize: THM continues + FC]
  FIN --> S2a[CLU theme clusters]
  S2a --> S2b[Stage 2: analyst LLM → SYN]
  S2b --> S3[Stage 3: news prose]
  S2b --> S4[Stage 4: investment prose]
  S3 --> OUT[index.html / index.md]
  S4 --> OUT
```

| Stage | MemNet role | LLM |
|-------|-------------|-----|
| Ingest skeleton | `DAY`, `SEC`, per-article `ENT`/`SRC`/`THM` | No |
| Stage 1 | `KYWD` nodes, supports/covers/relates edges | Yes — ATOMS + EDGES + POLARITY |
| Finalize | `THM --continues-->`, `@FC` fact-check nodes | No |
| Stage 2a | `@CLU` clusters from theme readings | No |
| Stage 2b | `@SYN` narrative arcs | Yes — reads keyword map first |
| Stage 3/4 | Query warm → graph context; SYN briefing → prose | Yes — editorial output |

---

## 3. Session policy

Configured in `MemNetBridge.ensure_session()`:

| Setting | Value | Meaning |
|---------|-------|---------|
| `SESSION_TTL_MINUTES` | 120 | Session expires after two hours |
| `memnet_session.id` | persisted | Resume same-day run if interrupted |
| `memnet_session.day` | ISO date | Fresh session when calendar day changes |
| `memnet.snapshot.txt` | persisted | Same-day snapshot reload |

**Fresh session:** `session open --map-file memnet_schema.txt --ttl 120`  
**MCP:** `session_open(map_lines=…, ttl=120, seed_lines=[…])` — seed block in one call  
**Resume:** `session resume <id>` if session day matches today  
**Reload:** `session load --file memnet.snapshot.txt` as fallback

Seeded on every fresh session (via `add` or MCP `seed_lines`):

```
@CFG: CFG01|daily_news|CFG01|3|knowledge_graph_digest
@LAW: LAW01|atomise|on_add|tokens_only|no_sentences_in_fields
@LAW: LAW02|graph|on_add|use_edg|relations_via_EDG_not_field_lists
@LAW: LAW03|short_term|on_read|session_scoped|strong_memory_within_run_only
```

These `@LAW` nodes document design constraints for downstream tooling and humans.

---

## 4. Schema map (`memnet_schema.txt`)

| Tag | Fields | Role |
|-----|--------|------|
| `@CFG` | id, pipeline, anchor, version, notes | Graph anchor (`CFG01`) |
| `@DAY` | id, date, slug, status, recycle | One node per digest day |
| `@SEC` | id, name, date, status, recycle | Section (politics, taiwan, …) |
| `@ENT` | id, kind, slug, keywords, date, status, recycle | Article entity |
| `@SRC` | id, outlet, url, tier, date, recycle | Source outlet |
| `@THM` | id, category, slug, keywords, first_seen, last_seen, status, recycle | Thematic thread |
| `@KYWD` | **id, edge_num** | Keyword token; id = plain token |
| `@CLU` | id, slug, arc, cites, date, tone, recycle | Theme cluster |
| `@SYN` | id, section, arc, cites, date, priority, recycle | Narrative arc for synthesis |
| `@FC` | id, slug, outlet, verdict, date, flags, recycle | Fact-check result |
| `@INV` | id, ticker, sector, stance, keywords, date, risk, recycle | Investment pick |

**Design choice — minimal `@KYWD`:** The node carries only `token|edge_num`. Type comes from the `@KYWD:` tag; semantic links live on `@EDG` rows, not duplicated in node fields.

---

## 5. Wire format examples

### Keyword node (batched upsert per article)

```
@KYWD: trump|11
@KYWD: war|6
```

`edge_num` = **node degree** — count of all incident edges:
- `ENT --supports--> token`
- `THM --covers--> token`
- `token --relates--> other` (both endpoints increment)

Nodes are **not** re-upserted after every edge. During `apply_article_reading()`, degrees are updated in memory; at article end, touched tokens are flushed once:

```python
self._upsert(f"@KYWD: {token}|{self._kywd_edge_num[token]}")
```

### Structural edges (three layers)

```
@EDG: E…|ENT20260612001|supports|trump|auto|persistent
@EDG: E…|THMirn_war_live_up|covers|trump|auto|persistent
@EDG: E…|trump|relates|war|auto|persistent
```

| Edge | Meaning |
|------|---------|
| `ENT --supports--> {token}` | Article mentions keyword |
| `THM --covers--> {token}` | Theme owns vocabulary |
| `{token_a} --relates--> {token_b}` | LLM semantic link within/across stories |

`DAY`/`SEC` do **not** link directly to `@KYWD`; reachability is via `ENT --part_of--> DAY` and `SEC --covers--> ENT`.

### Article ingest skeleton

```
@ENT: ENT20260612001|event|iran_war_live|iran,war,trump|2026-06-12|active|persistent
@SRC: SRC20260612001|nytimes|https://…|tier1|2026-06-12|persistent
@EDG: E…|SRC20260612001|reports|ENT20260612001|…
@EDG: E…|ENT20260612001|part_of|DAY20260612|…
@EDG: E…|SEC_politics|covers|ENT20260612001|…
@EDG: E…|THMirn_war_live_up|covers|ENT20260612001|…
```

---

## 6. Edge relations used

Declared in `RELATIONS` and written via `_edge()`:

| Relation | Typical use |
|----------|-------------|
| `reports` | SRC → ENT |
| `part_of` | ENT → DAY, CFG → DAY |
| `covers` | DAY/SEC → ENT/CLU/SYN/FC/INV; THM → ENT, THM → KYWD |
| `continues` | THM → THM (cross-session theme overlap ≥ 0.35) |
| `supports` | ENT → KYWD |
| `relates` | KYWD → KYWD; CFG → THM |
| `corroborates` / `contradicts` | FC → ENT |
| `clusters` | THM → CLU |
| `summarizes` | SYN → CLU |
| `draws_on` | CLU/SYN → KYWD |

Edge IDs are truncated to 80 characters: `E{src}{relation}{dst}`.

New relations use `--allow-new-relation` on first write.

---

## 7. Stage 1 — per-article atomisation

**Entry:** `ingest_articles_one_by_one()` in `generate.py`  
**Graph step:** `ingest_article_graph()` → rule-based ENT/SRC/THM  
**LLM step:** `apply_article_reading()` → updates ENT keywords and KYWD graph

### LLM output format

```
ATOMS: trump,iran,deal,war,strikes
EDGES: trump->deal, iran->war, deal->strikes
POLARITY: caution
```

### Connectivity guarantees

No keyword node should exist without at least one `relates` edge in the article subgraph:

1. If the LLM omits `EDGES`, `fallback_kywd_edges()` builds title→body links.
2. `ensure_kywd_connectivity()` wires any remaining orphan tokens to the title hub.

Structural `supports`/`covers` edges always exist for linked tokens; the log line **“N relates”** counts keyword↔keyword edges only.

### In-memory bookkeeping (reset in `begin_daily_graph()`)

| Structure | Purpose |
|-----------|---------|
| `_kywd_by_token` | token → id (plain token) |
| `_kywd_edge_num` | token → degree |
| `_kywd_ent_links` | token → set of ENT ids |
| `_kywd_thm_links` | token → set of THM ids |
| `_kywd_relates_pairs` | directed `(a,b)` → article count |
| `_ent_to_cite` | ENT id → citation number |
| `_reading_meta` | cite → tokens, polarity, edges, section |

After Stage 1, `format_kywd_stats()` reports session totals, e.g.:

```
MemNet KYWD: 842 unique, 1204 supports, 980 covers, 456 relates, top hubs: trump(11), war(8), …
```

---

## 8. Stage 2 — session keyword map

**Formatter:** `format_kywd_map_for_prompt()`  
**Consumer:** `build_graph_analysis_prompt()` — map is the **first** input block

Example output:

```
SESSION KEYWORD MAP (built from 62 articles):

HUBS (by edge_num on @KYWD node):
  trump(11), taiwan(8), war(6), …

INTER-EDGES (keyword relates, LLM + deduplicated):
  trump -> war (3 articles)
  war -> iran (2)

ARTICLE LINKS (ENT supports):
  trump <- [25, 26, 35]
  war <- [26, 28]

THEME LINKS (THM covers):
  trump <- THMirn_war_live_up, THMtrump_deal_close
```

Display caps: 30 hubs, 100 inter-edges, 20 article-link rows, 20 theme-link rows (from top hubs).

### CLU and SYN layers

**`build_theme_clusters()`** — groups `_thm_readings` into `@CLU` nodes; links `CLU --draws_on--> KYWD`.

**Stage 2 LLM** — produces per-section `ARC`, `CITES`, `PRIORITY` blocks.

**`store_syn_analysis()`** — persists `@SYN` nodes; links `SYN --summarizes--> CLU`, `SYN --draws_on--> KYWD`.

Deterministic fallback: `build_syn_from_clu()` if LLM parse fails.

---

## 9. Graph context for prompts

| Method | Used by | Content |
|--------|---------|---------|
| `format_kywd_map_for_prompt()` | Stage 2 | Aggregated keyword map |
| `format_readings_for_prompt()` | Stage 2 | Per-cite atoms, edges, polarity |
| `format_graph_for_prompt(raw)` | Stage 2, 3, 4 | Edge list from `query warm` |
| `format_reorganized_for_prompt()` | Stage 3 | SYN + CLU briefing |

**Query:** `query warm --anchor CFG01 --depth 3 --max-rows 500`

**Edge prioritisation** in `format_graph_for_prompt()` (cap 250 edges):

1. KYWD `--relates-->` KYWD  
2. ENT `--supports-->` KYWD  
3. THM `--covers-->` KYWD  
4. All other edges  

Stage 3/4 receive **SYN editorial briefing** (prose-oriented), not the raw keyword dump. The keyword map is working memory for Stage 2 only.

---

## 10. MemNet CLI usage from Python

```python
# Wrapped by MemNetBridge._cmd() — or MCP session_open(..., seed_lines=SEED)
send_command(["session", "open", "--map-file", "memnet_schema.txt", "--ttl", "120"])
send_command(["add", "--stdin"], stdin="\n".join(SEED))  # skip if MCP seed_lines used
send_command(["update", "--stdin"], stdin="@KYWD: trump|11")
send_command(["query", "warm", "--anchor", "CFG01", "--depth", "3", "--max-rows", "500"])
send_command(["session", "save", "--file", "data/memnet.snapshot.txt"])
```

Upsert pattern in bridge:

```python
def _upsert(self, wire: str, *, new_relation: bool = False) -> None:
    resp = self._cmd(["update", "--stdin", *extra], stdin=wire)
    if not self._ok(resp):
        self._cmd(["add", "--stdin", *extra], stdin=wire)
```

Remote `memnet serve` (e.g. on Raspberry Pi) requires serve **≥ 0.2.7** for `add`/`update --stdin` over TCP.

---

## 11. Atomisation helpers

Shared token extraction (LAW01 — tokens only, no sentences in fields):

```python
atom_tokens(text, max_tokens=8)   # "trump,iran,war"
atom_slug(text, max_len=28)       # "iran_war_live"
atom_outlet(name)                 # "nytimes"
kywd_id_from_token(token)         # plain token, max 48 chars
```

Stop-word filtering and deduplication are applied before tokens enter the graph.

---

## 12. Operational notes

### Running the pipeline

```bash
cd /home/instmeasure/daily-news
venv/bin/python3 -u generate.py
```

Progress: `data/generate.progress`  
Graph log: `data/memnet_graph.log`  
Stage 2 output: `data/{date}.graph_analysis.txt`

### Schema migration

When `@KYWD` field layout changes, delete stale session files before the next run:

```bash
rm -f data/memnet.snapshot.txt data/memnet_session.id data/memnet_session.day
```

Old 5-field `@KYWD` rows (`id|keyword|date|status|recycle`) are incompatible with the current 2-field schema.

### MemNet availability

If `probe()` fails, `generate.py` continues without graph ingest, using RSS briefing fallbacks for synthesis.

---

## 13. Design patterns for other MemNet applications

1. **Separate ingest skeleton from LLM enrichment** — create stable ENT/SRC nodes first; LLM updates keywords and semantic edges later.
2. **Minimal nodes, rich edges** — store connectivity in `@EDG`; keep node fields small and machine-readable.
3. **Session-scoped working memory** — use TTL sessions for batch pipelines; persist snapshot for crash recovery within the same day.
4. **Hub metric on nodes** — `@KYWD: token|edge_num` gives analysts a quick salience signal without parsing the full edge list.
5. **Layered summarisation** — raw readings → clusters → narrative arcs → prose; each layer is its own node type.
6. **Prompt formatters as views** — never pass raw `query warm` output directly to creative LLM stages; sort, cap, and label.
7. **Bookkeeping mirrors graph** — maintain in-memory indexes (`_kywd_relates_pairs`, `_ent_to_cite`) for O(1) map assembly instead of re-parsing MemNet output.
8. **Batched writes** — defer node upserts until end of logical unit (one article) to avoid O(edges) round-trips.

---

## 14. File reference

| File | Role |
|------|------|
| `memnet_schema.txt` | Map file for `session open` |
| `memnet_bridge.py` | All graph ingest, formatters, session lifecycle |
| `generate.py` | Pipeline orchestration, LLM prompts, Stage 1 connectivity |
| `data/memnet.snapshot.txt` | Saved session state |
| `data/memnet_session.id` | Active session id |
| `data/memnet_session.day` | Session calendar scope |
| `data/memnet_graph.log` | Human-readable ingest trace |

---

## 15. Related constants

```python
SESSION_TTL_MINUTES = 120
SYNTHESIS_QUERY_MAX_ROWS = 500
SYNTHESIS_GRAPH_MAX_EDGES = 250
MAX_ATOMS_PER_ARTICLE = 128
KYWD_MAP_MAX_HUBS = 30
KYWD_MAP_MAX_RELATES = 100
KYWD_MAP_MAX_STRUCTURAL = 20
```

---

**This file is one documented application example.** Use it as a template for batch LLM pipelines on MemNet: session-scoped working memory, hub metrics on minimal nodes, layered `@CLU`/`@SYN` summarisation, and prompt formatters as views over `query warm`. For interactive creative loops see `application-notes/llm-novel-writer.md`; for shared-world multiplayer see `application-notes/llm-mud.md`; for engine behaviour see `LLM-GUIDE.md`.

*This application note reflects the `daily-news` codebase as of June 2026. For pipeline scheduling and published page layout, see `.cursor/skills/daily-news-pipeline/reference.md` in the `daily-news` project.*
