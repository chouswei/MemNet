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


_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_ALPHA_KEYWORDS: frozenset[str] | None = None


def _alpha_keywords() -> frozenset[str]:
    """Single-word GraphGlot lexer keywords (uppercase). Cached per process."""
    global _ALPHA_KEYWORDS
    if _ALPHA_KEYWORDS is None:
        raw = graphglot_dialect().Lexer.KEYWORDS
        _ALPHA_KEYWORDS = frozenset(k.upper() for k in raw if k.isalpha())
    return _ALPHA_KEYWORDS


def quote_reserved_idents(text: str) -> str:
    """Backtick-quote reserved words used as labels, rel types, or property keys.

    GraphGlot's neo4j dialect tokenises DEC / ROUND / NEXT / … as keywords.
    MemNet house labels and property names stay unquoted on the leftover
    lowering path; this rewrite is GraphGlot-parse-only.
    """
    keywords = _alpha_keywords()
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in "'\"":
            q = c
            j = i + 1
            while j < n:
                if text[j] == q:
                    if j + 1 < n and text[j + 1] == q:
                        j += 2
                        continue
                    j += 1
                    break
                if text[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                j += 1
            out.append(text[i:j])
            i = j
            continue
        if c == "`":
            j = text.find("`", i + 1)
            end = n if j < 0 else j + 1
            out.append(text[i:end])
            i = end
            continue
        if c == ":" and i + 1 < n and (text[i + 1].isalpha() or text[i + 1] == "_"):
            if i > 0 and text[i - 1] == ":":
                out.append(c)
                i += 1
                continue
            m = _IDENT.match(text, i + 1)
            if m and m.group(0).upper() in keywords:
                out.append(":`" + m.group(0) + "`")
                i = m.end()
                continue
        if c.isalpha() or c == "_":
            m = _IDENT.match(text, i)
            assert m is not None
            k = m.end()
            while k < n and text[k] in " \t":
                k += 1
            if k < n and text[k] == ":" and not (k + 1 < n and text[k + 1] == ":"):
                p = i - 1
                while p >= 0 and text[p] in " \t\n\r":
                    p -= 1
                if p >= 0 and text[p] in "{," and m.group(0).upper() in keywords:
                    out.append("`" + m.group(0) + "`")
                    i = m.end()
                    continue
            out.append(m.group(0))
            i = m.end()
            continue
        out.append(c)
        i += 1
    return "".join(out)


def parse_program(text: str) -> list[Expression]:
    """Parse one GQL program with GraphGlot. Raises GraphGlotError on failure."""
    return list(graphglot_dialect().parse(quote_reserved_idents(text)))


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
    "quote_reserved_idents",
]
