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

Ingest caps (`max_nodes=2000` / `max_edges=2000`) are Path-B ingest, not this mutate path. Session row cap remains 5000 non-LAW rows (**nodes plus edges**). `session load` of a snapshot is **not** bound by ingest budget; it walks leftover `parse_line` + `MemStore.upsert` (`MEMNET_MAX_ROWS`, max sessions, leftover value/line/newline/FIELD_COUNT).

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

Opaque text must stay on one snapshot line. Newlines inside a property survive GQL mutate in RAM, but leftover `@TAG` emit does not escape them, so `session load` raises `@ERR: FIELD_COUNT`. Leftover emit **does** escape `\` and `|` (`join_payload`). A 16 KiB string survives CREATE / SET / `pin_map` in RAM (GQL mutate does not enforce pipe `value_bytes` / `line_bytes` — cap-contract bug 4) but snapshot load of a 16 KiB field refuses `@ERR: limit_exceeded|value_bytes 16384/4096`. Unicode, `|`, and quotes on a **short** single line do round-trip.

Expire: with save-on-expire and a dir, TTL drop writes `{dir}/{sid}.snap` (do not log the name). Next use: `@ERR: session_expired|snap_available`. Restore: `session load --session <id>` (no `--file`).

## ACL

CapsPolicy is off until grant/enable. Who and WorkerWriteScope apply to `pin_map`, `mutate`, and `export pin-map` when ACL is on. `session save` / `load` / `close` do not take `--caller` and do not who-check. Bind is skipped on `memnet serve` (`MEMNET_SERVE_INTERNAL=1`).

## Memory figures

Admin `memnet admin usage-report` (not agent MCP) reports **process** `rss_bytes`. `housekeep stats` is per-session row/edge/orphan counts, not bytes. `session expire-status` is flags only. Measure per-document RSS from `/proc/<serve-pid>/statm` by subtracting before/after populate.

The usage report `sessions.live` count is `registry_count()` and can include expired-but-unswept entries. `session list` purges first. Do not treat usage `live` as the true live set until that is fixed. Not fixed in the 0.19.18 probe.

## Probe

```bash
source .venv/bin/activate
python scripts/probe_doc_gate_readiness.py --out /opt/cursor/artifacts/doc-gate-readiness-proof.log
```

`--quick` shrinks nodes/churn/wait (not the product-gate proof). Extra flags: `--load-nodes` (E11, default 3000), `--fat-nodes` / `--fat-text-nodes` / `--fat-rss-samples` / `--fat-churn` (second RSS fixture), `--fulldoc-nodes` / `--fulldoc-fat` / `--e16-n` (third fixture + latency). Tests: `tests/test_doc_gate_readiness.py` (live subprocess serve; E11 uses 3000 nodes).

## Extra probes (E11–E14)

| Item | What holds on 0.19.18 |
|------|------------------------|
| E11 | `session load` of a 3000-node snapshot (mutate batches ≤1000 lines, then save/close/load) is **not** `ingest_budget`. Bound by `MEMNET_MAX_ROWS` (5000) at upsert. Neither batched load nor an ingest exemption is needed at 3000. |
| E12 | **yes** (revised, fulldoc). Counts **nodes plus edges** on write and `session_load`. 3000 nodes then 2000 edges fill default 5000; next edge `@ERR: limit_exceeded\|rows 5001/5000`. Pi 10000 holds 7500 (`rows=7500` `edges=4500`) and `session load` of that snapshot is **not** `ingest_budget` (loaded 7500). Same 7500 snapshot on 5000: `@ERR: limit_exceeded\|rows 5001/5000`. `pin_map` read is **not** the session cap: hub `M=50` → `## Truncation truncated=true M=50 omitted=2956 reason=max_rows`; hub `M=4000` → `@ERR: response_too_large\|response 9491260 bytes exceeds cap 4194304` (4 MiB serve frame). |
| E13 | 16 KiB strings with LaTeX / quotes / newline / `\|` / CJK survive GQL CREATE/SET/`pin_map` in RAM. Snapshot save/load does **not** survive byte-for-byte (`FIELD_COUNT` on newlines; `value_bytes 16384/4096` otherwise). Pipe leftover: value 4096, line 32768; GQL mutate skips those (bug 4). Escapes: `\\ \' \" \n \r \t` only. |
| E14 | List literals store as JSON strings and emit as GQL lists. `'k' IN p.citeKeys` is **not** a product filter (`MATCH (p:USR) WHERE … SET` ignores WHERE and raises `cue_conflict` when \|Q\|>1). Locators are `KEY=VAL` equality on the JSON string; leftover `read list --where` can glob that string. |

Second RSS fixture: 3000 nodes, no edges, 1500 of them with 2/3/4 KiB text (about 4.4 MiB of UTF-8 payload, not 1 MiB). Measure process RSS the same way as the 1800-part fixture. Short fat churn is on (`--fat-churn`, default 8); 110 cycles of this fixture is not the default.

Third fixture (fulldoc with edges): 3000 nodes (1500 with 2–4 KiB text) plus 4500 edges (`inSection`, `cites`, `refersTo`). Order is `SEC.order`, not an edge. New relation types need mutate `--allow-new-relation`. Default 5000 cannot hold 7500 rows; use 10000 (Pi) or split sessions.

E16 (on the 10000 fulldoc session, this VM `Intel(R) Xeon(R) Processor` 4-core KVM; the face host may be slower). Bar 300 ms p95, n=200, direct serve loopback, warm session.

| Leg | p50 / p95 / max (ms) | Versus 300 ms |
|-----|----------------------|---------------|
| (a) atomic SET 2 KiB + delete 1 edge + add 2 | 115.686 / **133.181** / 155.571 | under bar |
| (b) reverse `pin_map` hub `M=400` | 113.096 / **129.613** / 163.101 | under bar |

**note:** MemNet has **no** native delete-refused-while-referenced check. `DETACH DELETE` of a node with inbound edges exits 0 and leaves dangling edges. The gate must refuse from the reverse lookup (`## Truncation truncated=true M=400 omitted=2604 reason=max_rows` on the hub). Documented `MATCH ()-[r {id}]-() DELETE r` is lowered as a node DROP with an empty id and refuses `@ERR: not_found|DELETE matched no element` (not a referenced-delete check). The probe's working edge DROP is `MATCH (n WHERE true)-[r {id}]->() DELETE r`.
