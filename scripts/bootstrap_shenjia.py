"""Bootstrap 沈家鐵坊傳 session from application-notes/novel-shenjia-initial-state.md."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from memnet.registry import get
from memnet.session import open_session
from memnet.snapshot import write_snapshot
from memnet.tag_map import parse_line
from memnet_mcp.seed import supplement_seed_lines

SSOT = ROOT / "application-notes" / "novel-shenjia-initial-state.md"
OUT_DIR = ROOT / "novel-output" / "shenjia_caifa"
SNAP_PATH = OUT_DIR / "session_snap.json"


def _section(text: str, heading: str) -> str:
    marker = f"## {heading}"
    if marker not in text:
        raise SystemExit(f"missing {marker} in {SSOT}")
    body = text.split(marker, 1)[1]
    for stop in ("## ", "\n---"):
        idx = body.find(stop)
        if idx != -1:
            body = body[:idx]
    m = re.search(r"```text\n(.*?)```", body, re.DOTALL)
    if not m:
        raise SystemExit(f"no ```text fence under {heading}")
    return m.group(1)


def _lines(block: str) -> list[str]:
    return [ln.strip() for ln in block.splitlines() if ln.strip() and not ln.strip().startswith("#")]


def main() -> None:
    text = SSOT.read_text(encoding="utf-8")
    map_lines = _lines(_section(text, "Tag map"))
    rel_lines = _lines(_section(text, "Relations"))
    seed_lines = supplement_seed_lines(_lines(_section(text, "Opening seed")))

    relations = set()
    for ln in rel_lines:
        if ln.startswith("@REL:"):
            relations.add(ln.split(":", 1)[1].strip())
        else:
            relations.add(ln)

    ss = open_session(map_lines=map_lines)
    entry = get(ss.session_id)
    if entry is None:
        raise SystemExit("session open failed")
    entry.relations = relations

    with ss.lock(exclusive=True):
        for raw in seed_lines:
            rec = parse_line(raw, ss.tag_map)
            rel = set()
            if rec.tag == "EDG":
                rel = {rec.fields.get("relation", "")}
            ss.store.add_row(
                rec,
                allow_new_relation=True,
                relations=entry.relations,
            )
        ss.mark_written()
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        rows = write_snapshot(ss, SNAP_PATH)

    chapters = OUT_DIR / "chapters"
    chapters.mkdir(parents=True, exist_ok=True)
    for md in chapters.glob("第*.md"):
        md.unlink()

    print(f"session_id={ss.session_id}")
    print(f"rows={rows}")
    print(f"snap={SNAP_PATH}")


if __name__ == "__main__":
    main()
