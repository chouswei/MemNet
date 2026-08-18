# Agent context — MemNet

**MemNet session:** `(open when serve/MCP is up)` · **Anchor:** `TSK_model_memnet`

## Summary

Net of Memory: **mission working memory for LLMs** (session-scoped NODE|EDGE buffer) — not chat notepad, not search corpus, not GraphRAG, not a Cypher proxy. Cue then `pin_map`; host RAG stays outside. This repo is **engine + generic memnet-mcp** only. Novel-writer out of scope (`DROP-NOVEL-WRITER.md`). EvidenceCentre / MissionDock / CompanyMemory are application (downstream), not MemNet parts.

Doctrine: **GQL only** + shaped **`pin_map`** + gated mutate (`id:'NEW'`); handoff = **session id** (A→B pipe; B cue then `pin_map`; chat/HTTP/MissionDock never carry the graph). CapsPolicy **ACL shipped** when enabled; RSV + Path-B ingest shipped; 0.7 live cabinet proven (not vendored). Shape: `docs/SHAPE.md`. Pointers: `docs/grammar/gql-wire-profile.md` → `docs/LLM-GUIDE.md` → `docs/adr/ADR-001-gql-agent-wire.md`. Layer / Tier A archived — not product teach.

## MemNet

Query `TSK_model_memnet` — do not duplicate topology/backlog here.
