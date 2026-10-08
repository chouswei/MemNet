# Safe serve upgrade

Upgrade `memnet-serve` without silently dropping a loaded session (MN-REQ-06.14). The agent loop does not change: cue, then `pin_map`, then `mutate`. This is a patch-level cut on 0.19. Do not bump the package version from this procedure.

The manual procedure this replaces is a side-by-side virtualenv: install the new version, save every session, stop the old serve, start the new serve on the same port, reload, and check counts. Anything that failed to save was easy to miss. The drain below names every session it could not snapshot and refuses a ready-to-stop result unless you pass an explicit override.

## Order

Deploy client tolerance **before** the serve swap.

1. Install the new `memnet-mcp` (and the droplet gateway, if this host is the gateway) so `serve_draining` and a brief connection refusal are retried. Leave the gateway's `pinned_version` on the version that is still running.
2. Confirm `MEMNET_UPGRADE_RETRY_S` is unset or about `30` on those client processes. `0` disables retry.
3. Only then run `memnet-upgrade` against the serve.

During the gap, new `session_open` calls receive `@ERR: serve_draining|retry_after_s=<seconds>` and clients back off. After the old process has exited and before the new one listens, connections are refused. That refusal is retried for the same window. A command the serve already accepted is not retried on timeout.

Downtime that remains: a few seconds while the port is closed, covered by that retry. Sessions keep their ids, CapsPolicy ACL bindings, TTL expiry clock, and house (the session tag map).

## What the serve does

Admin credential: `MEMNET_ADMIN_TOKEN` (same rule as the usage report). Unset is `@ERR: admin_unconfigured`. A mismatch is `@ERR: admin_denied`. This command is not an agent MCP tool.

```bash
memnet admin upgrade-prepare --state-dir "$MEMNET_STATE_DIR"
```

Envelope form: `{"upgrade_prepare": true, "admin_token": "<token>"}`.

Drain behaviour:

- Refuse new `session_open` with `serve_draining`.
- Finish commands already in flight, then refuse further commands.
- Snapshot every loaded session with the lossless snapshot writer.
- Write `upgrade-manifest.json` and `upgrade-snapshots/` under `MEMNET_STATE_DIR` (default `~/.local/state/memnet`). The manifest records session ids, row and edge counts, sha256 checksums, the serve version, and snapshot format `1`.
- An ACL and clock passport is an extra `# upgrade-passport` line. Older v1 loaders skip `#` lines, so a rollback can still read the graph.
- If any session raises `snapshot_unsaveable` (or any other save error), the command exits non-zero, lists that session in `upgrade-blocked.json`, and does **not** write a ready manifest. The serve keeps accepting work. Pass `--allow-unsaved` only when you accept dropping those named sessions.
- Do not stop the process unless stderr contains `@STAT: upgrade_prepare|ready|`.

The new process reads the manifest on startup, reloads each snapshot, and checks counts and checksums. It prints:

```text
@STAT: upgrade_restore|ok|<n>|failed|<m>
```

Snapshot files stay on disk until `memnet admin upgrade-retire` after a clean restore report. A format this process does not support, or a checksum or parse failure, exits `3` and does not delete or rewrite the files. Restarting before retire replays the upgrade snapshots (writes made after the restore are not in those files). Retire as soon as the stat line is clean.

## Helper

`memnet-upgrade` encodes the side-by-side venv procedure. It refuses to start unless `--clients-ready` is set.

```bash
memnet-upgrade \
  --clients-ready \
  --new-python /opt/memnet/venv-new/bin/python \
  --new-exec "/opt/memnet/venv-new/bin/memnet serve --host 127.0.0.1 --port 18765" \
  --state-dir /var/lib/memnet \
  --unit /etc/systemd/system/memnet-serve.service \
  --restart-unit memnet-serve
```

Steps:

1. Preflight: import `memnet` with the new interpreter and check `SUPPORTED_SNAPSHOT_FORMATS` against the current manifest (or format `1` when no manifest exists yet).
2. `admin upgrade-prepare` on the running serve.
3. Copy the unit to `memnet-serve.service.bak` and replace `ExecStart=`.
4. If `--gateway-config` and `--product` are set, copy the config to `*.bak` and set that product's `pinned_version` to the new version **after** the old serve is drained and **before** the new process listens.
5. Restart the unit. The new process restores and writes `upgrade-restore.json`.
6. If `failed` is not `0`, write the unit backup and the config backup back and restart again.

`--state-dir` must be the same directory as the unit's `Environment=MEMNET_STATE_DIR`. The serve reads that variable at startup; the prepare command also receives `--state-dir`.

Build the new venv beside the old one. Do not overwrite it until the restore has verified.

```bash
python -m venv /opt/memnet/venv-new
/opt/memnet/venv-new/bin/pip install "memnet-llm==<new>"
```

Use the index you trust. Do not put tokens or session ids in the unit file. Keep `MEMNET_ADMIN_TOKEN` in a root-only `EnvironmentFile`.

## rpi5-syson

Local engine on the Pi:

| Process | Port | Unit (adjust to the host) |
|---------|------|---------------------------|
| `memnet serve` | `18765` | `memnet-serve.service` |
| `memnet-mcp` streamable-http | `18766` | `memnet-mcp-http.service` |

Upgrade the MCP unit first (retry code, same serve version pin). Then `memnet-upgrade` the serve unit on `18765` with `MEMNET_STATE_DIR` on the Pi disk. Leave `18766` up so clients retry against the serve gap.

## Endleaf engine serve

The Endleaf product backend is the serve named in the droplet gateway registry (host and port live in that config, not in this repo). Use that unit's port and state directory. The drain and restore are the same command. Do not point the gateway at a second backend to "move" live sessions.

## Droplet gateway

The gateway process is `memnet-mcp --transport gateway` with `MEMNET_GATEWAY_CONFIG`. Ship the retry-capable build first, with `pinned_version` still equal to the running engine. Then, in the same `memnet-upgrade` invocation that swaps the engine, pass:

```bash
--gateway-config /etc/memnet/gateway.json \
--product endleaf \
--restart-unit memnet-gateway
```

The pin changes only after drain succeeds, and it is restored from `gateway.json.bak` if the engine restore fails. Restart the gateway after the pin write so it stops caching the previous version (`version_cache_s`). No plaintext credentials in git. Hashes stay in the config file on the droplet.

## Rollback

A failed verification restores the previous `ExecStart=` and the previous pin, then restarts. Snapshot files are still in the state directory. The old venv loads format v1 snapshots (`#` passport lines are ignored). That reload keeps the session id and the graph. The old loader rebases the TTL clock from `ttl_minutes` and does not read ACL bindings from the passport; re-grant those on the old serve if you stay there. The new serve's restore path keeps the id, the ACL bindings, the expiry instant, and the house.

Neighbourhood reserves are not part of the snapshot. Take a fresh reserve after the new serve is up.
