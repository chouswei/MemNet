# Case study: safe serve upgrade (MN-REQ-06.14)

**Story:** A live `memnet-serve` has to move to a new patch without dropping sessions on the floor. The hand procedure (side-by-side venv, save, stop, start, reload) worked, and it also hid any session that failed to save.

**Requirement:** MN-REQ-06.14 (`safeServeUpgradeReq`). **Verify:** MN-VER-06-S12.

| | |
|--|--|
| Part | `SafeServeUpgrade` on `TcpServeBridge` |
| Command | `CmdAdminUpgradePrepare` on `CliFacade`; not on `McpFacade` |
| Retry | `McpFacade` and `MemNetProductGateway` (`upgradeRetry=true`, default 30s) |
| Helper | `memnet-upgrade` (`UpgradeHelperMod`) |
| Snapshot | lossless writer plus an optional `# upgrade-passport` line |
| Flag | `implemented=true`; `noSemVerBump=true`; `silentSessionLoss=false` |

Drain refuses new `session_open` with `serve_draining`. It snapshots through the lossless path, writes a manifest (counts, checksums, format version), and stays not-ready when any session is `snapshot_unsaveable` unless `--allow-unsaved` is set. Startup restore checks counts and checksums and prints `@STAT: upgrade_restore|ok|n|failed|m`. A corrupt file or an unsupported format fails loud and leaves the files in place.

Client tolerance ships first. Then the serve swaps. The gateway pin moves in that same procedure, after drain and before the new process listens.

Hosts in the operator note: rpi5-syson serve `18765` and mcp `18766`; the Endleaf engine serve named by the gateway registry; the droplet gateway. Teach: [`docs/operations/safe-upgrade.md`](../../docs/operations/safe-upgrade.md).
