#!/usr/bin/env python3
"""Model the engine + MCP packages via memnet-mcp tools and write a snapshot.

Uses the same in-process MCP tool functions Cursor would call (session_open,
ingest_codebase, add, pin_map, session_save). The snapshot file is gitignored.

    python scripts/snap_memnet_codebase.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("MEMNET_TEST_INLINE", "1")
os.environ.setdefault("MEMNET_MCP_TRANSPORT", "inprocess")

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "parts" / "common" / "memnet" / "memnet" / "examples"
SCHEMA = EXAMPLES / "schema.codebase.example.txt"
OUT = ROOT / "memnet-codebase.snap.txt"
ENGINE = ROOT / "parts" / "common" / "memnet" / "memnet"
MCP = ROOT / "parts" / "memnet-mcp" / "software" / "memnet_mcp"
TASK_ID = "TSK_model_memnet"
MAX_NODES = 8000
MAX_FILES = 128


def _load(payload: str) -> dict:
    data = json.loads(payload)
    if data.get("exit_code", 1) != 0:
        err = data.get("stderr") or data.get("errors") or payload
        raise SystemExit(f"mcp tool failed: {err}")
    return data


async def main() -> int:
    from memnet.session import get_session
    from memnet_mcp.server import add, ingest_codebase, pin_map, session_open, session_save

    if not SCHEMA.is_file():
        print(f"Missing schema: {SCHEMA}", file=sys.stderr)
        return 1

    opened = _load(
        await session_open(map_file=str(SCHEMA), ttl=1440)
    )
    sid = opened.get("session_id")
    if not sid:
        print(opened, file=sys.stderr)
        return 1
    print(f"session={sid}")

    anchors: list[str] = []
    for path in (ENGINE, MCP):
        ingest = _load(
            await ingest_codebase(
                path=str(path),
                max_nodes=MAX_NODES,
                max_files=MAX_FILES,
                root=str(ROOT),
                session=sid,
            )
        )
        stdout = ingest.get("stdout") or ""
        print(stdout.strip())
        for line in stdout.splitlines():
            if line.startswith("@ANCHORS:"):
                anchors.extend(
                    a.strip() for a in line.split(":", 1)[1].split(",") if a.strip()
                )

    _load(
        await add(
            wire_lines=[
                (
                    f"CREATE (:TSK {{id: '{TASK_ID}', goal: 'Model MemNet engine and MCP', "
                    "status: 'in_progress', recycle: 'persistent'})"
                )
            ],
            session=sid,
        )
    )

    primary = TASK_ID if TASK_ID else (anchors[0] if anchors else None)
    if primary:
        mapped = _load(
            await pin_map(anchor=primary, depth=2, max_rows=20, session=sid)
        )
        print("--- pin_map sample ---")
        print((mapped.get("stdout") or "")[:2500])

    saved = _load(await session_save(file=str(OUT), session=sid))
    print((saved.get("stdout") or "").strip())

    ss = get_session(sid)
    rows = ss.store.row_count_non_law()
    print(f"saved {OUT} ({rows} non-LAW rows)")
    if anchors:
        print("anchors: " + ",".join(anchors[:8]))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
