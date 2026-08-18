# Agent context — MemNet

**MemNet session:** `(open when serve/MCP is up)` · **Anchor:** `TSK_model_memnet`

## Summary

Net of Memory: **mission working memory for LLMs** (session-scoped NODE|EDGE buffer) — not chat notepad, not search corpus, not GraphRAG, not a Cypher proxy. Cue then `pin_map`; host RAG stays outside. This repo is **engine + generic memnet-mcp** only. Novel-writer out of scope (`DROP-NOVEL-WRITER.md`). EvidenceCentre / MissionDock / CompanyMemory are application (downstream), not MemNet parts.

Doctrine: **GQL only** + shaped **`pin_map`** + gated mutate (`id:'NEW'`); handoff = **session id** (A→B pipe; B `pin_map`; chat/HTTP/MissionDock never carry the graph; keep mission vs `companySessionId` distinct); CapsPolicy **ACL shipped** (who / TRAVERSE≈pin_map vs WRITE≈mutate / WorkerWriteScope / optional bind; session id = capability); M2.5 client hydrate/flush landed; live cabinet = **1.0.0** gate. Pointers: `docs/grammar/gql-wire-profile.md` → `docs/LLM-GUIDE.md` → `docs/adr/ADR-001-gql-agent-wire.md` → `sysml-models/outputs/system-design-notes.md`. Layer / Tier A archived — not product teach.

## MemNet

Query `TSK_model_memnet` — do not duplicate topology/backlog here.
