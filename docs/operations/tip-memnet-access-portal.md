# Tip MemNet access portal

Ops access for **tip MemNet MCP** keys (tip≠face). This is **not** the SysMLEdge product face and **not** an `openProject` key page. Model: `TipMemNetAccessPortal` outside `MemNetSystem` (`MN-REQ-06.8` / `MN-VER-06-S05`). Case study: [`sysml-models/outputs/tip-memnet-access-portal-case-study.md`](../../sysml-models/outputs/tip-memnet-access-portal-case-study.md).

**Live sidecar.** `portalWebImplemented=true`. `inventOnly=false`. Code: [`ops/tip_access_portal/`](../../ops/tip_access_portal/). Console script: `memnet-tip-portal`. The `memnet-llm` Hatch version is unchanged. `pin_map` and engine operators are unchanged. Do not sell this as invent_2_green (`sellsInvent2Green=false`). Google client secrets and Bearer plaintext stay in the environment and the one-time browser page. The server stores hashes.

## Who

| Role | What they do |
|------|----------------|
| Admin **Szu-Wei** | Signs in with the Google account in `MEMNET_TIP_ADMIN_EMAIL`. Mints an invite link. Revokes a Bearer or an invite. |
| Invited user | Opens the invite, signs in with Google, then the portal shows their Bearer once (copy on that page). |
| Stranger | Gets no key here. Free MemNet is the SysMLEdge free tier or self-hosted `memnet-llm`. |

## Environment

Copy [`ops/tip_access_portal/.env.example`](../../ops/tip_access_portal/.env.example) to a gitignored file. Leave placeholders empty in git.

| Variable | Role |
|----------|------|
| `MEMNET_GOOGLE_CLIENT_ID` | Google OAuth client id |
| `MEMNET_GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `MEMNET_TIP_PORTAL_SECRET` | HMAC for session and one-time display cookies |
| `MEMNET_TIP_ADMIN_EMAIL` | Only this Google email can mint and revoke |
| `MEMNET_TIP_PORTAL_BASE_URL` | Public origin. Production: `https://memnet.139-59-255-181.nip.io` |
| `MEMNET_TIP_PORTAL_DB` | SQLite path for invites and key hashes. Default `data/tip-access-portal.sqlite` |
| `MEMNET_TIP_PORTAL_BIND` | Default `127.0.0.1` |
| `MEMNET_TIP_PORTAL_PORT` | Default `8766` |
| `MEMNET_TIP_INVITE_TTL_HOURS` | Default `168` |
| `MEMNET_STATUS_PROBES` | Optional look-only probes: `name=target,...`. Target is `http(s)://` or `tcp://host:port`. Do not point this at the portal's own `/healthz` from the same worker. |
| `MEMNET_TIP_MCP_PROBE` | Optional extra probe named `tip-mcp` (skipped if that name is already in `MEMNET_STATUS_PROBES`). Example: `https://memnet.139-59-255-181.nip.io/mcp` |

Required Google redirect URI:

`https://memnet.139-59-255-181.nip.io/auth/callback`

Local redirect URI, when `MEMNET_TIP_PORTAL_BASE_URL` is `http://127.0.0.1:8766`:

`http://127.0.0.1:8766/auth/callback`

## Run

```bash
pip install -e ops/tip_access_portal
memnet-tip-portal
```

Package notes: [`ops/tip_access_portal/README.md`](../../ops/tip_access_portal/README.md).

Admin opens `/`, signs in with Google, and mints an invite. The invite URL is shown once. The invitee opens `/invite/<token>`, signs in with Google, and `/key` shows `mn_tip_…` once. Reload does not show it again. Ask the admin for a new invite after a revoke.

`/` and `/status` show look-only service probes (name and up/down; probe targets stay admin-only). A 401 on `/mcp` still counts as up. Admin `/status` and `/admin` show Bearer client last-used and call counts. The page does not restart, mutate, `session_close`, or unpark `MemNetUsageDashboard` HTTP (`httpImplemented` stays false). `GET /auth/validate` records last-used when the Bearer is active.

## Call the tip

Public URL (gate only):

`https://memnet.139-59-255-181.nip.io/mcp`

Header:

```http
Authorization: Bearer <key>
```

`TipMcpGate` is nginx `auth_request` in front of that location. It calls the portal `GET /auth/validate` (alias `GET /internal/bearer-check`). The portal returns **200** when the Bearer hash is active and the invite is not revoked, and **401** otherwise. nginx then proxies the MCP call to the Pi tip. A missing or revoked Bearer is refused. Unauthenticated MemNet MCP on that WWW URL stays off. Keyed tip MemNet on droplet WWW stays on.

The portal does not terminate `/mcp`. Do not `proxy_pass` `/mcp` straight at the Pi.

## nginx (Devicor)

Replace `PI_TIP_UPSTREAM` with the Pi tip streamable-http listener (the engine default port is `18766`; the path on that upstream is `/mcp`). Keep the portal on loopback.

```nginx
upstream pi_tip_mcp {
    server PI_TIP_UPSTREAM;  # example: 10.0.0.8:18766
}

server {
    listen 443 ssl;
    server_name memnet.139-59-255-181.nip.io;

    # Portal HTML, Google callback, and the auth_request target.
    location / {
        proxy_pass http://127.0.0.1:8766;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Keyed tip MemNet MCP. Unauthenticated requests never reach the Pi.
    location /mcp {
        auth_request /_tip_bearer_check;
        proxy_pass http://pi_tip_mcp;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Connection "";
        proxy_set_header Authorization $http_authorization;
        proxy_pass_request_headers on;
    }

    location = /_tip_bearer_check {
        internal;
        proxy_pass http://127.0.0.1:8766/auth/validate;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header Authorization $http_authorization;
    }
}
```

`auth_request` does not forward `Authorization` unless `proxy_set_header Authorization $http_authorization` is set on `/_tip_bearer_check`. Without that line the gate would refuse every caller.

## systemd

`/etc/systemd/system/memnet-tip-portal.service`:

```ini
[Unit]
Description=MemNet tip access portal
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/memnet
EnvironmentFile=/etc/memnet/tip-portal.env
ExecStart=/opt/memnet/.venv/bin/memnet-tip-portal
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

`/etc/memnet/tip-portal.env` holds the variables above. It is not in git.

```bash
sudo systemctl enable --now memnet-tip-portal
```

## Soft-pass kills

- A sysmledge product key page, or an `openProject` gate, invented from this portal
- Open or unauthenticated MemNet MCP on the WWW URL
- Selling **invent_2_green** (production-green) from this portal
- Unparking engine `MemNetUsageDashboard` HTTP from this status look
- Restart / mutate / `session_close` from the portal page
