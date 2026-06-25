"""Beat prose gate: metrics + chapter append in one process (Shell fallback)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from novel_mcp.chapter_io import chapter_prose_gate
from novel_mcp.zh_text import prose_status


def _read_prose(args: argparse.Namespace) -> str:
    if args.prose_file:
        return Path(args.prose_file).read_text(encoding="utf-8")
    if args.prose is not None:
        return args.prose
    return sys.stdin.read()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate beat prose (RULE09) and append one chapter paragraph.",
    )
    parser.add_argument("--prose", help="Prose string (omit to read stdin)")
    parser.add_argument("--prose-file", help="Path to prose text file")
    parser.add_argument("--chapter-dir", required=True, help="Relative chapter directory (USR06)")
    parser.add_argument("--chp-num", type=int, required=True, help="Open @CHP.chp_num")
    parser.add_argument("--workspace-root", default=str(ROOT), help="Repo root (default: MemNet)")
    parser.add_argument("--min-chars", type=int, default=None, help="Gate lower bound (with --max-chars)")
    parser.add_argument("--max-chars", type=int, default=None, help="Gate upper bound (with --min-chars)")
    parser.add_argument(
        "--replace-last",
        action="store_true",
        help="Replace last paragraph (RULE09 fix)",
    )
    parser.add_argument(
        "--metrics-only",
        action="store_true",
        help="Count only; do not write chapter file",
    )
    args = parser.parse_args()

    prose = _read_prose(args)
    if args.metrics_only:
        result = prose_status(prose, min_chars=args.min_chars, max_chars=args.max_chars)
        result["exit_code"] = 0
        result["errors"] = []
    else:
        result = chapter_prose_gate(
            prose,
            chapter_dir=args.chapter_dir,
            chp_num=args.chp_num,
            workspace_root=args.workspace_root,
            min_chars=args.min_chars,
            max_chars=args.max_chars,
            replace_last_paragraph=args.replace_last,
        )

    print(json.dumps(result, ensure_ascii=False))
    sys.exit(result.get("exit_code", 1))


if __name__ == "__main__":
    main()
