"""Admin checkpoint of every loaded session (MN-REQ-06.15).

Not an agent MCP tool. Copies each loaded session through the lossless
snapshot path without draining the serve, refusing new opens, sliding
TTL, or loading anything back into the live registry.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from memnet import __version__
from memnet.admin_usage import authenticate
from memnet.exceptions import MemNetError
from memnet.registry import list_entries
from memnet.session import iso_timestamp
from memnet.upgrade import snapshot_format_version, state_dir

CHECKPOINT_DIRNAME = "checkpoint"
MANIFEST_NAME = "checkpoint-manifest.json"
MANIFEST_FORMAT = 1
_PHASE_OPEN = "open"
_checkpoint_lock = threading.Lock()


def _fsync_fd(fd: int) -> None:
    os.fsync(fd)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write ``data`` via a temp file, fsync, and rename.

    A failure before rename leaves the destination untouched and removes
    the temp file. The destination is never a partial write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        with tmp.open("wb") as handle:
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
        try:
            _fsync_fd(dir_fd)
        except OSError:
            return
    finally:
        os.close(dir_fd)


def _safe_name(session_id: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in session_id)
    return cleaned or "session"


def _edge_count(store: Any) -> int:
    total = 0
    for hid in store.write_order:
        rec = store._by_hid.get(hid)
        if rec is not None and rec.tag == "EDG":
            total += 1
    return total


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stat(saved: int, skipped: int, nbytes: int) -> str:
    return f"@STAT: checkpoint|ok|{saved}|skipped|{skipped}|bytes|{nbytes}"


def _verify_stat(ok: int, failed: int) -> str:
    return f"@STAT: checkpoint_verify|ok|{ok}|failed|{failed}"


def checkpoint_dir(directory: Path | None = None) -> Path:
    root = directory or state_dir()
    return root / CHECKPOINT_DIRNAME


def _refuse_if_draining() -> None:
    from memnet.upgrade import drain_gate

    if drain_gate.phase != _PHASE_OPEN:
        raise MemNetError(
            "serve_draining",
            f"retry_after_s={drain_gate.retry_after_s}",
            exit_code=2,
        )


def _serialise(entry: Any) -> tuple[bytes, int, int, dict[str, Any]]:
    """Copy one session. The session lock covers serialise only."""
    from memnet.session import SessionStore
    from memnet.snapshot import snapshot_text

    sid = entry.meta.session_id
    with entry.lock:
        ss = SessionStore(sid, entry.store.caps)
        text = snapshot_text(ss)
        rows = entry.store.row_count_non_law()
        edges = _edge_count(entry.store)
        meta = {
            "expires_at": entry.meta.expires_at,
            "created_at": entry.meta.created_at,
            "ttl_minutes": entry.meta.ttl_minutes,
            "house_tags": sorted(entry.tag_map.tags.keys()),
            "product": entry.meta.product,
        }
    return text.encode("utf-8"), rows, edges, meta


@dataclass
class CheckpointResult:
    saved: int
    skipped: list[dict[str, str]]
    nbytes: int
    manifest_path: Path
    stat: str
    exit_code: int

    def stdout_text(self) -> str:
        return self.stat + "\n"

    def stderr_text(self) -> str:
        lines = []
        for row in self.skipped:
            lines.append(f"@ERR: {row['code']}|{row['session_id']}|{row['detail']}")
        return ("\n".join(lines) + "\n") if lines else ""


def run_checkpoint(
    presented_token: str | None,
    *,
    directory: Path | None = None,
) -> CheckpointResult:
    """Snapshot every loaded session. Unsaveable sessions are skipped."""
    authenticate(presented_token)
    with _checkpoint_lock:
        return _checkpoint_locked(directory)


def _checkpoint_locked(directory: Path | None) -> CheckpointResult:
    _refuse_if_draining()
    dest = checkpoint_dir(directory)
    dest.mkdir(parents=True, exist_ok=True)
    saved_rows: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for entry in list_entries():
        sid = entry.meta.session_id
        try:
            payload, rows, edges, meta = _serialise(entry)
        except MemNetError as exc:
            skipped.append({"session_id": sid, "code": exc.code, "detail": exc.message})
            continue
        except OSError as exc:
            skipped.append(
                {"session_id": sid, "code": "snapshot_io_error", "detail": type(exc).__name__}
            )
            continue
        name = f"{_safe_name(sid)}.snap"
        path = dest / name
        try:
            atomic_write_bytes(path, payload)
        except OSError as exc:
            skipped.append(
                {"session_id": sid, "code": "snapshot_io_error", "detail": type(exc).__name__}
            )
            continue
        digest = _sha256(payload)
        saved_rows.append(
            {
                "session_id": sid,
                "file": name,
                "rows": rows,
                "edges": edges,
                "checksum_sha256": digest,
                "expires_at": meta["expires_at"],
                "created_at": meta["created_at"],
                "ttl_minutes": meta["ttl_minutes"],
                "house_tags": meta["house_tags"],
                "product": meta["product"],
                "saved": True,
            }
        )
    loaded = {item.meta.session_id for item in list_entries()}
    saved_rows = [row for row in saved_rows if row["session_id"] in loaded]
    keep = {row["file"] for row in saved_rows}
    nbytes = 0
    for row in saved_rows:
        snap = dest / row["file"]
        if snap.is_file():
            nbytes += snap.stat().st_size
    for path in dest.glob("*.snap"):
        if path.name not in keep:
            path.unlink()
    for path in dest.glob("*.tmp"):
        path.unlink()
    manifest = {
        "manifest_format": MANIFEST_FORMAT,
        "snapshot_format": snapshot_format_version(),
        "serve_version": __version__,
        "timestamp": iso_timestamp(),
        "sessions": saved_rows,
        "unsaved": skipped,
    }
    manifest_path = dest / MANIFEST_NAME
    atomic_write_bytes(
        manifest_path,
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    stat = _stat(len(saved_rows), len(skipped), nbytes)
    return CheckpointResult(
        saved=len(saved_rows),
        skipped=skipped,
        nbytes=nbytes,
        manifest_path=manifest_path,
        stat=stat,
        exit_code=2 if skipped else 0,
    )


def checkpoint_envelope(token: str | None) -> dict[str, Any]:
    """Serve wire op ``{checkpoint: true, admin_token}``."""
    try:
        result = run_checkpoint(token)
    except MemNetError as exc:
        return {
            "exit_code": exc.exit_code,
            "stdout": "",
            "stderr": f"@ERR: {exc.code}|{exc.message}\n",
        }
    return {
        "exit_code": result.exit_code,
        "stdout": result.stdout_text(),
        "stderr": result.stderr_text(),
    }


def _fail(failed: list[dict[str, str]], name: str, code: str, detail: str) -> None:
    failed.append({"file": name, "code": code, "detail": detail})


def _snap_name(file_field: str) -> str | None:
    if not file_field or file_field != Path(file_field).name:
        return None
    if file_field in {".", ".."} or "/" in file_field or "\\" in file_field:
        return None
    return file_field


@dataclass
class VerifyResult:
    ok: int
    failed: list[dict[str, str]]
    stat: str
    exit_code: int

    def stdout_text(self) -> str:
        return self.stat + "\n"

    def stderr_text(self) -> str:
        lines = [f"@ERR: {row['code']}|{row['file']}|{row['detail']}" for row in self.failed]
        return ("\n".join(lines) + "\n") if lines else ""


def verify_checkpoint(directory: Path, presented_token: str | None) -> VerifyResult:
    """Load each snap in ``directory`` into a throwaway store and check the manifest."""
    authenticate(presented_token)
    failed: list[dict[str, str]] = []
    ok = 0
    manifest_path = directory / MANIFEST_NAME
    if not manifest_path.is_file():
        _fail(failed, MANIFEST_NAME, "checkpoint_manifest_missing", "missing manifest")
        stat = _verify_stat(0, len(failed))
        return VerifyResult(ok=0, failed=failed, stat=stat, exit_code=2)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(failed, MANIFEST_NAME, "checkpoint_manifest", type(exc).__name__)
        stat = _verify_stat(0, len(failed))
        return VerifyResult(ok=0, failed=failed, stat=stat, exit_code=2)
    if not isinstance(manifest, dict):
        _fail(failed, MANIFEST_NAME, "checkpoint_manifest", "manifest must be an object")
        stat = _verify_stat(0, len(failed))
        return VerifyResult(ok=0, failed=failed, stat=stat, exit_code=2)
    sessions = manifest.get("sessions") or []
    if not isinstance(sessions, list):
        _fail(failed, MANIFEST_NAME, "checkpoint_manifest", "sessions must be a list")
        sessions = []
    listed: set[str] = set()
    from memnet.snapshot import materialise_snapshot_text

    for row in sessions:
        if not isinstance(row, dict):
            _fail(failed, "", "checkpoint_manifest", "bad row")
            continue
        name = _snap_name(str(row.get("file") or ""))
        label = name or str(row.get("session_id") or "")
        if name is None:
            _fail(failed, label, "checkpoint_path", "snapshot file must be a single name")
            continue
        listed.add(name)
        path = directory / name
        if not path.is_file():
            _fail(failed, name, "checkpoint_missing", "missing snapshot file")
            continue
        data = path.read_bytes()
        want = str(row.get("checksum_sha256") or "")
        if _sha256(data) != want:
            _fail(failed, name, "checkpoint_checksum", "checksum mismatch")
            continue
        try:
            entry = materialise_snapshot_text(data.decode("utf-8"))
        except (MemNetError, UnicodeError) as exc:
            code = exc.code if isinstance(exc, MemNetError) else "checkpoint_corrupt"
            detail = exc.message if isinstance(exc, MemNetError) else type(exc).__name__
            _fail(failed, name, code, detail)
            continue
        rows = entry.store.row_count_non_law()
        edges = _edge_count(entry.store)
        if rows != int(row.get("rows", -1)) or edges != int(row.get("edges", -1)):
            _fail(failed, name, "checkpoint_counts", "row or edge count mismatch")
            continue
        ok += 1
    if directory.is_dir():
        for path in sorted(directory.glob("*.snap")):
            if path.name not in listed:
                _fail(failed, path.name, "checkpoint_extra", "snapshot not in the manifest")
    stat = _verify_stat(ok, len(failed))
    return VerifyResult(ok=ok, failed=failed, stat=stat, exit_code=2 if failed else 0)
