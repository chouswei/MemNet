# MemNet for article breakdown

Use MemNet to **atomise a long article** into a knowledge graph — one claim per node, **`pin_map`** to load only the slice you need.

**Do not** store the full article text in the graph. Store **structure + atomic claims** (codes/keys). Prose summaries are generated in the agent turn from pin-map atoms.

Agent I/O is the **GQL wire** (shaped pin_map + openCypher-shaped mutate) only. Do **not** emit pipe `@TAG:…` rows as mutate input.

Pair with [atomisation.md](atomisation.md) and [wire-format.md](wire-format.md).

**Full instrument-manual / SCPI pattern:** see MemNet repo `docs/application-notes/domains/llm-tech-docs-decomposition.md` — `CMD` rows, procedure layers, RTO remote-mode worked example.

## When to use

| Situation | Use MemNet? |
|-----------|-------------|
| Long article; summarise section-by-section across turns | **Yes** |
| Compare claims across sections or two papers | **Yes** — `CLM` + `supports` / `contradicts` edges |
| Cross-check article against your project (code, SysML) | **Yes** — link `CLM` to `SYM` / `REQ` via edges |
| Instrument manual; drive SCPI remotely | **Yes** — extend map with `CMD`; see tech-docs note above |
| Read once, never reference again | **No** |
| Need exact verbatim quotes often | Store **short** `CLM` code + source locator; not full paragraphs |

## Tag map (session_open map_lines)

Map lines declare kind schemas (field names). Prefer shared-dialect style keys:

```text
SCHEMA ART ; fields=title source kind status recycle
SCHEMA SEC ; fields=heading order status recycle
SCHEMA CLM ; fields=type code status recycle
SCHEMA ENT ; fields=name kind code recycle
SCHEMA TSK ; fields=goal deadline status recycle
```

| Kind | Role |
|------|------|
| `ART` | Document root (title, URL/file, `kind`: paper\|blog\|spec) |
| `SEC` | Section — `heading` short, `order` numeric |
| `CLM` | **One atomic claim** — `type`: fact\|stat\|method\|conclusion\|quote; `code` = distilled (≤ ~12 words) |
| `ENT` | Entity — person, org, concept, metric (`kind` + short `code`) |
| `TSK` | Analysis job — e.g. "summarise section 3", "extract methods" |
| `EDG` | `contains`, `part_of`, `mentions`, `supports`, `contradicts`, `cites`, `owns` |

## Breakdown loop

```text
1. session_open(map_lines=[...])
2. add ART + TSK_breakdown (GQL / openCypher-shaped)
3. Per section:
     add SEC
     split into CLM rows (one idea each)
     add ENT for named entities
     add edges: ART→SEC, SEC→CLM, CLM→ENT
4. Each turn: pin_map(kind='SEC', locators=['heading=…'])  # or TSK by goal
5. Generate summary / synthesis from pin-map slice only
6. settle TSK when article pass is done
```

## Example — bad vs good

**Bad** (whole article in one row — destroys token efficiency):

```cypher
CREATE (:ART {title: 'MemNet paper', source: 'memnet.md', kind: 'spec'})
CREATE (:CLM {type: 'blob', code: 'MemNet is a goldfish brain graph. You query warm. Atomisation matters…'})
```

**Good** (hierarchy + atoms):

```cypher
CREATE (:ART {title: 'MemNet agent memory', source: 'README.md', kind: 'doc'})
CREATE (:TSK {goal: 'Break down README', status: 'in_progress'})
CREATE (:SEC {heading: 'Goldfish loop', order: 1})
CREATE (:SEC {heading: 'Wire format', order: 2})
CREATE (:CLM {type: 'fact', code: 'external graph not chat'})
CREATE (:CLM {type: 'method', code: 'pin map from a cue'})
CREATE (:ENT {name: 'pin_map', kind: 'concept', code: 'primary_read'})
MATCH (a:ART {title: 'MemNet agent memory'}), (s:SEC {heading: 'Goldfish loop'})
CREATE (a)-[:contains {note: 'struct'}]->(s)
MATCH (s:SEC {heading: 'Goldfish loop'}), (c:CLM {code: 'pin map from a cue'})
CREATE (s)-[:contains {note: 'claim'}]->(c)
MATCH (c:CLM {code: 'pin map from a cue'}), (e:ENT {name: 'pin_map'})
CREATE (c)-[:mentions {note: 'term'}]->(e)
```

Cue the next turn by labels+properties. leftover `[NEW]` mint is leftover.

## MCP: open + ingest one section

```text
session_open(map_lines=[
  "ART: id|title|source|kind|status|recycle",
  "SEC: id|art|heading|order|status|recycle",
  "CLM: id|sec|type|code|status|recycle",
  "ENT: id|name|kind|code|recycle",
  "TSK: id|goal|deadline|status|recycle",
  "EDG: id|from|rel|to|note|recycle"
])
```

```text
add(wire_lines=[
  "## Nodes",
  "+ ART [A01] ; title=Design report section 3 ; source=outputs/design.md ; kind=report ; recycle=persistent",
  "+ TSK [TSK_s3] ; goal=Summarise section 3 ; deadline=1 ; status=in_progress ; recycle=persistent",
  "+ SEC [S03] ; art=A01 ; heading=Power budget ; order=3 ; recycle=persistent",
  "+ CLM [C31] ; sec=S03 ; type=stat ; code=peak 120W at launch ; recycle=persistent",
  "+ CLM [C32] ; sec=S03 ; type=fact ; code=battery 400Wh nominal ; recycle=persistent",
  "+ CLM [C33] ; sec=S03 ; type=conclusion ; code=margin 15 percent at P99 ; recycle=persistent",
  "+ ENT [EN1] ; name=PDU ; kind=component ; code=power_unit ; recycle=persistent",
  "## Edges",
  "+ E31 [TSK_s3] --(owns)--> [S03] ; note=focus ; recycle=persistent",
  "+ E32 [A01] --(contains)--> [S03] ; note=struct ; recycle=persistent",
  "+ E33 [S03] --(contains)--> [C31] ; note=claim ; recycle=persistent",
  "+ E34 [S03] --(contains)--> [C32] ; note=claim ; recycle=persistent",
  "+ E35 [S03] --(contains)--> [C33] ; note=claim ; recycle=persistent",
  "+ E36 [C31] --(mentions)--> [EN1] ; note=subject ; recycle=persistent"
])
```

Next turn — summarise **only** section 3:

```text
pin_map(kind='SEC', locators=['name=S03'], depth=2)
```

Returns LAW pins + `S03` + linked `CLM` / `ENT` (bare present) — not sections 1–2.

## Cross-section reasoning

```text
## Nodes
+ CLM [C10] ; sec=S01 ; type=fact ; code=assumed ambient 25C ; recycle=persistent
+ CLM [C40] ; sec=S04 ; type=stat ; code=measured ambient 32C ; recycle=persistent

## Edges
+ E40 [C40] --(contradicts)--> [C10] ; note=measurement ; recycle=persistent
+ E41 [C40] --(mentions)--> [C10] ; note=revises ; recycle=persistent
```

Pin-map anchor `C40` → both claims if edge-linked within depth.

## Link article to project work

```text
## Nodes
+ CLM [C50] ; sec=S05 ; type=requirement ; code=SHALL log power each orbit ; recycle=persistent
+ REQ [REQ_PWR] ; topic=orbit ; code=SHALL log power ; recycle=persistent

## Edges
+ E50 [C50] --(maps_to)--> [REQ_PWR] ; note=trace ; recycle=persistent
+ E51 [TSK_sysml] --(informed_by)--> [C50] ; note=article ; recycle=persistent
```

## Quote handling

Store **locator + short code**, not block quotes:

```text
+ CLM [C99] ; sec=S02 ; type=quote ; code=pin map not full context ; recycle=persistent
```

If verbatim text is required occasionally, keep it outside MemNet or in a file; the graph holds **where** and **what kind**, not the full quote.

## Anchors

| Anchor | Use for |
|--------|---------|
| `TSK_read` | Whole breakdown job + linked `ART` |
| `S03` | One section's claims |
| `C31` | Single claim + neighbours |
| `ENT` id | All claims mentioning an entity (via `mentions` edges) |

## Limits

- Re-read source when precision matters — atoms are **your distillation**, not OCR
- Very long papers: one `SEC` per H2/H3, not per paragraph
- Settle `TSK_read` when breakdown pass is complete; keep `ART`/`CLM` if still citing later

## Instrument manual / SCPI remote mode

Extend the tag map with `CMD`:

```text
CMD: id|sec|scpi|role|params_code|status|recycle
```

One SCPI command per row; `scpi` field uses **mixed-case long+short** canonical form (e.g. `:CHANnel1:SCALe`, `:MEASurement1:RESult?`). Wire automation order with `CLM type=procedure` + `precedes` / `requires` edges.

Mini example (GQL wire):

```text
## Nodes
+ CMD [CMD_idn] ; sec=S_cmd_common ; scpi=*IDN? ; role=query ; params_code=- ; recycle=persistent
+ CMD [CMD_run] ; sec=S_acq_remote ; scpi=:RUN ; role=set ; params_code=- ; recycle=persistent
+ CLM [CLM_capture_seq] ; sec=S_acq_remote ; type=procedure ; code=acq_mode_run_opc ; recycle=persistent

## Edges
+ E_cap_1 [CLM_capture_seq] --(precedes)--> [CMD_run] ; note=step2 ; recycle=persistent
```

Full walkthrough: MemNet `docs/application-notes/domains/llm-tech-docs-decomposition.md`. Regenerate: `python scripts/extract_rto_scpi.py`.

Cross-ref: [atomisation.md](atomisation.md) · [user-input-memory.md](user-input-memory.md) · [coding-memory.md](coding-memory.md)
