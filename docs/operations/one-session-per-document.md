# One session per document over serve

How a **product gate** keeps **one MemNet session per document** by calling `memnet-serve` on loopback. No MCP front. Synthetic proof: `scripts/probe_doc_gate_readiness.py`. Cap refuse/clip strings stay in [`../cap-contract.md`](../cap-contract.md) (unchanged on 0.19.18).

Never log a session id (`mn_…`).

## Process shape

1. Start serve on loopback. The gate talks the length-prefixed JSON argv envelope, not `memnet-mcp`.
2. Open one session per document (`session open --map-file` with the tech-docs map, or an equivalent SCHEMA).
3. Populate with product `mutate` (CREATE / MATCH…SET). Split stdin at `MEMNET_MAX_BATCH_LINES` (default 1000).
4. Read with `query pin-map` (raise `--max-rows` when the neighbourhood must exceed default \(M=50\)).
5. Close the session when the document leaves the live set. Opt-in expire snapshot if the graph must survive TTL.

Settings this gate uses:

| Knob | Value |
|------|--------|
| TTL | 60 minutes (`MEMNET_SESSION_TTL_MINUTES` or `session open --ttl 60`) |
| Save on expire | on (`MEMNET_SAVE_ON_EXPIRE=1`) plus `MEMNET_EXPIRE_SNAPSHOT_DIR` |
| Concurrent sessions | 1024 (`MEMNET_MAX_SESSIONS`) |
| Document size | about 1 800 part nodes plus a few opaque `USR` text nodes |

Ingest caps (`max_nodes=2000` / `max_edges=2000`) are Path-B ingest, not this mutate path. Session row cap remains 5000 non-LAW rows (**nodes plus edges**). `session load` of a snapshot is **not** bound by ingest budget; it walks leftover `parse_line` + `MemStore.upsert` (`MEMNET_MAX_ROWS`, max sessions, leftover value/line/`FIELD_COUNT` on a malformed pipe line).

## Request envelope (direct serve)

Length-prefixed UTF-8 JSON on TCP `127.0.0.1` (default port 18765):

```json
{"args": ["query", "pin-map", "--session", "<id>", "--cue", "SEC_0001"], "stdin": null}
```

`stdin` is omitted unless the CLI flag `--stdin` needs a body (`mutate --stdin`). Reply is only:

```json
{"exit_code": 0, "stdout": "…", "stderr": "…"}
```

There is no MCP `errors` array and no `session_id` field on this envelope. Session id appears only as `@SESSION:` on stdout. Hard refuse is stderr `@ERR: {code}|{message}` (exit 1 or 2). Mutate also prints `ok=N fail=M` on stderr.

Client helper: `memnet.serve.send_command(args, stdin=…, host=…, port=…)`. Wait default is 30 s (`SERVE_CLIENT_TIMEOUT_S`); a 1 800-node mutate batch may need a longer `timeout=` from the gate.

## Snapshot

`session save --file` writes `# memnet-snapshot-v1` via `Path.write_text` (overwrite). MemNet does **not** make that file write-once (no `O_EXCL`, no `chmod`, no immutable flag). The caller or the filesystem can.

Anything mutate accepts must save and reload as the same property values. Snapshot emit escapes every Python `str.splitlines()` separator (LF, CR, VT, FF, FS/GS/RS, NEL, LS, PS) plus `\` and `|`; load splits records on LF only. A 16 KiB string is refused at GQL CREATE/SET with `@ERR: limit_exceeded|value_bytes 16384/4096` (one decoded cap with leftover pipe and snapshot load). Unicode, `|`, quotes, CR, and newlines on a value under the cap round-trip. Undeclared RAM keys persist by widening the snapshot SCHEMA; extras over `max_fields` refuse `snapshot_unsaveable`.

Expire: with save-on-expire and a dir, TTL drop writes `{dir}/{sid}.snap` (do not log the name). Next use: `@ERR: session_expired|snap_available`. Restore: `session load --session <id>` (no `--file`).

## ACL

CapsPolicy is off until grant/enable. Who and WorkerWriteScope apply to `pin_map`, `mutate`, and `export pin-map` when ACL is on. `session save` / `load` into an ACL'd session / `close` accept `--caller` / `MEMNET_CALLER` and who-check with the same codes. Bind is skipped on `memnet serve` (`MEMNET_SERVE_INTERNAL=1`).

## Memory figures

Admin `memnet admin usage-report` (not agent MCP) reports **process** `rss_bytes`. `housekeep stats` is per-session row/edge/orphan counts, not bytes. `session expire-status` is flags only. Measure per-document RSS from `/proc/<serve-pid>/statm` by subtracting before/after populate.

The usage report `sessions.live` count is `registry_count()` and can include expired-but-unswept entries. `session list` purges first. Do not treat usage `live` as the true live set until that is fixed. Not fixed in the 0.19.18 probe.

## Probe

```bash
source .venv/bin/activate
python scripts/probe_doc_gate_readiness.py --out /opt/cursor/artifacts/doc-gate-readiness-proof.log
```

`--quick` shrinks nodes/churn/wait (not the product-gate proof). Extra flags: `--load-nodes` (E11, default 3000), `--fat-nodes` / `--fat-text-nodes` / `--fat-rss-samples` / `--fat-churn` (second RSS fixture), `--fulldoc-nodes` / `--fulldoc-fat` / `--e16-n` (third fixture + latency). E18-only: `--churn 0 --rss-samples 0 --expire-wait 0 --fat-churn 0 --fat-rss-samples 0 --load-nodes 0 --fulldoc-nodes 0 --nodes 40`. Tests: `tests/test_doc_gate_readiness.py` (live subprocess serve; E11 uses 3000 nodes).

## Extra probes (E11–E14)

| Item | What holds on 0.19.18 |
|------|------------------------|
| E11 | `session load` of a 3000-node snapshot (mutate batches ≤1000 lines, then save/close/load) is **not** `ingest_budget`. Bound by `MEMNET_MAX_ROWS` (5000) at upsert. Neither batched load nor an ingest exemption is needed at 3000. |
| E12 | **yes** (revised, fulldoc). Counts **nodes plus edges** on write and `session_load`. 3000 nodes then 2000 edges fill default 5000; next edge `@ERR: limit_exceeded\|rows 5001/5000`. Pi 10000 holds 7500 (`rows=7500` `edges=4500`) and `session load` of that snapshot is **not** `ingest_budget` (loaded 7500). Same 7500 snapshot on 5000: `@ERR: limit_exceeded\|rows 5001/5000`. `pin_map` read is **not** the session cap: hub `M=50` → `## Truncation truncated=true M=50 omitted=2956 reason=max_rows`; hub `M=4000` → `@ERR: response_too_large\|response 9491260 bytes exceeds cap 4194304` (4 MiB serve frame). |
| E13 | 16 KiB strings with LaTeX / quotes / newline / `\|` / CJK are refused at GQL CREATE/SET (`value_bytes 16384/4096`). Pipe leftover, GQL mutate, and snapshot load share decoded value 4096. `line_bytes` 32768 is leftover-pipe / snapshot escaped line. GQL string escapes: `\\ \' \" \n \r \t`. |
| E14 | List literals store as JSON strings and emit as GQL lists. `'k' IN p.citeKeys` honours membership on MATCH…SET. Locators are `KEY=VAL` equality on the JSON string; leftover `read list --where` can glob that string. |
| E17 | `WHERE n.value CONTAINS` is honoured on SET/DELETE. RETURN → `product_gate`. Unique MATCH miss → `not_found` (nothing SET). SET of \|Q\|>1 after WHERE is still `cue_conflict` (unique-SET law). `STARTS WITH` / `ENDS WITH` / `=~` same. Keyword: `find`/`pin_map --keyword` (casefold). See paragraph below. |
| E18 | Snapshot `value_bytes` 4096 is the **decoded** field after `split_payload` (`>` not `>=`); `join_payload` expansion of splitlines separators / `\\` / `\|` is not the value cap. `line_bytes` 32768 is the escaped/raw snapshot line. SCHEMA `max_fields=32`. Tab, CR, and LF round-trip. Undeclared extras persist unless they exceed `max_fields`. Live table below. |

Second RSS fixture: 3000 nodes, no edges, 1500 of them with 2/3/4 KiB text (about 4.4 MiB of UTF-8 payload, not 1 MiB). Measure process RSS the same way as the 1800-part fixture. Short fat churn is on (`--fat-churn`, default 8); 110 cycles of this fixture is not the default.

Third fixture (fulldoc with edges): 3000 nodes (1500 with 2–4 KiB text) plus 4500 edges (`inSection`, `cites`, `refersTo`). Order is `SEC.order`, not an edge. New relation types need mutate `--allow-new-relation`. Default 5000 cannot hold 7500 rows; use 10000 (Pi) or split sessions.

E16 (on the 10000 fulldoc session, this VM `Intel(R) Xeon(R) Processor` 4-core KVM; the face host may be slower). Bar 300 ms p95, n=200, direct serve loopback, warm session.

| Leg | p50 / p95 / max (ms) | Versus 300 ms |
|-----|----------------------|---------------|
| (a) atomic SET 2 KiB + delete 1 edge + add 2 | 115.686 / **133.181** / 155.571 | under bar |
| (b) reverse `pin_map` hub `M=400` | 113.096 / **129.613** / 163.101 | under bar |

**note:** MemNet has **no** native delete-refused-while-referenced check. `DETACH DELETE` of a node with inbound edges exits 0 and leaves dangling edges. The gate must refuse from the reverse lookup (`## Truncation truncated=true M=400 omitted=2604 reason=max_rows` on the hub). Documented `MATCH ()-[r {id}]-() DELETE r` is lowered as a node DROP with an empty id and refuses `@ERR: not_found|DELETE matched no element` (not a referenced-delete check). The probe's working edge DROP is `MATCH (n WHERE true)-[r {id}]->() DELETE r`.

E18: **yes.** Snapshot `value_bytes` 4096 is the **decoded** UTF-8 after `split_payload` (`check_value_bytes`: decoded length `>` cap, so 4096 passes). `join_payload` expansion of splitlines separators / `\\` / `|` is not the value cap (4000 `\\` or `|` emit 8000 escaped bytes, snap line ~8021, still loads). `parse_line` measures the escaped/raw line vs `line_bytes` 32768 first; save verify uses the same check. SCHEMA register vs `max_fields=32`. Snapshot save widens SCHEMA for undeclared RAM keys; leftover `emit_record` still writes SCHEMA columns. Loopback CREATE → save → load into a fresh session → `pin_map` cue. Binary search skipped (4000 exact for `\\` and `|`).

| Case | Wire shape | Save / load | Exact? |
|------|------------|-------------|--------|
| E18a 4000 `\\` | `CREATE (:USR {id: 'USR_a4kbs', key: 'e18', value: <blob utf8=4000 chars=4000>, recycle: ''})` | 0 / 0, no `@ERR` | **yes** (escaped 8000, snap line 8021) |
| E18a 4000 `\|` | `CREATE (:USR {id: 'USR_b4kpp', key: 'e18', value: <blob utf8=4000 chars=4000>, recycle: ''})` | 0 / 0 | **yes** (escaped 8000, snap line 8021) |
| E18a 4000 `"` | `CREATE (:USR {id: 'USR_c4kdq', …})` | 0 / 0 | **yes** (escaped 4000, snap line 4021) |
| E18a 4000 `'` | `CREATE (:USR {id: 'USR_d4ksq', …})` | 0 / 0 | **yes** (escaped 4000, snap line 4021) |
| E18a 4000 CJK | 1333 × U+6D4B (`测`, 3-byte UTF-8) + 1 ASCII X; `USR_e4kcj` | 0 / 0 | **yes** (1334 chars, utf8 4000, snap line 4021) |
| E18a 4096 (a–e) | same shapes; CJK is 1365 × `测` + 1 X | 0 / 0 all five | **yes** (`\\`/`\|` snap line 8215; quotes/CJK 4119) |
| E18b tab mid/end | `CREATE (:USR {id: 'USR_tabm', … value: 'ab\\tcd'})` / `'ab\\t'` | 0 / 0 | **yes** (byte-exact) |
| E18b CR mid/end | `… value: 'ab\\rcd'` / `'ab\\r'` | save 0 / load 0 | **yes** (byte-exact; LF-only record split) |
| E18c SCHEMA 64/128 | `SCHEMA WIDE ; fields=id p000 …` (64 / 128 names) | open 1 | `@ERR: limit_exceeded\|fields 64/32` and `128/32` |
| E18c SCHEMA 32 | `SCHEMA PRT ; fields=id p00 … p30` | save 0 / load 0 | yes |
| E18c 64/128 extras on USR | CREATE 60 / 124 keys beyond 4-field SCHEMA | save 1 | RAM extras yes; save refuses `snapshot_unsaveable` (`fields\|n/32`). Extras that fit persist by widening snapshot SCHEMA. |
| E18c 8 × 4000 ASCII | `CREATE (:FAT {id: 'FAT_8x4000', p000: <4000 A>, … p007: <4000 A>})` | 0 / 0 | **yes** (snap line 32024 < 32768; all eight fields exact) |

E17: **yes.** GQL `WHERE n.value CONTAINS '…'` is honoured on SET/DELETE. `MATCH … WHERE … RETURN n` → `@ERR: product_gate|agent surface forbids RETURN …`. Unique MATCH miss → `@ERR: not_found` and nothing SET. SET of `|Q|>1` after WHERE is still `@ERR: cue_conflict|SET  Q =…` (unique-SET law, not a dropped WHERE). Inline `MATCH (n WHERE n.value CONTAINS '…')` → `@ERR: parse_error|unsupported MATCH shape`. Bare WHERE without SET/RETURN → `@ERR: parse_error|unsupported MATCH continuation`. `STARTS WITH` / `ENDS WITH` / `=~` are honoured the same way. Keyword substring: `query find --keyword` / `pin_map --keyword` (casefold across all fields, hard `--limit` / `--max-rows`). leftover `read list --where value=*测例*` works on a small graph; on this fulldoc it is `@ERR: response_too_large|response 4659616 bytes exceeds cap 4194304`. Substitute latency (n=200, `find --limit 50`, warm 10000-row session, this VM): common `测例` (1500 USR hits, 50 returned) p50 **67.282** / p95 **84.020** / max **94.672** ms; rare `Part 1500` (1 hit) p50 **51.183** / p95 **69.090** / max **85.424** ms.
