"""Merge bar: DurableBuffer.hydrateFlushCallers matches non-test callers.

``tests`` means no caller outside ``tests/``. The model value is parsed
from ``deploy.sysml`` so the string and the scan cannot drift.
A non-empty caller set is encoded as comma-sorted
``path:qualname`` labels (repo-relative, POSIX).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "sysml-models" / "models" / "deploy.sysml"

# Public hydrate/flush entry points. Definitions are not callers.
# The SessionLifecycle wrappers delegate to DurableSyncOwner; that
# delegation is the entry body, not a second product caller.
ENTRY_POINTS = frozenset(
    {
        "hydrate_from_durable",
        "flush_to_durable",
        "hydrate_into_session",
        "flush_from_session",
    }
)
DELEGATES = {
    "hydrate_from_durable": "hydrate_into_session",
    "flush_to_durable": "flush_from_session",
}
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
_CALLERS_ATTR = re.compile(r'attribute hydrateFlushCallers : String = "([^"]*)";')


def _model_hydrate_flush_callers() -> str:
    text = DEPLOY.read_text(encoding="utf-8")
    found = _CALLERS_ATTR.findall(text)
    assert len(found) == 1, (
        f"deploy.sysml must declare hydrateFlushCallers exactly once, found {found}"
    )
    return found[0]


def _call_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


class _CallerScan(ast.NodeVisitor):
    def __init__(self, rel: str) -> None:
        self.rel = rel
        self.stack: list[str] = []
        self.callers: set[str] = set()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node.func)
        owner = self.stack[-1] if self.stack else "<module>"
        if name in ENTRY_POINTS and DELEGATES.get(owner) != name:
            qual = ".".join(self.stack) if self.stack else "<module>"
            self.callers.add(f"{self.rel}:{qual}")
        self.generic_visit(node)


def _encode(callers: set[str]) -> str:
    if not callers:
        return "tests"
    return ",".join(sorted(callers))


def _non_test_caller_set() -> set[str]:
    found: set[str] = set()
    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT)
        if any(part in SKIP_PARTS for part in rel.parts):
            continue
        # utf-8-sig strips a leading BOM so a seed script can be scanned.
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(rel))
        scan = _CallerScan(rel.as_posix())
        scan.visit(tree)
        found |= scan.callers
    return found


def test_hydrate_flush_callers_match_model():
    expected = _model_hydrate_flush_callers()
    found = _non_test_caller_set()
    assert _encode(found) == expected, (
        f"hydrateFlushCallers={expected!r} but non-test callers are {sorted(found)}"
    )
