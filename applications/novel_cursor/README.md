# Novel Cursor beat runner

Generic MemNet novel-play application: **thin Cursor chat** + **thick SDK beat** via `cursor_beat.py`.

## Setup

```powershell
pip install -e ".[mcp,novel-mcp]"
pip install -r applications/novel_cursor/requirements.txt
memnet serve
$env:CURSOR_API_KEY = "..."
```

Optional default story: `$env:NOVEL_APP = "shenjia_caifa"`.

## Run a beat

```powershell
# Registered instance (applications/novel_cursor/instances/<id>.json)
python applications/novel_cursor/cursor_beat.py --app shenjia_caifa --choice 2

# Or point at any seed markdown (paths from USR14/USR15 in seed)
python applications/novel_cursor/cursor_beat.py --seed application-notes/novel-shenjia-initial-state.md --choice 1

python applications/novel_cursor/cursor_beat.py --app shenjia_caifa --steering "低聲問芯"
python applications/novel_cursor/cursor_beat.py --app shenjia_caifa --continue
```

Session id: `novel-output/<slug>/session_id.txt` (one line `mn_…`), or `--session`.

## Output

- Stdout: `NOVEL_BEAT_RESULT\t{json}`
- File: `novel-output/<slug>/last_beat.json`

## New story

1. Add `application-notes/novel-<slug>-initial-state.md` with `@USR` rows including `USR14|chapter_out|…` and `USR15|snapshot|…`.
2. Add `applications/novel_cursor/instances/<slug>.json` (optional; or use `--seed`).
3. Bootstrap: `python scripts/novel_bootstrap.py application-notes/novel-<slug>-initial-state.md`
4. Write `session_id` to `novel-output/<slug>/session_id.txt`.

See [`application-notes/llm-novel-cursor-sdk.md`](../../application-notes/llm-novel-cursor-sdk.md).

## Legacy shim

`applications/shenjia_caifa/cursor_beat.py` forwards to `--app shenjia_caifa`.
