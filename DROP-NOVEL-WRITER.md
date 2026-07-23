# Drop novel writer

Novel writer was removed from the MemNet repository so this repo hosts the **graph engine + memnet-mcp** only. User intent: keep novel-writer dropped even when a concurrent re-layout briefly restored `parts/novel-writer/`.

## Removed (in-repo)

| Area | Paths |
|------|--------|
| Product part | `parts/novel-writer/` (`novel_mcp`, `novel_mobile`, `novel_cursor`, `shenjia_caifa`) |
| Legacy trees | Already gone / not restored: `applications/novel_*`, `src/novel_mcp/` |
| Docs | `docs/application-notes/llm-novel-*.md`, `novel-seed-spec.md`, `novel-shenjia-*.md` |
| Cursor rule | `.cursor/rules/novel-writer.mdc` |
| Scripts | `scripts/novel_*.py`, `beat_turn.py`, `bench_novel_turn.py`, `debug_cursor_beat_timing.py`, `estimate_novel_io_tokens.py`, `prose_count.py`, `run_beats_smoke.py`, `reorganize_seed.py` |
| Tests / fixtures | Novel-domain `tests/test_*.py`; `tests/fixtures/catalog_schema_fantasy.json`; novel fixtures in `conftest.py` |
| Examples | `schema.novel.example.txt`, `schema.shenjia.example.txt`, `workflow.novel.example.txt`, `examples/restore_beat10.py` |
| Scratch cut | `_ref_novel_cut/` (untracked) |
| Packaging | `novel-mcp` / `novel-mobile` extras and console scripts in `pyproject.toml`; `novel-writer` removed from `project.toml` `[parts].roots` |
| MCP config | `novel-writer` entry removed from `.cursor/mcp.json` |
| Agent hub | `AGENTS.md` / `LAYOUT.md` no longer register novel as a product surface |

## Kept

- `parts/common/memnet/` — core library / CLI (Tier A, pin map, MutateGate)
- `parts/memnet-mcp/` — generic MemNet MCP
- Non-novel application notes (coding, news, tech-docs, SysML, MUD, build-on-memnet)
- Engine tests under `tests/` that do not import novel packages
- Part-based layout per SYSTEM-REPO-LAYOUT (`parts/common/memnet`, `parts/memnet-mcp`)
- Doctrine docs: `README.md`, `docs/grammar/`, `sysml-models/` — Net of Memory only

## Left on disk (manual)

| Item | Action |
|------|--------|
| `novel-output/` | Local session / chapter data (gitignored). Delete locally if you no longer need it. |
| User Cursor MCP | Remove any `novel-writer` / `novel-mcp` server from `~/.cursor/mcp.json` (or OS-equivalent) if still registered outside this repo. |
| User skill | Optional: remove or archive `~/.cursor/skills/mcp-novel-writer/` if present. |
| Historical `CHANGELOG.md` | Still mentions novel releases; left as history. |

## Layout agreement

`LAYOUT.md` and `project.toml` list only `common/memnet` and `memnet-mcp`. Do not reintroduce `parts/novel-writer/` under a layout migration without an explicit product decision to restore it.

## Smoke

Verified after reconcile (via `PYTHONPATH=parts/common/memnet;parts/memnet-mcp/software`):

- `import memnet`, `import memnet_mcp` → OK
- `novel_mcp` / `novel_mobile` → not found
- Focused `pytest` on remaining engine tests → see latest smoke run

Reinstall editable when no process holds `memnet-mcp.exe`:

```powershell
pip install -e ".[mcp,dev]"
python -c "import memnet, memnet_mcp; print(memnet.__file__)"
pytest -q
```
