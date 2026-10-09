# Safe serve upgrade

Upgrade `memnet-serve` without dropping a loaded session (MN-REQ-06.14). The procedure stays inside the serve process: save every session, restart on the new version, reload every session. The agent loop does not change: cue, then `pin_map`, then `mutate`.

During the restart, clients see `@ERR: serve_draining|retry_after_s=<seconds>` or a connection error. There is no client retry window.

## Procedure

1. Install the new version in a separate virtualenv. Leave the running venv in place.

```bash
python -m venv /opt/memnet/venv-new
/opt/memnet/venv-new/bin/pip install "memnet-llm==<new>"
```

2. Drain the running serve. `MEMNET_ADMIN_TOKEN` is required (unset is `@ERR: admin_unconfigured`; a mismatch is `@ERR: admin_denied`). This command is not an agent MCP tool.

```bash
memnet admin upgrade-prepare --state-dir "$MEMNET_STATE_DIR"
```

3. Check ready-to-stop. Stop the process only when stderr contains `@STAT: upgrade_prepare|ready|`. If a session cannot be snapshotted, the command names it, exits non-zero, and does not write a ready manifest. Pass `--allow-unsaved` only when those named sessions may be dropped.

4. Point the unit `ExecStart` at the new venv, on the same port and the same `MEMNET_STATE_DIR`, and restart.

5. Read the restore stat from the new process:

```text
@STAT: upgrade_restore|ok|<n>|failed|<m>
```

A clean stat retires the manifest inside that process. A later restart does not replay the snapshots. The snapshot files stay on disk. A checksum failure, a parse failure, or an unsupported snapshot format exits `3`, leaves the files untouched, and does not retire.

## Rollback

Point the unit `ExecStart` back at the old venv and start it when the restore stat is not clean. After a clean stat the manifest is retired, so a later start does not reload those snapshots.

## Hosts

On rpi5-syson the serve listens on `18765` (`memnet-serve.service`). `memnet-mcp` on `18766` is not part of this procedure. The Endleaf engine serve is the backend named in the gateway registry; use that unit's port and state directory. The droplet gateway is unchanged: do not edit its version pin as part of this restart.

Do not put tokens or session ids in the unit file. Keep `MEMNET_ADMIN_TOKEN` in a root-only `EnvironmentFile`.
