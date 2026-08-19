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
# 0.11 session outline: Browser-style LIMIT k exemplars per kind (one hard LIMIT).
OUTLINE_EXEMPLAR_LIMIT = 3


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


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
    # CapsPolicy ACL TARGET flags — engineAclShipped matches live gates
    acl_who_check: bool
    acl_pin_map_vs_mutate: bool
    acl_worker_write_scope_hard_reject: bool
    acl_optional_bind_match: bool
    engine_acl_shipped: bool
    acl_default_enabled: bool

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
        # Honest shipped ACL cut (who / pin_map-vs-mutate / scope / bind)
        self.acl_who_check = True
        self.acl_pin_map_vs_mutate = True
        self.acl_worker_write_scope_hard_reject = True
        self.acl_optional_bind_match = True
        self.engine_acl_shipped = True
        # Optional force-enable ACL on newly opened sessions
        self.acl_default_enabled = _env_bool("MEMNET_ACL", False)


DEFAULT_SERVE_MAX_FRAME_BYTES = 4 * 1024 * 1024  # 4 MiB


def serve_host() -> str:
    return os.environ.get("MEMNET_SERVE_HOST", "127.0.0.1")


def serve_port() -> int:
    return _env_int("MEMNET_SERVE_PORT", 18765)


def serve_max_frame_bytes() -> int:
    return _env_int("MEMNET_SERVE_MAX_FRAME_BYTES", DEFAULT_SERVE_MAX_FRAME_BYTES)


def serve_allow_remote() -> bool:
    raw = os.environ.get("MEMNET_SERVE_ALLOW_REMOTE", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def ipc_socket_path() -> str | None:
    """AF_UNIX socket path for LocalIpcGateway (MN-REQ-06.2).

    Env: ``MEMNET_IPC_SOCKET``. When unset, clients stay on TCP ``memnet serve``.
    """
    raw = os.environ.get("MEMNET_IPC_SOCKET", "").strip()
    return raw or None


def default_ipc_socket_path() -> str:
    """Default path when ``memnet serve --ipc`` runs without ``MEMNET_IPC_SOCKET``."""
    runtime = os.environ.get("XDG_RUNTIME_DIR", "").strip()
    if runtime:
        return str(Path(runtime) / "memnet.sock")
    try:
        uid = os.getuid()
    except AttributeError:
        uid = os.getpid()
    return f"/tmp/memnet-{uid}.sock"


def examples_dir() -> Path:
    return Path(__file__).resolve().parent / "examples"


def default_ttl_minutes() -> int:
    return _env_int("MEMNET_SESSION_TTL_MINUTES", 60)
