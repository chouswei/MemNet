"""Atomic private file writes for snapshots and manifests (MN-REQ-06.16).

The temp file is created with mode 0600 (``mkstemp`` uses ``O_CREAT|O_EXCL``
and 0600), written, fsynced, then renamed over the destination. The
destination is never a partial write, and it is never readable by other
users, even when it replaces an older file created with a looser mode.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _fsync_fd(fd: int) -> None:
    os.fsync(fd)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write ``data`` via a 0600 temp file, fsync, and rename.

    A failure before rename leaves the destination untouched and removes
    the temp file.
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
    try:
        dir_fd = os.open(path.parent, os.O_RDONLY)
    except OSError:
        return
    try:
        _fsync_fd(dir_fd)
    except OSError:
        pass
    finally:
        os.close(dir_fd)
