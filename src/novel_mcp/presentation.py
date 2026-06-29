"""Seed-driven presentation compiler (novel-agnostic)."""

from __future__ import annotations

from typing import Any

from novel_mcp.character_gender import (
    PLR_IDX_BODY,
    PLR_IDX_GENDER,
    normalise_npc_parts,
    normalise_plr_parts,
    npc_presentation_entry,
    plr_gender,
)
from novel_mcp.entity_knowledge import (
    build_knowledge_view,
    format_knowledge_hud,
    knowledge_meta,
    merge_knowledge_index,
    resolve_biz_display,
    resolve_npc_display_name,
)
from novel_mcp.body_state import hud_keys_from_body_plot
from novel_mcp.library_contracts import compile_library_contracts
from novel_mcp.warm_index import WarmIndex, index_warm, laws_for_stage, usr_value
from novel_mcp.warm_walk import curated_walk_lines

_TOKEN_GLOSS: dict[str, str] = {
    "ban_telegraphic": "no telegraphic / outline style",
    "no_action_chain": "no verb chains",
    "full_sentence": "complete readable sentences",
    "opt_readable_baihua": "readable vernacular options",
    "length_advisory": "length advisory only",
    "no_hard_gate": "no hard length gate",
    "cite_usr51": "see prose_warm USR",
    "prose_embed": "embed body state in prose",
    "oln_embed": "embed constraints in OLN",
    "opt_respect": "options must respect body state",
    "vit03_suspend": "unconscious: suspend player options",
    "no_permadeath": "no permadeath",
    "inner_voice_modern": "「我」僅限內心獨白／自言自語；旁白禁句句「我」起首",
    "sentence_rhythm": "句式起首多樣；禁連續三句同主語（尤其「我」「你」）起首",
    "prose_from_script": "expand SCR shots only; no invented plot",
    "readable_prose": "complete sentences; not outline bullets",
}

_USR_LABELS: dict[str, str] = {
    "prose_warm": "Narrative voice",
    "narration": "Narration POV",
    "prose_style": "Prose register",
    "inner_voice": "Inner voice",
    "option_style": "Option wording",
    "opt_copy": "Option copy rules",
    "opt_layout": "Option slot layout",
    "lib_opt_copy": "Library slot (6) wording",
    "scene_length": "Scene length band",
    "prose_target": "Prose length advisory",
    "prose_draft": "Prose length advisory",
    "opening_scene": "Opening scene (SCN01 until settled)",
}

_VOICE_USR_KEYS = ("narration", "prose_style", "inner_voice", "prose_warm")
_OPTION_USR_KEYS = ("opt_copy", "option_style", "opt_layout", "lib_opt_copy")


def _expand_law(law_id: str, mechanism: str, constraint: str) -> str:
    tokens = [
        t.strip()
        for t in constraint.replace(";", ",").split(",")
        if t.strip() and t.strip() != "-"
    ]
    gloss = [_TOKEN_GLOSS.get(t, t) for t in tokens[:8]]
    tail = "; ".join(gloss) if gloss else mechanism
    return f"{law_id} ({mechanism}): {tail}"


def _stage_task(index: WarmIndex, stage: str) -> str:
    hint_key = f"stage_hint_{stage}"
    hint = usr_value(index, hint_key)
    if hint:
        return hint
    return f"Draft stage: {stage}"


def _scene_snapshot(
    index: WarmIndex,
    pipeline: dict[str, Any],
    *,
    session: str | None = None,
) -> dict[str, Any]:
    scene: dict[str, Any] = {
        "focus": pipeline.get("step_focus"),
        "beat_stage": pipeline.get("beat_stage", "oln"),
    }
    if pipeline.get("time_display"):
        scene["time"] = pipeline["time_display"]
    if pipeline.get("game_time"):
        scene["game_time"] = pipeline["game_time"]
    if pipeline.get("character_ages"):
        scene["ages"] = pipeline["character_ages"]
    if pipeline.get("age_hint"):
        scene["age_hint"] = pipeline["age_hint"]
    ages = pipeline.get("character_ages") or {}
    plr_id: str | None = None
    know_idx = merge_knowledge_index(session) if session else {}
    if index.plr_rows:
        parts = normalise_plr_parts(index.plr_rows[0])
        if len(parts) >= 7:
            plr_id = parts[0]
            scene["plr_id"] = plr_id
            scene["plr_identity"] = parts[1]
            scene["plr_body"] = parts[PLR_IDX_BODY] if len(parts) > PLR_IDX_BODY else parts[6]
            scene["plr_parts"] = parts
            pid = parts[0]
            if pid in ages:
                scene["plr_age"] = ages[pid]
            if len(parts) >= 3 and str(parts[2]).isdigit():
                scene["plr_birth_year"] = int(parts[2])
            g = plr_gender(parts, usr_gender=usr_value(index, "pc_gender"))
            if g and g != "未定":
                scene["plr_gender"] = g
    npcs = []
    for raw in index.npc_rows[:12]:
        parts = normalise_npc_parts(raw)
        if len(parts) >= 4:
            entry = npc_presentation_entry(raw)
            nid = entry["id"]
            if len(parts) >= 3 and str(parts[2]).isdigit():
                entry["birth_year"] = int(parts[2])
            if nid in ages:
                entry["age"] = ages[nid]
            entry["name"] = resolve_npc_display_name(
                session, plr_id, parts, index=know_idx
            )
            entry.update(knowledge_meta(session, plr_id, nid, index=know_idx))
            npcs.append(entry)
    if npcs:
        scene["npcs"] = npcs
    if index.biz_rows:
        bparts = index.biz_rows[0]
        if len(bparts) >= 4:
            scene["biz"] = resolve_biz_display(session, plr_id, bparts, index=know_idx)
    if index.scn_rows:
        sparts = index.scn_rows[0]
        if len(sparts) >= 2:
            scene["scn_code"] = sparts[1]
    if pipeline.get("oln_row"):
        scene["oln_row"] = pipeline["oln_row"]
    name = usr_value(index, "pc_name")
    gender = usr_value(index, "pc_gender")
    if name:
        scene["plr_name"] = name
    if gender:
        scene["plr_gender"] = gender
    raw_arts = usr_value(index, "opening_arts")
    if raw_arts and raw_arts != "未定" and "未定" not in raw_arts:
        scene["opening_arts"] = [p.strip() for p in raw_arts.split(";") if p.strip()]
    return scene


def _usr_contract_bullets(index: WarmIndex, stage: str) -> list[str]:
    bullets: list[str] = []
    if stage in ("oln", "sbd", "scr"):
        opening = usr_value(index, "opening_scene")
        if opening:
            bullets.append(f"{_USR_LABELS['opening_scene']}: {opening}")
    skip = {"opening_scene", *_OPTION_USR_KEYS}
    for key in _VOICE_USR_KEYS:
        if stage != "prose":
            continue
        val = usr_value(index, key)
        if val:
            bullets.append(f"{_USR_LABELS[key]}: {val}")
    for key, label in _USR_LABELS.items():
        if key in skip or key in _VOICE_USR_KEYS:
            continue
        val = usr_value(index, key)
        if val:
            bullets.append(f"{label}: {val}")
    return bullets


def _law_contract_bullets(index: WarmIndex, stage: str) -> list[str]:
    return [
        _expand_law(law.id, law.mechanism, law.constraint)
        for law in laws_for_stage(index, stage, for_options=False)
    ]


def _option_contract_bullets(index: WarmIndex) -> list[str]:
    bullets: list[str] = []
    for key in _OPTION_USR_KEYS:
        val = usr_value(index, key)
        if val:
            bullets.append(f"{_USR_LABELS[key]}: {val}")
    for law in laws_for_stage(index, "prose", for_options=True):
        bullets.append(_expand_law(law.id, law.mechanism, law.constraint))
    return bullets


def _pipeline_extras(pipeline: dict[str, Any]) -> list[str]:
    bullets: list[str] = []
    if pipeline.get("auto_beat"):
        bullets.insert(
            0,
            "Unconscious beat: no player options; write rescue/wake narrative then finish.",
        )
    if pipeline.get("plr_body") or pipeline.get("body_hint"):
        body = pipeline.get("plr_body") or pipeline.get("body_hint")
        bullets.append(f"Body state: {body}")
    if pipeline.get("pipeline_no_bundle"):
        bullets.append(
            "Stage FSM (LAW-PIPE20 no_bundle): one wire type per beat_turn_finish; "
            f"current beat_stage={pipeline.get('beat_stage', 'oln')}."
        )
    target = pipeline.get("draft_target_chars")
    if target:
        bullets.append(f"Prose length advisory: ~{target} chars (not a gate).")
    return bullets


def compile_presentation(
    warm_stdout: str,
    pipeline: dict[str, Any],
    *,
    warm_walk: str | None = None,
    walk_filter: str = "governs",
    session: str | None = None,
) -> dict[str, Any]:
    """Build novel-agnostic presentation envelope from warm + pipeline."""
    index = index_warm(warm_stdout)
    stage = pipeline.get("beat_stage", "oln")

    contracts: list[str] = [_stage_task(index, stage)]
    contracts.extend(_pipeline_extras(pipeline))
    contracts.extend(_usr_contract_bullets(index, stage))
    contracts.extend(_law_contract_bullets(index, stage))

    option_contracts = _option_contract_bullets(index) if stage == "prose" else []

    lib_query = bool(pipeline.get("lib_query"))
    library_contracts, library_meta = compile_library_contracts(index, lib_query=lib_query)
    if lib_query and library_contracts:
        contracts = library_contracts + contracts

    walk_hops = curated_walk_lines(
        warm_walk or "",
        walk_filter=walk_filter,
        max_rows=12,
    )

    knowledge_graph = build_knowledge_view(warm_stdout, session=session)
    knowledge_hud = format_knowledge_hud(knowledge_graph)

    body_plot_raw = usr_value(index, "body_plot")
    body_plot_keys = hud_keys_from_body_plot(body_plot_raw)
    hud_pipe = usr_value(index, "hud_pipe")

    return {
        "stage": stage,
        "contracts": contracts,
        "option_contracts": option_contracts,
        "library_contracts": library_contracts,
        "library_meta": library_meta,
        "scene": _scene_snapshot(index, pipeline, session=session),
        "walk_hops": walk_hops,
        "body_plot": body_plot_raw,
        "body_plot_keys": body_plot_keys,
        "hud_pipe": hud_pipe,
        "knowledge": {
            "hud": knowledge_hud,
            "holdings_count": len(knowledge_graph.get("holdings") or []),
        },
    }


def compile_writing_contract(
    warm_stdout: str,
    pipeline: dict[str, Any],
    *,
    warm_walk: str | None = None,
) -> list[str]:
    """Deprecated: flat list for backward compatibility."""
    pres = compile_presentation(warm_stdout, pipeline, warm_walk=warm_walk)
    return pres["contracts"] + pres.get("option_contracts", [])
