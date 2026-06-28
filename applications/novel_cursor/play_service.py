"""Shared beat pipeline for cursor_beat CLI and novel_mobile HTTP server."""

from __future__ import annotations

import json
import socket
from collections.abc import Callable
from typing import Any

from app_config import NovelAppConfig, repo_root
from beat_orchestrator import run_prose_phase, run_script_phase
from mcp_config import SERVE_HOST, SERVE_PORT

from memnet_mcp.client import run_memnet

from novel_mcp.play_context import prose_beat_prepare, read_beat_stage, script_beat_prepare

_LEGACY_SESSION = repo_root() / "applications" / "shenjia_caifa" / "session_id.txt"

_PHASE_HOOKS = frozenset(
    {"prepare_script", "oln", "sbd", "scr", "prepare_prose", "prose"}
)


def _emit_phase(on_phase: Callable[[str], None] | None, phase: str) -> None:
    if on_phase and phase in _PHASE_HOOKS:
        on_phase(phase)


def _session_live(resp) -> bool:
    import re

    for line in resp.stdout.splitlines():
        m = re.match(r"^@SESSION:\s*(\S+)", line.strip())
        if m:
            sid = m.group(1).split("|", 1)[0].strip()
            return bool(sid and sid != "none")
    return False


def _migrate_legacy_session(config: NovelAppConfig) -> None:
    if config.session_id_file.is_file():
        return
    if _LEGACY_SESSION.is_file() and config.app_id == "shenjia_caifa":
        config.session_id_file.parent.mkdir(parents=True, exist_ok=True)
        config.session_id_file.write_text(
            _LEGACY_SESSION.read_text(encoding="utf-8"),
            encoding="utf-8",
        )


def probe_serve() -> bool:
    try:
        with socket.create_connection((SERVE_HOST, int(SERVE_PORT)), timeout=3):
            return True
    except OSError:
        return False


def read_session_id(config: NovelAppConfig, explicit: str | None = None) -> str:
    if explicit:
        return explicit.strip()
    _migrate_legacy_session(config)
    if config.session_id_file.is_file():
        line = config.session_id_file.read_text(encoding="utf-8").strip().splitlines()
        if line and line[0].startswith("mn_"):
            return line[0].strip()
    raise FileNotFoundError(f"missing session id at {config.session_id_file}")


def preflight_session(config: NovelAppConfig, session: str) -> tuple[str, int]:
    snap = config.snapshot_file
    cur = run_memnet(["session", "current"], session=session)
    if not _session_live(cur):
        if snap.is_file():
            load = run_memnet(
                ["session", "load", "--file", str(snap), "--keep-id"],
            )
            if load.exit_code != 0:
                return session, 1
            if load.session_id:
                session = load.session_id
                config.session_id_file.parent.mkdir(parents=True, exist_ok=True)
                config.session_id_file.write_text(session.strip() + "\n", encoding="utf-8")
        else:
            return session, 1

    return read_beat_stage(session), 0


def _snap_rel(config: NovelAppConfig) -> str:
    return str(config.snapshot_file.relative_to(repo_root())).replace("\\", "/")


def write_last_beat(config: NovelAppConfig, result: dict[str, Any]) -> None:
    path = config.last_beat_file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def read_last_beat(config: NovelAppConfig) -> dict[str, Any] | None:
    path = config.last_beat_file
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def fail_result(
    config: NovelAppConfig,
    session: str,
    code: int,
    error: str,
) -> dict[str, Any]:
    return {
        "exit_code": code,
        "session": session,
        "app_id": config.app_id,
        "prose": "",
        "options": [""] * 6,
        "hud": "",
        "snapshot_saved": False,
        "snapshot_file": _snap_rel(config),
        "beat_stage": read_beat_stage(session),
        "error": error,
    }


def run_beat(
    config: NovelAppConfig,
    session: str,
    *,
    choice: int | None = None,
    steering: str | None = None,
    continue_beat: bool = False,
    script_only: bool = False,
    prose_only: bool = False,
    stream: bool = False,
    on_phase: Callable[[str], None] | None = None,
) -> tuple[dict[str, Any] | None, int]:
    snap_rel = _snap_rel(config)
    ch_dir = str(config.chapter_dir.relative_to(repo_root())).replace("\\", "/")

    run_script = not prose_only
    if continue_beat and read_beat_stage(session) == "prose":
        run_script = False

    script_prep: dict[str, Any] = {}
    if run_script:
        script_prep = script_beat_prepare(
            session=session,
            choice=choice,
            steering=steering,
            continue_beat=continue_beat and not choice and not steering,
            snapshot_file=snap_rel,
            chapter_dir=ch_dir,
        )
        if script_prep.get("exit_code", 1) != 0:
            return None, int(script_prep.get("exit_code", 2))
        _emit_phase(on_phase, "prepare_script")

    if run_script:
        code, errors = run_script_phase(
            config,
            session,
            script_prep,
            stream=stream,
            on_phase=on_phase,
        )
        if code != 0:
            return None, code

    if script_only:
        return None, 0

    prose_prep = prose_beat_prepare(
        session=session,
        snapshot_file=snap_rel,
        chapter_dir=ch_dir,
    )
    if prose_prep.get("exit_code", 1) != 0:
        return None, int(prose_prep.get("exit_code", 2))
    _emit_phase(on_phase, "prepare_prose")

    result, code, errors = run_prose_phase(
        config,
        session,
        prose_prep,
        stream=stream,
        on_phase=on_phase,
    )
    if code != 0:
        if result is None:
            return None, code
        result["exit_code"] = code
        result["error"] = "; ".join(errors)
    return result, code
