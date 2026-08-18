# LLM SysML v2 modeling

> **Dialect (1.x):** **GQL only** — [`../grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md). Do **not** teach Layer / Tier A. Product shape: [`../SHAPE.md`](../SHAPE.md).

**Application example (documentation only).** Long-form SysML v2 textual modelling: MemNet is **session goldfish**; the live `.sysml` tree is **structural SSOT**. Complements user-pack `sysml-memnet-documentation` (when installed).

**Teach:** openCypher-shaped GQL + shaped `pin_map` + gated mutate. Electrical law-leaf wire (InvAmp) is a **different grain** — [`examples/inverting-amplifier-gql-case-study.md`](examples/inverting-amplifier-gql-case-study.md).

British English. ASCII.

---

## 1. Problem

The modeller is goldfish. Chat is not SSOT. Dumping the model (or the whole session) burns tokens. Corpus RAG searches documents, not this campaign’s `TSK` / locators.

| Store | SSOT for |
|-------|----------|
| **`.sysml` files** (git) | Structure, satisfy / trace, names |
| **MemNet session** | Live `TSK` / `USR` / `DEC`, **confirmed** locators, ingest pins |
| **Host search** (optional) | May propose locators only — MUST NOT Snap-on-session |

MemNet is not a SysML clone and not GraphRAG. Do **not** import product `MemNetRequirements` into a downstream load tree.

---

## 2. What lives in the graph

Path-B ingest (`ingest_sysml`) commits **PKG | PRT | REQ | POR** with deterministic locators (`path=`, `qname=`, `requirementId=`). **No client `NEW`** on those pins.

Campaign locators (`MOD` / `SYM`) and goldfish rows (`TSK` / `USR` / `DEC`) need **SCHEMA in the open map**. Kinds **not** in the map fail `unknown_tag`.

| Kind | Role | Default map |
|------|------|-------------|
| `PKG` / `PRT` / `REQ` / `POR` | Ingest atoms (connection/item/action defs ingest as **`PRT`**, not a separate `CON` / `BEH` tag) | `schema.sysml.example.txt` |
| `MOD` / `SYM` | File + symbol locators (path, line hint) | `schema.coding.example.txt` |
| `TSK` / `USR` | Campaign and modeller constraints | both maps |
| `DEC` | Open forks (`recycle=delete_on_settle`) | coding map |

Do **not** teach `ART` / `SEC` / `CLM` / `CON` / `BEH` / `ITM` / `ISSUE` unless you add matching `SCHEMA` lines. Ingest will not mint those labels.

Background enters the next call only via `pin_map` neighbourhood — no “remember the other file.”

---

## 3. Open the session (map)

`session_open` requires a map (`map_file` or `map_lines`). MCP arg is **`session`**, not `session_id`.

**Wrong:** game `schema.example.txt` — ingest then fails `unknown_tag|PKG not in schema`.

**Right:** union SysML ingest + coding locators in `map_lines` (LAW / EDG merge automatically). Raise `max_nodes` on ingest for large trees (default 200; this repo’s `requirements.sysml` needs ~200).

Then `ingest_sysml(path=…, max_nodes=…)` (or CLI `memnet ingest sysml --path …`). Copy returned `@ANCHORS` / ids; **do not** invent ingest ids.

---

## 4. Goldfish loop (each turn)

This is **Recall Shape** of \(S\), not host **Snap**.

1. **Cue then `pin_map`** — known `TSK_*` id (or `read_list` for tag `TSK`). Skip extra topic pins when that neighbourhood covers them. Empty seed ⇒ skip (do not invent). Leftover LIMIT find is **not** claimed (#73).
2. **Locate then edit** — from `SYM` / ingest pin → narrow Read/grep → edit `.sysml`. Never trust stale `SYM.line` without re-check.
3. **Validate** — project SysML v2 MCP / `validate` on the load config until clean (tool name is host-specific; this repo does not ship `mcp-sysml-v2`).
4. **Doc sync (conditional)** — host `sysml-view-doc-sync` (or equivalent) only if `outputs/` changed.
5. **Sparse Commit** — gated GQL `add`/`update`; refresh `SYM.line`; settle transients. Writeback is mutate, not Path-B absorb.
6. **Loop** — settle finished `TSK` (`recycle=delete_on_settle` when done).

`serve_status` only if TCP/shared; skip under in-process MCP. If serve/MCP is down: edit `.sysml` only and treat the graph as stale.

After heavy settlement, optional `housekeep prune recyclable --apply`. Ingest pins are not recyclable campaign junk.

---

## 5. Mutate vs display

**Create (goldfish rows):** `id: 'NEW'` — engine mints; copy from the next pin map.  
**Ingest / locator pins:** ground ids from ingest or locators — `NEW` illegal.  
**Update / settle:** known ids only.

Shaped **display** (copy ids; not a mutate payload):

```cypher
(:TSK {id:'TSK_model_pdu', goal:'Model 6U CubeSat PDU', status:'in_progress'})
(:MOD {id:'MOD_pdu', path:'project/pdu-controller.sysml', summary:'PDU controller part', status:'active'})
(:SYM {id:'SYM_PDUController', name:'PDUController', kind:'partDef', path:'project/pdu-controller.sysml', line:12, status:'active'})
(:SYM {id:'SYM_PDUController'})-[:inFile {id:'E04'}]->(:MOD {id:'MOD_pdu'})
```

Sparse **mutate** after a validated edit (illustrative):

```cypher
CREATE (d:DEC {id:'NEW', task:'TSK_model_pdu', question:'Command channel', options:'UART / GPIO', recycle:'delete_on_settle'})
MATCH (s {id:'SYM_PDUController'}) SET s.line = 58
```

Relationships: `MATCH` both ends by known `id`, then `CREATE (a)-[:TYPE {id:'NEW'}]->(b)`. Teach `:declaredIn`, `:typedBy`, `:inFile`, `:about`, `:owns`. Do **not** invent ports on locator rows to force `:bind` unless the atom is a true electrical law leaf (`:CST`).

---

## 6. Electrical vs SysML grains

| Grain | Shape | Doc |
|-------|-------|-----|
| SysML / locator | `PKG`/`PRT`/`REQ`/`POR` + `MOD`/`SYM` + bare-id relationships | this note |
| Electrical (GQL) | `:CST` + `ports` + `law` + `:bind` | [`llm-circuit-schematic.md`](llm-circuit-schematic.md) |

Same device may appear in both — keep ids stable; relate across grains with bare-id relationships. Do not put Ohm/KCL on SysML locator rows.

---

## 7. Multitask

Shared TCP/HTTP session (not default in-process): [`llm-system-dev-multitask.md`](llm-system-dev-multitask.md) and [`../multi-agent-sessions.md`](../multi-agent-sessions.md). Handoff = **session id**; peers re-`pin_map`. Prefer **import** for path-B member slices. Chat is never SSOT.

---

## 8. Pitfalls

| Mistake | Fix |
|---------|-----|
| Game `schema.example.txt` then ingest | SysML + coding SCHEMA union |
| Client `NEW` or invented ids on ingest pins | Copy locators from `ingest_sysml` |
| Teaching `CON`/`BEH` as ingest labels | Ingest maps those defs to **`PRT`** |
| `query_warm` / Layer / `@TAG` as primary | GQL + `pin_map` |
| “Snap loop” as host RAG of \(S\) | Goldfish `pin_map`; Snap is corpus locators only |
| `CREATE` with a client-chosen `id` for `DEC` | `id:'NEW'` then copy |
| Prose blobs in `USR` / extra claim rows | Distilled codes / short values |
| Dual-teaching Layer ASCII | Typed GQL relationships |
| `rag_query` / ANN of the session | Forbidden by product shape |

---

## 9. Related

- [`../SHAPE.md`](../SHAPE.md) — product shape this note applies
- [`../LLM-GUIDE.md`](../LLM-GUIDE.md) — Path-B ingest table
- [`../grammar/gql-wire-profile.md`](../grammar/gql-wire-profile.md)
- [`llm-system-dev-multitask.md`](llm-system-dev-multitask.md)
- [`llm-circuit-schematic.md`](llm-circuit-schematic.md) — electrical GQL
- `parts/common/memnet/memnet/examples/schema.sysml.example.txt`
- `parts/common/memnet/memnet/examples/schema.coding.example.txt`
- `~/.cursor/skills/sysml-memnet-documentation/` (user pack; not in this repo)

---

## 10. Retired dialects (pointer only)

Older `@PKG` / `@EDG` pipe or Layer ASCII seeds are **not** agent teach. Archive: [`../grammar/archive/`](../grammar/archive/).
