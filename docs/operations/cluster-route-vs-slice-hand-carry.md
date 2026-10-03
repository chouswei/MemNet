# ClusterRoute vs SliceHandCarry

Agents keep conflating two moves. They are not the same invent. **tip≠face.** Invent-only: no engine code, no SemVer. Public operator: **InkMirage**.

| | **ClusterRoute (A)** | **SliceHandCarry (B)** |
|---|---|---|
| **What** | Where the session **lives** | Explicit **copy** into another session |
| **Issue / req** | [#191](https://github.com/chouswei/MemNet/issues/191) / MN-REQ-06.9 | [#47](https://github.com/chouswei/MemNet/issues/47) cousin / MN-REQ-06.10 |
| **Nest** | `MemNetLanMcpFront.clusterRoute` | `SliceHandCarry` |
| **One diagram** | `MemNetTwoMoves` (both children) | same |
| **Live hop?** | No. MCP forwards to the **owning** serve | No. A **file** leaves one serve |
| **`pin_map` / `find`** | Owning serve only. MUST NOT span backends | After absorb, **dest** session only |
| **`import_slice`** | Not this move | ONLY when both sessions are on the **SAME** serve |
| **Cross-host path** | Optional same-sid relocate: `session_save` → copy → `session_load` → update registry | `export_pin_map` or `session_save` → LAN file copy → dest `import` / `session_load` |
| **`import_slice(from_url)`** | Not shipped | Not shipped |
| **Caps / truncation** | Survive routing. Loud incomplete if a backend is down or clipped | Survive the file. MUST NOT claim a complete extract when clipped |
| **Commit gate** | Owning serve | Dest session’s owning serve after absorb |
| **Shared graph DB** | No (Neo4j retired [#189](https://github.com/chouswei/MemNet/issues/189)) | No |
| **Result** | Same session, one owner | Dest session absorbs a copy; source still lives on source |

Model: `MemNetTwoMoves` outside `MemNetSystem` (`MN-VER-06-S08`). Cluster detail: [`memnet-lan-mcp-front.md`](memnet-lan-mcp-front.md). Case study: [`sysml-models/outputs/cluster-route-vs-slice-hand-carry-case-study.md`](../../sysml-models/outputs/cluster-route-vs-slice-hand-carry-case-study.md).

`inventOnly=true`; `implemented=false`; `codeApproved=false`.
