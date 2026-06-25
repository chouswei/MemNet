"""Local prose length check — same logic as novel-writer prose_metrics, no MCP round-trip.

Use while drafting a beat; call beat_prose_finalize (MCP) once when gate_ready=true.
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
    if args.usr05:
        min_c, max_c = parse_scene_band(args.usr05)

    result = prose_status(prose, min_chars=min_c, max_chars=max_c)
    result["exit_code"] = 0
    result["errors"] = []
    result["mcp_hint"] = (
        "gate_ready → call beat_prose_finalize once; else rewrite beat, re-run this script (no MCP)"
    )
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result.get("gate_ready") else 1)


if __name__ == "__main__":
    main()
