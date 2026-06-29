"""Bootstrap / rebootstrap MemNet novel session (shared by CLI and novel_mobile)."""

from __future__ import annotations

from typing import Any

from app_config import NovelAppConfig, repo_root
from catalog_expand import load_schema, run_catalog_expand
from chat_thread import reset_threads
from memnet.config import serve_host
from memnet_mcp.client import run_memnet

from novel_mcp.bootstrap import (
    bootstrap_from_md,
    catalog_lines_from_md,
    catalog_path_from_seed_md,
    ingest_lines,
)
from novel_mcp.catalog_schema import CatalogSchema
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
) -> dict[str, Any]:
    """Open a fresh graph session from seed, ingest catalog, reset chat threads."""
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
    if config.catalog_schema:
        schema_rel = str(config.catalog_schema.relative_to(root)).replace("\\", "/")
        code, errs = graph_update(
            sid,
            [f"@USR: USR69|catalog_schema|{schema_rel}|persistent"],
        )
        if code != 0:
            return {"exit_code": 2, "errors": errs or ["catalog_schema graph_update failed"]}
        schema = CatalogSchema.load_json(config.catalog_schema)

    catalog_lines = 0
    catalog_path = catalog_path_from_seed_md(seed_path, root)
    if catalog_path and catalog_path.is_file():
        cat_lines = catalog_lines_from_md(catalog_path, schema)
        cat_boot = ingest_lines(sid, cat_lines)
        if cat_boot.get("exit_code", 1) != 0:
            return {
                "exit_code": cat_boot.get("exit_code", 1),
                "errors": cat_boot.get("errors", []),
            }
        catalog_lines = int(cat_boot.get("lines", 0))
        if schema is not None:
            burn_sync = sync_art_neili_burn(sid, schema)
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
    if do_expand:
        if schema is None:
            schema = load_schema(config)
        try:
            expand_result = run_catalog_expand(
                sid, schema=schema, target=target, seed=seed, config=config
            )
        except RuntimeError as err:
            return {"exit_code": 2, "errors": [str(err)]}
        if expand_result.get("exit_code", 1) != 0:
            return {
                "exit_code": expand_result.get("exit_code", 2),
                "errors": expand_result.get("errors", []),
                "catalog_expand": expand_result,
            }

    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.session_id_file.write_text(sid + "\n", encoding="utf-8")
    reset_threads(config)
    if clear_last_beat and config.last_beat_file.is_file():
        config.last_beat_file.unlink()

    save = run_memnet(["session", "save", "--file", str(config.snapshot_file)], session=sid)
    if save.exit_code != 0:
        return {"exit_code": save.exit_code, "errors": save.errors or ["session save failed"]}

    setup = read_player_setup(sid)
    art_count = len(arts_from_session(sid, schema)) if schema else 0
    return {
        "exit_code": 0,
        "session_id": sid,
        "serve_host": serve_host(),
        "player_setup": setup,
        "seed_lines": boot.get("seed_lines"),
        "catalog_lines": catalog_lines,
        "catalog_art_count": art_count,
        "catalog_expand": expand_result,
        "threads_reset": True,
        "last_beat_cleared": clear_last_beat,
    }
