# Admin serve usage report

Read-only **admin** snapshot of one `memnet-serve` process (MN-REQ-06.11 / MN-VER-06-S09). For the InkMirage admin MCP / face to call later. **Not** agent wire. **Not** on the generic `memnet-mcp` tool list.

Counts and caps only. No graph content, no node text, no locators, no real session id (`mn_…`). Distinct from the human usage look (MN-REQ-06.5), which may list live ids.

No version bump. No PyPI publish.

## Command

CLI (proxied by serve argv, same as other subcommands):

```text
memnet admin usage-report --token "$TOKEN"
```

Serve JSON envelope (length-prefixed, existing `args` / `stdin` shape):

```json
{"args": ["admin", "usage-report", "--token", "<token>"]}
```

Optional dedicated entry (token not on argv):

```json
{"admin_usage": true, "admin_token": "<token>"}
```

Optional: `{"args": ["admin", "usage-report"], "admin_token": "<token>"}` — envelope token is used when `--token` is omitted.

Python helper: `memnet.serve.send_command(["admin", "usage-report"], admin_token=token)` or `send_command([], admin_usage=True, admin_token=token)`.

Reply envelope is the usual `{exit_code, stdout, stderr}`. Success: `exit_code=0`, **stdout is one JSON object** plus newline. Refuse: `exit_code=2`, **empty stdout**, stderr `@ERR: …`.

## Env

| Name | Role |
|------|------|
| `MEMNET_ADMIN_TOKEN` | **Configured** secret on the **serve process**. Unset or blank → refuse. Not the agent ACL / `MEMNET_CALLER`. |

The caller **presents** the same string via `--token` or `admin_token`. Do not bind `--token` to this env on the serve host: serve runs CLI with its own env, and that would auto-authorise every local argv.

Do not log the token. Do not put it in traces.

## Named `@ERR`

| Code | When | Body |
|------|------|------|
| `admin_unconfigured` | `MEMNET_ADMIN_TOKEN` unset/blank | Empty stdout. `@ERR: admin_unconfigured\|MEMNET_ADMIN_TOKEN unset` |
| `admin_denied` | Token missing or mismatch | Empty stdout. `@ERR: admin_denied\|token mismatch` |
| `bad_product` | CLI `session open --product` slug invalid or looks like `mn_*` | Session not opened |

A refuse MUST NOT look like a complete empty report (`ok` JSON). If a measured field cannot be computed, it is listed in `unavailable` (for example `rss_bytes` when `/proc` is missing) rather than filled with a fake zero.

## Success JSON (stdout)

```json
{
  "ok": true,
  "sessions": {"live": 2, "max": 1024},
  "session_rows": [
    {
      "alias": "s_ab12cd34ef56a1b2",
      "product": "inkmirage",
      "rows": 12,
      "rows_max": 5000,
      "relations": 41,
      "relations_max": 200,
      "last_access": "2026-10-08T02:00:00Z",
      "ttl_left_s": 3510,
      "save_on_expire_armed": false
    }
  ],
  "process": {
    "version": "0.19.16",
    "uptime_s": 86400,
    "rss_bytes": 67108864,
    "save_on_expire": false,
    "expire_snapshot_dir_set": false,
    "caps": {
      "max_sessions": 1024,
      "max_rows": 5000,
      "max_relations": 200,
      "max_law": 100,
      "max_tags": 64,
      "max_fields": 32,
      "max_value_bytes": 4096,
      "max_line_bytes": 32768,
      "max_batch_lines": 1000,
      "max_depth": 4,
      "max_fanout": 256,
      "serve_max_frame_bytes": 4194304
    }
  },
  "pressure": {
    "limit_exceeded": {
      "sessions": 0,
      "rows": 3,
      "relations": 0,
      "law": 0,
      "tags": 0,
      "fields": 0,
      "value_bytes": 0,
      "line_bytes": 0,
      "batch_lines": 0
    },
    "ingest_budget": 0,
    "frame_too_large": 0,
    "acl": {
      "acl_who": 0,
      "acl_denied": 0,
      "acl_forbidden": 0,
      "acl_bind": 0,
      "acl_scope": 0,
      "acl_bad_caller": 0,
      "acl_bad_bind": 0,
      "acl_bad_scope": 0
    },
    "reserve_conflict": 0,
    "session_expired": 0,
    "truncation": {
      "max_rows": 2,
      "depth": 1,
      "fanout": 0,
      "shell": 0
    }
  },
  "unavailable": []
}
```

`alias` is HMAC-SHA256 of the real sid keyed by `MEMNET_ADMIN_TOKEN`, hex-truncated, prefixed `s_`. Stable for that serve credential; rotating the token rotates aliases. `save_on_expire_armed` repeats the **process** Caps flag (not a per-session arm today).

Peek only: the report does not `session_open` / close / load / save / mutate / purge or slide TTL.

`pressure` is since serve start (process tallies). leftover silent clips are **not** Truncation.

## Optional product label

CLI `session open --product <slug>` may attach a short slug (`^[a-z][a-z0-9_.-]{0,31}$`, not `mn_*`). Product gates that already wrap serve argv can pass it. **MCP `session_open` does not take this argument** (would appear on the agent tool list).

Open question (`mcpProductLabelOpen`): how an in-process MCP-only gate attaches a label without changing the agent usage method. Unbuilt. MUST NOT invent an MCP arg in this cut.

## MUST NOT

- Register this on `memnet-mcp` tools.
- Emit `mn_*` or graph text.
- Treat CapsPolicy ACL as the admin gate.
- Return an empty JSON object when the credential is unset.
