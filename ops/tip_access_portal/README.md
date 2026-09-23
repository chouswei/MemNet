# Tip MemNet access portal

Ops sidecar for **tip** MemNet MCP keys. tip is not the product face. This package is not the `memnet-llm` wheel and it does not change `pin_map`.

Teach and the nginx gate: [`docs/operations/tip-memnet-access-portal.md`](../../docs/operations/tip-memnet-access-portal.md).

## Run locally

From the MemNet repo root, with the repo virtualenv active:

```bash
pip install -e ops/tip_access_portal
# Put real values in a gitignored env file. The example file has empty placeholders.
export MEMNET_GOOGLE_CLIENT_ID="..."
export MEMNET_GOOGLE_CLIENT_SECRET="..."
export MEMNET_TIP_PORTAL_SECRET="..."
export MEMNET_TIP_ADMIN_EMAIL="..."
export MEMNET_TIP_PORTAL_BASE_URL="http://127.0.0.1:8766"
memnet-tip-portal
```

Google Cloud must list the redirect URI `{MEMNET_TIP_PORTAL_BASE_URL}/auth/callback`.

Production redirect URI:

`https://memnet.139-59-255-181.nip.io/auth/callback`

The process binds `127.0.0.1:8766` unless `MEMNET_TIP_PORTAL_BIND` / `MEMNET_TIP_PORTAL_PORT` say otherwise. Put TLS and the public host on nginx.

`/` is the invite-only gate. `/status` looks at configured MemNet listeners (`MEMNET_STATUS_PROBES` / `MEMNET_TIP_MCP_PROBE`). A 401 on the tip MCP still counts as up (shown as Reachable). Admin `/status` and `/admin` also show Bearer last-used and call counts. The page does not restart serve, mutate, or unpark the engine usage dashboard.
