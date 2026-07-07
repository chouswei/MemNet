"""Guards against the class of bug in issue #9: a syntax error (e.g. unterminated
docstring) shipped in a released wheel because no test ever imported the module.

Every src/**/*.py file must at least parse and, for the two published packages,
import cleanly.
"""

from __future__ import annotations

import ast
import importlib
import pkgutil
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent.parent / "src"


def _all_py_files() -> list[Path]:
    return sorted(SRC_ROOT.rglob("*.py"))


def test_all_source_files_parse():
    """ast.parse must succeed for every .py file under src/ (catches unterminated
    strings, stray indentation, etc. that py_compile/import alone might mask via
    cached .pyc files)."""
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
    """Belt-and-braces: walk every submodule of the memnet package and import it,
    so a broken module can't hide behind not being explicitly named above."""
    import memnet

    failures: list[str] = []
    for module_info in pkgutil.walk_packages(memnet.__path__, prefix="memnet."):
        try:
            importlib.import_module(module_info.name)
        except Exception as exc:  # noqa: BLE001 - we want to report any import failure
            failures.append(f"{module_info.name}: {type(exc).__name__}: {exc}")
    assert not failures, "\n".join(failures)
