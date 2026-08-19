"""GraphGlot official-grammar parse front (PyPI ``graphglot``).

MemNet product gate and leftover lowering live elsewhere. This module only
calls GraphGlot ``Dialect.parse`` and names forbidden AST clauses after a
successful parse.

GraphGlot dialect id ``neo4j`` is the registered dialect that accepts
``CREATE ()``. ISO ``fullgql`` rejects that spelling (INSERT, not CREATE).
That is a package dialect name — MemNet is not Cypher.
"""

from __future__ import annotations

import re
from typing import Any

from graphglot.ast.base import Expression
from graphglot.ast.cypher import CypherWithStatement
from graphglot.ast.expressions import CallProcedureStatement, ForStatement, ReturnStatement
from graphglot.dialect import Dialect
from graphglot.error import GraphGlotError

# Registered GraphGlot dialect that parses CREATE () / labelled CREATE.
GRAPHGLOT_DIALECT_NAME = "neo4j"
GRAPHGLOT_PACKAGE = "graphglot"

_ANSI = re.compile(r"\x1b\[[0-9;]*m")

# Clause name → AST class (UNWIND lowers to ISO FOR in GraphGlot).
_FORBIDDEN: tuple[tuple[str, type[Expression]], ...] = (
    ("WITH", CypherWithStatement),
    ("UNWIND", ForStatement),
    ("CALL", CallProcedureStatement),
    ("RETURN", ReturnStatement),
)


def graphglot_dialect() -> Any:
    """Return the GraphGlot dialect used on the MemNet accept path."""
    return Dialect.get_or_raise(GRAPHGLOT_DIALECT_NAME)


def clean_graphglot_message(exc: BaseException) -> str:
    text = _ANSI.sub("", str(exc)).strip()
    if not text:
        return "GraphGlot parse failed"
    return text.splitlines()[0]


def parse_program(text: str) -> list[Expression]:
    """Parse one GQL program with GraphGlot. Raises GraphGlotError on failure."""
    return list(graphglot_dialect().parse(text))


def forbidden_clauses(program: Expression) -> list[str]:
    """Return product-forbidden clause names present in a parsed program."""
    found: list[str] = []
    for name, cls in _FORBIDDEN:
        if program.find_first(cls) is not None:
            found.append(name)
    return found


def gate_programs(programs: list[Expression]) -> str | None:
    """Return a gate message if any parsed program uses a non-product clause."""
    hit: list[str] = []
    for program in programs:
        for name in forbidden_clauses(program):
            if name not in hit:
                hit.append(name)
    if not hit:
        return None
    joined = ", ".join(hit)
    return (
        f"agent surface forbids {joined} (GraphGlot parsed; MemNet product gate). "
        "Use pin_map / bounded find / gated mutate — not free WITH / UNWIND / CALL / "
        "unbounded MATCH…RETURN"
    )


__all__ = [
    "GRAPHGLOT_DIALECT_NAME",
    "GRAPHGLOT_PACKAGE",
    "GraphGlotError",
    "clean_graphglot_message",
    "forbidden_clauses",
    "gate_programs",
    "graphglot_dialect",
    "parse_program",
]
