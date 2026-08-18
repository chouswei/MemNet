# MemNet roadmap (all versions)

**Status:** plan (docs). **MUST NOT** treat leftover engine as shipped.  
**Audience:** product developers. British English.  
**SSOT** for SemVer intent. Patch notes stay in [`../CHANGELOG.md`](../CHANGELOG.md). Live package: `project.toml` **0.4.6** (`memnet-llm`; CLI `memnet`).  
**Agent ops:** [`LLM-GUIDE.md`](LLM-GUIDE.md) / [`multi-agent-sessions.md`](multi-agent-sessions.md). Dialect: **GQL** ([`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md)).

**Product:** mission working memory (session NODE | EDGE) between LLM pipelines and data search — not the corpus, not GraphRAG. Handoff = **session id**; peers re-`pin_map`; chat is never SSOT. Durable GQL **backs** sessions; it is not the handoff handle.

Orthodox = theorems you **build from**. Paradox = **all** examination and test. [`../sysml-models/outputs/recall-commit-orthodox-plan.md`](../sysml-models/outputs/recall-commit-orthodox-plan.md). Math: [`grammar/math-skeleton.md`](grammar/math-skeleton.md).

Historical filename [`ROADMAP-0.5.md`](ROADMAP-0.5.md) redirects here.

---

## Lineage (shipped)

Coarse eras only. Every patch: CHANGELOG.

| Era | When | What landed |
|-----|------|-------------|
| **0.1.x** | 2026-06 | In-memory session graph; TCP `memnet serve`; pipe `@TAG` wire; `query warm`; recycle; snapshots. Local only. |
| **0.2.x** | 2026-06–07 | Packaging, CLI harden, MCP beginnings, serve protocol. Still pipe / early MCP. |
| **0.3.x** | 2026-07–08 | **MutateGate** / **PinMapComposer** / `NEW` mint; in-process MCP default; **novel-writer dropped**; parts layout; serve bind/frame caps. Teach was **Tier A**. |
| **0.4.0–0.4.2** | 2026-08 | `pin_map(view=)`; Layer slice then **ADR-001: GQL-only wire**; Layer/Tier A retired from accept. |
| **0.4.3–0.4.6 (now)** | 2026-08 | M2 GQL emit; M3 in-repo GQL teach; CapsPolicy ACL; RSV; Path-B ingest (#64); ImportAbsorb / ImportGuard / CheapLlmImportGuard (#63); **M2.5 client** hydrate/flush (Fake always-on). Goldfish orthodox **erected**. |

M-phases (wire, not SemVer): **M1** profile · **M2** engine GQL · **M3** in-repo GQL docs — **done**. **M2.5 client** done in 0.4.x. **Live cabinet** is a **1.0.0** gate (durable proof), not the whole of 1.0, and not a 0.5 lock.

---

## Forward map

| Version | Owns | SemVer claim blocked by |
|---------|------|-------------------------|
| **0.4.x** | Lineage above | — (current PyPI) |
| **0.5.0** | Leftover **goldfish Recall** (in-process) | **Not** live AgensGraph |
| **1.0.0** | **Mature tool for people** (0.5 leftover claimed + live durable path + one GQL teach) | Fake-alone as “durable”; leftover find still `implemented=false`; Layer teach |
| **Later** | Host Snap ship; N-server; pin-map export; Peak_L; close [#77](https://github.com/chouswei/MemNet/issues/77) | Not required to call 1.0 mature working memory |

User-pack GQL skills (`chouswei/cursor-user-skills`) run **in parallel** — not a repo SemVer gate.

---

## 0.5.0 — leftover goldfish

In-process. Cabinet does **not** serialise this track.

| Order | Kind | Work | Done when |
|-------|------|------|-----------|
| 1 | Paradox | Pytest V1, V3, V4, V6 (no new MCP) | CI green; no `rag_query` |
| 2 | Erect | [#73](https://github.com/chouswei/MemNet/issues/73) `BoundedMatchFind` | Hard LIMIT \(L\); shaped emit not `RETURN`; `implemented=true` |
| 3 | Erect | Multi-ego union-under-**one** \(M\) | One LAW prepend; **not** Path-B \(M\times\)anchors |

**Out of the 0.5.0 claim:** `Peak_L`; Host Snap ship; live cabinet. V-probes: orthodox plan.

**MUST NOT:** `rag_query`; ANN of \(S\); RRF; HostSearch under `MemNetSystem`; goldfish Δ via ImportAbsorb; Peak_L as default; Layer teach; claim #73 from `pin_map` alone.

---

## 1.0.0 — mature tool for people

**1.0.0** means an outsider can install MemNet and use it as **mission working memory**: one GQL dialect, goldfish `pin_map`, gated mutate, cue-then-shape (including find when there is no ego), and an optional **proven** durable cabinet so a session can outlive a process. It does **not** mean GraphRAG, `rag_query`, or Peak_L.

People already have in 0.4.x: PyPI `memnet-llm`, MCP, `pin_map` / mutate, playbook, Multitask over TCP/HTTP, Fake hydrate/flush. 1.0 **closes the leftover** and **proves durability**.

| Gate | Pass | Fail |
|------|------|------|
| Goldfish leftover | **0.5.0 claimed**: V-tests; [#73](https://github.com/chouswei/MemNet/issues/73) LIMIT find; union-under-one-\(M\) | `pin_map` only; free `MATCH`/`RETURN` as goldfish; Path-B \(M\times\)anchors as goldfish budget |
| Live durable path | Hydrate/flush against **external** AgensGraph; one sync owner; README says how | Claim 1.0 durable on Fake-alone; LLM↔store direct; MemNet-as-Cypher-proxy |
| Teach | In-repo [`LLM-GUIDE.md`](LLM-GUIDE.md) GQL-only; Layer archived | Dual dialect; Layer as accept path |
| Role | Working memory ≠ corpus; locators-only if host Snap is used | `rag_query` on `memnet-mcp`; chunk bodies as memory |

Client hydrate/flush is already 0.4.x. The cabinet gate is **operator proof**, not a rebuild. [`grammar/agensgraph-buffer.md`](grammar/agensgraph-buffer.md).

Cabinet does **not** block starting 0.5 work. Prefer 0.5 leftover **claimed** before tagging 1.0.

User-pack GQL skills (`chouswei/cursor-user-skills`) should match the playbook; they are **not** a second engine gate.

---

## Later (after 1.0, or beside it)

Not required for **mature working memory**. Do **not** hold 1.0 for these.

| Item | Notes |
|------|--------|
| Host search / RAG nest | `HostSearchBridge` **outside** `MemNetSystem`; locators only ([#84](https://github.com/chouswei/MemNet/pull/84)) |
| `Peak_L` | Last-resort topology cue; never default goldfish |
| N-server session pipe | [#47](https://github.com/chouswei/MemNet/issues/47) |
| Pin-map export / round-trip | MN-REQ-11.1–11.5 / [#66](https://github.com/chouswei/MemNet/issues/66) |
| First-class `PORT` NODE; SCHEMA vocab freeze | Ports stay properties |
| Full ACL modes / `session_token` | CapsPolicy cut already ships when enabled |

[#77](https://github.com/chouswei/MemNet/issues/77) stays open until HostSearch ship / Peak_L are **decided**.

---

## Standing teach / ops (every version from 0.4.x)

| Lock | MUST | MUST NOT |
|------|------|----------|
| Remote | Cursor **`memnet-pi`** `"url"` → `:18766/mcp` | Treat stdio `memnet-local` as default shared remote |
| Dialect | GQL only; Write = display = shaped `pin_map` | Layer / Tier A teach or accept |
| Owner | HTTP MCP bridges **`memnet serve`** `:18765` | Two writers on one mission |
| Footguns | Trusted hosts; non-empty HTTP token; omit `view=` → shell | Empty-token LAN as safe |
| Role | Working memory ≠ corpus; host locators optional | `rag_query`; chunk bodies as memory |

---

## Related

| Path | Role |
|------|------|
| [`ROADMAP-0.5.md`](ROADMAP-0.5.md) | Stub (old filename) |
| [`../CHANGELOG.md`](../CHANGELOG.md) | Patch history |
| [`../README.md`](../README.md) | Doctrine / how to run |
| [`adr/ADR-001-gql-agent-wire.md`](adr/ADR-001-gql-agent-wire.md) | GQL wire |
| [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md) | M1 SSOT |
| [`../sysml-models/outputs/recall-commit-orthodox-plan.md`](../sysml-models/outputs/recall-commit-orthodox-plan.md) | Paradox V1–V10 |
| [`grammar/agensgraph-buffer.md`](grammar/agensgraph-buffer.md) | Durable adapter |
| [`multi-agent-sessions.md`](multi-agent-sessions.md) | Multitask |
| [`../.cursor/mcp.json.example`](../.cursor/mcp.json.example) | `memnet-pi` |
