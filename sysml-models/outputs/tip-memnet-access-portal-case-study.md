# Case study: tip MemNet access portal (keyed Bearer)

**Shelf:** product canon — ops access (not the SysMLEdge product)

Evidence walk of a **gated** human portal that mints invites and shows Bearer keys for **tip MemNet MCP only**.  
Companions: [device-fleet-one-mcp-case-study.md](device-fleet-one-mcp-case-study.md) (tip≠face; Pi tip legal), [usage-dashboard-case-study.md](usage-dashboard-case-study.md) (engine HTTP parked; portal `/status` is a separate look-only page, not that dashboard).  
Lock: portal = **tip/ops access**; product invent face stays cousin `sysmledge`. The portal web is the ops sidecar (`portalWebImplemented=true`). Do not sell it as invent_2_green. Status look (`statusLookOnly=true`) MUST NOT unpark `MemNetUsageDashboard` HTTP (`unparksUsageDashboard=false`).

**Wire:** agents still GQL / `pin_map` / `mutate`. The portal does not change those operators. Callers of the public tip URL send `Authorization: Bearer <key>`.

## 1. Purpose

Let admin **Szu-Wei** invite a person, let that person sign in with **Google**, and let them **see their Bearer** for the tip MemNet MCP. Droplet WWW keeps **keyed** tip MemNet. **Unauthenticated** MemNet MCP on that WWW URL is refused. Strangers who want a free MemNet do **not** get one here: they use the SysMLEdge free tier or self-host `memnet-llm`.

## 2. Model locus

| Concern | SysML |
|---------|-------|
| Requirement | **MN-REQ-06.8** (`tipMemNetAccessPortalReq`) |
| Verify | **MN-VER-06-S05** |
| Part | `TipMemNetAccessPortal` **outside** `MemNetSystem` |
| Load | Already on `ProjectMemNet` via `deploy.sysml` (`config.yaml` / `root.sysml` import `MemNet`) |
| Items | `InviteLink`, `GoogleLoginAssert`, `TipMcpBearer`, `TipMcpForward`, `TipMemNetAccess` |
| Parts | `TipAccessAdmin`, `InvitedTipUser`, `GoogleIdP`, `PortalWeb`, `InviteStore`, `KeyStore`, `TipMcpGate`, `PiTipMemNetMcp` |

```text
MemNetSystem                                 // SharedLlmMemory product (unchanged)
TipMemNetAccessPortal                        // OUTSIDE — ops access, tip≠face
├── TipAccessAdmin                           // Szu-Wei; mint invite; revoke
├── InvitedTipUser
├── GoogleIdP
├── PortalWeb                                // ops sidecar; portalWebImplemented=true
├── InviteStore
├── KeyStore
├── TipMcpGate                               // WWW URL; Bearer required
└── PiTipMemNetMcp                           // forward target; not public by itself
```

Public URL (gate only): `https://memnet.139-59-255-181.nip.io/mcp`.

## 3. Scenario

**Title:** Admin invites a user; user fetches a Bearer; the gate checks it

**Premise:** Tip MemNet MCP is reachable on droplet WWW only through `TipMcpGate`. The Pi runs the tip process. The portal web is `ops/tip_access_portal`. Google client secrets stay in the environment. nginx `auth_request` is taught for Devicor and is not applied by the model file.

**Actors:**

- Szu-Wei — admin (`displayName=Szu-Wei`)
- Invited user — allowlist redeem, then Google login
- `TipMcpGate` — refuses a request with no Bearer

**Steps (model mandates):**

| Step | What happens | MUST NOT |
|------|----------------|----------|
| **1. Mint invite** | Admin → `InviteStore` | Stranger self-signup; sysmledge `openProject` |
| **2. Redeem** | Invite lands on the portal allowlist | Grant a key before redeem |
| **3. Google login** | User → `GoogleIdP` → `PortalWeb` | Treat Google as the product-face login |
| **4. Show Bearer** | Portal → `KeyStore` → portal shows the key | Show a key to a user who is not invited |
| **5. Call tip MCP** | Client sends `Authorization: Bearer <key>` to the WWW URL; gate forwards to the Pi tip | Unauthenticated MemNet MCP on that URL |
| **6. Revoke** | Admin revokes the Bearer or the invite | Leave a revoked key accepted at the gate |
| **7. Status look** | `/` and `/status` probe configured listeners; admin sees last-used | Unpark dashboard HTTP; restart / mutate / `session_close` / `session_drop_stale` from the page |

## 4. Contrast (soft-pass kills)

| Not this | Why |
|----------|-----|
| SysMLEdge product / `openProject` key page | `isSysmlEdgeProduct=false`; `openProjectKeyPage=false`; `gatesSysmlEdge=false` |
| Tip as product face | `tipIsFace=false`; `gatesTipMcpOnly=true` |
| Open / unauthenticated MemNet MCP on WWW | `unauthenticatedWwwMcp=false`; `gate.unauthenticatedAllowed=false`; keyed WWW stays (`keyedWwwMcp=true`) |
| Portal grants free MemNet to strangers | `grantsOpenMemNet=false`; `freeStrangerPath=sysmledge-free-tier-or-memnet-llm-self-host` |
| Nest under `MemNetSystem` | `tipAccessPortalInsideSystem=false` |
| Selling **invent_2_green** | `sellsInvent2Green=false`; `inventOnly=false`; `portalWebImplemented=true` (sidecar shipped; secrets stay in env; engine unchanged) |
| Unparking engine usage-dashboard HTTP | `unparksUsageDashboard=false`; `statusLookOnly=true`; `MemNetUsageDashboard.httpImplemented` stays `false` |

## 5. Teach (live sidecar)

`portalWebImplemented=true`. Steps and nginx: [`docs/operations/tip-memnet-access-portal.md`](../../docs/operations/tip-memnet-access-portal.md).

1. **Admin mints an invite.** Szu-Wei signs in as `MEMNET_TIP_ADMIN_EMAIL` and creates an invite link. That link is the only way onto the allowlist.
2. **User fetches a key.** The invitee opens the link, signs in with Google, and the portal shows their Bearer once. The server stores a hash.
3. **Tip MCP header.** Requests to `https://memnet.139-59-255-181.nip.io/mcp` carry `Authorization: Bearer <key>`. nginx `auth_request` calls `GET /auth/validate`, then forwards to the Pi tip. A missing or revoked Bearer is refused.
4. **Revoke.** Szu-Wei revokes the key or the invite. The gate then refuses that Bearer.
5. **Status look.** `/` and `/status` show configured MemNet listeners (401 on `/mcp` still counts as up). Admin sees probe targets and Bearer last-used. The page does not manage serve.

## 6. Honesty

The portal web is the ops sidecar `ops/tip_access_portal` (`memnet-tip-portal`). Google secrets are environment variables. nginx for `/mcp` is documented for Devicor and still refuses unauthenticated calls. `pin_map` / mutate operators are unchanged. Hatch `memnet-llm` is not bumped. `sellsInvent2Green=false`. Status look does not unpark `MemNetUsageDashboard` HTTP.
