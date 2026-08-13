# Agent context — MemNet

**MemNet session:** `(open when serve/MCP is up)` · **Anchor:** `TSK_model_memnet`

## Summary

Net of Memory: shared LLM working memory (session-scoped graph) between LLM call pipelines and data search. This repo is **engine + generic memnet-mcp** only (part layout under `parts/`). Novel-writer is out of scope — see `DROP-NOVEL-WRITER.md`.

Doctrine (**GQL only** agent wire; shaped **`pin_map`** read; gated mutate; in-process first; `NEW` vs locators; handoff = **session id** (module A→B pipe; B `pin_map`; chat/HTTP never carry the graph); prefer **import** over session merge): `docs/grammar/gql-wire-profile.md` → `docs/LLM-GUIDE.md` → `docs/adr/ADR-001-gql-agent-wire.md` → `sysml-models/`. Historical Layer / Tier A sources are quarantined under `docs/grammar/archive/` — not product teach.

## MemNet

Query `TSK_model_memnet` — do not duplicate topology/backlog here.
