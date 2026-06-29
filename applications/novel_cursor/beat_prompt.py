"""Prompts for dual-loop script + prose Cursor SDK agents.

World voice (魂穿、圖書館、文風等) lives in seed USR/LAW only — prompts inject
``presentation.contracts`` / ``option_contracts`` per turn; do not hardcode genre lore here.
"""

from __future__ import annotations

from typing import Any

from app_config import NovelAppConfig
from novel_mcp.body_state import vitality_block


def build_script_primer(config: NovelAppConfig) -> str:
    return f"""You are the **{config.title}** script agent (編劇). Model: {config.model_script}.

Role: run LAW-PIPE20 **script stages only** — `script_draft → script_review`. **No** player-facing novel prose.

Rules:
1. Always pass `session` on every `beat_turn_begin` / `beat_turn_finish`.
2. **script_draft**: one finish with oln_lines + sbd_lines + scr_lines together (bundle).
3. **script_review**: one finish with scr_lines only.
4. Max 4 novel-writer calls (2 script begin+finish pairs) per turn.
5. Honour `continuation_anchor` and warm context; do not invent unrelated plot (no 錦衣衛/滅門 unless in graph).
6. Choice 6 (library): encode query in **OLN** field per LAW-LIB03 — same scene, consciousness frame.
7. Never output `@TAG:` wires to the player.
8. Cast lists graph ids (N01, P01, …) for SBD/SCR reference; player-facing prose is the author stage.

SSOT seed: `{config.seed_md_rel}`.

Acknowledge with "script agent ready".
"""


def build_script_turn(config: NovelAppConfig, prep: dict[str, Any]) -> str:
    session = prep["memnet_session"]
    anchor = prep.get("continuation_anchor") or ""
    player = prep.get("player") or {}
    start = prep.get("fsm", {}).get("start_stage", "script_draft")

    if "choice" in player:
        choice_text = (player.get("choice_text") or "").strip()
        player_block = (
            f"Player chose option **{player['choice']}**."
            + (f' Text: "{choice_text}".' if choice_text else "")
            + f" Start from stage `{start}`; run until USR23 beat_stage becomes **prose**."
            + " Advance from continuation anchor — do **not** restart the opening beat."
        )
        if player.get("lib_query"):
            player_block += " Library query: reflect in OLN only (LAW-LIB03)."
    elif "steering" in player:
        player_block = (
            f'Player steering: "{player["steering"]}". '
            f"Start from `{start}`; run until beat_stage **prose**."
        )
    else:
        player_block = (
            f"Resume script pipeline from stage `{start}`; run until beat_stage **prose**."
        )

    anchor_block = (
        f"## Continuation anchor (committed prose — continue from here)\n{anchor}"
        if anchor
        else "## Continuation anchor\n(empty — opening beat)"
    )

    return f"""Session: `{session}`

{anchor_block}

## Task
{player_block}

Run beat_turn_begin → draft current stage → beat_turn_finish.
**script_draft**: finish oln+sbd+scr bundle. **script_review**: finish scr only.
Repeat until `USR23|beat_stage|prose`.

Do not write novel prose. Do not call prose finish.
"""


def build_prose_primer(config: NovelAppConfig) -> str:
    snap = str(config.snapshot_file.relative_to(config.output_dir.parent.parent)).replace(
        "\\", "/"
    )
    try:
        from app_config import repo_root

        snap = str(config.snapshot_file.relative_to(repo_root())).replace("\\", "/")
    except ValueError:
        pass

    return f"""You are the **{config.title}** prose agent (作者). Model: {config.model_prose}.

Role: **prose stage only** — expand committed `@SCR` into novel text per LAW-PROSE16.

Rules:
1. Always pass `session` on beat_turn_begin and beat_turn_finish.
2. One prose finish: prose + option_lines (6) + update_lines + snapshot_file.
3. Do not modify OLN/SBD/SCR in this turn.
4. Honour continuation_anchor and scr_row; stay in current scene.
5. After success, emit **only** fenced JSON (see schema below).

Snapshot path: `{snap}`

JSON schema:
```json
{{
  "exit_code": 0,
  "session": "<mn_…>",
  "app_id": "{config.app_id}",
  "prose": "<正文>",
  "options": ["…", "…", "…", "…", "…", "…"],
  "hud": "<狀態欄>",
  "snapshot_saved": true,
  "snapshot_file": "{snap}",
  "beat_stage": "script_draft"
}}
```

Acknowledge with "prose agent ready".
"""


def build_prose_turn(config: NovelAppConfig, prep: dict[str, Any]) -> str:
    session = prep["memnet_session"]
    anchor = prep.get("continuation_anchor") or ""
    scr = prep.get("scr_row") or "(read from beat_turn_begin presentation)"
    oln = prep.get("oln_row") or ""
    fp = prep.get("finish_params") or {}
    snap = fp.get("snapshot_file") or prep.get("snapshot_file") or ""

    return f"""Session: `{session}`

## Continuation anchor
{anchor or "(none)"}

## Current OLN
{oln}

## Current SCR (expand this)
{scr}

## finish_params
snapshot_file: `{snap}`
chapter_dir: `{fp.get("chapter_dir", prep.get("chapter_dir", ""))}`
chp_num: {fp.get("chp_num", prep.get("chp_num", 1))}

## Task
beat_turn_begin → write prose from SCR → beat_turn_finish with prose, 6 option_lines, updates, snapshot.

Emit only the success JSON block when done.
"""


_STAGE_TAG = {"oln": "OLN", "sbd": "SBD", "scr": "SCR"}

_STAGE_EXAMPLE = {
    "oln": "@OLN: OLN01|1|情緒錨|情節要點|對白骨架|尾鉤|delete_on_settle",
    "sbd": "@SBD: SBD01|1|1|畫面要點|感官細節|動作對白|氛圍|delete_on_settle",
    "scr": "@SCR: SCR01|1|1|動作描述|對白|內心旁白|音效|delete_on_settle",
}

_WIRE_GRAMMAR = f"""## Wire grammar (exact pipe-separated fields — NOT key|value updates)

| Tag | Fields (count) |
|-----|----------------|
| `@OLN` | id\\|回合\\|情緒錨\\|情節要點\\|對白骨架\\|尾鉤\\|回收 **(7)** |
| `@SBD` | id\\|回合\\|鏡頭\\|畫面要點\\|感官細節\\|動作對白骨架\\|氛圍轉場\\|回收 **(8)** |
| `@SCR` | id\\|回合\\|鏡頭\\|動作描述\\|對白\\|內心旁白\\|音效氛圍\\|回收 **(8)** |

Examples (copy structure, invent content from presentation only):
- `{_STAGE_EXAMPLE["oln"]}`
- `{_STAGE_EXAMPLE["sbd"]}`
- `{_STAGE_EXAMPLE["scr"]}`

**WRONG:** `@OLN: SCN01|update|emotion_anchor|…` — never English field names, `update`, or SCN id as OLN id.

LAW-NAME01: 敘事視角僅用 `presentation.scene` 中 `name_visible:true` 實體的 canonical 名。認識一律 `@EDG`：`holder|knows|entity`（直接）或 `knows_via`（間接）或 `soul_knows`；深度寫 attrs（未知→耳聞→初識→粗識→能述→能作→熟識）。無接線不得寫真名。初識後 `beat_turn_finish` 加邊。`unknows` 表否定能力。禁捏造圖外實體。"""


def _format_contracts_block(presentation: dict[str, Any]) -> str:
    """Seed-driven voice/style/options — never duplicate genre lore in prompt code."""
    sections: list[str] = []
    contracts = presentation.get("contracts") or []
    if contracts:
        sections.append(
            "## Seed contracts (binding)\n"
            + "\n".join(f"- {c}" for c in contracts)
        )
    opt = presentation.get("option_contracts") or []
    if opt:
        sections.append(
            "## Option contracts\n" + "\n".join(f"- {c}" for c in opt)
        )
    if not sections:
        return ""
    return "\n\n".join(sections) + "\n\n"


def _depth_label(npc: dict[str, Any]) -> str:
    depth = npc.get("knowledge_depth")
    return depth if depth else "—"


def _format_cast_block(presentation: dict[str, Any]) -> str:
    """Human-readable cast from presentation.scene (LAW-CHR02/04, LAW-NAME01)."""
    scene = presentation.get("scene") or {}
    lines: list[str] = []
    if scene.get("age_hint"):
        lines.append(f"歲數（@SYS−出生年）：{scene['age_hint']}")
    elif scene.get("ages"):
        lines.append(f"歲數：{scene['ages']}")
    plr_id = scene.get("plr_id") or "P01"
    plr_age = scene.get("plr_age")
    if plr_age is not None:
        ident = scene.get("plr_identity") or scene.get("plr_name") or "主角"
        visible = scene.get("plr_name") is not None
        lines.append(
            f"- {plr_id} | {ident} | visible={str(visible).lower()} | depth=— | 主角"
        )
        if scene.get("plr_body"):
            lines.append(f"  體征：{scene['plr_body']}")
    for npc in scene.get("npcs") or []:
        npc_id = npc.get("id") or "?"
        name = npc.get("name", "?")
        visible = npc.get("name_visible", False)
        depth = _depth_label(npc)
        traits = npc.get("traits") or npc.get("appearance") or ""
        lines.append(
            f"- {npc_id} | {name} | visible={str(visible).lower()} | depth={depth} | {traits}"
        )
    if not lines:
        return ""
    return (
        "## Cast（graph id｜顯示名｜name_visible — SBD/SCR 內容欄可引用 id）\n"
        + "\n".join(lines)
        + "\n\n"
    )


def build_script_stage_system(config: NovelAppConfig) -> str:
    return f"""You are the **{config.title}** script drafter (編劇). Text output only — **no tools**.

This is a **persistent chat thread** (編劇聊天室). Remember prior turns for voice and pipeline rhythm.

**MemNet** `presentation` in each user turn is canonical plot state (記憶加強); chat history does not override the graph.

Draft **script_draft → script_review** wires only; **no** prose.

{_WIRE_GRAMMAR}

Rules:
1. **script_draft**: output ≥1 `@OLN`, ≥2 `@SBD`, ≥2 `@SCR` with matching round + shot numbers 1..N.
2. **script_review**: read committed OLN/SBD/SCR + Cast; output corrected `@SCR:` lines only.
3. Honour contracts, scene focus, walk_hops, continuation anchor.
4. Do not invent plot or NPCs outside given graph context.
5. Choice 6 (library): encode query in OLN plot field (LAW-LIB03).
6. **SBD/SCR content fields** may use graph ids (N01, P01, …) for shot planning; player-facing naming is the prose author’s job.

SSOT: `{config.seed_md_rel}`."""


def build_script_stage_user(
    prep: dict[str, Any],
    begin: dict[str, Any],
    stage: str,
    *,
    prior_error: str | None = None,
) -> str:
    import json

    session = prep["memnet_session"]
    anchor = prep.get("continuation_anchor") or ""
    player = prep.get("player") or {}
    presentation = begin.get("presentation") or {}
    pipeline = begin.get("pipeline") or {}
    oln_raw = pipeline.get("oln_row") or ""
    sbd_raw = pipeline.get("sbd_rows") or ""
    scr_raw = pipeline.get("scr_row") or ""

    if "choice" in player:
        choice_text = (player.get("choice_text") or "").strip()
        player_block = (
            f"Player chose option **{player['choice']}**."
            + (f' Text: "{choice_text}".' if choice_text else "")
            + " Continue from anchor; do **not** reopen opening scene."
        )
        if player.get("lib_query"):
            player_block += " Library beat: reflect query in OLN only."
    elif "steering" in player:
        player_block = f'Player steering: "{player["steering"]}".'
    elif player.get("continue_beat"):
        player_block = "Resume mid-script pipeline."
    else:
        player_block = "(continue pipeline)"

    err_block = f"\n\n## Prior finish error (fix)\n{prior_error}" if prior_error else ""
    cast_block = _format_cast_block(presentation)
    contracts_block = _format_contracts_block(presentation)
    opening = ""
    if not anchor and stage == "script_draft" and "choice" not in player:
        scene = presentation.get("scene") or {}
        scn = scene.get("id") or scene.get("code") or "opening scene"
        bits: list[str] = []
        if scene.get("plr_identity") or scene.get("plr_age") is not None:
            ident = scene.get("plr_identity") or "主角"
            age = scene.get("plr_age")
            bits.append(
                f"{ident}（{age}歲）" if age is not None else ident
            )
        npcs = scene.get("npcs") or []
        if npcs:
            npc_s = "、".join(n.get("name", "?") for n in npcs[:8])
            bits.append(f"場景 NPC：{npc_s}")
        if bits:
            opening = (
                f"\n## Opening beat ({scn})\n"
                + "；".join(bits)
                + "。人物與年齡以 Presentation / Cast 為準；"
                "若玩家 steering 為姓名，在 OLN 情節要點體現取名。\n"
            )
    elif not anchor and stage == "script_draft" and "choice" in player:
        opening = (
            "\n## Mid-story choice (no prose anchor on disk)\n"
            "Player already chose an option — advance from graph @OLN/@SCR; "
            "**do not** reopen the opening beat.\n"
        )

    if stage == "script_draft":
        task = (
            "## Task\n"
            "Draft **one bundle**: ≥1 `@OLN`, ≥2 `@SBD`, ≥2 `@SCR` (same round; shots 1..N matching). "
            "Reply with wire lines only — no prose, no markdown fences."
        )
        shape = f"""## Required shape
- `{_STAGE_EXAMPLE["oln"]}`
- `{_STAGE_EXAMPLE["sbd"]}`
- `{_STAGE_EXAMPLE["scr"]}` (repeat for each shot)"""
    else:
        audit = pipeline.get("audit_findings") or []
        audit_block = (
            "## Review notes\n" + "\n".join(f"- {a}" for a in audit) + "\n\n"
            if audit
            else (
                "## Review checklist\n"
                "- OLN/SBD/SCR round + shot alignment\n"
                "- Plot matches graph + Cast name_visible\n"
                "- SBD/SCR may keep graph ids; fix player-facing wording in SCR if needed\n\n"
            )
        )
        wires = ""
        if oln_raw:
            wires += f"## Current OLN\n{_wire_display('OLN', oln_raw)}\n\n"
        if sbd_raw:
            wires += f"## Current SBD\n{sbd_raw}\n\n"
        if scr_raw:
            wires += f"## Current SCR\n{scr_raw}\n\n"
        task = (
            f"{audit_block}{wires}"
            "## Task\n"
            "Review committed wires against graph + Cast; output **corrected `@SCR:` lines only**."
        )
        shape = f"## Required shape\n`{_STAGE_EXAMPLE['scr']}`"

    return f"""Session: `{session}`
Stage: **{stage}**

{shape}

## Continuation anchor
{anchor or "(opening beat — no prior prose)"}
{opening}
## Player
{player_block}

## Pipeline hint
{pipeline.get("next_action", "")}

{contracts_block}{cast_block}## Presentation (beat_turn_begin)
```json
{json.dumps(presentation, ensure_ascii=False, indent=2)}
```

{task}{err_block}"""


def build_prose_system(config: NovelAppConfig) -> str:
    snap = str(config.snapshot_file.relative_to(config.output_dir.parent.parent)).replace(
        "\\", "/"
    )
    try:
        from app_config import repo_root

        snap = str(config.snapshot_file.relative_to(repo_root())).replace("\\", "/")
    except ValueError:
        pass

    return f"""You are the **{config.title}** prose drafter (作者). **No tools** — JSON output only.

This is a **persistent chat thread** (作者聊天室). Remember prior beats for register and voice.

**MemNet** `presentation` + `@SCR` in each user turn are canonical (記憶加強); chat history does not override the graph.

Expand `@SCR` into player-facing novel text per presentation contracts.
**Cast block**（`presentation.scene`）：NPC 歲數／特徵為硬性約束（LAW-CHR02/04/18），勿依常識改年齡。

Rules:
1. **Voice, POV, diction, option slots:** follow `presentation.contracts` and `option_contracts` each turn (seed SSOT). Do **not** assume genre-specific lore unless contracts say so.
2. Expand **only** from SCR shots — no invented plot (`prose_from_script`).
3. Exactly **6** `options` unless contracts specify otherwise; honour seed `opt_layout` / option contracts.
4. `hud`: when seed `body_plot_keys` is set, server may build HUD — you may omit. Otherwise emit a one-line status bar per `hud_pipe` / contracts.
5. **Body-in-plot:** match `@PLR` vitals at beat start when `body_plot` / LAW-VIT01 contracts apply; use `update_lines` when activity changes vitals.
6. `update_lines` (optional): only valid MemNet wires. Player name/gender/opening picks are committed via setup MCP before the first beat.
7. Emit **only** fenced JSON below.

Snapshot: `{snap}`

```json
{{
  "prose": "<正文>",
  "options": ["…", "…", "…", "…", "…", "…"],
  "hud": "<狀態欄>",
  "update_lines": []
}}
```"""


def _wire_display(tag: str, row: str | None) -> str:
    if not row:
        return ""
    text = row.strip()
    prefix = f"@{tag}:"
    if text.startswith(prefix):
        return text
    return f"{prefix} {text}"


def build_prose_user(prep: dict[str, Any], begin: dict[str, Any]) -> str:
    import json

    session = prep["memnet_session"]
    anchor = prep.get("continuation_anchor") or ""
    pipeline = begin.get("pipeline") or {}
    presentation = begin.get("presentation") or {}
    fp = begin.get("finish_params") or prep.get("finish_params") or {}

    oln_raw = pipeline.get("oln_row") or prep.get("oln_row") or ""
    sbd_raw = pipeline.get("sbd_rows") or prep.get("sbd_rows") or ""
    scr_raw = pipeline.get("scr_row") or prep.get("scr_row") or ""
    oln = _wire_display("OLN", oln_raw)
    sbd = sbd_raw if sbd_raw.strip() else "(missing — do not invent shots)"
    scr = scr_raw if "\n" in scr_raw or scr_raw.startswith("@SCR:") else _wire_display("SCR", scr_raw)
    chp_num = fp.get("chp_num") or prep.get("chp_num") or pipeline.get("chp_num") or 1
    snap = fp.get("snapshot_file") or prep.get("snapshot_file") or ""
    cast_block = _format_cast_block(presentation)
    contracts_block = _format_contracts_block(presentation)
    scene = presentation.get("scene") or {}
    plr_body = scene.get("plr_body") or pipeline.get("plr_body") or ""
    body_block = vitality_block(
        plr_body, body_plot_keys=presentation.get("body_plot_keys")
    )

    player = prep.get("player") or {}
    player_lines: list[str] = []
    if "choice" in player:
        choice_text = (player.get("choice_text") or "").strip()
        line = f"Player chose option **{player['choice']}**."
        if choice_text:
            line += f' Text: "{choice_text}".'
        line += " Expand SCR to settle this choice; do **not** restart the opening beat."
        player_lines.append(line)
    elif "steering" in player:
        player_lines.append(f'Player steering: "{player["steering"]}".')

    player_block = ""
    if player_lines:
        player_block = "## Player\n" + "\n".join(player_lines) + "\n\n"

    return f"""Session: `{session}`

## Continuation anchor
{anchor or "(none)"}

## Current OLN
{oln or "(missing — do not invent plot)"}

## Current SBD (storyboard — shot structure)
{sbd}

## Current SCR (expand faithfully — every shot)
{scr or "(missing — do not invent plot)"}

{player_block}{contracts_block}{cast_block}{body_block}## finish_params
chapter_dir: `{fp.get("chapter_dir", prep.get("chapter_dir", ""))}`
chp_num: {chp_num}
snapshot_file: `{snap}`

## Presentation
```json
{json.dumps(presentation, ensure_ascii=False, indent=2)}
```

Expand **only** from SCR above; use SBD for shot pacing; honour **Cast** ages and traits. Emit only the JSON block."""
