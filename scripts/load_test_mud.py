"""Small concurrent load test — MUD-style warm + update on a shared world session.

Simulates N players hammering one MemNet session (same lock as memnet serve).
Use --serve to hit a real TCP server instead of in-process threads.

Examples:
  python scripts/load_test_mud.py
  python scripts/load_test_mud.py --rooms 5000 --players 50 --workers 50 --seconds 15
  python scripts/load_test_mud.py --serve --workers 20 --seconds 10
"""

from __future__ import annotations

import argparse
import os
import random
import statistics
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

MUD_MAP = """\
@ROM: id|key|zone|flags|recycle
@CHR: id|name|role|attr|status|recycle
@OBJ: id|name|kind|state|recycle
@STEP: id|n|focus|recycle
"""

LAW_LINES = [
    "@LAW: LAW01|EDG|on_context|hide|settled_edg_unless_anchor",
    "@LAW: LAW02|*|on_add|unique|one_id_add_then_update",
    "@LAW: LAW-ATOM01|*|on_add|no_sentences|break_to_nodes_edges",
    "@LAW: LAW-MUD01|ROM|on_turn|anchor|warm_anchor_rom_or_plr",
]


@dataclass
class OpResult:
    ok: bool
    latency_ms: float
    op: str


@dataclass
class LoadStats:
    results: list[OpResult] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def add(self, result: OpResult) -> None:
        with self.lock:
            self.results.append(result)


def build_world(ss, *, rooms: int, players: int) -> tuple[list[str], list[str]]:
    """Seed grid world: ROM chain + PLR located + sparse OBJ. Returns (room_ids, plr_ids)."""
    from memnet.tag_map import parse_line

    schema = ss.tag_map
    relations = ss.relations
    relations.update({"exit", "located", "contains", "focus"})

    for line in LAW_LINES:
        ss.store.upsert(parse_line(line, schema), relations=relations)
    ss.store.upsert(
        parse_line("@STEP: STEP01|1|ROM0000|persistent", schema),
        relations=relations,
    )

    room_ids = [f"ROM{i:04d}" for i in range(rooms)]
    for i, rid in enumerate(room_ids):
        zone = f"z{i // 100:02d}"
        ss.store.upsert(
            parse_line(f"@ROM: {rid}|room|{zone}|lit|persistent", schema),
            relations=relations,
        )
        if i + 1 < rooms:
            ss.store.upsert(
                parse_line(
                    f"@EDG: E{i:05d}|{rid}|exit|{room_ids[i + 1]}||persistent", schema
                ),
                relations=relations,
            )
        if i % 7 == 0:
            ss.store.upsert(
                parse_line(f"@OBJ: O{i:05d}|bottle|item|idle|persistent", schema),
                relations=relations,
            )
            ss.store.upsert(
                parse_line(f"@EDG: Eo{i:05d}|{rid}|contains|O{i:05d}||persistent", schema),
                relations=relations,
            )

    plr_ids = [f"PLR{i:02d}" for i in range(players)]
    for i, pid in enumerate(plr_ids):
        rom = room_ids[i % rooms]
        ss.store.upsert(
            parse_line(f"@CHR: {pid}|player{i}|plr|Cur:2|idle|persistent", schema),
            relations=relations,
        )
        ss.store.upsert(
            parse_line(f"@EDG: Ep{i:03d}|{pid}|located|{rom}||persistent", schema),
            relations=relations,
        )
        ss.store.upsert(
            parse_line(f"@EDG: Es{i:03d}|STEP01|focus|{rom}||persistent", schema),
            relations=relations,
        )

    ss.mark_written()
    return room_ids, plr_ids


def player_rom(ss, plr_id: str) -> str:
    for edge in ss.store._edges_from(plr_id):
        if edge.fields.get("relation") == "located":
            return edge.fields.get("dist", "ROM0000")
    return "ROM0000"


def op_warm_inprocess(ss, anchor: str) -> OpResult:
    from memnet.config import DEFAULT_QUERY_MAX_ROWS

    t0 = time.perf_counter()
    try:
        with ss.lock(exclusive=False):
            ss.store.context_pack(
                anchor_id=anchor,
                depth=2,
                max_rows=DEFAULT_QUERY_MAX_ROWS,
                active_only=True,
            )
        ms = (time.perf_counter() - t0) * 1000
        return OpResult(True, ms, "warm")
    except Exception:
        return OpResult(False, (time.perf_counter() - t0) * 1000, "warm")


def op_update_inprocess(ss, plr_id: str, tick: int) -> OpResult:
    from memnet.tag_map import parse_line

    status = "idle" if tick % 2 == 0 else "busy"
    t0 = time.perf_counter()
    try:
        with ss.lock(exclusive=True):
            rec = ss.store.get(plr_id)
            if rec is None:
                return OpResult(False, (time.perf_counter() - t0) * 1000, "update")
            fields = dict(rec.fields)
            fields["status"] = status
            updated = parse_line(
                f"@CHR: {plr_id}|{fields.get('name', 'x')}|{fields.get('role', 'plr')}|"
                f"{fields.get('attr', 'Cur:2')}|{status}|persistent",
                ss.tag_map,
            )
            ss.store.replace_row(updated, relations=ss.relations)
            ss.mark_written()
        ms = (time.perf_counter() - t0) * 1000
        return OpResult(True, ms, "update")
    except Exception:
        return OpResult(False, (time.perf_counter() - t0) * 1000, "update")


def op_warm_serve(session_id: str, anchor: str) -> OpResult:
    from memnet.serve import send_command

    t0 = time.perf_counter()
    try:
        resp = send_command(["query", "warm", "--anchor", anchor, "--depth", "2", "--session", session_id])
        ok = resp.get("exit_code") == 0
        return OpResult(ok, (time.perf_counter() - t0) * 1000, "warm")
    except Exception:
        return OpResult(False, (time.perf_counter() - t0) * 1000, "warm")


def op_update_serve(session_id: str, plr_id: str, tick: int) -> OpResult:
    from memnet.serve import send_command

    status = "idle" if tick % 2 == 0 else "busy"
    line = f"@CHR: {plr_id}|player|plr|Cur:2|{status}|persistent"
    t0 = time.perf_counter()
    try:
        resp = send_command(["update", line, "--session", session_id])
        ok = resp.get("exit_code") == 0
        return OpResult(ok, (time.perf_counter() - t0) * 1000, "update")
    except Exception:
        return OpResult(False, (time.perf_counter() - t0) * 1000, "update")


def worker_inprocess(
    ss,
    plr_ids: list[str],
    stats: LoadStats,
    stop_at: float,
    update_ratio: float,
    think_ms: float,
    rng: random.Random,
) -> None:
    tick = 0
    while time.perf_counter() < stop_at:
        pid = rng.choice(plr_ids)
        rom = player_rom(ss, pid)
        stats.add(op_warm_inprocess(ss, rom))
        if rng.random() < update_ratio:
            stats.add(op_update_inprocess(ss, pid, tick))
        tick += 1
        if think_ms > 0:
            time.sleep(think_ms / 1000.0)


def worker_serve(
    session_id: str,
    plr_ids: list[str],
    stats: LoadStats,
    stop_at: float,
    update_ratio: float,
    rng: random.Random,
) -> None:
    tick = 0
    while time.perf_counter() < stop_at:
        pid = rng.choice(plr_ids)
        rom = f"ROM{rng.randint(0, 9999):04d}"  # serve path: approximate anchor
        stats.add(op_warm_serve(session_id, rom))
        if rng.random() < update_ratio:
            stats.add(op_update_serve(session_id, pid, tick))
        tick += 1


def summarize(stats: LoadStats, elapsed_s: float, rows: int, label: str, *, update_ratio: float) -> None:
    ok = [r for r in stats.results if r.ok]
    fail = [r for r in stats.results if not r.ok]
    by_op: dict[str, list[float]] = {}
    fail_by_op: dict[str, int] = {}
    for r in ok:
        by_op.setdefault(r.op, []).append(r.latency_ms)
    for r in fail:
        fail_by_op[r.op] = fail_by_op.get(r.op, 0) + 1
    all_lat = [r.latency_ms for r in ok]

    print(f"\n=== {label} ===")
    print(f"World rows (non-LAW): {rows}")
    print(f"Duration:             {elapsed_s:.2f} s")
    print(f"Total ops:            {len(stats.results)}  (failed: {len(fail)})")
    if fail_by_op:
        print(f"  failures by op:       {fail_by_op}")
    if elapsed_s > 0:
        print(f"Throughput:           {len(ok) / elapsed_s:.1f} ops/s")
    if all_lat:
        s = sorted(all_lat)
        p95_i = max(0, int(len(s) * 0.95) - 1)
        print(
            f"Latency (all ok):     med {statistics.median(s):.2f} ms  "
            f"p95 {s[p95_i]:.2f} ms  max {s[-1]:.2f} ms"
        )
    for op, latencies in sorted(by_op.items()):
        s = sorted(latencies)
        p95_i = max(0, int(len(s) * 0.95) - 1)
        print(
            f"  {op:8} n={len(s):5}  med {statistics.median(s):.2f} ms  "
            f"p95 {s[p95_i]:.2f} ms"
        )
    if ok and elapsed_s > 0:
        ops_per_cmd = 1.0 + update_ratio
        cmd_per_s = (len(ok) / elapsed_s) / ops_per_cmd
        for interval, label in ((0.2, "active"), (3.0, "casual"), (10.0, "slow")):
            est = cmd_per_s / (1.0 / interval)
            print(f"Capacity hint ({label} {interval}s/cmd): ~{est:.0f} players")


def seed_via_cli(session_id: str, rooms: int, players: int) -> None:
    """Not used for serve mode in small test — in-process seed is faster."""
    del session_id, rooms, players


def run_inprocess(args: argparse.Namespace) -> None:
    os.environ["MEMNET_TEST_INLINE"] = "1"
    from memnet.config import Caps
    from memnet.session import SessionStore, open_session, purge_expired, reset_registry

    reset_registry()
    purge_expired()
    caps = Caps()
    needed = args.rooms * 2 + (args.rooms // 7 + 1) * 2 + args.players * 3 + 200
    if needed > caps.max_rows:
        caps.max_rows = int(needed * 1.1) + 500

    map_lines = [ln.strip() for ln in MUD_MAP.strip().splitlines() if ln.strip()]
    base = open_session(map_lines=map_lines)
    base.caps = caps
    base.store.caps = caps
    ss = SessionStore(base.session_id, caps)

    t_seed = time.perf_counter()
    _, plr_ids = build_world(ss, rooms=args.rooms, players=args.players)
    seed_s = time.perf_counter() - t_seed
    rows = ss.store.row_count_non_law()
    print(f"Seeded session {ss.session_id}: {rows} rows in {seed_s:.2f} s")

    stats = LoadStats()
    stop_at = time.perf_counter() + args.seconds
    threads = []
    for w in range(args.workers):
        rng = random.Random(args.seed + w)
        t = threading.Thread(
            target=worker_inprocess,
            args=(ss, plr_ids, stats, stop_at, args.update_ratio, args.think_ms, rng),
            daemon=True,
        )
        threads.append(t)
        t.start()

    t0 = time.perf_counter()
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - t0
    summarize(stats, elapsed, rows, "in-process (shared session lock)", update_ratio=args.update_ratio)


def run_serve(args: argparse.Namespace) -> None:
    from memnet.config import serve_host, serve_port
    from memnet.serve import probe, send_command

    if not probe():
        print("Starting memnet serve...", flush=True)
        env = os.environ.copy()
        subprocess.Popen(
            [sys.executable, "-m", "memnet", "serve"],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(50):
            if probe():
                break
            time.sleep(0.1)
        else:
            sys.exit("memnet serve did not start")

    map_payload = MUD_MAP.replace("\n", "\\n")
    resp = send_command(["session", "open", "--map", map_payload])
    if resp.get("exit_code") != 0:
        print(resp.get("stderr", ""), resp.get("stdout", ""))
        sys.exit("session open failed")
    sid = resp["stdout"].strip().split("\n")[0].split("|")[0].replace("@SESSION: ", "")
    print(f"Serve session {sid} on {serve_host()}:{serve_port()}")
    print("(Serve mode uses random ROM anchors — seed world via in-process first for full fidelity)")

    plr_ids = [f"PLR{i:02d}" for i in range(args.players)]
    stats = LoadStats()
    stop_at = time.perf_counter() + args.seconds
    threads = []
    for w in range(args.workers):
        rng = random.Random(args.seed + w)
        t = threading.Thread(
            target=worker_serve,
            args=(sid, plr_ids, stats, stop_at, args.update_ratio, rng),
            daemon=True,
        )
        threads.append(t)
        t.start()

    t0 = time.perf_counter()
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - t0
    summarize(stats, elapsed, 0, "memnet serve (TCP)", update_ratio=args.update_ratio)


def main() -> None:
    p = argparse.ArgumentParser(description="Small MUD-style MemNet load test")
    p.add_argument("--rooms", type=int, default=1000, help="ROM nodes in chain (default 1000)")
    p.add_argument("--players", type=int, default=20, help="PLR CHR rows (default 20)")
    p.add_argument("--workers", type=int, default=20, help="concurrent client threads")
    p.add_argument("--seconds", type=float, default=10.0, help="test duration")
    p.add_argument("--update-ratio", type=float, default=0.3, help="fraction of loops that also update")
    p.add_argument("--think-ms", type=float, default=0.0, help="pause between each player loop (ms)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--serve", action="store_true", help="use TCP memnet serve instead of in-process")
    args = p.parse_args()

    print("MemNet MUD load test (small)")
    print(
        f"rooms={args.rooms} players={args.players} workers={args.workers} "
        f"seconds={args.seconds} update_ratio={args.update_ratio} think_ms={args.think_ms}"
    )

    if args.serve:
        run_serve(args)
    else:
        run_inprocess(args)


if __name__ == "__main__":
    main()
