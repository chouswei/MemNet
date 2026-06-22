"""Benchmark novel turn pipeline steps."""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
env = {**dict(__import__("os").environ), "PYTHONPATH": str(ROOT / "src")}


def bench(label: str, fn) -> float:
    t0 = time.perf_counter()
    fn()
    ms = (time.perf_counter() - t0) * 1000
    print(f"{label:45} {ms:7.0f} ms")
    return ms


def main() -> None:
    prose = "測" * 280 + "試" * 25  # ~305 chars

    def prose_inproc():
        from novel_mcp.zh_text import prose_status

        prose_status(prose)

    def append_inproc():
        from novel_mcp.chapter_io import chapter_prose_append

        chapter_prose_append(
            prose,
            chapter_dir="novel-output/wanming_caifa_zhuan/chapters",
            chp_num=6,
            workspace_root=ROOT,
            replace_last_paragraph=True,
        )

    def cli(*args: str):
        subprocess.run(
            [sys.executable, "-m", "memnet.cli", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**env, "MEMNET_TEST_INLINE": "1"},
        )

    def cold_python_prose():
        subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.path.insert(0,'src'); from novel_mcp.zh_text import prose_status; prose_status('x'*300)",
            ],
            capture_output=True,
            cwd=ROOT,
            env=env,
        )

    print("=== In-process (MCP-equivalent) ===")
    bench("prose_metrics", prose_inproc)
    bench("chapter_prose_append", append_inproc)

    print("\n=== Subprocess overhead ===")
    bench("python cold start + prose_metrics", cold_python_prose)
    bench("memnet CLI version", lambda: cli("version"))
    bench("memnet session open (inline)", lambda: cli("session", "open", "--map-file", "src/memnet/examples/schema.novel.example.txt"))

    print("\n=== Simulated bad turn (10x cold prose check) ===")
    t0 = time.perf_counter()
    for _ in range(10):
        cold_python_prose()
    print(f"{'10x cold prose_metrics loop':45} {(time.perf_counter()-t0)*1000:7.0f} ms")


if __name__ == "__main__":
    main()
