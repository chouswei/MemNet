"""Environment-overridable limits and paths."""

from __future__ import annotations

import os
import re
from pathlib import Path

from memnet.exceptions import MemNetError

RESERVED_TAGS = frozenset({"SESSION", "ERR", "WRN", "STAT", "REL", "DEL"})
ORPHAN_EXEMPT_TAGS = frozenset({"LAW", "CFG", "SYS", "PLR"})
RECYCLE_INACTIVE = frozenset({"delete_on_settle", "delete_on_expire"})
ID_PATTERN = r"^[A-Za-z0-9_.-]+$"
# The one relation-name rule for every write path: lowerCamel (inFile), UPPER_SNAKE
# (HAS_FACT), Mixed_1. Accepted names are then folded to one standard spelling by
# ``standard_relation``; stored, saved and returned names are always standard.
RELATION_BODY = r"[A-Za-z][A-Za-z0-9_]*"
RELATION_PATTERN = rf"^{RELATION_BODY}$"
RELATION_RE = re.compile(RELATION_PATTERN)
# Saved-snapshot check stays strict lowerCamel (unchanged since 0.19.x).
SNAPSHOT_RELATION_PATTERN = r"^[a-z][a-zA-Z0-9_]*$"
_SNAPSHOT_RELATION_RE = re.compile(SNAPSHOT_RELATION_PATTERN)
_UPPER_SNAKE_RE = re.compile(r"[A-Z][A-Z0-9_]*")


def validate_relation(name: str) -> None:
    """Single relation-name check for write, restore and seed loaders."""
    if not RELATION_RE.fullmatch(name):
        raise MemNetError(
            "invalid_relation",
            f"relation {name!r} must match {RELATION_PATTERN}",
        )


def standard_relation(name: str) -> str:
    """Fold a relation name to its standard spelling (the one normalization point).

    All upper case -> lowerCamel (HAS_FACT -> hasFact); any other name keeps its
    spelling but a leading capital is lowered (Mixed_1 -> mixed_1). Names that are
    not valid relation names are returned unchanged for ``validate_relation``.
    """
    if not name or not RELATION_RE.fullmatch(name):
        return name
    if _UPPER_SNAKE_RE.fullmatch(name):
        head, *rest = [p for p in name.lower().split("_") if p]
        return head + "".join(p[0].upper() + p[1:] for p in rest)
    return name[0].lower() + name[1:]


def normalize_relation(name: str) -> str:
    """Validate then fold: the entry point for write paths."""
    validate_relation(name)
    return standard_relation(name)


def validate_snapshot_relation(name: str) -> None:
    """Strict check for names written to a snapshot (standard names only)."""
    if not _SNAPSHOT_RELATION_RE.fullmatch(name):
        raise MemNetError(
            "invalid_relation",
            f"relation {name!r} must match {SNAPSHOT_RELATION_PATTERN}",
        )


MAX_WRN_PER_CALL = 12

DEFAULT_QUERY_MAX_ROWS = 50
DEFAULT_QUERY_DEPTH = 2
# Path-B ingest: a pin is a node. One node/pin budget; one edge budget.
DEFAULT_INGEST_MAX_NODES = 2000
DEFAULT_INGEST_MAX_EDGES = 2000
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
    """Process resource and query caps.

    Concurrent named sessions default to 1024 (``MEMNET_MAX_SESSIONS``).
    """

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
        self.max_fields = _env_int("MEMNET_MAX_FIELDS", 64)
        self.max_value_bytes = _env_int("MEMNET_MAX_VALUE_BYTES", 4096)
        self.max_line_bytes = _env_int("MEMNET_MAX_LINE_BYTES", 32768)
        self.max_batch_lines = _env_int("MEMNET_MAX_BATCH_LINES", 1000)
        self.max_sessions = _env_int("MEMNET_MAX_SESSIONS", 1024)
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
        self.save_on_expire = save_on_expire()
        self.expire_snapshot_dir = expire_snapshot_dir()


DEFAULT_SERVE_MAX_FRAME_BYTES = 4 * 1024 * 1024  # 4 MiB


def serve_host() -> str:
    return os.environ.get("MEMNET_SERVE_HOST", "127.0.0.1")


def serve_port() -> int:
    return _env_int("MEMNET_SERVE_PORT", 18765)


def serve_max_frame_bytes() -> int:
    return _env_int("MEMNET_SERVE_MAX_FRAME_BYTES", DEFAULT_SERVE_MAX_FRAME_BYTES)


def request_log_path() -> str | None:
    """JSONL per-request log file for ``memnet serve``. Env ``MEMNET_REQUEST_LOG``; off when unset."""
    raw = os.environ.get("MEMNET_REQUEST_LOG", "").strip()
    return raw or None


def request_log_max_bytes() -> int:
    return _env_int("MEMNET_REQUEST_LOG_MAX_BYTES", 10 * 1024 * 1024)


def request_log_backups() -> int:
    return _env_int("MEMNET_REQUEST_LOG_BACKUPS", 3)


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


def save_on_expire() -> bool:
    """TTL-expire ``session_save`` is off unless ``MEMNET_SAVE_ON_EXPIRE`` is truthy."""
    return _env_bool("MEMNET_SAVE_ON_EXPIRE", False)


def expire_snapshot_dir() -> Path | None:
    """Snapshot directory: expire-save, cap eviction and session load by sid (MN-REQ-05.5).

    ``MEMNET_EXPIRE_SNAPSHOT_DIR``, read whether or not save-on-expire is on. The
    neutral alias ``MEMNET_SNAPSHOT_DIR`` may name the same directory. Two different
    paths refuse with ``config_conflict``; the message names neither path.
    """
    primary = (os.environ.get("MEMNET_EXPIRE_SNAPSHOT_DIR") or "").strip()
    alias = (os.environ.get("MEMNET_SNAPSHOT_DIR") or "").strip()
    if primary and alias and os.path.realpath(primary) != os.path.realpath(alias):
        raise MemNetError(
            "config_conflict",
            "MEMNET_EXPIRE_SNAPSHOT_DIR and MEMNET_SNAPSHOT_DIR name different directories",
        )
    raw = primary or alias
    if not raw:
        return None
    return Path(raw)


def expire_save_status() -> dict[str, bool]:
    """Booleans for ``serve_status``. Path is redacted (dir set or not)."""
    return {
        "save_on_expire": save_on_expire(),
        "expire_snapshot_dir_set": expire_snapshot_dir() is not None,
    }
