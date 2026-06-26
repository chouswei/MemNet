"""One-off: split novel-shenjia-initial-state Opening seed into Engine / World fences."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "application-notes" / "novel-shenjia-initial-state.md"

ENGINE_HEADINGS = {
    "LAW", "CFG", "STEP", "USR", "GLO",
}

WORLD_HEADINGS = {
    "SYS", "PLR", "BIZ", "NPC", "TSK", "TEC", "PRD", "LOC", "SCN",
    "TRT", "PRS", "PTY", "SKL", "WUX", "ART", "MWU", "ITM", "LIB",
}

ENGINE_EDG_PREFIXES = ("EG", "ES")


def _tag(line: str) -> str | None:
    m = re.match(r"^@(\w+):", line.strip())
    return m.group(1) if m else None


def _edg_id(line: str) -> str | None:
    m = re.match(r"^@EDG:\s*(\S+)", line.strip())
    return m.group(1) if m else None


def _classify(line: str) -> str:
    tag = _tag(line)
    if tag == "EDG":
        eid = _edg_id(line) or ""
        if eid.startswith(ENGINE_EDG_PREFIXES):
            return "engine"
        return "world"
    if tag in ENGINE_HEADINGS:
        return "engine"
    if tag in WORLD_HEADINGS:
        return "world"
    raise ValueError(f"unclassified: {line[:80]}")


def _fence_lines(text: str, heading: str) -> list[str]:
    pattern = rf"## {re.escape(heading)}\s*\n(?:\s*\n)*```text\s*\n(.*?)\n```"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        pattern2 = rf"## {re.escape(heading)}[\s\S]*?```text\s*\n([\s\S]*?)\n```"
        match = re.search(pattern2, text)
    if not match:
        return []
    return [ln for ln in match.group(1).strip().splitlines() if ln.strip()]


def _law_sort_key(s: str) -> tuple:
    m = re.match(r"@LAW:\s*(\S+)", s)
    lid = m.group(1) if m else s
    prefixes = (
        "LAW-G", "LAW-DATA", "LAW06", "LAW-NAME", "LAW-PIPE", "LAW-BAN", "LAW-MCP",
        "LAW-OLN", "LAW-SBD", "LAW-SCR", "LAW-PROSE", "LAW-CHR", "LAW-PERS", "LAW-NPC",
        "LAW-OUT", "LAW-HUD",
    )
    for i, pfx in enumerate(prefixes):
        if lid.startswith(pfx):
            num = re.search(r"(\d+)$", lid)
            return (i, int(num.group(1)) if num else 0, lid)
    return (99, 0, lid)


def _group_engine(lines: list[str]) -> list[str]:
    """Reorder engine block: LAW groups, CFG/STEP, USR sorted, GLO, EDG."""
    laws, cfg, steps, usrs, glos, edgs = [], [], [], [], [], []
    for ln in lines:
        tag = _tag(ln)
        if tag == "LAW":
            laws.append(ln)
        elif tag == "CFG":
            cfg.append(ln)
        elif tag == "STEP":
            steps.append(ln)
        elif tag == "USR":
            usrs.append(ln)
        elif tag == "GLO":
            glos.append(ln)
        elif tag == "EDG":
            edgs.append(ln)
    laws.sort(key=_law_sort_key)
    usrs.sort(key=lambda s: (
        int(m.group(1)) if (m := re.search(r"USR(\d+)", s)) else 999,
        "b" in s,
    ))
    edgs.sort(key=lambda s: _edg_id(s) or s)

    out: list[str] = []

    def add_block(_title: str, block: list[str]) -> None:
        if block:
            if out:
                out.append("")
            out.extend(block)

    add_block("law", laws)
    add_block("cfg", cfg)
    add_block("step", steps)
    add_block("usr", usrs)
    add_block("glo", glos)
    add_block("edg", edgs)
    return out


def _group_world(lines: list[str]) -> list[str]:
    """World order: macro → cast → economy graph → scene → traits → persona → skills → items."""
    buckets: dict[str, list[str]] = {
        "sys": [], "plr": [], "biz": [], "npc": [], "tsk": [], "tec": [], "prd": [], "loc": [],
        "scn": [], "edg_macro": [], "edg_scene": [], "trt": [], "pty": [], "prs": [], "edg_prs": [],
        "skl": [], "edg_skl": [], "itm": [], "edg_itm": [], "edg_trait": [],
    }
    for ln in lines:
        tag = _tag(ln)
        if tag == "SYS":
            buckets["sys"].append(ln)
        elif tag == "PLR":
            buckets["plr"].append(ln)
        elif tag == "BIZ":
            buckets["biz"].append(ln)
        elif tag == "NPC":
            buckets["npc"].append(ln)
        elif tag == "TSK":
            buckets["tsk"].append(ln)
        elif tag == "TEC":
            buckets["tec"].append(ln)
        elif tag == "PRD":
            buckets["prd"].append(ln)
        elif tag == "LOC":
            buckets["loc"].append(ln)
        elif tag == "SCN":
            buckets["scn"].append(ln)
        elif tag == "TRT":
            buckets["trt"].append(ln)
        elif tag == "PTY":
            buckets["pty"].append(ln)
        elif tag == "PRS":
            buckets["prs"].append(ln)
        elif tag == "SKL":
            buckets["skl"].append(ln)
        elif tag == "ITM":
            buckets["itm"].append(ln)
        elif tag == "EDG":
            eid = _edg_id(ln) or ""
            if eid.startswith("E2") or eid == "ES01":
                buckets["edg_scene"].append(ln)
            elif eid.startswith("EP"):
                buckets["edg_prs"].append(ln)
            elif eid.startswith("EK"):
                buckets["edg_skl"].append(ln)
            elif eid.startswith("EI"):
                buckets["edg_itm"].append(ln)
            elif eid.startswith("E3"):
                buckets["edg_trait"].append(ln)
            else:
                buckets["edg_macro"].append(ln)
        else:
            raise ValueError(ln)
    order = [
        "sys", "plr", "biz", "npc", "tsk", "tec", "prd", "loc",
        "edg_macro", "scn", "edg_scene", "trt", "edg_trait",
        "pty", "prs", "edg_prs", "skl", "edg_skl", "itm", "edg_itm",
    ]
    out: list[str] = []
    for key in order:
        if buckets[key]:
            if out:
                out.append("")
            out.extend(sorted(buckets[key], key=lambda s: _edg_id(s) or s))
    return out


def main() -> None:
    text = MD.read_text(encoding="utf-8")
    raw = _fence_lines(text, "Opening seed")
    if not raw:
        raw = _fence_lines(text, "Opening seed — Engine") + _fence_lines(
            text, "Opening seed — World"
        )
    engine_raw, world_raw = [], []
    for ln in raw:
        if ln.startswith("@USR: USR23|beat_stage|"):
            ln = "@USR: USR23|beat_stage|oln|persistent"
        if _classify(ln) == "engine":
            engine_raw.append(ln)
        else:
            world_raw.append(ln)

    engine = _group_engine(engine_raw)
    world = _group_world(world_raw)
    if not engine:
        raise SystemExit("engine seed block is empty")
    if not world:
        raise SystemExit("world seed block is empty — refusing to overwrite SSOT")

    layout = """## Seed layout

| 區塊 | 維護時機 | 內容 |
|------|----------|------|
| **Opening seed — Engine** | 改管線／語風／介面／LAW 時 | `@LAW` `@CFG` `@STEP` `@USR` `@GLO`；`EG*`／`ES*` 接線 |
| **Opening seed — World** | 改開局劇情／人物／產業／科技樹時 | `@SYS`～`@PTY` 實體；劇情 `@EDG`（`E*` `EP*` `EK*` `EI*`） |

`scripts/shenjia_bootstrap.py` 依序合併兩段 fence → `session_open` + `add`。

## Opening seed — Engine

```text
"""

    engine_fence = "\n".join(engine) + "\n```\n\n## Opening seed — World\n\n```text\n"
    world_fence = "\n".join(world) + "\n```\n"

    # replace from ## Opening seed OR ## Seed layout through first closing ``` after world
    pat = r"## (?:Seed layout|Opening seed)[\s\S]*?```\n\n\*\*Note:\*\*"
    new_mid = layout + engine_fence + world_fence + "\n**Note:**"
    if not re.search(pat, text):
        raise SystemExit("could not find seed block to replace")
    new_text = re.sub(pat, new_mid, text, count=1)
    MD.write_text(new_text, encoding="utf-8")
    print(f"engine_lines={len(engine)} world_lines={len(world)} total={len(engine)+len(world)}")


if __name__ == "__main__":
    main()
