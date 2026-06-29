"""World registry — user-owned worlds, each with its own MemNet session."""

from __future__ import annotations

import json
import shutil
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app_config import NovelAppConfig, load_config, repo_root

from novel_mobile.world_slot import normalise_world_id, world_root, worlds_base_dir


@dataclass
class WorldMeta:
    world_id: str
    owner_id: str
    title: str
    created_at: float
    app_id: str | None = None
    memnet_session: str | None = None


def new_world_id() -> str:
    return "w_" + uuid.uuid4().hex[:16]


def _meta_path(wcfg: NovelAppConfig) -> Path:
    return wcfg.output_dir / "meta.json"


def write_meta(wcfg: NovelAppConfig, meta: WorldMeta) -> None:
    wcfg.output_dir.mkdir(parents=True, exist_ok=True)
    _meta_path(wcfg).write_text(
        json.dumps(asdict(meta), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def read_meta(base: NovelAppConfig, world_id: str) -> WorldMeta | None:
    normalise_world_id(world_id)
    wcfg = world_root(base, world_id)
    path = _meta_path(wcfg)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    wid = str(data.get("world_id") or world_id).strip()
    owner = str(data.get("owner_id") or "").strip()
    if not owner:
        return None
    app_id = str(data.get("app_id") or base.app_id).strip() or base.app_id
    return WorldMeta(
        world_id=wid,
        owner_id=owner,
        title=str(data.get("title") or wid),
        created_at=float(data.get("created_at") or 0),
        app_id=app_id,
        memnet_session=str(data.get("memnet_session") or "").strip() or None,
    )


def app_config_for_meta(meta: WorldMeta, default: NovelAppConfig) -> NovelAppConfig:
    aid = (meta.app_id or default.app_id).strip()
    if aid == default.app_id:
        return default
    return load_config(app_id=aid)


def locate_world(default_base: NovelAppConfig, world_id: str) -> tuple[NovelAppConfig, WorldMeta]:
    """Find a world under novel-output/<app>/worlds/ (Many SEEDS)."""
    normalise_world_id(world_id)
    meta = read_meta(default_base, world_id)
    if meta is not None:
        return app_config_for_meta(meta, default_base), meta
    novel_out = repo_root() / "novel-output"
    if novel_out.is_dir():
        for app_dir in sorted(novel_out.iterdir()):
            if not app_dir.is_dir() or app_dir.name == default_base.app_id:
                continue
            try:
                app_cfg = load_config(app_id=app_dir.name)
            except (FileNotFoundError, ValueError):
                continue
            meta = read_meta(app_cfg, world_id)
            if meta is not None:
                return app_cfg, meta
    raise FileNotFoundError(world_id)


def resolve_world_config(default_base: NovelAppConfig, world_id: str | None) -> NovelAppConfig:
    if not world_id:
        return default_base
    app_cfg, _meta = locate_world(default_base, world_id)
    return world_root(app_cfg, world_id)


def _world_summary(app_cfg: NovelAppConfig, meta: WorldMeta) -> dict[str, Any]:
    wcfg = world_root(app_cfg, meta.world_id)
    has_session = wcfg.session_id_file.is_file()
    session: str | None = None
    if has_session:
        line = wcfg.session_id_file.read_text(encoding="utf-8").strip().splitlines()
        if line and line[0].startswith("mn_"):
            session = line[0].strip()
    return {
        "world_id": meta.world_id,
        "title": meta.title,
        "app_id": meta.app_id or app_cfg.app_id,
        "story_title": app_cfg.title,
        "created_at": meta.created_at,
        "has_session": has_session,
        "memnet_session": session,
    }


def _collect_worlds_for_app(
    app_cfg: NovelAppConfig,
    owner_id: str,
    *,
    seen_apps: set[str],
    out: list[dict[str, Any]],
) -> None:
    if app_cfg.app_id in seen_apps:
        return
    seen_apps.add(app_cfg.app_id)
    root = worlds_base_dir(app_cfg)
    if not root.is_dir():
        return
    for child in root.iterdir():
        if not child.is_dir():
            continue
        meta = read_meta(app_cfg, child.name)
        if meta and meta.owner_id == owner_id:
            out.append(_world_summary(app_cfg, meta))


def list_worlds_for_owner(default_base: NovelAppConfig, owner_id: str) -> list[dict[str, Any]]:
    seen_apps: set[str] = set()
    out: list[dict[str, Any]] = []
    _collect_worlds_for_app(default_base, owner_id, seen_apps=seen_apps, out=out)
    novel_out = repo_root() / "novel-output"
    if novel_out.is_dir():
        for app_dir in sorted(novel_out.iterdir()):
            if not app_dir.is_dir():
                continue
            if app_dir.name in seen_apps:
                continue
            try:
                app_cfg = load_config(app_id=app_dir.name)
            except (FileNotFoundError, ValueError):
                continue
            _collect_worlds_for_app(app_cfg, owner_id, seen_apps=seen_apps, out=out)
    out.sort(key=lambda w: float(w.get("created_at") or 0), reverse=True)
    return out


def create_world_record(
    base: NovelAppConfig,
    owner_id: str,
    *,
    title: str | None = None,
    world_id: str | None = None,
) -> WorldMeta:
    wid = world_id or new_world_id()
    normalise_world_id(wid)
    if read_meta(base, wid) is not None:
        raise FileExistsError(wid)
    meta = WorldMeta(
        world_id=wid,
        owner_id=owner_id,
        title=(title or "").strip() or f"世界 {wid[-6:]}",
        created_at=time.time(),
        app_id=base.app_id,
    )
    write_meta(world_root(base, wid), meta)
    return meta


def require_world_owner(default_base: NovelAppConfig, world_id: str, owner_id: str) -> WorldMeta:
    _app_cfg, meta = locate_world(default_base, world_id)
    if meta.owner_id != owner_id:
        raise PermissionError("world_owner_mismatch")
    return meta


def update_meta_session(default_base: NovelAppConfig, world_id: str, memnet_session: str) -> None:
    app_cfg, meta = locate_world(default_base, world_id)
    meta.memnet_session = memnet_session
    write_meta(world_root(app_cfg, world_id), meta)


def delete_world_record(default_base: NovelAppConfig, world_id: str, owner_id: str) -> None:
    """Remove a world directory after verifying ownership."""
    meta = require_world_owner(default_base, world_id, owner_id)
    app_cfg = app_config_for_meta(meta, default_base)
    wdir = world_root(app_cfg, meta.world_id).output_dir
    if wdir.is_dir():
        shutil.rmtree(wdir)
