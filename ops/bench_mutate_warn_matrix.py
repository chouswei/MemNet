"""Run bench_mutate_warn.py for base vs head, several sizes and repeats, one at a time.

usage: python ops/bench_mutate_warn_matrix.py <base memnet dir> <head memnet dir> [repeats]

Each run is a fresh process, alternating base and head within a size so load
drift hits both. Prints a table of the median across repeats of each run's p50
and p95 (ms), plus the per-repeat p50s.
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys

SIZES = (490, 4900, 9800, 50000)
here = os.path.dirname(os.path.abspath(__file__))
base, head = sys.argv[1], sys.argv[2]
repeats = int(sys.argv[3]) if len(sys.argv) > 3 else 3
print(f"nproc={os.cpu_count()} load1={os.getloadavg()[0]:.2f} python={sys.version.split()[0]}")
runs: dict[tuple[str, int], list[dict]] = {}
for _rep in range(repeats):
    for rows in SIZES:
        for name, src in (("base", base), ("head", head)):
            out = subprocess.run(
                [sys.executable, os.path.join(here, "bench_mutate_warn.py"), str(rows), src],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            runs.setdefault((name, rows), []).append(json.loads(out.strip().splitlines()[-1]))
print("op    rows  | base p50 / p95 | head p50 / p95 | per-repeat p50 base | head")
for rows in SIZES:
    for op in ("node", "edge"):
        cells = {}
        for name in ("base", "head"):
            rs = [r[op] for r in runs[(name, rows)]]
            cells[name] = (
                statistics.median(r["p50"] for r in rs),
                statistics.median(r["p95"] for r in rs),
                [r["p50"] for r in rs],
            )
        b, h = cells["base"], cells["head"]
        print(
            f"{op:5s} {rows:6d} | {b[0]:7.2f} / {b[1]:7.2f} | {h[0]:7.2f} / {h[1]:7.2f}"
            f" | {b[2]} | {h[2]}"
        )
