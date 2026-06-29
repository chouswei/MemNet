"""Skill catalog background graph — separate MemNet session from story play state.

Generic: one @ART row = one skill entry (武學、魔法、異能…). Sub-types (slots, kinds,
tiers, labels) come from ``catalog_specs/*.json`` + seed ``setup_scene_{slot}`` — not Python.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from memnet_mcp.client import run_memnet

from novel_mcp.bootstrap import catalog_lines_from_md, ingest_lines
from novel_mcp.catalog_schema import CatalogSchema
from novel_mcp.skill_catalog_keys import (
    SKILL_CATALOG_SESSION_KEY,
    read_skill_catalog_md_rel,
    read_skill_catalog_session_from_story,
)
from novel_mcp.setup_constants import SENTINEL
from novel_mcp.setup_graph import ensure_usr_row, graph_update, read_usr_by_key
from novel_mcp.paths import workspace_root

_SESSION_RE = re.compile(r"^@SESSION:\s*(\S+)")


def _arts_from_session(session: str | None, schema: CatalogSchema) -> list[dict[str, str]]:
    from novel_mcp.opening_loadout import arts_from_session

    return arts_from_session(session, schema)


def catalog_schema_key(schema_path: Path) -> str:
    return schema_path.stem


def catalog_store_dir(
    schema_path: Path,
    *,
    workspace_root_path: str | Path | None = None,
) -> Path:
    root = workspace_root(workspace_root_path)
    return root / "novel-output" / "catalogs" / catalog_schema_key(schema_path)


def catalog_session_id_file(
    schema_path: Path,
    *,
    workspace_root_path: str | Path | None = None,
) -> Path:
    return catalog_store_dir(schema_path, workspace_root_path=workspace_root_path) / "catalog_session_id.txt"


def catalog_snapshot_file(
    schema_path: Path,
    *,
    workspace_root_path: str | Path | None = None,
) -> Path:
    return catalog_store_dir(schema_path, workspace_root_path=workspace_root_path) / "catalog_snap.json"


def catalog_tag_map_lines(schema: CatalogSchema) -> list[str]:
    cols = "|".join(schema.wire_columns)
    return [
        f"@ART: {cols}",
        "@CFG: id|標題|錨點|版本|回收",
    ]


def _parse_session_current(stdout: str) -> str | None:
    for line in stdout.splitlines():
        m = _SESSION_RE.match(line.strip())
        if m:
            sid = m.group(1).split("|", 1)[0].strip()
            return sid if sid and sid != "none" else None
    return None


def session_is_live(session_id: str) -> bool:
    resp = run_memnet(["session", "current"], session=session_id)
    return _parse_session_current(resp.stdout or "") == session_id


def read_catalog_session_id_file(
    schema_path: Path,
    *,
    workspace_root_path: str | Path | None = None,
) -> str | None:
    path = catalog_session_id_file(schema_path, workspace_root_path=workspace_root_path)
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        sid = line.strip()
        if sid.startswith("mn_"):
            return sid
    return None


def resolve_catalog_session_id(
    story_session: str | None,
    schema: CatalogSchema | None,
    *,
    schema_path: Path | None = None,
    workspace_root_path: str | Path | None = None,
) -> str | None:
    """Catalog session id: story USR skill_catalog_session (or legacy martial_*), then store file."""
    if story_session:
        linked = read_skill_catalog_session_from_story(story_session)
        if linked:
            return linked
    if schema_path is not None:
        return read_catalog_session_id_file(
            schema_path, workspace_root_path=workspace_root_path
        )
    if story_session and schema is not None:
        rel = read_usr_by_key(story_session, "catalog_schema")
        if rel and rel not in (SENTINEL, "_"):
            root = workspace_root(workspace_root_path)
            sp = root / rel.replace("\\", "/")
            if sp.is_file():
                return read_catalog_session_id_file(sp, workspace_root_path=workspace_root_path)
    return None


def link_skill_catalog_session(story_session: str, catalog_session_id: str) -> dict[str, Any]:
    uid = ensure_usr_row(
        story_session,
        SKILL_CATALOG_SESSION_KEY,
        initial=SENTINEL,
    )
    code, errs = graph_update(
        story_session,
        [
            f"@USR: {uid}|{SKILL_CATALOG_SESSION_KEY}|{catalog_session_id}|persistent",
        ],
    )
    if code != 0:
        return {"exit_code": code, "errors": errs or ["link catalog session failed"]}
    return {"exit_code": 0, "catalog_session": catalog_session_id}


def link_martial_catalog_session(story_session: str, catalog_session_id: str) -> dict[str, Any]:
    """Legacy name — use :func:`link_skill_catalog_session`."""
    return link_skill_catalog_session(story_session, catalog_session_id)


def _try_load_catalog_snapshot(session_id: str, snap_path: Path) -> bool:
    if not snap_path.is_file():
        return False
    load = run_memnet(
        ["session", "load", "--file", str(snap_path), "--keep-id"],
        session=session_id,
    )
    return load.exit_code == 0 and session_is_live(session_id)


def bootstrap_catalog_session(
    catalog_md: Path,
    schema: CatalogSchema,
    *,
    schema_path: Path,
    workspace_root_path: str | Path | None = None,
) -> dict[str, Any]:
    """Open a fresh catalog-only session and ingest @ART rows from markdown."""
    if not catalog_md.is_file():
        return {"exit_code": 2, "errors": [f"catalog not found: {catalog_md}"]}

    map_lines = catalog_tag_map_lines(schema)
    argv = ["session", "open"]
    for line in map_lines:
        argv.extend(["--map", line])
    open_resp = run_memnet(argv)
    if open_resp.exit_code != 0:
        return {
            "exit_code": open_resp.exit_code,
            "errors": open_resp.errors,
        }

    sid = open_resp.session_id
    cat_lines = catalog_lines_from_md(catalog_md, schema)
    ing = ingest_lines(sid, cat_lines)
    if ing.get("exit_code", 1) != 0:
        return {
            "exit_code": ing.get("exit_code", 2),
            "errors": ing.get("errors", ["catalog ingest failed"]),
            "session_id": sid,
        }

    store = catalog_store_dir(schema_path, workspace_root_path=workspace_root_path)
    store.mkdir(parents=True, exist_ok=True)
    snap = catalog_snapshot_file(schema_path, workspace_root_path=workspace_root_path)
    save = run_memnet(["session", "save", "--file", str(snap)], session=sid)
    if save.exit_code != 0:
        return {
            "exit_code": save.exit_code,
            "errors": save.errors or ["catalog session save failed"],
            "session_id": sid,
        }

    id_file = catalog_session_id_file(schema_path, workspace_root_path=workspace_root_path)
    id_file.write_text(sid + "\n", encoding="utf-8")

    return {
        "exit_code": 0,
        "session_id": sid,
        "catalog_lines": len(cat_lines),
        "catalog_art_count": len(_arts_from_session(sid, schema)),
        "catalog_session_id_file": str(id_file),
        "catalog_snapshot_file": str(snap),
        "bootstrapped": True,
    }


def ensure_catalog_session(
    catalog_md: Path,
    schema: CatalogSchema,
    *,
    schema_path: Path,
    workspace_root_path: str | Path | None = None,
    force_rebootstrap: bool = False,
) -> dict[str, Any]:
    """Return live catalog session id; bootstrap or reload snapshot when missing."""
    snap = catalog_snapshot_file(schema_path, workspace_root_path=workspace_root_path)

    if not force_rebootstrap:
        existing = read_catalog_session_id_file(
            schema_path, workspace_root_path=workspace_root_path
        )
        if existing:
            if session_is_live(existing):
                return {
                    "exit_code": 0,
                    "session_id": existing,
                    "bootstrapped": False,
                    "catalog_art_count": len(_arts_from_session(existing, schema)),
                }
            if _try_load_catalog_snapshot(existing, snap) and session_is_live(existing):
                return {
                    "exit_code": 0,
                    "session_id": existing,
                    "bootstrapped": False,
                    "reloaded": True,
                    "catalog_art_count": len(_arts_from_session(existing, schema)),
                }

    return bootstrap_catalog_session(
        catalog_md,
        schema,
        schema_path=schema_path,
        workspace_root_path=workspace_root_path,
    )


def resolve_catalog_md_for_story(
    story_session: str | None,
    *,
    seed_md: Path | None = None,
    workspace_root_path: str | Path | None = None,
) -> Path | None:
    from novel_mcp.bootstrap import catalog_path_from_seed_md

    root = workspace_root(workspace_root_path)
    if story_session:
        rel = read_skill_catalog_md_rel(story_session)
        if rel and rel not in (SENTINEL, "_"):
            return root / rel.replace("\\", "/")
    if seed_md and seed_md.is_file():
        return catalog_path_from_seed_md(seed_md, root)
    return None
