# Novel Cursor beat runner

Dual **persistent** Cursor SDK agents per story: **編劇** (OLN→SBD→SCR) + **作者** (prose).

Operator guide: [`application-notes/llm-novel-cursor-sdk.md`](../../application-notes/llm-novel-cursor-sdk.md).

## Setup

```powershell
pip install -e ".[mcp,novel-mcp]"
pip install -r applications/novel_cursor/requirements.txt
memnet serve
$env:CURSOR_API_KEY = "..."
```

## New game

```powershell
python scripts/novel_bootstrap.py application-notes/novel-<slug>-initial-state.md
# write novel-output/<slug>/session_id.txt

python applications/novel_cursor/cursor_beat.py --app <slug> --reset-agents --choice 1
```

## Play

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
| `--reset-agents` | Delete `agents/*.txt`; recreate SDK sessions |
| `--stream` | SDK events to stderr |

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

## Agent id files

```text
novel-output/<slug>/agents/script_agent_id.txt
novel-output/<slug>/agents/prose_agent_id.txt
```

Resumed via `Agent.resume` each beat (not recreated unless missing or `--reset-agents`).

## Legacy shim

`applications/shenjia_caifa/cursor_beat.py` → `--app shenjia_caifa`.
