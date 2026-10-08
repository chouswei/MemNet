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

Ingest caps (`max_nodes=2000` / `max_edges=2000`) are Path-B ingest, not this mutate path. Session row cap remains 5000 non-LAW rows.

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

Opaque text must stay on one snapshot line. Newlines inside a property survive GQL mutate in RAM, but leftover `@TAG` emit does not escape them, so `session load` raises `@ERR: FIELD_COUNT`. Unicode, `|`, and quotes on a single line do round-trip.

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

`--quick` shrinks nodes/churn/wait (not the product-gate proof). Tests: `tests/test_doc_gate_readiness.py` (live subprocess serve, smaller graphs).
