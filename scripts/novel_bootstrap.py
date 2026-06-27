"""Bootstrap any novel session from an application-notes markdown seed."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from memnet.config import serve_host
from novel_mcp.beat_pipeline import beat_turn_begin
from novel_mcp.bootstrap import bootstrap_from_md
from novel_mcp.warm_index import index_warm, usr_value

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap novel session from seed md")
    parser.add_argument(
        "md_path",
        nargs="?",
        default=str(ROOT / "application-notes" / "novel-shenjia-initial-state.md"),
    )
    args = parser.parse_args()

    boot = bootstrap_from_md(args.md_path)
    if boot.get("exit_code", 1) != 0:
        print(json.dumps(boot, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(boot.get("exit_code", 1))

    sid = boot["session_id"]
    begin = beat_turn_begin(session=sid, include_warm=True)
    warm = begin.get("warm_stdout") or ""
    idx = index_warm(warm)
    pc_unset = usr_value(idx, "pc_name") == "未定"

    out = {
        "session_id": sid,
        "serve_host": serve_host(),
        "exit_code": begin.get("exit_code"),
        "pipeline": begin.get("pipeline"),
        "presentation": begin.get("presentation"),
        "session_modified": begin.get("session_modified"),
        "pc_name_unset": pc_unset,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
