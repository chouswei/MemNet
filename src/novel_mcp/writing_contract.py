"""Compile per-beat writing contract from MemNet warm (novel-writer layer).

Deprecated: use ``novel_mcp.presentation.compile_presentation``.
"""

from __future__ import annotations

from typing import Any

from novel_mcp.presentation import compile_presentation, compile_writing_contract as _compile

__all__ = ["compile_writing_contract", "compile_presentation"]


def compile_writing_contract(
    warm_stdout: str,
    pipeline: dict[str, Any],
    *,
    warm_walk: str | None = None,
) -> list[str]:
    return _compile(warm_stdout, pipeline, warm_walk=warm_walk)
