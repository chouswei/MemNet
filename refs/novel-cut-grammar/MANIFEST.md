# novel-cut grammar extract — manifest

**Source:** https://github.com/chouswei/novel-cut  
**Pinned commit:** `6a0ed88396f6a6e295c7f7adef8852b04a3cf515`  
**Fetched:** selective `gh api` blob download (not a full clone)  
**`.g4` files in upstream:** none

## Files fetched

| Relative path | Purpose |
|---------------|---------|
| `specs/md_triple_grammar.md` | LLM wire grammar SSOT @1.3 — **Write = display** |
| `specs/md_triple_module.json` | Machine flags + grammar path |
| `specs/prose_thread_module.json` | Digest budgets (`GN_CAP`, ego hops, class include) |
| `specs/core_engine.json` | Author-prompt contracts (WDC) |
| `docs/architecture.md` | Flow: option → prose_thread → **G_n digest** → assembler |
| `SOURCE-README.md` | Upstream README snapshot |
| `src/novel_engine/md_triple.py` | Compile author md_triple lines → bags |
| `src/novel_engine/assembler.py` | `load_md_triple_grammar()` into system prompt |
| `src/novel_engine/world_graph.py` | `compose_g_n_digest(...)` implementation |
| `src/novel_engine/currency.py` | Grammar contract notes for cash/owe |

## Gn / compose_g_n_digest pointers

- Architecture flow (`docs/architecture.md`): `prose_thread classify -> G_n digest -> assembler`.
- Implementation: `src/novel_engine/world_graph.py` — function `compose_g_n_digest` (ego expand, EDG class filter, cast/status lines; ages stay in Cast SSOT).
- Budgets / include sets: `specs/prose_thread_module.json` (`GN_CAP`, `ego_hops`, `digest_include`).

## Explicitly not fetched

- `applications/`, `seeds/`, prompt packs, novel modules, play loop, tests, deploy.
- Nothing under MemNet `parts/` (novel-writer stays dropped).
