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

from app_config import NovelAppConfig, load_config, list_story_instances
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
from novel_mcp.party_sheet import read_party_panel
from novel_mcp.player_profile import commit_profile
from novel_mcp.player_setup import player_setup_gate_payload, read_player_setup
from novel_mcp.player_sheet import read_player_sheet
from novel_mcp.play_context import read_beat_stage
from novel_mcp.setup_ack import VALID_SETUP_ACK_STEPS, commit_setup_ack

from novel_mobile.auth import (
    AuthConfig,
    AuthContext,
    authenticate_request,
    exchange_google_login,
    exchange_guest_login,
    load_auth_config,
    resolve_user_id,
)
from novel_mobile.jobs import BeatJob, BeatJobStore, world_job_slot
from novel_mobile.world_registry import (
    create_world_record,
    delete_world_record,
    locate_world,
    list_worlds_for_owner,
    require_world_owner,
    resolve_world_config,
    update_meta_session,
)
from novel_mobile.world_slot import (
    USER_ID_HEADER,
    WORLD_ID_HEADER,
    normalise_world_id,
)
from chat_thread import thread_path

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


class GoogleLoginBody(BaseModel):
    credential: str


class WorldCreateBody(BaseModel):
    title: str | None = None
    app_id: str | None = None
    expand_catalog: bool | None = None


_app_config: NovelAppConfig | None = None
_job_store = BeatJobStore()
_auth_config: AuthConfig = AuthConfig(mode="open")


def _llm_configured() -> bool:
    return any(
        os.environ.get(k, "").strip()
        for k in ("DEEPSEEK_API_KEY", "LLM_API_KEY", "LLM_API_KEY_SCRIPT", "LLM_API_KEY_PROSE")
    )


def get_config() -> NovelAppConfig:
    if _app_config is None:
        raise RuntimeError("app not configured")
    return _app_config


def _authenticate(authorization: str | None) -> AuthContext:
    try:
        return authenticate_request(_auth_config, authorization)
    except PermissionError as err:
        raise HTTPException(status_code=401, detail={"error": "unauthorized"}) from err
    except ValueError as err:
        raise HTTPException(status_code=401, detail={"error": "unauthorized"}) from err


def _user_from_request(
    authorization: str | None,
    x_novel_user_id: str | None,
) -> tuple[AuthContext, str]:
    ctx = _authenticate(authorization)
    try:
        user_id = resolve_user_id(
            ctx,
            x_novel_user_id,
            auth_mode=_auth_config.mode,
        )
    except ValueError as err:
        msg = str(err)
        if msg == "user_id_mismatch":
            raise HTTPException(
                status_code=403,
                detail={"errors": ["user_id_mismatch"]},
            ) from err
        raise HTTPException(
            status_code=400,
            detail={"errors": ["invalid_user_id"]},
        ) from err
    if not user_id:
        raise HTTPException(status_code=400, detail={"errors": ["missing_user_id"]})
    return ctx, user_id


def _world_context(
    authorization: str | None,
    x_novel_world_id: str | None,
    x_novel_user_id: str | None,
    *,
    require_world: bool = False,
) -> tuple[AuthContext, str | None, str | None]:
    ctx = _authenticate(authorization)
    try:
        user_id = resolve_user_id(
            ctx,
            x_novel_user_id,
            auth_mode=_auth_config.mode,
        )
    except ValueError as err:
        msg = str(err)
        if msg == "user_id_mismatch":
            raise HTTPException(
                status_code=403,
                detail={"errors": ["user_id_mismatch"]},
            ) from err
        raise HTTPException(
            status_code=400,
            detail={"errors": ["invalid_user_id"]},
        ) from err

    try:
        world_id = normalise_world_id(x_novel_world_id)
    except ValueError as err:
        raise HTTPException(
            status_code=400,
            detail={"errors": ["invalid_world_id"]},
        ) from err

    if require_world and not world_id:
        raise HTTPException(status_code=400, detail={"errors": ["missing_world_id"]})

    if world_id:
        if not user_id:
            raise HTTPException(status_code=400, detail={"errors": ["missing_user_id"]})
        try:
            require_world_owner(get_config(), world_id, user_id)
        except FileNotFoundError as err:
            raise HTTPException(status_code=404, detail={"error": "world_not_found"}) from err
        except PermissionError as err:
            raise HTTPException(
                status_code=403,
                detail={"errors": ["world_owner_mismatch"]},
            ) from err

    return ctx, user_id, world_id


def _wcfg(config: NovelAppConfig, world_id: str | None) -> NovelAppConfig:
    if world_id:
        return resolve_world_config(config, world_id)
    return config


def _session_or_raise(config: NovelAppConfig, world_id: str | None = None) -> str:
    try:
        return read_session_id(_wcfg(config, world_id))
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail={"ok": False, "issues": ["no_session"]},
        ) from None


def create_app(
    config: NovelAppConfig,
    *,
    auth_token: str | None = None,
    auth_config: AuthConfig | None = None,
) -> FastAPI:
    global _app_config, _auth_config
    _app_config = config
    if auth_config is not None:
        _auth_config = auth_config
    else:
        _auth_config = load_auth_config(shared_token=auth_token)

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

    @app.get("/api/auth/config")
    async def api_auth_config():
        return {
            "auth_mode": _auth_config.mode,
            "google_client_id": _auth_config.google_client_id,
            "auth_required": _auth_config.mode != "open",
        }

    @app.post("/api/auth/guest")
    async def api_auth_guest():
        if _auth_config.mode != "guest":
            raise HTTPException(status_code=404, detail={"error": "guest_auth_disabled"})
        return exchange_guest_login(_auth_config)

    @app.post("/api/auth/google")
    async def api_auth_google(payload: GoogleLoginBody):
        if _auth_config.mode != "google":
            raise HTTPException(status_code=404, detail={"error": "google_auth_disabled"})
        credential = payload.credential.strip()
        if not credential:
            raise HTTPException(status_code=400, detail={"errors": ["missing_credential"]})
        try:
            return exchange_google_login(_auth_config, credential)
        except PermissionError as err:
            raise HTTPException(status_code=403, detail={"error": "email_not_allowed"}) from err
        except ValueError as err:
            raise HTTPException(status_code=401, detail={"error": "invalid_google_token"}) from err

    @app.get("/api/seeds")
    async def api_seeds_list(
        authorization: str | None = Header(default=None),
        x_novel_user_id: str | None = Header(default=None, alias=USER_ID_HEADER),
    ):
        _authenticate(authorization)
        return {"seeds": list_story_instances()}

    @app.get("/api/worlds")
    async def api_worlds_list(
        authorization: str | None = Header(default=None),
        x_novel_user_id: str | None = Header(default=None, alias=USER_ID_HEADER),
    ):
        _, user_id = _user_from_request(authorization, x_novel_user_id)
        return {"worlds": list_worlds_for_owner(get_config(), user_id)}

    @app.post("/api/worlds")
    async def api_worlds_create(
        payload: WorldCreateBody,
        authorization: str | None = Header(default=None),
        x_novel_user_id: str | None = Header(default=None, alias=USER_ID_HEADER),
    ):
        ctx, user_id = _user_from_request(authorization, x_novel_user_id)
        if not probe_serve():
            raise HTTPException(
                status_code=503,
                detail={"errors": ["serve_unreachable"]},
            )
        cfg = get_config()
        app_id = (payload.app_id or cfg.app_id).strip()
        try:
            app_cfg = load_config(app_id=app_id) if app_id != cfg.app_id else cfg
        except (FileNotFoundError, ValueError) as err:
            raise HTTPException(status_code=400, detail={"errors": ["invalid_app_id"]}) from err
        if not probe_serve():
            raise HTTPException(
                status_code=503,
                detail={"errors": ["serve_unreachable"]},
            )
        meta = create_world_record(app_cfg, user_id, title=payload.title)
        wcfg = _wcfg(cfg, meta.world_id)
        if _job_store.has_active(meta.world_id):
            raise HTTPException(status_code=409, detail={"errors": ["beat_job_active"]})

        def _run() -> dict[str, Any]:
            return rebootstrap_session(
                wcfg,
                expand_catalog=payload.expand_catalog,
            )

        result = await anyio.to_thread.run_sync(_run)
        if result.get("exit_code", 0) != 0:
            raise HTTPException(
                status_code=500,
                detail={"errors": result.get("errors", ["rebootstrap_failed"])},
            )
        update_meta_session(cfg, meta.world_id, str(result.get("session_id") or ""))
        return {
            "world_id": meta.world_id,
            "app_id": meta.app_id or app_cfg.app_id,
            "story_title": app_cfg.title,
            "title": meta.title,
            "owner_id": meta.owner_id,
            "user_id": user_id,
            "email": ctx.email,
            **result,
        }

    @app.delete("/api/worlds/{world_id}")
    async def api_worlds_delete(
        world_id: str,
        authorization: str | None = Header(default=None),
        x_novel_user_id: str | None = Header(default=None, alias=USER_ID_HEADER),
    ):
        _, user_id = _user_from_request(authorization, x_novel_user_id)
        try:
            normalise_world_id(world_id)
        except ValueError as err:
            raise HTTPException(status_code=400, detail={"errors": ["invalid_world_id"]}) from err
        if _job_store.has_active(world_id):
            raise HTTPException(status_code=409, detail={"errors": ["beat_job_active"]})
        try:
            delete_world_record(get_config(), world_id, user_id)
        except FileNotFoundError as err:
            raise HTTPException(status_code=404, detail={"errors": ["world_not_found"]}) from err
        except PermissionError as err:
            raise HTTPException(status_code=403, detail={"errors": ["world_owner_mismatch"]}) from err
        return {"deleted": world_id}

    @app.get("/api/health")
    async def health(
        authorization: str | None = Header(default=None),
        x_novel_world_id: str | None = Header(default=None, alias=WORLD_ID_HEADER),
        x_novel_user_id: str | None = Header(default=None, alias=USER_ID_HEADER),
    ):
        ctx, user_id, world_id = _world_context(
            authorization, x_novel_world_id, x_novel_user_id
        )
        cfg = get_config()
        wcfg = _wcfg(cfg, world_id)
        app_cfg = cfg
        if world_id:
            try:
                app_cfg, _meta = locate_world(cfg, world_id)
            except FileNotFoundError:
                app_cfg = cfg
        issues: list[str] = []
        serve_ok = probe_serve()
        if not serve_ok:
            issues.append("serve_unreachable")
        llm_ok = _llm_configured()
        if not llm_ok:
            issues.append("llm_not_configured")
        session: str | None = None
        setup_complete = False
        beat_stage: str | None = None
        has_last_beat = False
        try:
            session = read_session_id(wcfg)
            setup = read_player_setup(session)
            setup_complete = bool(setup.get("setup_complete"))
            from novel_mcp.beat_stage import normalize_beat_stage

            beat_stage = normalize_beat_stage(read_beat_stage(session))
            has_last_beat = read_last_beat(wcfg) is not None
        except FileNotFoundError:
            issues.append("no_session")
        return {
            "ok": serve_ok and llm_ok and session is not None,
            "serve_reachable": serve_ok,
            "llm_configured": llm_ok,
            "app_id": app_cfg.app_id,
            "title": app_cfg.title,
            "user_id": user_id,
            "world_id": world_id,
            "email": ctx.email,
            "session": session,
            "setup_complete": setup_complete,
            "beat_stage": beat_stage,
            "has_last_beat": has_last_beat,
            "auth_mode": _auth_config.mode,
            "auth_required": _auth_config.mode != "open",
            "agent_threads": {
                "script": thread_path(wcfg, "script").is_file(),
                "prose": thread_path(wcfg, "prose").is_file(),
            },
            "issues": issues if issues else None,
        }

    @app.get("/api/setup")
    async def api_setup(
        authorization: str | None = Header(default=None),
        x_novel_world_id: str | None = Header(default=None, alias=WORLD_ID_HEADER),
        x_novel_user_id: str | None = Header(default=None, alias=USER_ID_HEADER),
    ):
        _, _user_id, world_id = _world_context(
            authorization, x_novel_world_id, x_novel_user_id, require_world=False
        )
        session = _session_or_raise(get_config(), world_id)
        setup = read_player_setup(session)
        if setup.get("exit_code", 0) != 0:
            raise HTTPException(status_code=502, detail=setup)
        return setup

    @app.post("/api/setup/profile")
    async def api_setup_profile(
        payload: ProfileBody,
        authorization: str | None = Header(default=None),
        x_novel_world_id: str | None = Header(default=None, alias=WORLD_ID_HEADER),
        x_novel_user_id: str | None = Header(default=None, alias=USER_ID_HEADER),
    ):
        _, _user_id, world_id = _world_context(
            authorization, x_novel_world_id, x_novel_user_id, require_world=False
        )
        session = _session_or_raise(get_config(), world_id)
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
        x_novel_world_id: str | None = Header(default=None, alias=WORLD_ID_HEADER),
        x_novel_user_id: str | None = Header(default=None, alias=USER_ID_HEADER),
    ):
        _, _user_id, world_id = _world_context(
            authorization, x_novel_world_id, x_novel_user_id, require_world=False
        )
        session = _session_or_raise(get_config(), world_id)
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
    async def api_catalog(
        authorization: str | None = Header(default=None),
        x_novel_world_id: str | None = Header(default=None, alias=WORLD_ID_HEADER),
        x_novel_user_id: str | None = Header(default=None, alias=USER_ID_HEADER),
    ):
        _, _user_id, world_id = _world_context(
            authorization, x_novel_world_id, x_novel_user_id, require_world=False
        )
        session = _session_or_raise(get_config(), world_id)
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
        x_novel_world_id: str | None = Header(default=None, alias=WORLD_ID_HEADER),
        x_novel_user_id: str | None = Header(default=None, alias=USER_ID_HEADER),
    ):
        _, _user_id, world_id = _world_context(
            authorization, x_novel_world_id, x_novel_user_id, require_world=False
        )
        session = _session_or_raise(get_config(), world_id)
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
        x_novel_world_id: str | None = Header(default=None, alias=WORLD_ID_HEADER),
        x_novel_user_id: str | None = Header(default=None, alias=USER_ID_HEADER),
    ):
        _, _user_id, world_id = _world_context(
            authorization, x_novel_world_id, x_novel_user_id, require_world=False
        )
        session = _session_or_raise(get_config(), world_id)
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
    async def api_session_rebootstrap(
        authorization: str | None = Header(default=None),
        x_novel_world_id: str | None = Header(default=None, alias=WORLD_ID_HEADER),
        x_novel_user_id: str | None = Header(default=None, alias=USER_ID_HEADER),
    ):
        _, _user_id, world_id = _world_context(
            authorization, x_novel_world_id, x_novel_user_id, require_world=False
        )
        if not probe_serve():
            raise HTTPException(
                status_code=503,
                detail={"errors": ["serve_unreachable"]},
            )
        if _job_store.has_active(world_id):
            raise HTTPException(
                status_code=409,
                detail={"errors": ["beat_job_active"]},
            )
        cfg = _wcfg(get_config(), world_id)

        def _run() -> dict[str, Any]:
            return rebootstrap_session(cfg)

        result = await anyio.to_thread.run_sync(_run)
        if result.get("exit_code", 0) != 0:
            raise HTTPException(
                status_code=500,
                detail={"errors": result.get("errors", ["rebootstrap_failed"])},
            )
        if world_id:
            update_meta_session(get_config(), world_id, str(result.get("session_id") or ""))
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
        x_novel_world_id: str | None = Header(default=None, alias=WORLD_ID_HEADER),
        x_novel_user_id: str | None = Header(default=None, alias=USER_ID_HEADER),
    ):
        _, _user_id, world_id = _world_context(
            authorization, x_novel_world_id, x_novel_user_id, require_world=False
        )
        cfg = _wcfg(get_config(), world_id)
        session = _session_or_raise(get_config(), world_id)

        raw = await request.json()
        if not isinstance(raw, dict):
            raise HTTPException(status_code=400, detail={"errors": ["invalid_body"]})
        choice = raw.get("choice")
        steering = raw.get("steering")
        continue_beat = bool(raw.get("continue", False))
        start_beat = bool(raw.get("start", False))

        modes = sum(
            [
                choice is not None,
                bool(steering and str(steering).strip()),
                continue_beat,
                start_beat,
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

        from novel_mcp.beat_stage import SCRIPT_STAGES, normalize_beat_stage

        beat_stage = normalize_beat_stage(read_beat_stage(session))

        if continue_beat and beat_stage in SCRIPT_STAGES:
            raise HTTPException(
                status_code=400,
                detail={"errors": ["continue_requires_prose_stage"]},
            )
        if start_beat and beat_stage == "prose":
            # Script already finished (e.g. prior job failed during prose) but no last_beat yet.
            if read_last_beat(cfg) is None:
                start_beat = False
                continue_beat = True
            else:
                raise HTTPException(
                    status_code=400,
                    detail={"errors": ["start_requires_script_stage"]},
                )

        if _job_store.has_active(world_id):
            raise HTTPException(status_code=409, detail={"errors": ["beat_job_active"]})

        job = _job_store.create(world_id)
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
    async def api_beat_job(
        job_id: str,
        authorization: str | None = Header(default=None),
        x_novel_world_id: str | None = Header(default=None, alias=WORLD_ID_HEADER),
        x_novel_user_id: str | None = Header(default=None, alias=USER_ID_HEADER),
    ):
        _, _user_id, world_id = _world_context(
            authorization, x_novel_world_id, x_novel_user_id, require_world=False
        )
        job = _job_store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail={"error": "job_not_found"})
        slot = world_job_slot(world_id)
        if job.world_id != slot:
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
    async def api_beat_last(
        authorization: str | None = Header(default=None),
        x_novel_world_id: str | None = Header(default=None, alias=WORLD_ID_HEADER),
        x_novel_user_id: str | None = Header(default=None, alias=USER_ID_HEADER),
    ):
        _, _user_id, world_id = _world_context(
            authorization, x_novel_world_id, x_novel_user_id, require_world=False
        )
        cfg = _wcfg(get_config(), world_id)
        result = read_last_beat(cfg)
        if result is None:
            raise HTTPException(status_code=404, detail={"error": "no_last_beat"})
        return result

    @app.get("/api/player/sheet")
    async def api_player_sheet(
        authorization: str | None = Header(default=None),
        x_novel_world_id: str | None = Header(default=None, alias=WORLD_ID_HEADER),
        x_novel_user_id: str | None = Header(default=None, alias=USER_ID_HEADER),
    ):
        _, _user_id, world_id = _world_context(
            authorization, x_novel_world_id, x_novel_user_id, require_world=False
        )
        session = _session_or_raise(get_config(), world_id)
        sheet = read_player_sheet(session)
        if sheet.get("exit_code", 0) != 0:
            raise HTTPException(status_code=502, detail=sheet)
        return sheet

    @app.get("/api/party/panel")
    async def api_party_panel(
        authorization: str | None = Header(default=None),
        x_novel_world_id: str | None = Header(default=None, alias=WORLD_ID_HEADER),
        x_novel_user_id: str | None = Header(default=None, alias=USER_ID_HEADER),
    ):
        _, _user_id, world_id = _world_context(
            authorization, x_novel_world_id, x_novel_user_id, require_world=False
        )
        session = _session_or_raise(get_config(), world_id)
        panel = read_party_panel(session)
        if panel.get("exit_code", 0) != 0:
            raise HTTPException(status_code=502, detail=panel)
        return panel

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

    try:
        auth_cfg = load_auth_config(shared_token=args.token)
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2

    app = create_app(config, auth_config=auth_cfg)

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
