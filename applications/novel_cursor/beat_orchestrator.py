"""Python-orchestrated beat pipeline: MCP begin/finish + dual chat threads."""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

from app_config import NovelAppConfig, repo_root
from beat_prompt import (
    build_prose_system,
    build_prose_user,
    build_script_stage_system,
    build_script_stage_user,
)
from chat_thread import ChatThread, reset_role_thread
from llm_client import complete_messages, model_for_role
from wire_parse import extract_draft_bundle, extract_scr_lines, normalise_options, parse_prose_payload
from novel_mcp.body_state import (
    hud_config_from_presentation,
    plr_update_downgrade_satiety,
    resolve_beat_hud,
    vitality_satiety_conflict,
)

from novel_mcp.beat_pipeline import beat_turn_begin, beat_turn_finish
from novel_mcp.play_context import read_beat_stage

_SCRIPT_STAGES = ("script_draft", "script_review")


def _lib_query(prep: dict[str, Any]) -> bool:
    player = prep.get("player") or {}
    return bool(player.get("lib_query"))


def _finish_kwargs_from_begin(begin: dict[str, Any], prep: dict[str, Any]) -> dict[str, Any]:
    fp = begin.get("finish_params") or prep.get("finish_params") or {}
    snap = fp.get("snapshot_file") or prep.get("snapshot_file")
    return {
        "chapter_dir": fp.get("chapter_dir") or prep.get("chapter_dir"),
        "chp_num": fp.get("chp_num") or prep.get("chp_num"),
        "snapshot_file": snap,
        "workspace_root": fp.get("workspace_root") or str(repo_root()),
        "min_chars": fp.get("min_chars"),
        "max_chars": fp.get("max_chars"),
        "usr05_band": fp.get("usr05_band"),
    }


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


def _script_thread(config: NovelAppConfig) -> ChatThread:
    model = model_for_role("script", config=config)
    thread = ChatThread.load(config, "script", model=model)
    thread.ensure_system(build_script_stage_system(config))
    thread.model = model
    return thread


def _prose_thread(config: NovelAppConfig) -> ChatThread:
    model = model_for_role("prose", config=config)
    thread = ChatThread.load(config, "prose", model=model)
    thread.ensure_system(build_prose_system(config))
    thread.model = model
    return thread


def run_script_stage(
    config: NovelAppConfig,
    session: str,
    prep: dict[str, Any],
    stage: str,
    thread: ChatThread,
    *,
    stream: bool = False,
) -> tuple[int, list[str]]:
    """One script stage: begin → threaded LLM wire → finish."""
    begin = beat_turn_begin(
        session=session,
        include_warm=True,
        lib_query=_lib_query(prep),
    )
    if begin.get("exit_code", 1) != 0:
        return int(begin.get("exit_code", 1)), begin.get("errors") or ["beat_turn_begin failed"]

    base_finish = _finish_kwargs_from_begin(begin, prep)
    since = begin.get("session_modified")
    prior_error: str | None = None

    for attempt in range(3):
        user = build_script_stage_user(prep, begin, stage, prior_error=prior_error)
        thread.append_user(user)
        _log(
            f"[orchestrator:script] LLM {stage} "
            f"model={thread.model} attempt={attempt + 1} turns={len(thread.messages)}"
        )
        try:
            text = complete_messages(
                thread.messages,
                stream=stream,
                role="script",
                model=thread.model,
                config=config,
            )
        except RuntimeError as err:
            thread.drop_last_user()
            return 1, [str(err)]

        if stage == "script_draft":
            oln_lines, sbd_lines, scr_lines = extract_draft_bundle(text)
            if not oln_lines or not sbd_lines or not scr_lines:
                thread.drop_last_user()
                missing = []
                if not oln_lines:
                    missing.append("@OLN")
                if not sbd_lines:
                    missing.append("@SBD")
                if not scr_lines:
                    missing.append("@SCR")
                prior_error = f"Draft bundle missing: {', '.join(missing)}."
                _log(f"[orchestrator:script] {stage} retry: {prior_error}")
                continue
            finish_kw = {
                "oln_lines": oln_lines,
                "sbd_lines": sbd_lines,
                "scr_lines": scr_lines,
            }
        elif stage == "script_review":
            scr_lines = extract_scr_lines(text)
            if not scr_lines:
                thread.drop_last_user()
                prior_error = "No @SCR: line in model output."
                _log(f"[orchestrator:script] {stage} retry: {prior_error}")
                continue
            finish_kw = {"scr_lines": scr_lines}
        else:
            thread.drop_last_user()
            return 1, [f"Unknown script stage: {stage}"]
        finish = beat_turn_finish(
            session=session,
            since_modified=since,
            **base_finish,
            **finish_kw,
        )
        if finish.get("exit_code", 1) == 0:
            thread.append_assistant(text)
            thread.save()
            return 0, []

        thread.drop_last_user()
        prior_error = "; ".join(finish.get("errors") or ["beat_turn_finish failed"])
        _log(f"[orchestrator:script] {stage} finish rejected: {prior_error}")
        since = finish.get("session_modified") or since
        begin = beat_turn_begin(session=session, include_warm=True, lib_query=_lib_query(prep))
        base_finish = _finish_kwargs_from_begin(begin, prep)

    return 1, [prior_error or f"{stage} stage failed"]


def run_script_phase(
    config: NovelAppConfig,
    session: str,
    prep: dict[str, Any],
    *,
    stream: bool = False,
    on_phase: Callable[[str], None] | None = None,
) -> tuple[int, list[str]]:
    """script_draft → script_review until USR23=prose (script chat thread)."""
    stage = read_beat_stage(session)
    if stage == "prose":
        return 0, []
    if stage not in _SCRIPT_STAGES:
        stage = "script_draft"

    reset_role_thread(config, "script")
    thread = _script_thread(config)
    start = _SCRIPT_STAGES.index(stage)
    for st in _SCRIPT_STAGES[start:]:
        if read_beat_stage(session) == "prose":
            break
        if on_phase and st in _SCRIPT_STAGES:
            on_phase(st)
        code, errors = run_script_stage(
            config,
            session,
            prep,
            st,
            thread,
            stream=stream,
        )
        if code != 0:
            thread.save()
            return code, errors

    thread.save()
    if read_beat_stage(session) != "prose":
        return 4, ["handoff: USR23 never reached prose"]
    return 0, []


def run_prose_phase(
    config: NovelAppConfig,
    session: str,
    prep: dict[str, Any],
    *,
    stream: bool = False,
    on_phase: Callable[[str], None] | None = None,
) -> tuple[dict[str, Any] | None, int, list[str]]:
    """prose begin → threaded LLM JSON → finish (prose chat thread)."""
    if read_beat_stage(session) != "prose":
        return None, 2, ["beat_stage must be prose"]

    if on_phase:
        on_phase("prose")

    thread = _prose_thread(config)
    begin = beat_turn_begin(session=session, include_warm=True)
    if begin.get("exit_code", 1) != 0:
        return None, int(begin.get("exit_code", 1)), begin.get("errors") or []

    base_finish = _finish_kwargs_from_begin(begin, prep)
    since = begin.get("session_modified")
    prior_error: str | None = None
    _PROSE_ATTEMPTS = 5

    for attempt in range(_PROSE_ATTEMPTS):
        user = build_prose_user(prep, begin)
        if prior_error:
            user += f"\n\n## Prior finish error (fix)\n{prior_error}"
        thread.append_user(user)
        _log(
            f"[orchestrator:prose] LLM model={thread.model} "
            f"attempt={attempt + 1} turns={len(thread.messages)}"
        )
        try:
            text = complete_messages(
                thread.messages,
                stream=stream,
                role="prose",
                model=thread.model,
                config=config,
            )
        except RuntimeError as err:
            thread.drop_last_user()
            thread.save()
            return None, 1, [str(err)]

        payload = parse_prose_payload(text)
        if payload is None:
            thread.drop_last_user()
            prior_error = "No parseable JSON with prose field."
            continue

        prose = str(payload.get("prose") or "").strip()
        options = normalise_options(payload.get("options"))
        update_lines = payload.get("update_lines") or []
        if not isinstance(update_lines, list):
            update_lines = []
        update_lines = [str(ln) for ln in update_lines if str(ln).strip()]

        presentation = begin.get("presentation") or {}
        scene = presentation.get("scene") or {}
        pipeline = begin.get("pipeline") or {}
        plr_body = (
            scene.get("plr_body")
            or pipeline.get("plr_body")
            or ""
        )
        hud_keys, hud_pipe = hud_config_from_presentation(presentation)
        llm_hud = str(payload.get("hud") or "").strip()
        vit_err = vitality_satiety_conflict(
            prose,
            plr_body,
            body_plot_keys=hud_keys or None,
            update_lines=update_lines,
        )
        if vit_err:
            plr_parts = scene.get("plr_parts")
            if plr_parts:
                auto = plr_update_downgrade_satiety(plr_parts)
                if auto and auto not in update_lines:
                    trial = list(update_lines) + [auto]
                    vit_err = vitality_satiety_conflict(
                        prose,
                        plr_body,
                        body_plot_keys=hud_keys or None,
                        update_lines=trial,
                    )
                    if not vit_err:
                        update_lines = trial
        if vit_err:
            thread.drop_last_user()
            prior_error = vit_err
            continue

        finish = beat_turn_finish(
            session=session,
            prose=prose,
            option_lines=options,
            update_lines=update_lines or None,
            since_modified=since,
            **base_finish,
        )
        if finish.get("exit_code", 1) == 0:
            hud = resolve_beat_hud(
                plr_body=plr_body,
                update_lines=update_lines,
                hud_keys=hud_keys or None,
                hud_pipe=hud_pipe,
                time_display=scene.get("time") or pipeline.get("time_display"),
                llm_fallback=llm_hud,
            )
            thread.append_assistant(text)
            thread.save()
            snap = base_finish.get("snapshot_file") or prep.get("snapshot_file") or ""
            saved = any(
                p.get("phase") == "session_save" and p.get("exit_code") == 0
                for p in finish.get("phases") or []
            )
            chapter = finish.get("chapter") or {}
            result = {
                "exit_code": 0,
                "session": session,
                "app_id": config.app_id,
                "prose": prose,
                "options": options,
                "hud": hud,
                "snapshot_saved": saved,
                "snapshot_file": snap,
                "beat_stage": finish.get("beat_stage") or read_beat_stage(session),
                "beat_index": chapter.get("paragraph_count"),
                "chapter_path": chapter.get("path"),
            }
            if prose and not chapter.get("path"):
                result["exit_code"] = 1
                result["error"] = "prose committed but chapter file not written"
                thread.drop_last_user()
                prior_error = result["error"]
                continue
            return result, 0, []

        thread.drop_last_user()
        prior_error = "; ".join(finish.get("errors") or ["beat_turn_finish failed"])
        begin = beat_turn_begin(session=session, include_warm=True)
        base_finish = _finish_kwargs_from_begin(begin, prep)
        since = begin.get("session_modified")

    thread.save()
    return None, 1, [prior_error or "prose finish failed"]
