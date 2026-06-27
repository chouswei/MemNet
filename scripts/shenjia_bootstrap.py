"""Bootstrap shenjia session from novel-shenjia-initial-state.md."""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from memnet.config import serve_host
from memnet_mcp.client import run_memnet
from novel_mcp.beat_pipeline import beat_turn_begin
from novel_mcp.bootstrap import bootstrap_from_md
from novel_mcp.warm_index import index_warm, usr_value

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "application-notes" / "novel-shenjia-initial-state.md"
OUT_DIR = ROOT / "novel-output" / "shenjia_caifa"
SNAP_PATH = OUT_DIR / "session_snap.json"
CHAPTERS = OUT_DIR / "chapters"


def main() -> None:
    boot = bootstrap_from_md(MD)
    if boot.get("exit_code", 1) != 0:
        print(json.dumps(boot, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(boot.get("exit_code", 1))

    sid = boot["session_id"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    save = run_memnet(["session", "save", "--file", str(SNAP_PATH)], session=sid)
    if save.exit_code != 0:
        print(json.dumps({"save": save.errors}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(save.exit_code)

    if CHAPTERS.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive = OUT_DIR / f"chapters_pre_bootstrap_{stamp}"
        shutil.move(str(CHAPTERS), str(archive))

    begin = beat_turn_begin(session=sid, include_warm=True)
    warm = begin.get("warm_stdout") or ""
    idx = index_warm(warm)
    out = {
        "session_id": sid,
        "serve_host": serve_host(),
        "exit_code": begin.get("exit_code"),
        "pipeline": begin.get("pipeline"),
        "presentation": begin.get("presentation"),
        "session_modified": begin.get("session_modified"),
        "snapshot": str(SNAP_PATH),
        "pc_name_unset": usr_value(idx, "pc_name") == "未定",
        "pipeline_no_bundle": begin.get("pipeline", {}).get("pipeline_no_bundle"),
        "stage_hint": (begin.get("presentation") or {}).get("contracts", [""])[0],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
