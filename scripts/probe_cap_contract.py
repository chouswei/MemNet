#!/usr/bin/env python3
"""Hit every documented cap and write a sid-free proof log.

Usage (from repo root, venv active):

    python scripts/probe_cap_contract.py --out /opt/cursor/artifacts/cap-contract-proof.log
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
for path in (str(ROOT), str(TESTS)):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("MEMNET_TEST_INLINE", "1")
os.environ.pop("MEMNET_SESSION", None)

from cap_contract_lib import (  # noqa: E402
    _SID_RE,
    collect_all,
    defaults_record,
    render_proof,
)
from memnet.session import purge_expired, reset_registry, set_now_override  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe MemNet cap contract (no session ids).")
    parser.add_argument(
        "--out",
        default="cap-contract-proof.log",
        help="Proof log path (session ids are refused if present).",
    )
    args = parser.parse_args()
    set_now_override(None)
    reset_registry()
    purge_expired()
    with tempfile.TemporaryDirectory(prefix="cap-contract-") as raw:
        tmp = Path(raw)
        cases = collect_all(tmp)
        blob = render_proof(cases, defaults=defaults_record())
    if _SID_RE.search(blob):
        raise SystemExit("refusing to write proof: session id leaked")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(blob, encoding="utf-8")
    sys.stdout.write(f"wrote {out} ({len(cases)} cases)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
