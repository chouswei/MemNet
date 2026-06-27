# 《工匠傳奇》 instance

This folder is a **story instance** for the generic novel Cursor runner.

- Instance config: [`../novel_cursor/instances/shenjia_caifa.json`](../novel_cursor/instances/shenjia_caifa.json)
- SSOT seed: [`application-notes/novel-shenjia-initial-state.md`](../../application-notes/novel-shenjia-initial-state.md)
- Output: `novel-output/shenjia_caifa/` (chapters, snapshot, `session_id.txt`, `last_beat.json`)

## Commands

```powershell
# Preferred (generic runner)
python applications/novel_cursor/cursor_beat.py --app shenjia_caifa --choice 2

# Legacy shim (same behaviour)
python applications/shenjia_caifa/cursor_beat.py --choice 2

# Bootstrap new session
python scripts/novel_bootstrap.py application-notes/novel-shenjia-initial-state.md
```

See [`application-notes/llm-novel-cursor-sdk.md`](../../application-notes/llm-novel-cursor-sdk.md).
