"""Mutate latency vs session size (in-process, throwaway state dir).

usage: python ops/bench_mutate_warn.py <rows> [<memnet source dir>]

Builds a session of about <rows> rows (nodes + edges, one ``knows`` edge per
node), then times 100 single-node and 100 single-edge inserts through
``run_argv`` (the same path the wire takes, no socket). Prints one JSON line
with p50 and p95 in ms. Run it in a fresh process per size and per repeat; to
compare a base checkout, pass its ``parts/common/memnet`` as the second argument.
"""

from __future__ import annotations

import json
import math
import os
import random
import shutil
import sys
import tempfile
import time

rows = int(sys.argv[1])
if len(sys.argv) > 2:
    sys.path.insert(0, sys.argv[2])
state = tempfile.mkdtemp(prefix="memnet-bench-")
os.environ.update(
    MEMNET_STATE_DIR=state,
    MEMNET_MAX_ROWS="400000",
    MEMNET_MAX_RELATIONS="400000",
    MEMNET_ADMIN_TOKEN="bench-local-not-a-secret",
)
os.environ.pop("MEMNET_TOKEN", None)
import memnet  # noqa: E402
from memnet.in_process_engine import run_argv  # noqa: E402
from memnet.registry import list_entries  # noqa: E402

SCHEMA = "SCHEMA NPC ; fields=id name status"


def pct(xs: list[float], p: float) -> float:
    s = sorted(xs)
    k = (len(s) - 1) * p / 100
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def node(i: int) -> str:
    return f"CREATE (n:NPC {{id:'N{i}', name:'item{i}', status:'active'}})"


def edge(a: int, b: int) -> str:
    ends = f"MATCH (a:NPC {{id:'N{a}'}}), (b:NPC {{id:'N{b}'}})"
    return f"{ends}\nCREATE (a)-[:knows {{note:'e'}}]->(b)"


def run(args: list[str], stdin: str | None = None) -> dict:
    r = run_argv(args, stdin=stdin)
    assert r["exit_code"] == 0, r["stderr"]
    return r


n = rows // 2
sid = run(["session", "open", "--map", SCHEMA, "--ttl", "1440"])["stderr"].split("=")[1].strip()
for s in range(0, n, 500):
    body = "\n".join(node(i) for i in range(s, min(n, s + 500)))
    run(["mutate", "--session", sid, "--stdin"], body)
rnd = random.Random(7)
pairs = {(a, (a + 1 + rnd.randrange(n - 1)) % n) for a in range(n)}
pairs = sorted(pairs)
for s in range(0, len(pairs), 250):
    body = "\n".join(edge(a, b) for a, b in pairs[s : s + 250])
    run(["mutate", "--session", sid, "--stdin"], body)
built = list_entries()[0].store.row_count_non_law()

base = n + 1000
count = [0, 0]


def ins_node() -> None:
    i = base + count[0]
    count[0] += 1
    run(["mutate", "--session", sid, "--stdin"], node(i))


def ins_edge() -> None:
    a = base + count[1]
    count[1] += 1
    run(["mutate", "--session", sid, "--stdin"], edge(a, a + 1))


def timed(fn, reps: int = 100, warm: int = 10) -> dict:
    for _ in range(warm):
        fn()
    out = []
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        out.append((time.perf_counter() - t) * 1000)
    return {"p50": round(pct(out, 50), 3), "p95": round(pct(out, 95), 3)}


res = {"rows": built, "node": timed(ins_node)}
ins_node()  # edge i joins base+i and base+i+1: one more end than nodes timed
res["edge"] = timed(ins_edge)
res["source"] = os.path.dirname(memnet.__file__)
print(json.dumps(res))
shutil.rmtree(state, ignore_errors=True)
