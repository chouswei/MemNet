# Agent context — MemNet

**MemNet session:** `(open when serve/MCP is up)` · **Anchor:** `TSK_model_memnet`

## Summary

Net of Memory: agent memory graph (NODE|EDGE) between LLM call pipelines and data search. This repo is **engine + generic memnet-mcp** only (part layout under `parts/`). Novel-writer is out of scope — see `DROP-NOVEL-WRITER.md`.

Doctrine (shared read/write dialect = **Tier A** Write=display; live **pin map**; in-process first; `NEW` vs locators): `README.md` → `docs/grammar/` → `sysml-models/`. Operational loop still in `docs/LLM-GUIDE.md` (pipe migration pending; prefer pin map over “warm” as the primary term).

## MemNet

Query `TSK_model_memnet` — do not duplicate topology/backlog here.
