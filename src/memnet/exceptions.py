"""MemNet errors with wire-format exit codes."""

from __future__ import annotations


class MemNetError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        example: str | None = None,
        exit_code: int = 1,
    ) -> None:
        self.code = code
        self.message = message
        self.example = example
        self.exit_code = exit_code
        super().__init__(message)
