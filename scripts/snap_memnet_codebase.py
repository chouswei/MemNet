#!/usr/bin/env python3
"""Build MemNet codebase index and write memnet-codebase.snap.txt (inline, one process)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Inline mode: single process retains session registry.
os.environ.setdefault("MEMNET_TEST_INLINE", "1")

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "parts" / "common" / "memnet" / "memnet" / "examples"
SCHEMA = EXAMPLES / "schema.coding.example.txt"
SEED = EXAMPLES / "workflow.memnet-codebase.snap.txt"
OUT = ROOT / "memnet-codebase.snap.txt"


def main() -> int:
    from typer.testing import CliRunner

    from memnet.cli import app
    from memnet.session import get_session

    if not SEED.is_file():
        print(f"Missing seed: {SEED}", file=sys.stderr)
        print("Run: python scripts/generate_memnet_codebase_seed.py", file=sys.stderr)
        return 1

    runner = CliRunner()
    r1 = runner.invoke(app, ["session", "open", "--map-file", str(SCHEMA), "--ttl", "1440"])
    if r1.exit_code != 0:
        print(r1.stdout, r1.stderr, file=sys.stderr)
        return r1.exit_code
    sid = r1.stdout.strip().split("|")[0].replace("@SESSION: ", "")
    print(f"session={sid}")

    seed_lines = [
        ln
        for ln in SEED.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    chunk_size = 400
    for i in range(0, len(seed_lines), chunk_size):
        chunk = "\n".join(seed_lines[i : i + chunk_size])
        r2 = runner.invoke(
            app,
            ["add", "--stdin", "--allow-new-relation", "--session", sid],
            input=chunk + "\n",
        )
        if r2.exit_code != 0:
            print(r2.stdout, r2.stderr, file=sys.stderr)
            return r2.exit_code

    r3 = runner.invoke(app, ["session", "save", "--file", str(OUT), "--session", sid])
    if r3.exit_code != 0:
        print(r3.stdout, r3.stderr, file=sys.stderr)
        return r3.exit_code

    r4 = runner.invoke(
        app,
        [
            "query",
            "warm",
            "--anchor",
            "TSK_codebase_snap_memnet",
            "--depth",
            "2",
            "--max-rows",
            "15",
            "--session",
            sid,
        ],
    )
    print("--- warm sample (first 15 rows) ---")
    print(r4.stdout[:2000])

    ss = get_session(sid)
    rows = ss.store.row_count_non_law()
    print(f"saved {OUT} ({rows} non-LAW rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
