"""Atomic private file writes for snapshots and manifests (MN-REQ-06.16).

The temp file is created with mode 0600 (``mkstemp`` uses ``O_CREAT|O_EXCL``
and 0600), written, fsynced, then renamed over the destination. The
destination is never a partial write, and it is never readable by other
users, even when it replaces an older file created with a looser mode.
"""

from __future__ import annotations

import errno
import os
import tempfile
from pathlib import Path

# Directory fsync errors that mean "this filesystem has no directory fsync".
# Any other error is a real I/O failure and raises (EIO, ENOSPC, EDQUOT, EROFS, ...).
_DIR_SYNC_UNSUPPORTED = frozenset({errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP})


def _fsync_fd(fd: int) -> None:
    os.fsync(fd)


def _sync_dir(path: Path) -> None:
    """fsync the directory entry after rename. Unsupported filesystems are skipped."""
    try:
        dir_fd = os.open(path, os.O_RDONLY)
    except OSError as exc:
        if exc.errno in _DIR_SYNC_UNSUPPORTED:
            return
        raise
    try:
        _fsync_fd(dir_fd)
    except OSError as exc:
        if exc.errno in _DIR_SYNC_UNSUPPORTED:
            return
        raise
    finally:
        os.close(dir_fd)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write ``data`` via a 0600 temp file, fsync, and rename.

    A failure before rename leaves the destination untouched and removes
    the temp file. A failed directory fsync raises after the rename, so the
    caller treats the save as failed (eviction keeps the victim live). A
    directory fsync that the filesystem does not support (EINVAL, ENOTSUP,
    EOPNOTSUPP) is skipped.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f"{path.name}.",
        suffix=".tmp",
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            _fsync_fd(handle.fileno())
        os.replace(tmp, path)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    _sync_dir(path.parent)
