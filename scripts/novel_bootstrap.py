"""Bootstrap any novel session from an application-notes markdown seed."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "applications" / "novel_cursor"))

from app_config import load_config, repo_root  # noqa: E402
from catalog_expand import load_schema, run_catalog_expand  # noqa: E402
from chat_thread import reset_threads  # noqa: E402
from memnet.config import serve_host  # noqa: E402
from memnet_mcp.client import run_memnet  # noqa: E402
from novel_mcp.bootstrap import (  # noqa: E402
    bootstrap_from_md,
    catalog_lines_from_md,
    catalog_path_from_seed_md,
    ingest_lines,
)
from novel_mcp.catalog_schema import CatalogSchema  # noqa: E402
from novel_mcp.opening_loadout import arts_from_session  # noqa: E402
from novel_mcp.player_setup import read_player_setup  # noqa: E402
from novel_mcp.setup_graph import graph_update  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap novel session from seed md")
    parser.add_argument("--app", required=True, metavar="SLUG", help="Instance slug")
    parser.add_argument(
        "--expand-catalog",
        action="store_true",
        help="After base catalog ingest, call LLM to grow @ART on graph",
    )
    parser.add_argument(
        "--no-expand-catalog",
        action="store_true",
        help="Disable expand even if instance json has expand_catalog=true",
    )
    parser.add_argument("--expand-target", type=int, metavar="N", help="Target @ART count")
    parser.add_argument("--expand-seed", type=int, metavar="N", help="LLM reproducibility hint")
    args = parser.parse_args()

    config = load_config(app_id=args.app)
    seed_path = config.seed_md
    root = repo_root()

    boot = bootstrap_from_md(seed_path)
    if boot.get("exit_code", 1) != 0:
        print(json.dumps(boot, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(boot.get("exit_code", 1))

    sid = boot["session_id"]
    schema: CatalogSchema | None = None
    if config.catalog_schema:
        schema_rel = str(config.catalog_schema.relative_to(root)).replace("\\", "/")
        code, errs = graph_update(
            sid,
            [f"@USR: USR69|catalog_schema|{schema_rel}|persistent"],
        )
        if code != 0:
            print(json.dumps({"exit_code": 2, "errors": errs}, ensure_ascii=False), file=sys.stderr)
            raise SystemExit(2)
        schema = CatalogSchema.load_json(config.catalog_schema)

    catalog_path = catalog_path_from_seed_md(seed_path, root)
    if catalog_path and catalog_path.is_file():
        cat_lines = catalog_lines_from_md(catalog_path, schema)
        cat_boot = ingest_lines(sid, cat_lines)
        if cat_boot.get("exit_code", 1) != 0:
            print(json.dumps(cat_boot, ensure_ascii=False, indent=2), file=sys.stderr)
            raise SystemExit(cat_boot.get("exit_code", 1))
        boot["catalog_lines"] = cat_boot.get("lines", 0)

    do_expand = config.expand_catalog and not args.no_expand_catalog
    if args.expand_catalog:
        do_expand = True
    target = args.expand_target if args.expand_target is not None else config.expand_catalog_target
    seed = args.expand_seed if args.expand_seed is not None else config.expand_catalog_seed

    expand_result: dict | None = None
    if do_expand:
        if schema is None:
            schema = load_schema(config)
        try:
            expand_result = run_catalog_expand(
                sid, schema=schema, target=target, seed=seed, config=config
            )
        except RuntimeError as err:
            print(json.dumps({"exit_code": 2, "errors": [str(err)]}, ensure_ascii=False), file=sys.stderr)
            raise SystemExit(2)
        if expand_result.get("exit_code", 1) != 0:
            print(json.dumps(expand_result, ensure_ascii=False, indent=2), file=sys.stderr)
            raise SystemExit(expand_result.get("exit_code", 2))
        boot["catalog_expand"] = expand_result

    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.session_id_file.write_text(sid + "\n", encoding="utf-8")
    reset_threads(config)
    save = run_memnet(["session", "save", "--file", str(config.snapshot_file)], session=sid)
    if save.exit_code != 0:
        print(json.dumps({"save": save.errors}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(save.exit_code)

    setup = read_player_setup(sid)
    art_count = len(arts_from_session(sid, schema)) if schema else 0
    out = {
        "session_id": sid,
        "serve_host": serve_host(),
        "exit_code": 0,
        "player_setup": {
            "profile": setup.get("profile"),
            "loadout": {
                "next_slot": setup.get("loadout", {}).get("next_slot"),
                "complete": setup.get("loadout", {}).get("complete"),
            },
            "setup_complete": setup.get("setup_complete"),
            "setup_guidance": {
                "next_action": setup.get("setup_guidance", {}).get("next_action"),
            },
        },
        "seed_lines": boot.get("seed_lines"),
        "catalog_lines": boot.get("catalog_lines", 0),
        "catalog_art_count": art_count,
        "catalog_expand": expand_result,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
