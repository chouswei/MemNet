# Case study: serve checkpoint (MN-REQ-06.15)

**Story:** An hourly off-host backup only sees what a product has already saved. Some products never call `session_save`, so a live session can be missing from the backup. The checkpoint copies every loaded session to disk while the serve keeps accepting work.

**Requirement:** MN-REQ-06.15 (`serveCheckpointReq`). **Verify:** MN-VER-06-S13.

| | |
|--|--|
| Part | `ServeCheckpoint` on `TcpServeBridge` |
| Commands | `CmdAdminCheckpoint` and `CmdAdminCheckpointVerify` on `CliFacade`; not on `McpFacade` |
| Snapshot | lossless writer, atomic temp file plus fsync plus rename |
| Directory | `$MEMNET_STATE_DIR/checkpoint/` plus `checkpoint-manifest.json` |
| Flag | `implemented=true`; `noSemVerBump=true`; `drainsServe=false`; `retiresOrLoads=false` |

The admin credential is `MEMNET_ADMIN_TOKEN`. One session lock covers serialising that session only. Other sessions keep serving, and a new open is not refused. An unsaveable session is named (`snapshot_unsaveable` and the reason) and skipped; the exit code is non-zero. TTL, session id, ACL, and live state stay put. `checkpoint-verify` checks a restic-restored copy in a throwaway store and prints `@STAT: checkpoint_verify|ok|n|failed|m`.

Teach: [`docs/operations/backup.md`](../../docs/operations/backup.md).
