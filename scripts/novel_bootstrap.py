"""Bootstrap any novel session from an application-notes markdown seed."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "applications" / "novel_cursor"))

from app_config import load_config  # noqa: E402
from session_bootstrap import rebootstrap_session  # noqa: E402


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
    expand: bool | None = None
    if args.expand_catalog:
        expand = True
    elif args.no_expand_catalog:
        expand = False

    out = rebootstrap_session(
        config,
        expand_catalog=expand,
        expand_target=args.expand_target,
        expand_seed=args.expand_seed,
    )
    if out.get("exit_code", 1) != 0:
        print(json.dumps(out, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(out.get("exit_code", 1))

    setup = out.get("player_setup") or {}
    print(
        json.dumps(
            {
                "session_id": out["session_id"],
                "serve_host": out.get("serve_host"),
                "exit_code": 0,
                "player_setup": {
                    "profile": setup.get("profile"),
                    "loadout": {
                        "next_slot": (setup.get("loadout") or {}).get("next_slot"),
                        "complete": (setup.get("loadout") or {}).get("complete"),
                    },
                    "setup_complete": setup.get("setup_complete"),
                    "setup_guidance": {
                        "next_action": (setup.get("setup_guidance") or {}).get(
                            "next_action"
                        ),
                    },
                },
                "seed_lines": out.get("seed_lines"),
                "catalog_lines": out.get("catalog_lines", 0),
                "catalog_art_count": out.get("catalog_art_count"),
                "catalog_expand": out.get("catalog_expand"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
