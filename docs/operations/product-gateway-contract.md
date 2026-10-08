# Product gateway contract

**Status:** implemented for the behaviours in [This cut](#this-cut). **MN-REQ-06.12** / **MN-VER-06-S10**. Model: `MemNetProductGateway` nested on `MemNetLanMcpFront` (`sysml-models/models/deploy.sysml`). Code: `parts/memnet-mcp/software/memnet_mcp/product_gateway.py`. No SemVer bump.

The gateway is `memnet-mcp --transport gateway`. It is not a separate droplet shim. The #191 catalogue (MCP tool union, SnapshotHandCarry) stays invent-only on the parent part.

Online products reach a `memnet serve` only through this process. Endleaf now. Atelier and SysMLEdge later, each with their own credential and backend list.

## Today

Checked on tags **v0.19.6** (the droplet `memnet-mcp-http`) and **v0.19.18** (the Pi serve). This checkout matches tag v0.19.18 for the MCP and serve files cited below.

### (1) One MCP, one serve

Neither tag can point one MCP process at several serves.

| Tag | How the backend is chosen |
|-----|---------------------------|
| v0.19.6 | `MEMNET_MCP_TRANSPORT` is `inprocess` (default) or `tcp` / `serve`. TCP calls `probe()` and `send_command()` with no host argument, so both use `MEMNET_SERVE_HOST` (default `127.0.0.1`) and `MEMNET_SERVE_PORT` (default `18765`). |
| v0.19.18 | Same. The only client change is that `session expire-status` is left off the session flag. |

Citations:

- v0.19.6 `parts/memnet-mcp/software/memnet_mcp/client.py` lines 105–139 (`_transport`, `run_memnet`)
- v0.19.6 `parts/common/memnet/memnet/config.py` lines 90–95 (`serve_host`, `serve_port`)
- v0.19.18 `parts/memnet-mcp/software/memnet_mcp/client.py` lines 106–140
- v0.19.18 `parts/common/memnet/memnet/config.py` lines 96–101

There is no backend id, no product table, and no second host. Setting `MEMNET_SERVE_HOST=100.118.79.40` and `MEMNET_SERVE_PORT=18795` would aim the single TCP client at the Endleaf Pi. It would not route a second product elsewhere.

### (2) What auth exists in front

| Check | Where | What is checked |
|-------|--------|-----------------|
| Optional shared bearer | streamable-http only | `MEMNET_MCP_HTTP_TOKEN`. Exact `Authorization: Bearer <token>`. Empty or unset means auth off. |
| stdio | default `memnet-mcp` | No bearer, no tip key, no product credential. |
| `caller` | MCP tool argument, both tags | Optional `--caller` on pin_map / mutate / find when that session's CapsPolicy ACL is enabled. Not a gateway. Off unless the session turned ACL on. |
| Tip `mn_tip_…` | v0.19.18 portal only. Absent at v0.19.6. | SHA-256 of the key, invite not revoked. nginx `auth_request` in front of one public `/mcp`. Not scoped to a product's backends. Not a version pin. Not inside `memnet-mcp`. |

Citations:

- v0.19.6 and v0.19.18 `parts/memnet-mcp/software/memnet_mcp/http_transport.py` lines 70–76 and 230–264 (`mcp_http_token`, `SharedBearerASGI`). The file is identical across the two tags.
- v0.19.6 `parts/memnet-mcp/software/memnet_mcp/server.py` lines 233–234 (`--caller` only when the tool argument is set). The same argument exists on v0.19.18.
- v0.19.6 has no `ops/tip_access_portal/`.
- v0.19.18 `ops/tip_access_portal/tip_access_portal/store.py` lines 22–23 (`hash_secret`), 158–161 (`mn_tip_` + SHA-256 at insert), 206–210 (`key_is_active`)
- v0.19.18 `ops/tip_access_portal/tip_access_portal/gate.py` lines 8–12

**Reuse decision.** The portal already hashes and revokes a bearer. It does not map a key to a backend id, a house, or a pinned serve version. This gateway copies that hash-and-revoke pattern into its own config. It does not call the portal store and it does not accept an `mn_tip_` key as a product credential. `MEMNET_MCP_HTTP_TOKEN` stays the streamable-http shared secret and is not a product credential either.

### (3) Can a 0.19.6 MCP talk to a 0.19.18 serve?

Yes, for the argv that v0.19.6 MCP actually sends. The length-prefixed JSON envelope is the same shape.

| | v0.19.6 | v0.19.18 |
|--|---------|----------|
| Request | `{"args": [...]}` plus optional `"stdin"` (`serve.py` `send_command` lines 206–217; `_handle_request` lines 76–108) | Same, plus optional `admin_token` and `admin_usage` only when the client sets them (`serve.py` lines 81–126 and 263–282). v0.19.6 never sets them. |
| Frame | 4-byte big-endian length + JSON | Same |
| Reply | `{exit_code, stdout, stderr}` | Same. `parse.py` is identical across the tags, so session-id and `@ERR` extraction do not change. |
| Version line | `@VER: memnet\|<version>` (`cli.py` line 215) | Same shape (`cli.py` line 225). The text is `0.19.6` or `0.19.18`. |

v0.19.18 CLI adds optional flags `--max-edges`, `--product`, and `--token`. It removes none. New commands the old MCP does not send: `admin usage-report`, `session expire-status`.

A v0.19.6 MCP `session open`, `pin_map`, `mutate`, `session load --file`, and `session save` argv is still accepted. The old MCP cannot select a backend other than the one `MEMNET_SERVE_HOST` / `MEMNET_SERVE_PORT`.

The other direction is not the same. A v0.19.18 MCP `snap_model` / `ingest_*` call always sends `--max-edges`. A v0.19.6 serve CLI has no such flag and will refuse that argv. That does not block a 0.19.6 MCP talking to a 0.19.18 serve.

## This cut

`memnet-mcp --transport gateway` reads `MEMNET_GATEWAY_CONFIG` (a JSON file). stdio and streamable-http do not read it. With no registry, one memnet-mcp process behaves as it does today.

### Endpoint

`POST <path>` (default `/gateway`) with `Content-Type: application/json` and:

```http
Authorization: Bearer <product credential>
```

The JSON is the serve envelope plus routing fields. Only `args` and `stdin` are forwarded. `session`, `namespace`, `product`, `house`, and `backend` are not sent to the serve. `admin_token` in the body is dropped, so a product credential cannot call the backend admin report.

```json
{
  "args": ["mutate", "--stdin", "--session", "mn_…"],
  "stdin": "MATCH (n {id: 'TSK_gw'}) SET n.status = 'settled'\n",
  "session": "mn_…",
  "namespace": "endleaf",
  "house": "syson"
}
```

`namespace` or `product`, when present, must equal the product of the credential. `session`, when present both in the field and in `args`, must be the same string. The gateway does not insert `--session` into `args`.

`house` is a name in that product's `houses` map (a backend id). `backend` is an explicit backend id in that product's list. Either one pins placement of a **new** session. If the pinned backend is down or the version does not match, the gateway refuses. It does not fail over away from a pin.

With neither `house` nor `backend`, a new session walks `products.<id>.backends` in order and uses the first that accepts TCP and whose `memnet version` line equals `pinned_version`.

A later call for a known session goes to the owning backend only. A `house` or `backend` that names a different backend is `gateway_forbidden_session`. The session is not moved.

### Reply

```json
{"exit_code": 0, "stdout": "…", "stderr": "…"}
```

Engine `exit_code`, stdout, and stderr are the backend's bytes, including `@ERR`, `@WRN`, and `@STAT`, with one exception: `session list` drops `@SESSION` rows this product does not own and rewrites `@STAT: sessions|n/max` so `n` is the filtered count. `max` stays the backend's figure (the first successful backend's max). Other control lines are copied. If any allowed backend is down or the pin does not match, stderr also carries a `gateway_` line and `exit_code` is 2, so the list does not look complete.

HTTP status is a hint. The body is always the envelope.

| HTTP | When |
|------|------|
| 200 | Backend reply, including engine `exit_code` other than 0 |
| 401 | `gateway_auth` |
| 403 | `gateway_forbidden_session` or `gateway_forbidden` |
| 409 | `gateway_backend_version_mismatch` |
| 413 | `gateway_body_too_large` |
| 502 | `gateway_backend_unreachable` |

### Gateway errors

```text
@ERR: gateway_<code>|<detail>
```

| Code | Meaning |
|------|---------|
| `gateway_auth` | Missing, unknown, or revoked bearer, or namespace does not match the credential |
| `gateway_forbidden_session` | Unknown session, another product's session, or a pin that would move the owner. The detail does not say which. |
| `gateway_forbidden` | `house` or `backend` is outside the product, or argv is `admin` or `serve` |
| `gateway_backend_unreachable` | TCP probe failed, the version command did not answer, or the client wait expired |
| `gateway_backend_version_mismatch` | `memnet version` is not the product pin |
| `gateway_body_too_large` | Body above `body_max_bytes` |
| `gateway_bad_request` | JSON, `args`, or disagreeing session fields |
| `gateway_unconfigured` | Admin counts requested and no admin hash is set; also process exit when `MEMNET_GATEWAY_CONFIG` is missing |

`exit_code` on these refusals is 2. They are not engine lines. An engine `@ERR: not_found|…` stays `not_found`.

### Limits

The gateway does not enforce `MEMNET_MAX_ROWS`, `MEMNET_MAX_BATCH_LINES`, or `MEMNET_MAX_VALUE_BYTES`. The Endleaf Pi runs 0.19.18 with `MEMNET_MAX_ROWS=10000`. Engine defaults elsewhere are `MEMNET_MAX_ROWS` 5000, batch 1000 lines, value 4096 decoded bytes (`parts/common/memnet/memnet/config.py`). A product may send `--max-rows 10000` and a mutate stdin up to the body ceiling. The backend still applies its own caps. Those refusals come back verbatim.

The gateway body ceiling is `body_max_bytes`, default **4194304** (4 MiB), the same figure as `MEMNET_SERVE_MAX_FRAME_BYTES`. State it in the config. Leave the gateway process's `MEMNET_SERVE_MAX_FRAME_BYTES` at least that large so the TCP client does not refuse a body the contract already accepted.

### Version pin

Each product has `pinned_version` (for Endleaf, `0.19.18`). Before a forward, the gateway calls `version` on that backend and requires `@VER: memnet|<pin>`. A mismatch is `gateway_backend_version_mismatch` and the argv is not sent. Upgrading the Pi serve without changing the pin refuses the product. Changing the pin is how the owner is notified: edit the config and restart the gateway.

`version_cache_s` defaults to 15. Set `0` to check every call. A serve upgraded inside a non-zero window can still be reached until the cache expires.

### Admin counts

`GET <path>/admin/counts` with `Authorization: Bearer <admin credential>`.

The admin secret is stored as `admin.sha256` only. The JSON lists each product's `requests`, `gateway_refusals`, and `backend_errors`. It has no graph text and no session id. Counts are in memory and reset when the process stops.

### Listener

Default bind `127.0.0.1`. Tailnet addresses in `100.64.0.0/10` (for example `100.118.79.40`) and Tailscale IPv6 `fd7a:115c:a1e0::/48` are allowed. `0.0.0.0` and other public addresses are refused unless `MEMNET_GATEWAY_ALLOW_PUBLIC=1`. Endleaf on the droplet should not set that. Bind the droplet loopback, or the droplet's own tailnet address. Do not publish the port.

## Examples

Credential and session ids below are placeholders.

### session open

```http
POST /gateway
Authorization: Bearer <endleaf credential>
Content-Type: application/json

{
  "args": ["session", "open", "--map-file", "/var/memnet/schema.sysml.example.txt"],
  "namespace": "endleaf",
  "house": "syson"
}
```

```json
{
  "exit_code": 0,
  "stdout": "@SESSION: mn_example|2026-10-08T16:00:00Z|60\n",
  "stderr": "MEMNET_SESSION=mn_example\n"
}
```

The gateway records `mn_example` → backend `endleaf-rpi5-syson`. The map path is on the Pi, because `args` are not rewritten.

### MATCH … SET

```json
{
  "args": ["mutate", "--stdin", "--session", "mn_example"],
  "stdin": "MATCH (n {id: 'TSK_gw'}) SET n.status = 'settled'\n",
  "session": "mn_example",
  "namespace": "endleaf"
}
```

Reply `exit_code`, stdout, and stderr are the Pi's. A missing element comes back as the engine line `@ERR: not_found|…`, not a `gateway_` line.

### Edge delete

On 0.19.18 the form that reaches an edge delete is:

```json
{
  "args": ["mutate", "--stdin", "--session", "mn_example"],
  "stdin": "MATCH (n WHERE true)-[r {id: 'E_gw'}]->() DELETE r\n",
  "session": "mn_example"
}
```

`MATCH ()-[r {id: 'E_gw'}]-() DELETE r` is still forwarded byte for byte. On this engine it lowers as a node delete and the Pi replies `@ERR: not_found|DELETE matched no element`. The gateway does not rewrite it. See [Open decisions](#open-decisions).

## Endleaf configuration

Pi serve (already running, not changed by this repo): `rpi5-syson`, tailnet `100.118.79.40:18795`, MemNet 0.19.18, `MEMNET_MAX_ROWS=10000`, no token and no ACL, accepting loopback and the droplet.

On the droplet, hash the product credential and an admin credential. Do not commit the plaintext.

```bash
python -c "import hashlib,sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest())" 'REPLACE_WITH_ENDLEAF_CREDENTIAL'
```

`/etc/memnet/gateway.json` (mode 0600, not in git):

```json
{
  "bind": "127.0.0.1",
  "port": 18770,
  "path": "/gateway",
  "body_max_bytes": 4194304,
  "state_path": "/var/lib/memnet/gateway-owners.json",
  "version_cache_s": 0,
  "backend_timeout_s": 30,
  "admin": {"sha256": "<sha256 hex of the admin bearer>"},
  "backends": {
    "endleaf-rpi5-syson": {
      "host": "100.118.79.40",
      "port": 18795
    }
  },
  "products": {
    "endleaf": {
      "backends": ["endleaf-rpi5-syson"],
      "houses": {"syson": "endleaf-rpi5-syson"},
      "pinned_version": "0.19.18",
      "credentials": [
        {"id": "endleaf-1", "sha256": "<sha256 hex>", "revoked": false}
      ]
    }
  }
}
```

```bash
export MEMNET_GATEWAY_CONFIG=/etc/memnet/gateway.json
memnet-mcp --transport gateway
```

Rotate by appending a new `{id, sha256, revoked: false}` and setting the old object's `revoked` to true. Restart is required for a config edit. The owner file remembers session → backend across restarts. It holds session ids. The admin counts endpoint does not.

To add a standby later, append another backend id to `backends` and to `endleaf.backends`, in failover order. Do not put Atelier's backend on Endleaf's list.

The droplet's existing 0.19.6 `memnet-mcp-http` does not speak this contract. This cut is not deployed.

## Open decisions

1. **Agent MCP tools.** stdio and streamable-http `pin_map` / `mutate` do not use the registry. Only `--transport gateway` does. Whether those tools should route by session is open.
2. **One gateway process.** The owner file is local. A second gateway does not share it. Multi-instance ownership is open.
3. **Admin counts reset** when the process stops. Durable counts are open.
4. **List `max`.** The filtered stat keeps the backend's `max`. Whether to hide `max` is open.
5. **Unknown and foreign sessions** share `gateway_forbidden_session` so the caller cannot tell them apart.
6. **Failover** is only for a new session with no `house` and no `backend`. There is no automatic return to a recovered preferred backend, and no SnapshotHandCarry (same sid, new owner). That relocate stays the #191 invent.
7. **Public bind** exists only behind `MEMNET_GATEWAY_ALLOW_PUBLIC=1`. Endleaf should leave it unset.
8. **Bind host** must be an IP in loopback or tailnet, or the name `localhost`. MagicDNS names are not resolved.
9. **Tip keys.** Federating `mn_tip_` into this credential store is open. This cut does not.
10. **Version cache.** Default 15 seconds. Endleaf's sample config sets `0`.
11. **Empty-paren edge delete** (`MATCH ()-[r {id}]->() DELETE r`) does not delete an edge on 0.19.18. Fixing that engine lower is open. The gateway will not rewrite it.
12. **`session list` on a shared backend** shows only sids this gateway recorded for that product. A session opened on the Pi by a path other than this gateway is invisible here and is refused as unknown. Whether the gateway should adopt a sid the product already holds on its pinned backend is open.
