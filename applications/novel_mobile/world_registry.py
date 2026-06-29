"""World registry — user-owned worlds, each with its own MemNet session."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app_config import NovelAppConfig

from novel_mobile.world_slot import normalise_world_id, world_root, worlds_base_dir


@dataclass
class WorldMeta:
    world_id: str
    owner_id: str
    title: str
    created_at: float
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
    return WorldMeta(
        world_id=wid,
        owner_id=owner,
        title=str(data.get("title") or wid),
        created_at=float(data.get("created_at") or 0),
        memnet_session=str(data.get("memnet_session") or "").strip() or None,
    )


def _world_summary(base: NovelAppConfig, meta: WorldMeta) -> dict[str, Any]:
    wcfg = world_root(base, meta.world_id)
    has_session = wcfg.session_id_file.is_file()
    session: str | None = None
    if has_session:
        line = wcfg.session_id_file.read_text(encoding="utf-8").strip().splitlines()
        if line and line[0].startswith("mn_"):
            session = line[0].strip()
    return {
        "world_id": meta.world_id,
        "title": meta.title,
        "created_at": meta.created_at,
        "has_session": has_session,
        "memnet_session": session,
    }


def list_worlds_for_owner(base: NovelAppConfig, owner_id: str) -> list[dict[str, Any]]:
    root = worlds_base_dir(base)
    if not root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        meta = read_meta(base, child.name)
        if meta and meta.owner_id == owner_id:
            out.append(_world_summary(base, meta))
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
    )
    write_meta(world_root(base, wid), meta)
    return meta


def require_world_owner(base: NovelAppConfig, world_id: str, owner_id: str) -> WorldMeta:
    meta = read_meta(base, world_id)
    if meta is None:
        raise FileNotFoundError(world_id)
    if meta.owner_id != owner_id:
        raise PermissionError("world_owner_mismatch")
    return meta


def update_meta_session(base: NovelAppConfig, world_id: str, memnet_session: str) -> None:
    meta = read_meta(base, world_id)
    if meta is None:
        return
    meta.memnet_session = memnet_session
    write_meta(world_root(base, world_id), meta)
