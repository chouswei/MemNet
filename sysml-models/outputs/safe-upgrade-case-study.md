# Case study: safe serve upgrade (MN-REQ-06.14)

**Story:** A live `memnet-serve` has to move to a new patch without dropping sessions. The hand procedure (side-by-side venv, save, stop, start, reload) worked, and it also hid any session that failed to save. The shipped cut keeps that procedure inside the serve process.

**Requirement:** MN-REQ-06.14 (`safeServeUpgradeReq`). **Verify:** MN-VER-06-S12.

| | |
|--|--|
| Part | `SafeServeUpgrade` on `TcpServeBridge` |
| Command | `CmdAdminUpgradePrepare` on `CliFacade`; not on `McpFacade` |
| Snapshot | lossless writer plus an optional `# upgrade-passport` line |
| Retire | automatic after a clean restore, inside that startup |
| Flag | `implemented=true`; `noSemVerBump=true`; `silentSessionLoss=false` |

Drain enters quiesce and refuses new commands with `serve_draining`. It finishes in-flight work, snapshots through the lossless path, and writes a manifest (counts, checksums, format version). It stays not-ready when any session is `snapshot_unsaveable` unless `--allow-unsaved` is set. Startup restore checks counts and checksums and prints `@STAT: upgrade_restore|ok|n|failed|m`. A clean restore retires the manifest before the process accepts work, so a later restart does not replay those snapshots. A corrupt file or an unsupported format fails loud, leaves the files in place, and does not retire.

memnet-mcp and the product gateway are not part of the procedure. Clients see the refusal or a connection error while the port is down. Teach: [`docs/operations/safe-upgrade.md`](../../docs/operations/safe-upgrade.md).
