"""Run N beats and report failures (smoke / regression)."""
from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "applications" / "novel_cursor"))

from env_load import load_dotenv  # noqa: E402

load_dotenv()

from app_config import load_config  # noqa: E402
from play_service import (  # noqa: E402
    preflight_session,
    probe_serve,
    read_session_id,
    run_beat,
    write_last_beat,
)
from novel_mcp.player_setup import read_player_setup  # noqa: E402


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    app = sys.argv[2] if len(sys.argv) > 2 else "shenjia_caifa"
    config = load_config(app_id=app)
    if not probe_serve():
        print("FAIL: memnet serve unreachable", file=sys.stderr)
        return 1
    session = read_session_id(config)
    session, pf = preflight_session(config, session)
    if pf != 0:
        print(f"FAIL: preflight {pf}", file=sys.stderr)
        return pf
    setup = read_player_setup(session)
    if not setup.get("setup_complete"):
        print(
            f"FAIL: setup incomplete next={setup.get('setup_guidance', {}).get('next_action')}",
            file=sys.stderr,
        )
        return 2

    rng = random.Random(42)
    results: list[dict] = []
    failures = 0
    t0 = time.perf_counter()
    for i in range(1, n + 1):
        choice = rng.randint(1, 6)
        beat_t0 = time.perf_counter()
        result, code = run_beat(config, session, choice=choice)
        elapsed = time.perf_counter() - beat_t0
        entry = {
            "beat": i,
            "choice": choice,
            "code": code,
            "exit_code": result.get("exit_code") if result else None,
            "error": result.get("error") if result else "no result",
            "prose_len": len((result or {}).get("prose") or ""),
            "options": (result or {}).get("options"),
            "elapsed_s": round(elapsed, 1),
        }
        results.append(entry)
        ok = code == 0 and result and int(result.get("exit_code", 1)) == 0
        if not ok:
            failures += 1
            print(f"BEAT {i} FAIL code={code} {entry['error']}", file=sys.stderr)
        else:
            write_last_beat(config, result)
            print(
                f"BEAT {i} ok choice={choice} prose={entry['prose_len']}s "
                f"time={entry['elapsed_s']}s",
                file=sys.stderr,
            )

    summary = {
        "session": session,
        "beats": n,
        "failures": failures,
        "total_s": round(time.perf_counter() - t0, 1),
        "results": results,
    }
    out = config.output_dir / "beats_smoke_last.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"failures": failures, "beats": n, "session": session, "log": str(out)}))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
