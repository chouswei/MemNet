# Novel Cursor beat runner

Dual **chat threads** (編劇 / 作者) with per-role models; MemNet presentation augments each turn.

## Models

| Role | Env | Default |
|------|-----|---------|
| 編劇 | `LLM_MODEL_SCRIPT` | `deepseek-v4-flash` + **thinking on** |
| 作者 | `LLM_MODEL_PROSE` | `deepseek-v4-flash` + thinking off |

Instance: `thinking_script` / `thinking_prose` in `instances/<slug>.json`. 編劇可改 `deepseek-v4-pro` 若仍常出 wire 錯。

Operator guide: [`application-notes/llm-novel-cursor-sdk.md`](../../application-notes/llm-novel-cursor-sdk.md). SEED: [`application-notes/novel-seed-spec.md`](../../application-notes/novel-seed-spec.md).

**Session:** one `session_id` on `memnet serve` — shared by memnet-mcp, novel-mcp, and `cursor_beat`. `session_id.txt` is only a pointer.

## Setup

```powershell
pip install -e ".[mcp,novel-mcp]"
pip install -r applications/novel_cursor/requirements.txt
memnet serve
$env:DEEPSEEK_API_KEY = "..."   # https://platform.deepseek.com
# optional per-role: LLM_API_KEY_SCRIPT / LLM_API_KEY_PROSE
# optional override: LLM_BASE_URL (default https://api.deepseek.com)
```

## New game

```powershell
python scripts/novel_bootstrap.py application-notes/novel-<slug>-initial-state.md
# copy returned session_id → novel-output/<slug>/session_id.txt

python applications/novel_cursor/cursor_beat.py --app <slug> --reset-agents --choice 1
```

## Play

**Operator chat:** run `cursor_beat.py` only — do not commit beats via novel-mcp from the IDE agent (that path is for system tests).

```powershell
python applications/novel_cursor/cursor_beat.py --app shenjia_caifa --choice 2
python applications/novel_cursor/cursor_beat.py --app shenjia_caifa --steering "低聲問芯"
python applications/novel_cursor/cursor_beat.py --app shenjia_caifa --continue
```

## Flags

| Flag | Effect |
|------|--------|
| `--choice N` | Player option 1–6 (script then prose) |
| `--steering TEXT` | Free-text steering |
| `--continue` | Resume mid-beat (`sbd`/`scr`/`prose`) |
| `--script-only` | Script agent only; exit 4 if handoff fails |
| `--prose-only` | Prose agent only (`USR23` must be `prose`) |
| `--reset-threads` | Clear 編劇 + 作者 chat history |
| `--stream` | Log LLM provider to stderr |

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | OK |
| 1 | Serve / SDK failure |
| 2 | Bad args / prepare gate |
| 3 | Prose JSON unparseable |
| 4 | Script handoff failed |

## Output

- Stdout: `NOVEL_BEAT_RESULT\t{json}`
- File: `novel-output/<slug>/last_beat.json`

## Flow

1. `script_beat_prepare` → for each of oln/sbd/scr: `beat_turn_begin` → LLM wire draft → `beat_turn_finish`
2. `prose_beat_prepare` → `beat_turn_begin` → LLM prose JSON → `beat_turn_finish`
3. `NOVEL_BEAT_RESULT` + `last_beat.json`

LLM calls are **text-only** (OpenAI-compatible HTTP). MCP begin/finish run **in-process** in Python.

## Agent id files (legacy)

```text
novel-output/<slug>/agents/script_agent_id.txt
novel-output/<slug>/agents/prose_agent_id.txt
```

Unused in orchestrated mode; safe to delete.

## Legacy shim

`applications/shenjia_caifa/cursor_beat.py` → `--app shenjia_caifa`.
