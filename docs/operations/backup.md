# Hourly checkpoint backup

A backup of snapshot files only sees sessions a product has already saved. Loaded sessions stay in RAM until something calls `session_save`, and not every product does. `memnet admin checkpoint` copies every loaded session to disk without draining the serve and without refusing new work (MN-REQ-06.15).

The command is admin-only. It is not an agent MCP tool. `MEMNET_ADMIN_TOKEN` is the serve credential (unset is `@ERR: admin_unconfigured`; a mismatch is `@ERR: admin_denied`). The caller presents that same string with `--token`. Do not log the token, and do not commit it.

Each loaded session is locked only while its graph is serialised. Other sessions keep serving. The copy uses the lossless snapshot path and is written atomically (temp file, fsync, rename) to:

```text
$MEMNET_STATE_DIR/checkpoint/<session>.snap
```

`checkpoint-manifest.json` in that directory records each saved session's row count, edge count, and checksum, plus the serve version, the snapshot format version, and a timestamp. The row shape matches the upgrade manifest. A session that cannot be saved is named on stderr (`snapshot_unsaveable` and the reason) and skipped. The command still writes the others. The exit code is non-zero when any session was skipped. Stdout is:

```text
@STAT: checkpoint|ok|<n>|skipped|<m>|bytes|<b>
```

A checkpoint does not slide TTL or expiry clocks, and it does not change session ids, ACL, or live state. It does not retire a manifest and it does not load a snapshot into the serve. Files for sessions that are no longer loaded are removed. A skipped session does not keep an older snap, so the directory matches the manifest.

## Hourly: checkpoint, then restic to R2

Set the repository and the R2 credentials in the job environment. R2 speaks the S3 API. Do not write the key values into git or into this file.

```text
RESTIC_REPOSITORY=s3:https://<account>.r2.cloudflarestorage.com/<bucket>
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
MEMNET_STATE_DIR
MEMNET_ADMIN_TOKEN
```

```bash
memnet admin checkpoint \
  --token "$MEMNET_ADMIN_TOKEN" \
  --state-dir "$MEMNET_STATE_DIR"
restic backup "$MEMNET_STATE_DIR/checkpoint"
```

Run that once an hour. Restic the checkpoint directory when the command exits 0 (`skipped|0`). A non-zero exit means a loaded session was skipped; leave the previous restic snapshot as the latest good copy and alert on the named session.

## Weekly: restore, then checkpoint-verify

Restore the latest restic snapshot onto a scratch directory (not the live state directory). Then check that copy with the throwaway loader:

```bash
restic restore latest --target "$RESTORE_DIR"
memnet admin checkpoint-verify \
  --token "$MEMNET_ADMIN_TOKEN" \
  "$RESTORE_DIR$MEMNET_STATE_DIR/checkpoint"
```

Stdout is `@STAT: checkpoint_verify|ok|<n>|failed|<m>`. The helper loads each snapshot into a throwaway in-process store and checks row counts, edge counts, and checksums against the manifest. A corrupt or missing file fails the check and leaves the files in place. It does not load those sessions into the live serve. A non-zero exit means the restored copy is not a good backup.
