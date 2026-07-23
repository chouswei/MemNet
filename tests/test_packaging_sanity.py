"""Guards against shipping a broken wheel: every published package module must
parse and import cleanly.
"""

from __future__ import annotations

import ast
import importlib
import pkgutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCAN_ROOTS = (
    REPO / "parts" / "common" / "memnet" / "memnet",
    REPO / "parts" / "memnet-mcp" / "software" / "memnet_mcp",
)


def _all_py_files() -> list[Path]:
    out: list[Path] = []
    for root in SCAN_ROOTS:
        if root.is_dir():
            out.extend(sorted(root.rglob("*.py")))
    return out


def test_all_source_files_parse():
    failures: list[str] = []
    for path in _all_py_files():
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            failures.append(f"{path}: {exc}")
    assert not failures, "\n".join(failures)


def test_memnet_package_imports():
    import memnet  # noqa: F401
    import memnet.cli  # noqa: F401
    import memnet.serve  # noqa: F401
    import memnet.serve_client  # noqa: F401
    import memnet.session  # noqa: F401
    import memnet.snapshot  # noqa: F401
    import memnet.registry  # noqa: F401
    import memnet.mem_store  # noqa: F401
    import memnet.wire  # noqa: F401
    import memnet.housekeep  # noqa: F401


def test_memnet_mcp_package_imports():
    import memnet_mcp.client  # noqa: F401
    import memnet_mcp.server  # noqa: F401


def test_every_submodule_of_memnet_importable():
    import memnet

    failures: list[str] = []
    for module_info in pkgutil.walk_packages(memnet.__path__, prefix="memnet."):
        try:
            importlib.import_module(module_info.name)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{module_info.name}: {type(exc).__name__}: {exc}")
    assert not failures, "\n".join(failures)
