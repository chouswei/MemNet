"""MemNet efficiency benchmarks — in-process engine + CLI subprocess."""

from __future__ import annotations

import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

os.environ.setdefault("MEMNET_TEST_INLINE", "1")

from memnet.config import examples_dir  # noqa: E402
from memnet.mem_store import MemStore  # noqa: E402
from memnet.session import get_session, open_session, purge_expired, reset_registry  # noqa: E402
from memnet.tag_map import load_map_from_file, parse_line  # noqa: E402
from memnet.wire import emit_record_line  # noqa: E402


def ms(fn, n: int = 1) -> list[float]:
    times: list[float] = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    return times


def stat(label: str, times: list[float]) -> str:
    if len(times) == 1:
        return f"{label:40} {times[0]:8.2f} ms"
    return (
        f"{label:40} "
        f"med {statistics.median(times):7.2f} ms  "
        f"p95 {sorted(times)[int(len(times) * 0.95) - 1]:7.2f} ms  "
        f"(n={len(times)})"
    )


def build_store(n_nodes: int, n_edges: int) -> tuple[MemStore, list[str]]:
    schema = load_map_from_file(str(examples_dir() / "schema.example.txt"))
    store = MemStore(schema)
    relations = {"links"}
    lines: list[str] = []
    for i in range(n_nodes):
        line = emit_record_line(
            "NPC",
            [f"N{i:04d}", f"name{i}", "t", "0", "c", "0", "active", "persistent"],
        )
        lines.append(line)
        store.upsert(parse_line(line, schema), relations=relations)
    for i in range(n_edges):
        src = f"N{i % n_nodes:04d}"
        dst = f"N{(i + 1) % n_nodes:04d}"
        line = emit_record_line("EDG", [f"E{i:04d}", src, "links", dst, "", "persistent"])
        lines.append(line)
        store.upsert(parse_line(line, schema), relations=relations)
    return store, lines


def bench_in_process() -> list[str]:
    rows = []
    schema = load_map_from_file(str(examples_dir() / "schema.example.txt"))

    rows.append(stat("parse_line (single)", ms(lambda: parse_line("@PLR: PLR01|a|1|0|0|0|x", schema), 5000)))

    store, batch_lines = build_store(500, 800)
    t0 = time.perf_counter()
    build_store(500, 800)
    rows.append(f"{'build_store 500+800':40} {(time.perf_counter() - t0) * 1000:8.2f} ms")

    rows.append(
        stat(
            "context_pack warm (500+800)",
            ms(lambda: store.context_pack(anchor_id="N0000", depth=2, max_rows=50, active_only=True), 200),
        )
    )
    rows.append(
        stat(
            "neighbors depth=2 hub",
            ms(lambda: store.neighbors("N0000", depth=2), 200),
        )
    )
    rows.append(
        stat(
            "list_records tag+where exact (500+800)",
            ms(lambda: store.list_records("NPC", where=[("status", "active")]), 200),
        )
    )
    rows.append(
        stat(
            "list_records tag+where glob (500+800)",
            ms(lambda: store.list_records("NPC", where=[("name", "*name1*")]), 200),
        )
    )
    rows.append(
        stat(
            "list_records 2x where AND (500+800)",
            ms(
                lambda: store.list_records(
                    "NPC",
                    where=[("status", "active"), ("recycle", "persistent")],
                ),
                200,
            ),
        )
    )

    reset_registry()
    purge_expired()
    ss = open_session(map_file=str(examples_dir() / "schema.example.txt"))
    for line in batch_lines[:200]:
        ss.store.upsert(parse_line(line, schema), relations=ss.relations)
    sid = ss.session_id

    rows.append(stat("session get 200 rows (RAM)", ms(lambda: get_session(sid), 200)))

    return rows


def run_cli(args: list[str], *, input_text: str | None = None) -> tuple[float, int]:
    env = os.environ.copy()
    env["MEMNET_TEST_INLINE"] = "1"
    t0 = time.perf_counter()
    r = subprocess.run(
        [sys.executable, "-m", "memnet", *args],
        capture_output=True,
        text=True,
        input=input_text,
        env=env,
        cwd=str(ROOT),
    )
    elapsed = (time.perf_counter() - t0) * 1000
    return elapsed, r.returncode


def bench_cli() -> list[str]:
    rows = []
    reset_registry()
    purge_expired()
    schema = str(examples_dir() / "schema.example.txt")
    workflow = str(examples_dir() / "workflow.example.txt")

    times: list[float] = []
    for _ in range(10):
        elapsed, code = run_cli(["session", "open", "--map-file", schema])
        assert code == 0
        times.append(elapsed)
    rows.append(stat("CLI session open (subprocess)", times))

    r = subprocess.run(
        [sys.executable, "-m", "memnet", "session", "open", "--map-file", schema],
        capture_output=True,
        text=True,
        env={**os.environ, "MEMNET_TEST_INLINE": "1"},
        cwd=str(ROOT),
    )
    sid = r.stdout.strip().split("\n")[0].split("|")[0].replace("@SESSION: ", "")

    elapsed, code = run_cli(["add", "--file", workflow, "--session", sid])
    rows.append(f"{'CLI add --file workflow (15 lines)':40} {elapsed:8.2f} ms  exit={code}")

    rows.append(
        stat(
            "CLI query warm --anchor PLR01",
            [run_cli(["query", "warm", "--anchor", "PLR01", "--session", sid])[0] for _ in range(20)],
        )
    )

    rows.append(
        stat(
            "CLI read list --where status=active",
            [
                run_cli(
                    ["read", "list", "--tag", "NPC", "--where", "status=active", "--session", sid],
                )[0]
                for _ in range(20)
            ],
        )
    )

    loop_times = []
    for _ in range(10):
        t0 = time.perf_counter()
        run_cli(["update", "@SYS: SYS01|1|Day|0|0|0|1:1", "--session", sid])
        run_cli(["query", "warm", "--anchor", "PLR01", "--session", sid])
        loop_times.append((time.perf_counter() - t0) * 1000)
    rows.append(stat("CLI goldfish loop (1 update + warm)", loop_times))

    return rows


def main() -> None:
    print("MemNet efficiency benchmark")
    print("=" * 72)
    print("\n[in-process engine — pure RAM]")
    for line in bench_in_process():
        print(line)
    print("\n[CLI subprocess — MEMNET_TEST_INLINE=1]")
    for line in bench_cli():
        print(line)
    print("\n" + "=" * 72)
    print("Notes:")
    print("- Graph engine is in-memory; session get is registry lookup + TTL check.")
    print("- Production CLI uses memnet serve; subprocess times include Python startup.")
    print("- Run memnet serve for multi-terminal workflows without MEMNET_TEST_INLINE.")


if __name__ == "__main__":
    main()
