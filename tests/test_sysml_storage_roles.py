"""Merge bar: the durable cabinet is gone from code and model alike.

The cabinet client (``memnet.durable``) had no runtime caller and is removed.
The model says so with ``MemNetSystem.durableCabinetShipped = false`` and no
``DurableBuffer``. An AST scan keeps a hydrate/flush caller from coming back
outside ``tests/`` without the model changing with it.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "sysml-models" / "models" / "deploy.sysml"
PKG = ROOT / "parts" / "common" / "memnet" / "memnet"

# Former public hydrate/flush entry points of the removed cabinet.
ENTRY_POINTS = frozenset(
    {
        "hydrate_from_durable",
        "flush_to_durable",
        "hydrate_into_session",
        "flush_from_session",
    }
)
SKIP_PARTS = frozenset(
    {
        ".git",
        ".venv",
        "__pycache__",
        "node_modules",
        "tests",
        "refs",
    }
)


def _non_test_callers() -> set[str]:
    found: set[str] = set()
    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT)
        if any(part in SKIP_PARTS for part in rel.parts):
            continue
        # utf-8-sig strips a leading BOM so a seed script can be scanned.
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(rel))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = getattr(func, "attr", None) or getattr(func, "id", None)
                if name in ENTRY_POINTS:
                    found.add(f"{rel.as_posix()}:{node.lineno}")
    return found


def test_no_durable_package():
    assert not list((PKG / "durable").glob("*.py"))
    assert not (PKG / "session_lifecycle.py").exists()


def test_model_has_no_durable_cabinet():
    text = DEPLOY.read_text(encoding="utf-8")
    assert "attribute durableCabinetShipped : Boolean = false;" in text
    assert not re.search(r"^  part def DurableBuffer\b", text, re.M)
    assert "hydrateFlushCallers" not in text
    assert "part durable :" not in text


def test_no_hydrate_flush_caller_outside_tests():
    assert _non_test_callers() == set()
