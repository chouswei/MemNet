"""Environment-overridable limits and paths."""

from __future__ import annotations

import os
from pathlib import Path

RESERVED_TAGS = frozenset({"SESSION", "ERR", "WRN", "STAT", "REL", "DEL"})
ORPHAN_EXEMPT_TAGS = frozenset({"LAW", "CFG", "SYS", "PLR"})
RECYCLE_INACTIVE = frozenset({"delete_on_settle", "delete_on_expire"})
ID_PATTERN = r"^[A-Za-z0-9_.-]+$"
RELATION_PATTERN = r"^[a-z][a-z0-9_]*$"
MAX_WRN_PER_CALL = 12

DEFAULT_QUERY_MAX_ROWS = 50
DEFAULT_QUERY_DEPTH = 2


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class Caps:
    max_rows: int
    max_law: int
    max_relations: int
    max_tags: int
    max_fields: int
    max_value_bytes: int
    max_line_bytes: int
    max_batch_lines: int
    max_sessions: int
    max_depth: int
    max_fanout: int
    lock_timeout_ms: int

    def __init__(self) -> None:
        self.max_rows = _env_int("MEMNET_MAX_ROWS", 5000)
        self.max_law = _env_int("MEMNET_MAX_LAW", 100)
        self.max_relations = _env_int("MEMNET_MAX_RELATIONS", 200)
        self.max_tags = _env_int("MEMNET_MAX_TAGS", 64)
        self.max_fields = _env_int("MEMNET_MAX_FIELDS", 32)
        self.max_value_bytes = _env_int("MEMNET_MAX_VALUE_BYTES", 4096)
        self.max_line_bytes = _env_int("MEMNET_MAX_LINE_BYTES", 32768)
        self.max_batch_lines = _env_int("MEMNET_MAX_BATCH_LINES", 1000)
        self.max_sessions = _env_int("MEMNET_MAX_SESSIONS", 64)
        self.max_depth = _env_int("MEMNET_MAX_DEPTH", 4)
        self.max_fanout = _env_int("MEMNET_MAX_FANOUT", 256)
        self.lock_timeout_ms = _env_int("MEMNET_LOCK_TIMEOUT_MS", 2000)


def serve_host() -> str:
    return os.environ.get("MEMNET_SERVE_HOST", "127.0.0.1")


def serve_port() -> int:
    return _env_int("MEMNET_SERVE_PORT", 18765)


def examples_dir() -> Path:
    return Path(__file__).resolve().parent / "examples"


def default_ttl_minutes() -> int:
    return _env_int("MEMNET_SESSION_TTL_MINUTES", 60)
