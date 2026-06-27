# MemNet novel — Cursor SDK beat runner

Thin **Cursor chat** + thick **`applications/novel_cursor/cursor_beat.py`** on MemNet.

Chat rule: [`.cursor/rules/novel-writer.mdc`](../.cursor/rules/novel-writer.mdc). Graph reference: [`llm-novel-writer.md`](llm-novel-writer.md).

## Prerequisites

1. `pip install -e ".[mcp,novel-mcp]"` (repo root)
2. `pip install -r applications/novel_cursor/requirements.txt` (`cursor-sdk`)
3. `memnet serve` in a terminal (`127.0.0.1:18765`)
4. `$env:CURSOR_API_KEY` set
5. Cursor chat model: **kimi-k2.5**

## Layer split

| Layer | Location | Cursor SDK? |
|-------|----------|-------------|
| Engine | `src/memnet/`, `src/memnet_mcp/`, `src/novel_mcp/` | No |
| Application | `applications/novel_cursor/` | Yes |
| Story instance | `applications/novel_cursor/instances/<id>.json` + `application-notes/novel-*-initial-state.md` | Config only |
| Chat UI | `.cursor/rules/novel-writer.mdc` | No (invokes app) |

Chat **never** calls `beat_turn_begin` / `beat_turn_finish` during play. The SDK agent does, in one run per player choice.

## Story instance

Each novel needs:

1. **Seed markdown** — `application-notes/novel-<slug>-initial-state.md` with `@USR` rows including at least `USR14|chapter_out|…` and `USR15|snapshot|…`.
2. **Instance JSON** (optional) — `applications/novel_cursor/instances/<slug>.json`:

```json
{
  "app_id": "shenjia_caifa",
  "seed_md": "application-notes/novel-shenjia-initial-state.md",
  "title": "工匠傳奇"
}
```

3. **Output tree** — derived from seed paths, e.g. `novel-output/shenjia_caifa/`.

Example instance: [`instances/shenjia_caifa.json`](../applications/novel_cursor/instances/shenjia_caifa.json).

## Session lifecycle (chat)

1. **「新開局還是讀檔？」**
   - 讀檔 → `session_load(file="<USR15 path>", keep_id=true)`
   - 新開局 → `python scripts/novel_bootstrap.py application-notes/novel-<slug>-initial-state.md`
   - Write `novel-output/<slug>/session_id.txt` (one line `mn_…`)

2. **`serve_status`** — stop if serve down.

3. **Resume display** — last chapter paragraph; if `USR23` mid-beat → `cursor_beat.py --continue`.

4. **Name gate** — `USR03` 未定 → ask 2–4 漢字 → `update`.

5. **Play** — on choice or steering → shell `cursor_beat.py` → parse result → show 【劇情】+ options + HUD.

6. **Save** — prompt only if `snapshot_saved=false` or player asks.

## `cursor_beat.py`

```powershell
python applications/novel_cursor/cursor_beat.py --app <slug> [--session ID] (--choice N | --steering TEXT | --continue) [--stream]

# Or without instance JSON:
python applications/novel_cursor/cursor_beat.py --seed application-notes/novel-<slug>-initial-state.md --choice 1
```

| Flag | Meaning |
|------|---------|
| `--app ID` | Load `instances/<ID>.json` (or infer seed from naming convention) |
| `--seed PATH` | Seed markdown; paths from USR14/USR15 |
| `--choice N` | Player option (1–6 for 《工匠傳奇》) |
| `--steering TEXT` | Free-text steering |
| `--continue` | Finish mid-beat from `USR23` stage |
| `--session` | Optional if `novel-output/<slug>/session_id.txt` exists |

**Env:** `NOVEL_APP` defaults `--app` when set.

**Model:** `kimi-k2.5` (hardcoded).

**Preflight:** TCP probe serve; `CURSOR_API_KEY` required; auto-load snapshot if session inactive.

**Exit codes:** 0 OK · 1 preflight/SDK failure · 2 bad args/missing session · 3 unparseable agent JSON.

## Output contract

Stdout trailer:

```text
NOVEL_BEAT_RESULT	{"exit_code":0,"session":"mn_…","app_id":"shenjia_caifa","prose":"…","options":["",…],"hud":"…","snapshot_saved":true,"snapshot_file":"novel-output/shenjia_caifa/session_snap.json","beat_stage":"oln"}
```

Always written: `novel-output/<slug>/last_beat.json`.

Legacy marker `SHENJIA_BEAT_RESULT` is retired; use `NOVEL_BEAT_RESULT`.

## MCP (SDK inline)

`applications/novel_cursor/mcp_config.py` launches:

- `python -m memnet_mcp.server`
- `python -m novel_mcp.server`

Env: `MEMNET_SERVE_HOST`, `MEMNET_SERVE_PORT`, `MEMNET_WORKSPACE_ROOT`, `MEMNET_SESSION` (session id for the beat run).

## Chat MCP allowlist

**Allowed:** `serve_status`, `session_load`, `session_save`, `session_current`, `read_get`, `update` (name gate), `query_warm` (resume display only).

**Forbidden:** `beat_turn_begin`, `beat_turn_finish`, `bootstrap_from_seed`, deprecated prose gates.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Stale `USR23` / wrong `beat_stage` | Reload MCP; use `python -m memnet_mcp.server` not stale `.exe` |
| `serve_status` false | `memnet serve` |
| `CURSOR_API_KEY` missing | Dashboard → Integrations |
| Mid-beat after crash | `cursor_beat.py --continue` |
| Parse failure (exit 3) | Re-run; check agent JSON block in stderr with `--stream` |
| Wrong paths | Check seed `USR14`/`USR15`; re-run with matching `--app` or `--seed` |

## Related

- [`applications/novel_cursor/README.md`](../applications/novel_cursor/README.md) — quick commands
- [`applications/shenjia_caifa/README.md`](../applications/shenjia_caifa/README.md) — 《工匠傳奇》 instance
