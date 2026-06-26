"""Local prose length check — optional when USR05 has min/max band (e.g. 650_950_zh).

Under no_gate / length_advisory, beat_turn_finish counts in-process; this script is not needed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from novel_mcp.zh_text import parse_scene_band, prose_status


def main() -> None:
    parser = argparse.ArgumentParser(description="Count beat prose; gate_ready without MCP.")
    parser.add_argument("--prose", help="Prose string (omit to read stdin)")
    parser.add_argument("--prose-file", help="Path to prose text file")
    parser.add_argument("--min-chars", type=int, help="Lower bound (or use --usr05)")
    parser.add_argument("--max-chars", type=int, help="Upper bound (or use --usr05)")
    parser.add_argument("--usr05", help="USR05 band code, e.g. 650_950_zh")
    args = parser.parse_args()

    if args.prose_file:
        prose = Path(args.prose_file).read_text(encoding="utf-8")
    elif args.prose is not None:
        prose = args.prose
    else:
        prose = sys.stdin.read()

    min_c, max_c = args.min_chars, args.max_chars
    if args.usr05 in ("no_gate", "length_advisory"):
        min_c, max_c = None, None
    elif args.usr05 and (min_c is None or max_c is None):
        min_c, max_c = parse_scene_band(args.usr05)

    result = prose_status(prose, min_chars=min_c, max_chars=max_c)
    if result.get("status") == "no_gate":
        result["mcp_hint"] = "no_gate：不必呼叫本腳本；直接 beat_turn_finish。"
    else:
        result["mcp_hint"] = (
            "gate 啟用時本地確認長度；gate_ready 後 beat_turn_finish。"
        )
    result["exit_code"] = 0
    result["errors"] = []
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
