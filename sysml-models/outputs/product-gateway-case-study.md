# Case study: product gateway on memnet-mcp (MN-REQ-06.12)

**Shelf:** product canon — shipped memnet-mcp capability (parent catalogue stays inventOnly #191)

Online products reach a `memnet serve` through `memnet-mcp --transport gateway`. Endleaf now. Atelier and SysMLEdge later, each with their own credential and backend list. The #191 MCP tool union and SnapshotHandCarry stay invent-only on `MemNetLanMcpFront`. Lock: **tip≠face**. Product credentials are not `mn_tip_` keys. No SemVer. Wire: [`docs/operations/product-gateway-contract.md`](../../docs/operations/product-gateway-contract.md).

**Wire:** the gateway forwards argv and stdin. It does not merge graphs. A session has one owning serve. Chat is never SSOT.

## 1. Purpose

Give each product a scoped credential and a backend list, place each new session on one live serve that matches the version pin, and refuse a foreign session instead of moving it.

## 2. Model locus

| Concern | SysML |
|---------|-------|
| Requirement | **MN-REQ-06.12** (`productGatewayReq`) |
| Verify | **MN-VER-06-S10** |
| Part | `MemNetProductGateway` nested on `MemNetLanMcpFront`, **outside** `MemNetSystem` |
| Code | `productGatewayMod` → `parts/memnet-mcp/software/memnet_mcp/product_gateway.py` |

```text
MemNetLanMcpFront                            // OUTSIDE — inventOnly #191 (unchanged)
└── MemNetProductGateway                     // shipped child; implemented=true
```

Parent attributes stay `inventOnly=true`, `implemented=false`, `codeApproved=false`. The child is `reusesTipBearer=false`, `oneOwnerPerSession=true`, `silentCrossBackendMove=false`, `failoverOnlyForNewSession=true`, `publicBindDefault=false`.
