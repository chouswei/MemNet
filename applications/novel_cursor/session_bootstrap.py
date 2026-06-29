"""Bootstrap / rebootstrap MemNet novel session (shared by CLI and novel_mobile)."""

from __future__ import annotations

from typing import Any

from app_config import NovelAppConfig, repo_root
from catalog_expand import load_schema, run_catalog_expand
from chat_thread import reset_threads
from memnet.config import serve_host
from memnet_mcp.client import run_memnet

from novel_mcp.bootstrap import bootstrap_from_md, catalog_path_from_seed_md
from novel_mcp.catalog_schema import CatalogSchema
from novel_mcp.catalog_session import (
    ensure_catalog_session,
    link_skill_catalog_session,
    resolve_catalog_md_for_story,
)
from novel_mcp.martial_catalog_expand import sync_art_neili_burn
from novel_mcp.opening_loadout import arts_from_session
from novel_mcp.player_setup import read_player_setup
from novel_mcp.setup_graph import graph_update


def rebootstrap_session(
    config: NovelAppConfig,
    *,
    expand_catalog: bool | None = None,
    expand_target: int | None = None,
    expand_seed: int | None = None,
    clear_last_beat: bool = True,
    force_catalog_rebootstrap: bool = False,
) -> dict[str, Any]:
    """Open a fresh story session; attach or create genre catalog session."""
    root = repo_root()
    seed_path = config.seed_md

    boot = bootstrap_from_md(seed_path)
    if boot.get("exit_code", 1) != 0:
        return {
            "exit_code": boot.get("exit_code", 1),
            "errors": boot.get("errors", []),
            "stderr": boot.get("stderr"),
        }

    sid = boot["session_id"]
    schema: CatalogSchema | None = None
    schema_path = config.catalog_schema
    if schema_path:
        schema_rel = str(schema_path.relative_to(root)).replace("\\", "/")
        code, errs = graph_update(
            sid,
            [f"@USR: USR69|catalog_schema|{schema_rel}|persistent"],
        )
        if code != 0:
            return {"exit_code": 2, "errors": errs or ["catalog_schema graph_update failed"]}
        schema = CatalogSchema.load_json(schema_path)

    catalog_session_id: str | None = None
    catalog_lines = 0
    catalog_art_count = 0
    catalog_boot: dict[str, Any] | None = None

    if schema and schema_path:
        catalog_md = resolve_catalog_md_for_story(sid, seed_md=seed_path)
        if catalog_md is None or not catalog_md.is_file():
            catalog_md = catalog_path_from_seed_md(seed_path, root)
        if catalog_md and catalog_md.is_file():
            catalog_boot = ensure_catalog_session(
                catalog_md,
                schema,
                schema_path=schema_path,
                force_rebootstrap=force_catalog_rebootstrap,
            )
            if catalog_boot.get("exit_code", 1) != 0:
                return {
                    "exit_code": catalog_boot.get("exit_code", 2),
                    "errors": catalog_boot.get("errors", ["catalog bootstrap failed"]),
                    "catalog_bootstrap": catalog_boot,
                }
            catalog_session_id = catalog_boot["session_id"]
            catalog_lines = int(catalog_boot.get("catalog_lines", 0))
            catalog_art_count = int(
                catalog_boot.get("catalog_art_count")
                or len(arts_from_session(catalog_session_id, schema))
            )
            link = link_skill_catalog_session(sid, catalog_session_id)
            if link.get("exit_code", 0) != 0:
                return {
                    "exit_code": link.get("exit_code", 2),
                    "errors": link.get("errors", ["link catalog session failed"]),
                }
            burn_sync = sync_art_neili_burn(sid, schema, art_session=catalog_session_id)
            if burn_sync.get("exit_code", 0) != 0:
                return {
                    "exit_code": burn_sync.get("exit_code", 2),
                    "errors": burn_sync.get("errors", ["burn sync failed"]),
                }

    do_expand = bool(config.expand_catalog) if expand_catalog is None else expand_catalog
    target = (
        expand_target if expand_target is not None else config.expand_catalog_target
    )
    seed = expand_seed if expand_seed is not None else config.expand_catalog_seed

    expand_result: dict[str, Any] | None = None
    if do_expand and schema and catalog_session_id:
        try:
            expand_result = run_catalog_expand(
                catalog_session_id,
                schema=schema,
                target=target,
                seed=seed,
                config=config,
            )
        except RuntimeError as err:
            return {"exit_code": 2, "errors": [str(err)]}
        if expand_result.get("exit_code", 1) != 0:
            return {
                "exit_code": expand_result.get("exit_code", 2),
                "errors": expand_result.get("errors", []),
                "catalog_expand": expand_result,
            }
        catalog_art_count = int(expand_result.get("art_count", catalog_art_count))
        burn_sync = sync_art_neili_burn(sid, schema, art_session=catalog_session_id)
        if burn_sync.get("exit_code", 0) != 0:
            return {
                "exit_code": burn_sync.get("exit_code", 2),
                "errors": burn_sync.get("errors", ["post-expand burn sync failed"]),
            }
        if config.catalog_snapshot_file:
            run_memnet(
                ["session", "save", "--file", str(config.catalog_snapshot_file)],
                session=catalog_session_id,
            )

    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.session_id_file.write_text(sid + "\n", encoding="utf-8")
    reset_threads(config)
    if clear_last_beat and config.last_beat_file.is_file():
        config.last_beat_file.unlink()

    save = run_memnet(["session", "save", "--file", str(config.snapshot_file)], session=sid)
    if save.exit_code != 0:
        return {"exit_code": save.exit_code, "errors": save.errors or ["session save failed"]}

    setup = read_player_setup(sid)
    return {
        "exit_code": 0,
        "session_id": sid,
        "catalog_session_id": catalog_session_id,
        "serve_host": serve_host(),
        "player_setup": setup,
        "seed_lines": boot.get("seed_lines"),
        "catalog_lines": catalog_lines,
        "catalog_art_count": catalog_art_count,
        "catalog_bootstrap": catalog_boot,
        "catalog_expand": expand_result,
        "threads_reset": True,
        "last_beat_cleared": clear_last_beat,
    }
