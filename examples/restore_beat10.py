"""Restore novel session to beat-10 state and persist choice 3."""
from __future__ import annotations

import re
from pathlib import Path

from memnet.serve import send_command

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "src/memnet/examples/schema.novel.example.txt"
SEED = ROOT / "src/memnet/examples/workflow.novel.example.txt"
CH2 = ROOT / "novel-output/shenjia_caifa/chapters/第002回.md"


def cjk_count(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def main() -> None:
    map_lines = [ln for ln in MAP.read_text(encoding="utf-8").splitlines() if ln.strip()]
    seed_lines = [ln for ln in SEED.read_text(encoding="utf-8-sig").splitlines() if ln.strip()]

    r = send_command(["session", "open", "--map-file", str(MAP)])
    if r["exit_code"] != 0:
        raise SystemExit(r["stderr"])
    sid = None
    for line in r["stderr"].splitlines():
        if line.startswith("MEMNET_SESSION="):
            sid = line.split("=", 1)[1]
    if not sid:
        raise SystemExit("no session id")

    for line in seed_lines:
        rr = send_command(
            ["add", "--stdin", "--allow-new-relation", "--session", sid],
            stdin=line,
        )
        if rr["exit_code"] != 0 and "duplicate" not in rr["stderr"].lower():
            print("seed warn", line[:40], rr["stderr"])

    updates = [
        "@USR: USR04|pc_name|北見肖|persistent",
        "@CHR: CHR01|北見肖|protagonist|y1596|male|ragged_thin|dazed_polite|curious_cautious|isekai_mee_eng jinyong_reader soul_library_gift yijin_t0|Wit:5 Courage:2 Luck:3|neigong:0 jianfa:0 qinggong:0 duanzao:0 soul_library:0|weak_sore|persistent",
        "@LIB: LIB23|SK01|yijin_jing|0|in_progress|persistent",
        "@QUEST: QST01|smithy_job|1|accept_work_offer|half_food_share|completed|persistent",
        "@QUEST: QST03|gather_fuel|1|kiln_firing|door_patch|active|persistent",
        "@TEC: TEC01|CHR01|LIB01|charcoal_kiln|firing|persistent",
        "@PRD: PRD04|IND01|charcoal_sale|goods|0|0|in_progress|persistent",
        "@VIT: VIT01|CHR01|qi_blood|6|10|persistent",
        "@TIME: TIME01|10|calm|medium|required|persistent",
        "@CHP: CHP01|1|1|8|2400|closed|persistent",
        "@STEP: STEP01|2|SCN01|persistent",
    ]
    for line in updates:
        cmd = "add" if line.startswith("@TEC:") or line.startswith("@PRD:") else "update"
        rr = send_command([cmd, "--stdin", "--allow-new-relation", "--session", sid], stdin=line)
        print(cmd, line.split("|")[0], rr["exit_code"], rr.get("stderr", "")[:80])

    body = CH2.read_text(encoding="utf-8").split("# 第二回\n\n", 1)[1]
    total = cjk_count(body)
    paras = body.strip().split("\n\n")
    beat10 = cjk_count(paras[-1])
    print("beat10", beat10, "chp2_total", total)

    rr = send_command(
        ["update", "--stdin", "--session", sid],
        stdin=f"@CHP: CHP02|2|9|0|{total}|open|persistent",
    )
    print("CHP02", rr["exit_code"])

    rr = send_command(
        ["add", "--stdin", "--allow-new-relation", "--session", sid],
        stdin="@CHOICE: CHO09|SCN01|3|delete_on_settle",
    )
    print("CHO09", rr["exit_code"])

    print("SESSION", sid)


if __name__ == "__main__":
    main()
