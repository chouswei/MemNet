# Product gateway contract

**Status:** implemented and deployed. **MN-REQ-06.12** / **MN-VER-06-S10**. Model: `MemNetProductGateway` nested on `MemNetLanMcpFront` (`sysml-models/models/deploy.sysml`). Code: `parts/memnet-mcp/software/memnet_mcp/product_gateway.py`.

The gateway is `memnet-mcp --transport gateway`. It is not a separate droplet shim. The #191 catalogue (MCP tool union, SnapshotHandCarry) stays invent-only on the parent part.

Online products reach a `memnet serve` only through this process. Sample pin below is **0.19.20**. Backend ids are arbitrary strings. The live Endleaf backend id is `pi-endleaf`.

stdio and streamable-http do not read the registry. With no `MEMNET_GATEWAY_CONFIG`, one memnet-mcp process stays a single in-process or streamable-http server.

## Credentials

The gateway process reads `MEMNET_GATEWAY_CONFIG` (a JSON file). It stores each product credential as a SHA-256 hex digest and compares `Authorization: Bearer <secret>` to that digest.

The product side names its bearer `MEMNET_GATEWAY_TOKEN`, for example in `/etc/<product>/memnet-gateway.env`. The gateway process does not read `MEMNET_GATEWAY_TOKEN`. The caller puts that value in the `Authorization` header.

`MEMNET_MCP_HTTP_TOKEN` is the streamable-http shared secret only. It is unrelated to this gateway. The gateway does not accept an `mn_tip_` key.

## Endpoint

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

## Reply

```json
{"exit_code": 0, "stdout": "…", "stderr": "…"}
```

Engine `exit_code`, stdout, and stderr are the backend's bytes, including `@ERR`, `@WRN`, and `@STAT`, with one exception: `session list` drops `@SESSION` rows this product does not own and rewrites `@STAT: sessions|n/max` so `n` is the filtered count. `max` stays the backend's figure (the first successful backend's max). Other control lines are copied. If any allowed backend is down or the pin does not match, stderr also carries a `gateway_` line and `exit_code` is 2, so the list does not look complete.

HTTP status is a hint. The body is always the envelope. Backend engine errors stay HTTP 200 with the engine `exit_code`.

| HTTP | Code | When |
|------|------|------|
| 200 | engine lines | Backend reply, including engine `exit_code` other than 0 |
| 200 | list, some backends down | `session list` when at least one backend answered. `exit_code` is 2 if any backend was a gateway error |
| 400 | `gateway_bad_request` | Body is not a JSON object; `args` is not a list of strings; `stdin` is not a string; `session` field and `--session` disagree; `house` or `backend` is not a string; `session` is required and missing |
| 401 | `gateway_auth` | Missing, unknown, or revoked bearer; namespace does not match the credential; admin bearer missing or wrong |
| 403 | `gateway_forbidden_session` | Unknown session, another product's session, or a pin that would move the owner. The detail does not say which |
| 403 | `gateway_forbidden` | `house` or `backend` is outside the product, or argv is `admin` or `serve` |
| 404 | `gateway_bad_request` | Method or path is not `POST <path>`. The detail is `POST ` plus the configured path |
| 404 | `gateway_unconfigured` | `GET <path>/admin/counts` when `admin.sha256` is unset |
| 409 | `gateway_backend_version_mismatch` | `memnet version` is not the product pin |
| 413 | `gateway_body_too_large` | Body above `body_max_bytes` |
| 502 | `gateway_backend_unreachable` | TCP probe failed, the version command did not answer, the client wait expired, or `session list` and no backend answered |

No HTTP response (the process exits 2 instead):

| Exit | Code | When |
|------|------|------|
| 2 | `gateway_unconfigured` | `MEMNET_GATEWAY_CONFIG` is missing |
| 2 | `gateway_bad_request` | The config file does not load, or the bind address is refused |

`exit_code` on HTTP refusals is 2. They are not engine lines. An engine `@ERR: not_found|…` stays `not_found`.

## Concurrency

The gateway is a threaded HTTP server. Each POST is one `send_command` to the owning `memnet serve`. The serve is a threaded TCP server. MN-REQ-06.13: each command's stdout, stderr, and `exit_code` are captured on that request's context, not by swapping process-global `sys.stdout`. One session's records do not appear in another session's envelope. A failed mutate does not come back as another call's `ok=1 fail=0`.

There is no serve-wide lock. Requests on different sessions still overlap. The cost is a context-local lookup on each write, not a queue. On this VM, 12 successful TCP mutates at once took 0.494 s against 0.525 s one after another (ratio 0.94). The work is CPU-bound under the GIL, so the overlap is small. A lock would queue every command and could not beat that serial time. The TCP listen backlog is 128 so a burst is queued instead of refused at `accept`.

## Limits

The gateway does not enforce `MEMNET_MAX_ROWS`, `MEMNET_MAX_BATCH_LINES`, or `MEMNET_MAX_VALUE_BYTES`. Engine defaults are `MEMNET_MAX_ROWS` 5000, batch 1000 lines, value 4096 decoded bytes (`parts/common/memnet/memnet/config.py`). A product may send `--max-rows` and a mutate stdin up to the body ceiling. The backend still applies its own caps. Those refusals come back verbatim.

The gateway body ceiling is `body_max_bytes`, default **4194304** (4 MiB), the same figure as `MEMNET_SERVE_MAX_FRAME_BYTES`. State it in the config. Leave the gateway process's `MEMNET_SERVE_MAX_FRAME_BYTES` at least that large so the TCP client does not refuse a body the contract already accepted.

## Version pin

Each product has `pinned_version` (sample below, `0.19.20`). Before a forward, the gateway calls `version` on that backend and requires `@VER: memnet|<pin>`. A mismatch is `gateway_backend_version_mismatch` and the argv is not sent. Upgrading a serve without changing the pin refuses the product. Changing the pin is how the owner is notified: edit the config and restart the gateway.

`version_cache_s` defaults to 15. Set `0` to check every call. A serve upgraded inside a non-zero window can still be reached until the cache expires.

## Admin counts

`GET <path>/admin/counts` with `Authorization: Bearer <admin credential>`.

The admin secret is stored as `admin.sha256` only. The JSON lists each product's `requests`, `gateway_refusals`, and `backend_errors`. It has no graph text and no session id. Counts are in memory and reset when the process stops. If `admin.sha256` is unset, the route is `gateway_unconfigured` (HTTP 404).

## Listener

Default bind `127.0.0.1`. Tailnet addresses in `100.64.0.0/10` and Tailscale IPv6 `fd7a:115c:a1e0::/48` are allowed. `0.0.0.0` and other public addresses are refused unless `MEMNET_GATEWAY_ALLOW_PUBLIC=1`. Bind the loopback, or the host's own tailnet address. Do not publish the port.

## Examples

Credential and session ids below are placeholders. The backend id `pi-endleaf` is the live Endleaf id; any other string is valid if the config uses it consistently.

### session open

```http
POST /gateway
Authorization: Bearer <endleaf credential>
Content-Type: application/json

{
  "args": ["session", "open", "--map-file", "/var/memnet/schema.sysml.example.txt"],
  "namespace": "endleaf",
  "backend": "pi-endleaf"
}
```

```json
{
  "exit_code": 0,
  "stdout": "@SESSION: mn_example|2026-10-08T16:00:00Z|60\n",
  "stderr": "MEMNET_SESSION=mn_example\n"
}
```

The gateway records `mn_example` → backend `pi-endleaf`. The map path is on that serve, because `args` are not rewritten.

### MATCH … SET

```json
{
  "args": ["mutate", "--stdin", "--session", "mn_example"],
  "stdin": "MATCH (n {id: 'TSK_gw'}) SET n.status = 'settled'\n",
  "session": "mn_example",
  "namespace": "endleaf"
}
```

Reply `exit_code`, stdout, and stderr are the serve's. A missing element comes back as the engine line `@ERR: not_found|…`, not a `gateway_` line.

### Edge delete

```json
{
  "args": ["mutate", "--stdin", "--session", "mn_example"],
  "stdin": "MATCH ()-[r {id: 'E_gw'}]->() DELETE r\n",
  "session": "mn_example"
}
```

On 0.19.20 this empty-paren form deletes the edge (see closed decision 11). The gateway still forwards the bytes unchanged. It does not rewrite the statement. `MATCH (n WHERE true)-[r {id: 'E_gw'}]->() DELETE r` remains a valid spelling as well.

## Endleaf configuration

Hash the product credential and an admin credential. Do not commit the plaintext.

```bash
python -c "import hashlib,sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest())" 'REPLACE_WITH_ENDLEAF_CREDENTIAL'
```

The product host exports the plaintext bearer as `MEMNET_GATEWAY_TOKEN` (for example from `/etc/endleaf/memnet-gateway.env`). That file is not read by `memnet-mcp`. `MEMNET_MCP_HTTP_TOKEN` is a different variable and does not authenticate this route.

`/etc/memnet/gateway.json` (mode 0600, not in git). Backend ids are chosen by the operator. This sample uses the live id:

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
    "pi-endleaf": {
      "host": "100.118.79.40",
      "port": 18795
    }
  },
  "products": {
    "endleaf": {
      "backends": ["pi-endleaf"],
      "houses": {"syson": "pi-endleaf"},
      "pinned_version": "0.19.20",
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

To add a standby later, append another backend id to `backends` and to `endleaf.backends`, in failover order. Do not put another product's backend on Endleaf's list.

## Closed decisions

11. **Empty-paren edge delete.** On 0.19.18, `MATCH ()-[r {id}]->() DELETE r` did not delete an edge. On 0.19.20 it does (honoured; `tests/test_doc_gate_readiness.py`). The gateway still does not rewrite the statement. Closed for this pin.

## Open decisions

1. **Agent MCP tools.** stdio and streamable-http `pin_map` / `mutate` do not use the registry. Only `--transport gateway` does. Whether those tools should route by session is open.
2. **One gateway process.** The owner file is local. A second gateway does not share it. Multi-instance ownership is open.
3. **Admin counts reset** when the process stops. Durable counts are open.
4. **List `max`.** The filtered stat keeps the backend's `max`. Whether to hide `max` is open.
5. **Unknown and foreign sessions** share `gateway_forbidden_session` so the caller cannot tell them apart.
6. **Failover** is only for a new session with no `house` and no `backend`. There is no automatic return to a recovered preferred backend, and no SnapshotHandCarry (same sid, new owner). That relocate stays the #191 invent.
7. **Public bind** exists only behind `MEMNET_GATEWAY_ALLOW_PUBLIC=1`. Leave it unset on a public host.
8. **Bind host** must be an IP in loopback or tailnet, or the name `localhost`. MagicDNS names are not resolved.
9. **Tip keys.** Federating `mn_tip_` into this credential store is open. This cut does not.
10. **Version cache.** Default 15 seconds. The sample config sets `0`.
12. **`session list` on a shared backend** shows only sids this gateway recorded for that product. A session opened on the serve by a path other than this gateway is invisible here and is refused as unknown. Whether the gateway should adopt a sid the product already holds on its pinned backend is open.
