# Safe serve upgrade

Upgrade `memnet-serve` without dropping a loaded session (MN-REQ-06.14). The procedure stays inside the serve process: save every session, restart on the new version, reload every session. The agent loop does not change: cue, then `pin_map`, then `mutate`.

During the restart, clients see `@ERR: serve_draining|retry_after_s=<seconds>` or a connection error. There is no client retry window.

## Procedure

The unit runs the serve through a venv link, for example `ExecStart=/opt/memnet/venv/bin/memnet serve`, where `/opt/memnet/venv` is a symlink to the versioned venv (`/opt/memnet/venv-0.20.4`). Rollback swaps that link back.

1. Install the new version in a separate virtualenv. Leave the running venv in place.

```bash
python -m venv /opt/memnet/venv-<new>
/opt/memnet/venv-<new>/bin/pip install "memnet-llm[mcp]==<new>"
```

Hosts that run `memnet-mcp` (streamable-http or gateway) need the `[mcp]` extra.

2. Drain the running serve. `MEMNET_ADMIN_TOKEN` is required (unset is `@ERR: admin_unconfigured`; a mismatch is `@ERR: admin_denied`). This command is not an agent MCP tool.

```bash
memnet admin upgrade-prepare --state-dir "$MEMNET_STATE_DIR"
```

3. Check ready-to-stop. Stop the process only when stderr contains `@STAT: upgrade_prepare|ready|`. If a session cannot be snapshotted, the command names it, exits non-zero, and does not write a ready manifest. Pass `--allow-unsaved` only when those named sessions may be dropped.

4. Stop the serve and keep a copy of the state directory. This copy is what rollback restores.

```bash
systemctl stop memnet-serve
cp -a "$MEMNET_STATE_DIR" "$MEMNET_STATE_DIR.pre-upgrade"
```

5. Point the venv link at the new venv (same port, same `MEMNET_STATE_DIR`) and start.

```bash
ln -sfn /opt/memnet/venv-<new> /opt/memnet/venv.tmp && mv -T /opt/memnet/venv.tmp /opt/memnet/venv
systemctl start memnet-serve
```

6. Read the restore stats from the new process:

```text
@STAT: restore_source|upgrade|<timestamp>
@STAT: upgrade_restore|ok|<n>|failed|<m>
```

A clean stat marks the manifest `retired` (with `retired_at`) inside that process. A retired manifest stays a candidate: every later restart restores again from the newest valid set (see "Restart restore"). The snapshot files stay on disk. A checksum failure, a parse failure, or an unsupported snapshot format in every set exits `3`, leaves the files untouched, and does not retire. A session that fails to load from a set that passed the check also exits `3`, with no fallback (see "Restart restore").

7. Run the health and data check. The upgrade is done only when it passes.

```bash
memnet admin upgrade-verify --before "$MEMNET_STATE_DIR.pre-upgrade/upgrade-manifest.json"
```

Run it as the serve user, with `MEMNET_ADMIN_TOKEN` in the environment (or `--token`), before agents write again. The check runs in the client, so it works against any serve version: it asks the serve for an `admin checkpoint` into a new scratch directory (`--scratch`, default a temp directory; never the live state directory), compares that with the saved manifest, and removes the scratch directory. It passes when the session ids are the same and each session has the same rows and relations (edges):

```text
@STAT: upgrade_verify|ok|<n>
```

Any difference prints one line per session and exits `3`. Kinds are `missing`, `extra`, `unsaved`, `rows` and `edges`:

```text
@WARN: upgrade_verify_mismatch|<kind>|<session>|before=<x>|after=<y>
@ERR: upgrade_verify_mismatch|<count>
```

No serve, a refused token, or a missing or unreadable `--before` file exits `2`. stdout carries the same result as JSON (`ok`, `sessions.before`, `sessions.after`, `mismatches`). On a mismatch, roll back.

## Rollback

One command restores the old venv and the saved sessions:

```bash
scripts/upgrade-rollback.sh \
  --live-venv /opt/memnet/venv --old-venv /opt/memnet/venv-0.20.4 \
  --state-dir "$MEMNET_STATE_DIR" --saved "$MEMNET_STATE_DIR.pre-upgrade" \
  --stop 'systemctl stop memnet-serve' --start 'systemctl start memnet-serve'
```

It refuses with exit `2` and changes nothing when the live venv is not a symlink, the old venv has no `bin/python`, the saved copy has no ready-to-stop `upgrade-manifest.json`, or the stop command fails. Otherwise it:

1. runs the stop command;
2. moves the state directory aside to `<state-dir>.rolled-back-<UTC stamp>` (nothing is deleted; it holds every write made after the upgrade);
3. copies the saved directory back, removes its `upgrade-restore.json` and marks its upgrade manifest not retired, so the old build restores it;
4. points the live venv link at the old venv;
5. runs the start command and waits (`--wait-s`, default 60) for the old serve's `upgrade-restore.json`.

It prints `@STAT: upgrade_rollback|ok|<n>` when every saved session was restored and none failed, and exits `3` with `@ERR: upgrade_rollback|<restore|timeout|start>|...` otherwise. The saved copy is not changed, so the command can be run again. `upgrade-verify` exists only from the build after 0.20.4. To compare rows after a rollback, run it from the new venv (`/opt/memnet/venv-<new>/bin/memnet admin upgrade-verify ...`) against the old serve.

**This loses every write made after the upgrade** (they stay in the moved-aside directory).

The manual equivalent follows.


Point the unit `ExecStart` back at the old venv and start it when the restore stat is not clean. After a clean stat the manifest is marked retired. The new build still treats it as a restore candidate and restores the newest valid set again on every start, which may be these snapshots or a newer checkpoint. An old build (0.20.4 or earlier) started after a clean stat skips the retired manifest and starts empty. The snapshot files stay on disk, so roll forward to the new build again, or restore them with the new build.

From the build after 0.19.23 the first write of each snapshot in format 2 keeps the old bytes once. A format 1 file that is overwritten by a format 2 write is copied to `<file>.v1.bak` (mode `0600`, same directory) before the replace. A later save never overwrites that backup.

Rolling back to 0.19.23 (which reads format 1 only) means restoring those backups:

1. Stop the new serve. It must not write during the rollback.
2. For each snapshot that has a `.v1.bak`, rename the backup over the snapshot, for example `mv -f upgrade-snapshots/<sid>.snap.v1.bak upgrade-snapshots/<sid>.snap`. Do the same under `checkpoint/` and for any expire or session save file.
3. Start the old venv.

**This loses every write made after the upgrade.** The session state returns to the bytes saved before the upgrade, and nothing else is merged back.

Two things an old build does loudly by design:

- A format 2 snapshot with no `.v1.bak` (a file first written by the new build) is refused with `bad_snapshot` (`unsupported snapshot version 2`). It is not loaded as an empty or partial session.
- A format 2 upgrade manifest is refused by the old serve (`upgrade_snapshot_format`, exit `3`).

Keep the `.v1.bak` files until the new build has run cleanly. They are not removed by the new build.

## Restart restore

Every start of `memnet serve` restores the newest valid snapshot set, not only the first start after an upgrade. There are two candidates under `$MEMNET_STATE_DIR`:

- the upgrade set, `upgrade-manifest.json` (written by `admin upgrade-prepare`);
- the checkpoint set, `checkpoint/checkpoint-manifest.json` (written by `admin checkpoint`, see [backup.md](backup.md)).

`upgrade-blocked.json` is never a candidate.

**Order.** Each set's age is the manifest's `timestamp`, or the manifest file's modified time when it has none (manifests from builds before this one). The newest set goes first. On an exact tie the upgrade set goes first, because it was taken with the serve drained.

**Retired.** `retired` now means "restored cleanly at least once" and is kept for audit, with `retired_at`. A retired upgrade manifest stays a candidate. Restore never writes the checkpoint manifest.

**Fallback.** Each set is checked before anything is loaded: the manifest parses, the upgrade set is ready-to-stop, the snapshot format is supported, and each listed file exists, matches its checksum and has a snapshot header. The first set in order that passes is restored. Each newer set that failed is printed on stdout and stderr, on every start:

```text
@WARN: restore_fallback|<source>|<code>|<detail>
```

A checkpoint written half-way (a crash or a full disk) leaves files that do not match its manifest; the serve then starts from the older intact set and says so. The start-up then prints which set it used:

```text
@STAT: restore_source|<checkpoint|upgrade>|<timestamp>
@STAT: upgrade_restore|ok|<n>|failed|<m>
```

`upgrade-restore.json` records the same `source`, `timestamp`, `timestamp_source` (`manifest` or `mtime`), `manifest` and the `rejected` sets.

**No set.** With no manifest on disk (a fresh state directory) the serve starts with 0 sessions. When manifests exist but none passes the check, the serve prints `@ERR: <code>|<detail>` with the newest set's own code and exits `3`. It never starts silently empty while a manifest exists. A newest set that is valid and empty wins: it records that no session was loaded. A session that fails to load from a set that passed the check also exits `3`, with no fallback.

**Accepted risk.** A restart replays the newest set, so a session closed after that set was written comes back until the next checkpoint. Run `memnet admin checkpoint` after closing sessions and before a planned restart; the hourly checkpoint ([backup.md](backup.md)) bounds the rest. Both manifests are stamped by the running serve's clock: on a host without a real-time clock, restart after NTP has synchronised.

## Mixed versions

Clients and the serve may be on different builds during the upgrade. A 0.20.4 client (one connection per command, no keep-alive) works against the new serve. A new pooled client (keep-alive) works against a 0.20.4 serve, which closes the connection after every reply: the client keeps a socket only when the reply says `keep_alive`, and drops a kept socket that the serve has closed (a stop, a restart or a rollback) before it sends the next command.

## Hosts

On rpi5-syson the serve listens on `18765` (`memnet-serve.service`). `memnet-mcp` on `18766` is not part of this procedure. The Endleaf engine serve is the backend named in the gateway registry; use that unit's port and state directory. The droplet gateway is unchanged: do not edit its version pin as part of this restart.

Do not put tokens or session ids in the unit file. Keep `MEMNET_ADMIN_TOKEN` in a root-only `EnvironmentFile`.
