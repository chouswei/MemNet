# Case study: tip MemNet access portal (keyed Bearer)

**Shelf:** product canon — ops access (not the SysMLEdge product)

Evidence walk of a **gated** human portal that mints invites and shows Bearer keys for **tip MemNet MCP only**.  
Companions: [device-fleet-one-mcp-case-study.md](device-fleet-one-mcp-case-study.md) (tip≠face; Pi tip legal), [usage-dashboard-case-study.md](usage-dashboard-case-study.md) (look, not this key page).  
Lock: portal = **tip/ops access**; product invent face stays cousin `sysmledge`. This cut is **invent only**.

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
├── PortalWeb                                // invent only; portalWebImplemented=false
├── InviteStore
├── KeyStore
├── TipMcpGate                               // WWW URL; Bearer required
└── PiTipMemNetMcp                           // forward target; not public by itself
```

Public URL (gate only): `https://memnet.139-59-255-181.nip.io/mcp`.

## 3. Scenario

**Title:** Admin invites a user; user fetches a Bearer; the gate checks it

**Premise:** Tip MemNet MCP is reachable on droplet WWW only through `TipMcpGate`. The Pi runs the tip process. No Google client secret and no nginx change ship in this invent.

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

## 4. Contrast (soft-pass kills)

| Not this | Why |
|----------|-----|
| SysMLEdge product / `openProject` key page | `isSysmlEdgeProduct=false`; `openProjectKeyPage=false`; `gatesSysmlEdge=false` |
| Tip as product face | `tipIsFace=false`; `gatesTipMcpOnly=true` |
| Open / unauthenticated MemNet MCP on WWW | `unauthenticatedWwwMcp=false`; `gate.unauthenticatedAllowed=false`; keyed WWW stays (`keyedWwwMcp=true`) |
| Portal grants free MemNet to strangers | `grantsOpenMemNet=false`; `freeStrangerPath=sysmledge-free-tier-or-memnet-llm-self-host` |
| Nest under `MemNetSystem` | `tipAccessPortalInsideSystem=false` |
| Selling **invent_2_green** from this invent | `sellsInvent2Green=false`; `inventOnly=true`; `portalWebImplemented=false` (no live OAuth secret, no droplet nginx, no engine change) |

## 5. Teach (when the web app exists)

Until `portalWebImplemented` flips, these steps are the model, not a live site.

1. **Admin mints an invite.** Szu-Wei creates an invite link in the portal. That link is the only way onto the allowlist.
2. **User fetches a key.** The invitee opens the link, signs in with Google, and the portal shows their Bearer once.
3. **Tip MCP header.** Requests to `https://memnet.139-59-255-181.nip.io/mcp` carry `Authorization: Bearer <key>`. The gate forwards that call to the Pi tip. A missing or revoked Bearer is refused.
4. **Revoke.** Szu-Wei revokes the key or the invite. The gate then refuses that Bearer.

## 6. Honesty

SysML plus this note lock the access story. The portal web app, Google client secrets, and droplet nginx are **not** in this cut. `pin_map` / mutate operators are unchanged. Hatch is not bumped for this invent.
