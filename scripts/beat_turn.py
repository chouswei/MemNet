"""CLI for beat_turn_begin / beat_turn_finish (Shell fallback when MCP unavailable)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from novel_mcp.beat_pipeline import beat_turn_begin, beat_turn_finish


def main() -> None:
    parser = argparse.ArgumentParser(description="Novel beat pipeline (2-call orchestration).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    begin = sub.add_parser("begin", help="Warm read + pipeline envelope")
    begin.add_argument("--session")
    begin.add_argument("--anchor", default="STEP01")
    begin.add_argument("--depth", type=int, default=2)
    begin.add_argument("--max-rows", type=int, default=55)

    finish = sub.add_parser("finish", help="Atomic OLN + prose + persist + save")
    finish.add_argument("--session")
    finish.add_argument("--prose")
    finish.add_argument("--prose-file")
    finish.add_argument("--chapter-dir")
    finish.add_argument("--chp-num", type=int)
    finish.add_argument("--min-chars", type=int)
    finish.add_argument("--max-chars", type=int)
    finish.add_argument("--usr05")
    finish.add_argument("--add-file", help="Wire lines file for memnet add")
    finish.add_argument("--update-file", help="Wire lines file for memnet update")
    finish.add_argument("--oln-file")
    finish.add_argument("--oln-mode", default="add", choices=["add", "update"])
    finish.add_argument("--sbd-file")
    finish.add_argument("--sbd-mode", default="add", choices=["add", "update"])
    finish.add_argument("--scr-file")
    finish.add_argument("--scr-mode", default="add", choices=["add", "update"])
    finish.add_argument("--snapshot-file")
    finish.add_argument("--workspace-root", default=str(ROOT))
    finish.add_argument("--replace-last", action="store_true")
    finish.add_argument("--allow-new-relation", action="store_true")
    finish.add_argument("--prose-only-gate", action="store_true")
    finish.add_argument("--pipeline-bypass", action="store_true")

    args = parser.parse_args()

    if args.cmd == "begin":
        result = beat_turn_begin(
            session=args.session,
            anchor=args.anchor,
            depth=args.depth,
            max_rows=args.max_rows,
        )
    else:
        prose = args.prose
        if args.prose_file:
            prose = Path(args.prose_file).read_text(encoding="utf-8")
        add_lines = (
            [ln for ln in Path(args.add_file).read_text(encoding="utf-8").splitlines() if ln.strip()]
            if args.add_file
            else None
        )
        update_lines = (
            [ln for ln in Path(args.update_file).read_text(encoding="utf-8").splitlines() if ln.strip()]
            if args.update_file
            else None
        )
        oln_lines = (
            [ln for ln in Path(args.oln_file).read_text(encoding="utf-8").splitlines() if ln.strip()]
            if args.oln_file
            else None
        )
        sbd_lines = (
            [ln for ln in Path(args.sbd_file).read_text(encoding="utf-8").splitlines() if ln.strip()]
            if args.sbd_file
            else None
        )
        scr_lines = (
            [ln for ln in Path(args.scr_file).read_text(encoding="utf-8").splitlines() if ln.strip()]
            if args.scr_file
            else None
        )
        result = beat_turn_finish(
            session=args.session,
            prose=prose,
            chapter_dir=args.chapter_dir,
            chp_num=args.chp_num,
            min_chars=args.min_chars,
            max_chars=args.max_chars,
            usr05_band=args.usr05,
            add_lines=add_lines,
            update_lines=update_lines,
            oln_lines=oln_lines,
            oln_mode=args.oln_mode,
            sbd_lines=sbd_lines,
            sbd_mode=args.sbd_mode,
            scr_lines=scr_lines,
            scr_mode=args.scr_mode,
            snapshot_file=args.snapshot_file,
            workspace_root=args.workspace_root,
            replace_last_paragraph=args.replace_last,
            allow_new_relation=args.allow_new_relation,
            prose_only_gate=args.prose_only_gate,
            pipeline_bypass=args.pipeline_bypass,
        )

    print(json.dumps(result, ensure_ascii=False))
    sys.exit(result.get("exit_code", 1))


if __name__ == "__main__":
    main()
