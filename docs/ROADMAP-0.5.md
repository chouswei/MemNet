# Roadmap — 0.5 leftover and 1.0 gates

**Status:** plan (docs). **MUST NOT** treat leftover engine as shipped.  
**Audience:** product developers. British English.  
**Filename** `ROADMAP-0.5.md` is historical; this file is the product version map.  
**Agent ops:** [`LLM-GUIDE.md`](LLM-GUIDE.md) / [`multi-agent-sessions.md`](multi-agent-sessions.md) — dialect = **GQL** ([`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md)).

**Product:** MemNet is **mission working memory** (session NODE | EDGE) between LLM pipelines and data search — not the corpus, not GraphRAG. Handoff = **session id**; peers re-`pin_map`; chat is never SSOT. Durable GQL **backs** sessions; it is not the handoff handle and not Cypher-proxy teach.

Orthodox = theorems you **build from**. Paradox = **all** examination and test. Detail: [`../sysml-models/outputs/recall-commit-orthodox-plan.md`](../sysml-models/outputs/recall-commit-orthodox-plan.md). Math: [`grammar/math-skeleton.md`](grammar/math-skeleton.md).

---

## Version map (2026-08-18)

| Version | Owns | Blocks the SemVer claim? |
|---------|------|--------------------------|
| **0.4.x (now)** | M1–M3; M2.5 **client**; goldfish orthodox erected (`pin_map`, mutate, one live `TSK`, sparse Δ, RSV, Path-B ingest/Absorb, CapsPolicy ACL off-by-default) | — (PyPI `memnet-llm`) |
| **0.5.0** | Leftover **goldfish Recall**: paradox pytest, then leftover erect (#73 LIMIT find, union-under-one-\(M\)) | **No** live AgensGraph |
| **1.0.0** | **Live** M2.5 cabinet (external AgensGraph hydrate/flush, one sync owner) | Fake-alone **fails** this gate |
| **Later** | Host Snap adapter **outside** `MemNetSystem`; N-server pipe; pin-map export; Peak_L if still wanted; close [#77](https://github.com/chouswei/MemNet/issues/77) | Not 0.5 and not 1.0 |

User-pack GQL-only skills (`chouswei/cursor-user-skills`) run **in parallel** — not a repo SemVer gate.

---

## Already in 0.4.x (do not list as deferred)

M1 wire profile · M2 GQL accept + shaped `pin_map` · M3 in-repo GQL teach · M2.5 client (`DurableStoreAdapter` / Fake / optional AgensGraph client) · CapsPolicy ACL (off by default) · RSV · Path-B ingest (#64) · ImportAbsorb + ImportGuard / CheapLlmImportGuard · LocalIpcGateway.

Playbook goldfish: one live `TSK` map, optional `view=shell`, sparse `add`/`update`. Design-locked: Snap vs Shape; host search **outside**; Peak_L last never default.

---

## 0.5.0 — leftover goldfish

In-process. Cabinet does **not** serialise this track.

| Order | Kind | Work | Done when |
|-------|------|------|-----------|
| 1 | Paradox | Pytest V1, V3, V4, V6 (no new MCP) | CI green; no `rag_query` |
| 2 | Erect | [#73](https://github.com/chouswei/MemNet/issues/73) `BoundedMatchFind` | Hard LIMIT \(L\); shaped emit not `RETURN`; `implemented=true` + MN-VER-13 honesty |
| 3 | Erect | Multi-ego union-under-**one** \(M\) | One LAW prepend; **not** Path-B \(M\times\)anchors |

**Out of the 0.5.0 claim (still leftover, later):** optional `Peak_L` on \(\rho^*\) (explicit cue only). Host Snap ship. Live cabinet.

V-cases and probes: orthodox plan — do not copy them here.

**0.5.0 MUST NOT:** `rag_query`; ANN of \(S\); RRF; HostSearch under `MemNetSystem`; goldfish Δ via ImportAbsorb; Peak_L as default goldfish; Layer teach; claim #73 from `pin_map` alone.

---

## 1.0.0 — live cabinet

| Gate | Pass | Fail |
|------|------|------|
| Live M2.5 cabinet | Hydrate/flush against **external** AgensGraph in an operator environment; one sync owner | Claim 1.0 on Fake-alone; LLM↔store direct; MemNet-as-Cypher-proxy |

Client already landed in 0.4.x. This gate is **proof**, not a rebuild. Sketch: [`grammar/agensgraph-buffer.md`](grammar/agensgraph-buffer.md).

Prefer 0.5 leftover **claimed** before 1.0 (goldfish closed in-process, then durable proof). The cabinet still does **not** block starting 0.5 work.

---

## Later (not 0.5, not 1.0)

| Item | Notes |
|------|--------|
| Host search / RAG nest | Application `HostSearchBridge` **outside** `MemNetSystem`; locators only ([#84](https://github.com/chouswei/MemNet/pull/84) design-lock) |
| `Peak_L` | Last-resort topology cue; never default goldfish |
| N-server session pipe | [#47](https://github.com/chouswei/MemNet/issues/47) |
| Pin-map export / round-trip | MN-REQ-11.1–11.5 / [#66](https://github.com/chouswei/MemNet/issues/66); ingest ≠ export |
| First-class `PORT` NODE; SCHEMA vocab freeze | Ports stay properties |
| Full ACL modes / roles / `session_token` | CapsPolicy cut already ships when enabled |

[#77](https://github.com/chouswei/MemNet/issues/77) stays open until HostSearch ship / #73 / Peak_L are **decided**, not when this file exists.

---

## Standing teach / ops (all versions)

One remote: Cursor **`memnet-pi`** `"url"` → streamable-http (`:18766/mcp`). Stdio `memnet-local` is optional / dev-only.

One dialect: **GQL** only. Write = display = bounded shaped `pin_map`. Layer / Tier A archived.

One graph owner on Pi: HTTP MCP bridges **`memnet serve`** (`:18765`). No dual writers.

Footguns: LAN bind + trusted hosts; non-empty HTTP token; omit `view=` → shell-safe default.

Working memory ≠ corpus: retrieve / generate / remember unfused. Host MAY propose locators; skip is valid. Find leftover is **graph** lookup, not corpus RAG.

---

## Related

| Path | Role |
|------|------|
| [`../README.md`](../README.md) | Doctrine / how to run |
| [`adr/ADR-001-gql-agent-wire.md`](adr/ADR-001-gql-agent-wire.md) | GQL wire; no Layer |
| [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md) | **M1 SSOT** |
| [`grammar/math-skeleton.md`](grammar/math-skeleton.md) | Recall / Commit math |
| [`../sysml-models/outputs/recall-commit-orthodox-plan.md`](../sysml-models/outputs/recall-commit-orthodox-plan.md) | Orthodox; paradox V1–V10 |
| [`grammar/agensgraph-buffer.md`](grammar/agensgraph-buffer.md) | Durable adapter; live cabinet = 1.0.0 |
| [`grammar/memnet-host-search-nest.md`](grammar/memnet-host-search-nest.md) | Host Snap (later; outside engine) |
| [`grammar/gql-model-exam.md`](grammar/gql-model-exam.md) | GQL-wire paradox (historical filename) |
| [`multi-agent-sessions.md`](multi-agent-sessions.md) | Multitask transport |
| [`../.cursor/mcp.json.example`](../.cursor/mcp.json.example) | `memnet-pi` primary |
