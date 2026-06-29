"""LAN mobile browser UI for novel setup + play."""

from __future__ import annotations

import argparse
import os
import sys
import threading
from pathlib import Path
from typing import Any

_root = Path(__file__).resolve().parents[2]
_cursor = _root / "applications" / "novel_cursor"
sys.path.insert(0, str(_cursor))
sys.path.insert(0, str(_root / "src"))

from fastapi import FastAPI, Header, HTTPException, Request
import anyio
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app_config import NovelAppConfig, load_config
from env_load import load_dotenv
from session_bootstrap import rebootstrap_session
from play_service import (
    fail_result,
    preflight_session,
    probe_serve,
    read_last_beat,
    read_session_id,
    run_beat,
    write_last_beat,
)

from novel_mcp.opening_loadout import (
    commit_opening_pick,
    read_opening_catalog,
    reroll_opening_offers,
)
from novel_mcp.player_profile import commit_profile
from novel_mcp.player_setup import player_setup_gate_payload, read_player_setup
from novel_mcp.player_sheet import read_player_sheet
from novel_mcp.play_context import read_beat_stage
from novel_mcp.setup_ack import VALID_SETUP_ACK_STEPS, commit_setup_ack

from novel_mobile.jobs import BeatJob, BeatJobStore

STATIC_DIR = Path(__file__).resolve().parent / "static"


class ProfileBody(BaseModel):
    name: str | None = None
    gender: str | None = None


class PickBody(BaseModel):
    slot: str
    art_id: str


class RerollBody(BaseModel):
    slot: str


class AckBody(BaseModel):
    step: str


class BeatBody(BaseModel):
    choice: int | None = None
    steering: str | None = None
    continue_beat: bool = False


_app_config: NovelAppConfig | None = None
_job_store = BeatJobStore()
_auth_token: str | None = None


def _llm_configured() -> bool:
    return any(
        os.environ.get(k, "").strip()
        for k in ("DEEPSEEK_API_KEY", "LLM_API_KEY", "LLM_API_KEY_SCRIPT", "LLM_API_KEY_PROSE")
    )


def get_config() -> NovelAppConfig:
    if _app_config is None:
        raise RuntimeError("app not configured")
    return _app_config


def _require_auth(authorization: str | None = Header(default=None)) -> None:
    if not _auth_token:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"error": "unauthorized"})
    token = authorization[7:].strip()
    if token != _auth_token:
        raise HTTPException(status_code=401, detail={"error": "unauthorized"})


def _session_or_raise(config: NovelAppConfig) -> str:
    try:
        return read_session_id(config)
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail={"ok": False, "issues": ["no_session"]},
        ) from None


def create_app(config: NovelAppConfig, *, auth_token: str | None = None) -> FastAPI:
    global _app_config, _auth_token
    _app_config = config
    _auth_token = auth_token.strip() if auth_token else os.environ.get("NOVEL_MOBILE_TOKEN", "").strip() or None

    app = FastAPI(title=config.title)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def index():
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/api/health")
    async def health(authorization: str | None = Header(default=None)):
        _require_auth(authorization)
        cfg = get_config()
        issues: list[str] = []
        serve_ok = probe_serve()
        if not serve_ok:
            issues.append("serve_unreachable")
        llm_ok = _llm_configured()
        if not llm_ok:
            issues.append("llm_not_configured")
        session: str | None = None
        setup_complete = False
        try:
            session = read_session_id(cfg)
            setup = read_player_setup(session)
            setup_complete = bool(setup.get("setup_complete"))
        except FileNotFoundError:
            issues.append("no_session")
        return {
            "ok": serve_ok and llm_ok and session is not None,
            "serve_reachable": serve_ok,
            "llm_configured": llm_ok,
            "app_id": cfg.app_id,
            "title": cfg.title,
            "session": session,
            "setup_complete": setup_complete,
            "auth_required": bool(_auth_token),
            "issues": issues if issues else None,
        }

    @app.get("/api/setup")
    async def api_setup(authorization: str | None = Header(default=None)):
        _require_auth(authorization)
        cfg = get_config()
        session = _session_or_raise(cfg)
        setup = read_player_setup(session)
        if setup.get("exit_code", 0) != 0:
            raise HTTPException(status_code=502, detail=setup)
        return setup

    @app.post("/api/setup/profile")
    async def api_setup_profile(
        payload: ProfileBody,
        authorization: str | None = Header(default=None),
    ):
        _require_auth(authorization)
        cfg = get_config()
        session = _session_or_raise(cfg)
        setup = read_player_setup(session)
        if setup.get("setup_complete"):
            raise HTTPException(status_code=409, detail={"errors": ["setup_already_complete"]})
        if not payload.name and not payload.gender:
            raise HTTPException(status_code=400, detail={"errors": ["provide name and/or gender"]})
        prof = commit_profile(session, payload.name or "", payload.gender or "")
        if prof.get("exit_code") != 0:
            raise HTTPException(status_code=400, detail={"errors": prof.get("errors", [])})
        return read_player_setup(session)

    @app.post("/api/setup/ack")
    async def api_setup_ack(
        payload: AckBody,
        authorization: str | None = Header(default=None),
    ):
        _require_auth(authorization)
        cfg = get_config()
        session = _session_or_raise(cfg)
        setup = read_player_setup(session)
        if setup.get("setup_complete"):
            raise HTTPException(status_code=409, detail={"errors": ["setup_already_complete"]})
        guidance = setup.get("setup_guidance") or {}
        expected = guidance.get("next_action")
        step = payload.step.strip()
        if step not in VALID_SETUP_ACK_STEPS:
            raise HTTPException(status_code=400, detail={"errors": [f"invalid ack step: {step}"]})
        if step != expected:
            raise HTTPException(
                status_code=409,
                detail={"errors": [f"ack step {step} does not match next_action {expected}"]},
            )
        ack = commit_setup_ack(session, step)
        if ack.get("exit_code", 0) != 0:
            raise HTTPException(status_code=400, detail={"errors": ack.get("errors", [])})
        return read_player_setup(session)

    @app.get("/api/catalog")
    async def api_catalog(authorization: str | None = Header(default=None)):
        _require_auth(authorization)
        cfg = get_config()
        session = _session_or_raise(cfg)
        setup = read_player_setup(session)
        if setup.get("setup_complete"):
            raise HTTPException(status_code=409, detail={"errors": ["setup_already_complete"]})
        guidance = setup.get("setup_guidance") or {}
        next_action = guidance.get("next_action", "")
        if not next_action.startswith("pick_"):
            raise HTTPException(
                status_code=409,
                detail={"errors": ["not_in_pick_phase"]},
            )
        cat = read_opening_catalog(session)
        if cat.get("exit_code", 0) != 0:
            raise HTTPException(status_code=502, detail=cat)
        return cat

    @app.post("/api/setup/pick")
    async def api_setup_pick(
        payload: PickBody,
        authorization: str | None = Header(default=None),
    ):
        _require_auth(authorization)
        cfg = get_config()
        session = _session_or_raise(cfg)
        setup = read_player_setup(session)
        if setup.get("setup_complete"):
            raise HTTPException(status_code=409, detail={"errors": ["setup_already_complete"]})
        guidance = setup.get("setup_guidance") or {}
        next_action = guidance.get("next_action", "")
        if not next_action.startswith("pick_"):
            raise HTTPException(
                status_code=409,
                detail={"errors": ["not_in_pick_phase"]},
            )
        result = commit_opening_pick(session, payload.slot, payload.art_id)
        if result.get("exit_code", 0) != 0:
            raise HTTPException(status_code=400, detail={"errors": result.get("errors", [])})
        return read_player_setup(session)

    @app.post("/api/setup/reroll")
    async def api_setup_reroll(
        payload: RerollBody,
        authorization: str | None = Header(default=None),
    ):
        _require_auth(authorization)
        cfg = get_config()
        session = _session_or_raise(cfg)
        setup = read_player_setup(session)
        if setup.get("setup_complete"):
            raise HTTPException(status_code=409, detail={"errors": ["setup_already_complete"]})
        guidance = setup.get("setup_guidance") or {}
        next_action = guidance.get("next_action", "")
        expected = f"pick_{payload.slot.strip()}"
        if next_action != expected:
            raise HTTPException(
                status_code=409,
                detail={"errors": [f"next_action {next_action} does not match slot {payload.slot}"]},
            )
        result = reroll_opening_offers(session, payload.slot.strip())
        if result.get("exit_code", 0) != 0:
            raise HTTPException(status_code=400, detail={"errors": result.get("errors", [])})
        return result

    @app.post("/api/session/rebootstrap")
    async def api_session_rebootstrap(authorization: str | None = Header(default=None)):
        _require_auth(authorization)
        if not probe_serve():
            raise HTTPException(
                status_code=503,
                detail={"errors": ["serve_unreachable"]},
            )
        if _job_store.has_active():
            raise HTTPException(
                status_code=409,
                detail={"errors": ["beat_job_active"]},
            )
        cfg = get_config()

        def _run() -> dict[str, Any]:
            return rebootstrap_session(cfg, expand_catalog=False)

        result = await anyio.to_thread.run_sync(_run)
        if result.get("exit_code", 0) != 0:
            raise HTTPException(
                status_code=500,
                detail={"errors": result.get("errors", ["rebootstrap_failed"])},
            )
        return result

    def _run_beat_job(job: BeatJob, cfg: NovelAppConfig, session: str, beat: BeatBody) -> None:
        _job_store.set_running(job.job_id)

        def on_phase(phase: str) -> None:
            _job_store.set_phase(job.job_id, phase)

        try:
            _, pf_code = preflight_session(cfg, session)
            if pf_code != 0:
                result = fail_result(cfg, session, pf_code, "session preflight failed")
                _job_store.finish(job.job_id, result, error=result.get("error"))
                return

            result, code = run_beat(
                cfg,
                session,
                choice=beat.choice,
                steering=beat.steering,
                continue_beat=beat.continue_beat,
                on_phase=on_phase,
            )
            if result is None:
                result = fail_result(cfg, session, code, "beat returned no result")
            if int(result.get("exit_code", 0)) == 0:
                write_last_beat(cfg, result)
            else:
                err = str(result.get("error") or "beat failed")
                _job_store.finish(job.job_id, result, error=err)
                return
            _job_store.finish(job.job_id, result)
        except Exception as err:  # noqa: BLE001 — background job must not crash thread
            result = fail_result(cfg, session, 1, str(err))
            _job_store.finish(job.job_id, result, error=str(err))

    @app.post("/api/beat", status_code=202)
    async def api_beat(
        request: Request,
        authorization: str | None = Header(default=None),
    ):
        _require_auth(authorization)
        cfg = get_config()
        session = _session_or_raise(cfg)

        raw = await request.json()
        if not isinstance(raw, dict):
            raise HTTPException(status_code=400, detail={"errors": ["invalid_body"]})
        choice = raw.get("choice")
        steering = raw.get("steering")
        continue_beat = bool(raw.get("continue", False))

        modes = sum(
            [
                choice is not None,
                bool(steering and str(steering).strip()),
                continue_beat,
            ]
        )
        if modes != 1:
            raise HTTPException(status_code=400, detail={"errors": ["mutually_exclusive"]})
        choice_int: int | None = None
        if choice is not None:
            try:
                choice_int = int(choice)
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail={"errors": ["invalid_choice"]}) from None
            if not (1 <= choice_int <= 6):
                raise HTTPException(status_code=400, detail={"errors": ["choice_out_of_range"]})

        if not probe_serve() or not _llm_configured():
            raise HTTPException(
                status_code=503,
                detail={"errors": ["serve_or_llm_unavailable"]},
            )

        setup = read_player_setup(session)
        if not setup.get("setup_complete"):
            raise HTTPException(status_code=403, detail=player_setup_gate_payload(session))

        if continue_beat and read_beat_stage(session) == "oln":
            raise HTTPException(
                status_code=400,
                detail={"errors": ["continue_requires_prose_stage"]},
            )

        if _job_store.has_active():
            raise HTTPException(status_code=409, detail={"errors": ["beat_job_active"]})

        job = _job_store.create()
        if job is None:
            raise HTTPException(status_code=409, detail={"errors": ["beat_job_active"]})

        steering_text = str(steering).strip() if steering else None
        beat_body = BeatBody(
            choice=choice_int,
            steering=steering_text,
            continue_beat=continue_beat,
        )
        thread = threading.Thread(
            target=_run_beat_job,
            args=(job, cfg, session, beat_body),
            daemon=True,
        )
        thread.start()
        return {"job_id": job.job_id}

    @app.get("/api/beat/jobs/{job_id}")
    async def api_beat_job(job_id: str, authorization: str | None = Header(default=None)):
        _require_auth(authorization)
        job = _job_store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail={"error": "job_not_found"})
        return {
            "job_id": job.job_id,
            "status": job.status,
            "phase": job.phase,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "result": job.result,
            "error": job.error,
        }

    @app.get("/api/beat/last")
    async def api_beat_last(authorization: str | None = Header(default=None)):
        _require_auth(authorization)
        cfg = get_config()
        result = read_last_beat(cfg)
        if result is None:
            raise HTTPException(status_code=404, detail={"error": "no_last_beat"})
        return result

    @app.get("/api/player/sheet")
    async def api_player_sheet(authorization: str | None = Header(default=None)):
        _require_auth(authorization)
        cfg = get_config()
        session = _session_or_raise(cfg)
        sheet = read_player_sheet(session)
        if sheet.get("exit_code", 0) != 0:
            raise HTTPException(status_code=502, detail=sheet)
        return sheet

    return app


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Novel mobile LAN UI")
    parser.add_argument("--app", default="shenjia_caifa", metavar="ID")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--token", metavar="TEXT", help="Bearer token (or NOVEL_MOBILE_TOKEN)")
    args = parser.parse_args(argv)

    try:
        config = load_config(app_id=args.app)
    except (FileNotFoundError, ValueError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 2

    token = args.token or os.environ.get("NOVEL_MOBILE_TOKEN", "").strip() or None
    app = create_app(config, auth_token=token)

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
