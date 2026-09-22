# Tip MemNet access portal (invent)

Ops access for **tip MemNet MCP** keys (tip≠face). This is **not** the SysMLEdge product face and **not** an `openProject` key page. Model: `TipMemNetAccessPortal` outside `MemNetSystem` (`MN-REQ-06.8` / `MN-VER-06-S05`). Case study: [`sysml-models/outputs/tip-memnet-access-portal-case-study.md`](../../sysml-models/outputs/tip-memnet-access-portal-case-study.md).

**Invent only.** `portalWebImplemented=false`. No Google client secret, no droplet nginx, no `pin_map` / engine change in this cut. Do not treat this note as a live site.

## Who

| Role | What they do |
|------|----------------|
| Admin **Szu-Wei** | Mints an invite link. Revokes a Bearer or an invite. |
| Invited user | Opens the invite, signs in with Google, then the portal shows their Bearer. |
| Stranger | Gets no key here. Free MemNet is the SysMLEdge free tier or self-hosted `memnet-llm`. |

## Call the tip

Public URL (gate only):

`https://memnet.139-59-255-181.nip.io/mcp`

Header:

```http
Authorization: Bearer <key>
```

`TipMcpGate` checks that header and forwards to the **Pi tip** MemNet MCP. A missing or revoked Bearer is refused. Unauthenticated MemNet MCP on that WWW URL stays off. Keyed tip MemNet on droplet WWW stays on.

## Soft-pass kills

- A sysmledge product key page, or an `openProject` gate, invented from this portal
- Open or unauthenticated MemNet MCP on the WWW URL
- Selling **invent_2_green** (production-green) from this invent
