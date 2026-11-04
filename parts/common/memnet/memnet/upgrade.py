"""Safe serve upgrade: drain, manifest, and startup restore (MN-REQ-06.14).

Admin-only. Not an agent MCP tool. A session that cannot be snapshotted
blocks ready-to-stop unless the operator passes allow-unsaved. Every serve
start restores the newest valid snapshot set, checkpoint or upgrade-prepare.
A clean restore of the upgrade set marks it retired, and it stays a
candidate. Snapshot files are not deleted, and a failed restore does not retire.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from memnet import __version__
from memnet.acl import acl_from_dict, acl_to_dict
from memnet.admin_usage import authenticate
from memnet.atomic_file import atomic_write_bytes
from memnet.exceptions import MemNetError
from memnet.registry import count, get_entry, list_entries
from memnet.snapshot import (
    SNAPSHOT_FORMAT,
    SNAPSHOT_MAGIC,
    SUPPORTED_SNAPSHOT_FORMATS,
    load_snapshot_text,
    write_snapshot,
)

MANIFEST_FORMAT = 1
MANIFEST_NAME = "upgrade-manifest.json"
RESTORE_NAME = "upgrade-restore.json"
BLOCKED_NAME = "upgrade-blocked.json"
SNAPSHOT_DIRNAME = "upgrade-snapshots"
PASSPORT_PREFIX = "# upgrade-passport "
ENV_STATE_DIR = "MEMNET_STATE_DIR"
ENV_RETRY_AFTER = "MEMNET_UPGRADE_RETRY_AFTER_S"
ENV_DRAIN_WAIT = "MEMNET_UPGRADE_DRAIN_WAIT_S"
DEFAULT_RETRY_AFTER_S = 5
DEFAULT_DRAIN_WAIT_S = 20.0

_PHASE_OPEN = "open"
_PHASE_QUIESCE = "quiesce"
_PHASE_READY = "ready"


def snapshot_format_version() -> int:
    """Format written by this patch (@SNAP version 2). Format 1 files still load, ACL off."""
    return SNAPSHOT_FORMAT


def state_dir() -> Path:
    raw = (os.environ.get(ENV_STATE_DIR) or "").strip()
    if raw:
        return Path(raw)
    return Path.home() / ".local" / "state" / "memnet"


def _retry_after_s() -> int:
    raw = (os.environ.get(ENV_RETRY_AFTER) or "").strip()
    if not raw:
        return DEFAULT_RETRY_AFTER_S
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_RETRY_AFTER_S
    return value if value > 0 else DEFAULT_RETRY_AFTER_S


def _drain_wait_s() -> float:
    raw = (os.environ.get(ENV_DRAIN_WAIT) or "").strip()
    if not raw:
        return DEFAULT_DRAIN_WAIT_S
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_DRAIN_WAIT_S
    return value if value > 0 else DEFAULT_DRAIN_WAIT_S


def _is_upgrade_argv(argv: list[Any]) -> bool:
    if len(argv) < 2:
        return False
    return str(argv[0]) == "admin" and str(argv[1]) == "upgrade-prepare"


class DrainGate:
    """Process-wide drain. New work is refused once quiesce begins."""

    def __init__(self) -> None:
        self._cv = threading.Condition(threading.Lock())
        self._phase = _PHASE_OPEN
        self._inflight = 0
        self.retry_after_s = DEFAULT_RETRY_AFTER_S

    def reset(self) -> None:
        with self._cv:
            self._phase = _PHASE_OPEN
            self._inflight = 0
            self._cv.notify_all()

    @property
    def phase(self) -> str:
        with self._cv:
            return self._phase

    def set_phase_for_test(self, phase: str) -> None:
        with self._cv:
            self._phase = phase
            self._cv.notify_all()

    def begin(self, argv: list[Any]) -> tuple[bool, str | None]:
        """Return (counted, error). Upgrade commands are not counted."""
        with self._cv:
            upgrade = _is_upgrade_argv(argv)
            if self._phase != _PHASE_OPEN and not upgrade:
                return False, "serve_draining"
            if upgrade:
                return False, None
            self._inflight += 1
            return True, None

    def end(self, counted: bool) -> None:
        if not counted:
            return
        with self._cv:
            self._inflight = max(0, self._inflight - 1)
            if self._inflight == 0:
                self._cv.notify_all()

    def enter_quiesce(self, retry_after_s: int) -> None:
        with self._cv:
            self._phase = _PHASE_QUIESCE
            self.retry_after_s = retry_after_s

    def mark_ready(self) -> None:
        with self._cv:
            self._phase = _PHASE_READY

    def mark_open(self) -> None:
        with self._cv:
            self._phase = _PHASE_OPEN
            self._cv.notify_all()

    def wait_idle(self, timeout_s: float) -> bool:
        deadline = time.monotonic() + timeout_s
        with self._cv:
            while self._inflight > 0:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._cv.wait(remaining)
            return True


drain_gate = DrainGate()


def reset_drain_gate() -> None:
    drain_gate.reset()


def refuse_new_session() -> None:
    """Refuse session_open while the serve is draining or ready to stop."""
    if drain_gate.phase == _PHASE_OPEN:
        return
    raise MemNetError(
        "serve_draining",
        f"retry_after_s={drain_gate.retry_after_s}",
        exit_code=2,
    )


def draining_envelope(retry_after_s: int | None = None) -> dict[str, Any]:
    seconds = drain_gate.retry_after_s if retry_after_s is None else retry_after_s
    return {
        "exit_code": 2,
        "stdout": "",
        "stderr": f"@ERR: serve_draining|retry_after_s={seconds}\n",
    }


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


def _house_tags(tag_map: Any) -> list[str]:
    return sorted(tag_map.tags.keys())


def _apply_acl(entry: Any, data: dict[str, Any] | None) -> None:
    if not data:
        return
    entry.acl = acl_from_dict(data)
    entry.meta.acl_enabled = entry.acl.enabled


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _atomic_write(path: Path, text: str) -> None:
    """Manifest and report writes: 0600 temp file, fsync, rename (MN-REQ-06.16)."""
    atomic_write_bytes(path, text.encode("utf-8"))


def _passport(entry: Any) -> dict[str, Any]:
    meta = entry.meta
    return {
        "acl": acl_to_dict(entry.acl),
        "product": meta.product,
        "created_at": meta.created_at,
        "expires_at": meta.expires_at,
        "ttl_minutes": meta.ttl_minutes,
        "house_tags": _house_tags(entry.tag_map),
    }


def _passport_line(payload: dict[str, Any]) -> str:
    """Trailing ``#`` line written in the same atomic snapshot write."""
    return PASSPORT_PREFIX + json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"


def split_passport(text: str) -> tuple[str, dict[str, Any] | None]:
    """Split an optional upgrade passport. v1 loaders skip the # line."""
    body: list[str] = []
    passport: dict[str, Any] | None = None
    for line in text.splitlines():
        if line.startswith(PASSPORT_PREFIX):
            passport = json.loads(line[len(PASSPORT_PREFIX) :])
            continue
        body.append(line)
    return "\n".join(body) + ("\n" if body else ""), passport


@dataclass
class PrepareResult:
    ready_to_stop: bool
    saved: int
    unsaved: list[dict[str, str]]
    manifest_path: Path | None
    stat: str
    exit_code: int

    def stdout_json(self) -> str:
        payload = {
            "ok": self.ready_to_stop,
            "ready_to_stop": self.ready_to_stop,
            "saved": self.saved,
            "unsaved": self.unsaved,
            "stat": self.stat,
            "manifest": str(self.manifest_path) if self.manifest_path else None,
        }
        return json.dumps(payload, sort_keys=True) + "\n"


def _snapshot_one(entry: Any, snap_dir: Path) -> dict[str, Any]:
    from memnet.session import SessionStore

    sid = entry.meta.session_id
    path = snap_dir / f"{_safe_name(sid)}.snap"
    with entry.lock:
        rows = entry.store.row_count_non_law()
        edges = _edge_count(entry.store)
        house = _house_tags(entry.tag_map)
        passport = _passport(entry)
        write_snapshot(
            SessionStore(sid, entry.store.caps),
            path,
            trailer=_passport_line(passport),
        )
        checksum = _sha256(path)
    return {
        "session_id": sid,
        "file": f"{SNAPSHOT_DIRNAME}/{path.name}",
        "rows": rows,
        "edges": edges,
        "checksum_sha256": checksum,
        "expires_at": entry.meta.expires_at,
        "created_at": entry.meta.created_at,
        "ttl_minutes": entry.meta.ttl_minutes,
        "house_tags": house,
        "product": entry.meta.product,
        "saved": True,
    }


def prepare_upgrade(
    presented_token: str | None,
    *,
    allow_unsaved: bool = False,
    directory: Path | None = None,
    drain_wait_s: float | None = None,
) -> PrepareResult:
    """Quiesce, snapshot every loaded session, and write the manifest.

    On any unsaved session, ready_to_stop stays false unless allow_unsaved.
    The serve returns to accepting work when the drain is not ready to stop.
    """
    from memnet.session import iso_timestamp

    authenticate(presented_token)
    root = directory or state_dir()
    retry_after = _retry_after_s()
    wait_s = DEFAULT_DRAIN_WAIT_S if drain_wait_s is None else drain_wait_s
    drain_gate.enter_quiesce(retry_after)
    if not drain_gate.wait_idle(wait_s):
        drain_gate.mark_open()
        raise MemNetError("upgrade_inflight", "in-flight commands still running", exit_code=2)
    snap_dir = root / SNAPSHOT_DIRNAME
    snap_dir.mkdir(parents=True, exist_ok=True)
    saved_rows: list[dict[str, Any]] = []
    unsaved: list[dict[str, str]] = []
    for entry in list_entries():
        sid = entry.meta.session_id
        try:
            saved_rows.append(_snapshot_one(entry, snap_dir))
        except MemNetError as exc:
            unsaved.append({"session_id": sid, "code": exc.code, "detail": exc.message})
        except OSError as exc:
            unsaved.append(
                {"session_id": sid, "code": "snapshot_io_error", "detail": type(exc).__name__}
            )
    blocked = bool(unsaved) and not allow_unsaved
    if blocked:
        drain_gate.mark_open()
        report = {
            "manifest_format": MANIFEST_FORMAT,
            "snapshot_format": snapshot_format_version(),
            "serve_version": __version__,
            "timestamp": iso_timestamp(),
            "ready_to_stop": False,
            "allow_unsaved": False,
            "saved": saved_rows,
            "unsaved": unsaved,
        }
        path = root / BLOCKED_NAME
        _atomic_write(path, json.dumps(report, indent=2, sort_keys=True) + "\n")
        stat = f"@STAT: upgrade_prepare|blocked|{len(saved_rows)}|unsaved|{len(unsaved)}"
        return PrepareResult(
            ready_to_stop=False,
            saved=len(saved_rows),
            unsaved=unsaved,
            manifest_path=path,
            stat=stat,
            exit_code=2,
        )
    manifest = {
        "manifest_format": MANIFEST_FORMAT,
        "snapshot_format": snapshot_format_version(),
        "serve_version": __version__,
        "timestamp": iso_timestamp(),
        "ready_to_stop": True,
        "retired": False,
        "allow_unsaved": bool(allow_unsaved),
        "sessions": saved_rows,
        "unsaved": unsaved,
    }
    path = root / MANIFEST_NAME
    _atomic_write(path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    drain_gate.mark_ready()
    stat = f"@STAT: upgrade_prepare|ready|{len(saved_rows)}|unsaved|{len(unsaved)}"
    return PrepareResult(
        ready_to_stop=True,
        saved=len(saved_rows),
        unsaved=unsaved,
        manifest_path=path,
        stat=stat,
        exit_code=0,
    )


@dataclass
class RestoreReport:
    ok: int = 0
    failed: int = 0
    skipped: bool = False
    errors: list[dict[str, str]] = field(default_factory=list)
    session_ids: list[str] = field(default_factory=list)
    details: list[dict[str, Any]] = field(default_factory=list)
    source: str | None = None
    timestamp: str | None = None
    rejected: list[dict[str, str]] = field(default_factory=list)
    timestamp_source: str | None = None
    manifest: str | None = None

    @property
    def stat(self) -> str:
        return f"@STAT: upgrade_restore|ok|{self.ok}|failed|{self.failed}"

    @property
    def source_stat(self) -> str:
        return f"@STAT: restore_source|{self.source}|{self.timestamp}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "failed": self.failed,
            "skipped": self.skipped,
            "stat": self.stat,
            "errors": self.errors,
            "session_ids": self.session_ids,
            "details": self.details,
            "source": self.source,
            "timestamp": self.timestamp,
            "timestamp_source": self.timestamp_source,
            "manifest": self.manifest,
            "rejected": self.rejected,
        }


@dataclass
class RestoreCandidate:
    """One snapshot set that a serve start may restore (MN-REQ-06.14)."""

    source: str
    manifest_path: Path
    snap_root: Path
    timestamp: str
    timestamp_source: str
    error_code: str | None = None
    error_detail: str = ""


SOURCE_UPGRADE = "upgrade"
SOURCE_CHECKPOINT = "checkpoint"
# Exact tie: the upgrade set was taken drained, so it goes first.
_TIE_RANK = {SOURCE_UPGRADE: 0, SOURCE_CHECKPOINT: 1}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MemNetError("upgrade_manifest", type(exc).__name__, exit_code=3) from exc
    if not isinstance(data, dict):
        raise MemNetError("upgrade_manifest", "manifest must be an object", exit_code=3)
    return data


def _parse_stamp(value: Any) -> datetime | None:
    """ISO-8601 with a UTC offset or Z, else None."""
    if not isinstance(value, str) or not value:
        return None
    try:
        when = datetime.fromisoformat(value)
    except ValueError:
        return None
    if when.tzinfo is None:
        return None
    return when


def _candidate_paths(root: Path) -> list[tuple[str, Path, Path]]:
    from memnet.checkpoint import CHECKPOINT_DIRNAME
    from memnet.checkpoint import MANIFEST_NAME as CHECKPOINT_MANIFEST_NAME

    ckpt = root / CHECKPOINT_DIRNAME
    return [
        (SOURCE_CHECKPOINT, ckpt / CHECKPOINT_MANIFEST_NAME, ckpt),
        (SOURCE_UPGRADE, root / MANIFEST_NAME, root),
    ]


def _row_rel(source: str, row: dict[str, Any]) -> str:
    """Snapshot path relative to the set's root. Checkpoint rows are a single name."""
    rel = str(row.get("file") or "")
    if source == SOURCE_CHECKPOINT:
        from memnet.checkpoint import _snap_name

        name = _snap_name(rel)
        if name is None:
            raise MemNetError(
                "upgrade_manifest", "snapshot file must be a single name", exit_code=3
            )
        return name
    return rel


def _preflight(source: str, manifest: dict[str, Any], snap_root: Path) -> None:
    """Check a set before anything is loaded. Raises the first MemNetError found."""
    if source == SOURCE_UPGRADE and not manifest.get("ready_to_stop"):
        raise MemNetError("upgrade_not_ready", "manifest is not ready_to_stop", exit_code=3)
    try:
        fmt = int(manifest.get("snapshot_format") or 0)
    except (TypeError, ValueError):
        fmt = 0
    if fmt not in SUPPORTED_SNAPSHOT_FORMATS:
        raise MemNetError(
            "upgrade_snapshot_format",
            f"unsupported snapshot format {fmt}",
            exit_code=3,
        )
    sessions = manifest.get("sessions")
    if sessions is None:
        sessions = []
    if not isinstance(sessions, list) or not all(isinstance(r, dict) for r in sessions):
        raise MemNetError("upgrade_manifest", "sessions must be a list of objects", exit_code=3)
    for row in sessions:
        sid = str(row.get("session_id") or "")
        path = snap_root / _row_rel(source, row)
        if not path.is_file():
            raise MemNetError("snapshot_not_found", f"{sid}: missing snapshot file", exit_code=3)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != str(row.get("checksum_sha256") or ""):
            raise MemNetError("upgrade_checksum", f"{sid}: checksum mismatch", exit_code=3)
        try:
            body, _ = split_passport(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MemNetError(
                "bad_snapshot", f"{sid}: unsupported snapshot header", exit_code=3
            ) from exc
        if not body.startswith(SNAPSHOT_MAGIC):
            raise MemNetError("bad_snapshot", f"{sid}: unsupported snapshot header", exit_code=3)


def _check_candidate(
    source: str, manifest_path: Path, snap_root: Path
) -> tuple[RestoreCandidate, dict[str, Any] | None]:
    from memnet.session import iso_timestamp

    manifest: dict[str, Any] | None = None
    error: MemNetError | None = None
    try:
        manifest = _load_json(manifest_path)
    except MemNetError as exc:
        error = exc
    stamp = manifest.get("timestamp") if manifest else None
    if _parse_stamp(stamp) is not None:
        timestamp, timestamp_source = str(stamp), "manifest"
    else:
        mtime = manifest_path.stat().st_mtime
        timestamp = iso_timestamp(datetime.fromtimestamp(mtime, tz=UTC))
        timestamp_source = "mtime"
    if manifest is not None:
        try:
            _preflight(source, manifest, snap_root)
        except MemNetError as exc:
            error = exc
        except OSError as exc:
            error = MemNetError("upgrade_manifest", type(exc).__name__, exit_code=3)
    cand = RestoreCandidate(
        source=source,
        manifest_path=manifest_path,
        snap_root=snap_root,
        timestamp=timestamp,
        timestamp_source=timestamp_source,
        error_code=error.code if error else None,
        error_detail=error.message if error else "",
    )
    return cand, (manifest if error is None else None)


def _ranked(directory: Path | None) -> list[tuple[RestoreCandidate, dict[str, Any] | None]]:
    root = directory or state_dir()
    found = [
        _check_candidate(source, manifest_path, snap_root)
        for source, manifest_path, snap_root in _candidate_paths(root)
        if manifest_path.is_file()
    ]
    # Newest first; an exact tie goes to upgrade (stable sort keeps the rank order).
    found.sort(key=lambda item: _TIE_RANK[item[0].source])
    found.sort(key=lambda item: _parse_stamp(item[0].timestamp), reverse=True)
    return found


def restore_candidates(directory: Path | None = None) -> list[RestoreCandidate]:
    """Every snapshot set on disk, newest first, pre-flight checked. Reads only."""
    return [cand for cand, _ in _ranked(directory)]


def _fail_session(report: RestoreReport, sid: str, code: str, detail: str) -> None:
    report.failed += 1
    report.errors.append({"session_id": sid, "code": code, "detail": detail})


def _restore_one(
    root: Path, row: dict[str, Any], report: RestoreReport, source: str = SOURCE_UPGRADE
) -> None:
    sid = str(row.get("session_id") or "")
    try:
        rel = _row_rel(source, row)
    except MemNetError as exc:
        _fail_session(report, sid, exc.code, exc.message)
        return
    path = root / rel
    before = path.read_bytes() if path.is_file() else None
    try:
        if before is None:
            _fail_session(report, sid, "snapshot_not_found", "missing snapshot file")
            return
        got = hashlib.sha256(before).hexdigest()
        want = str(row.get("checksum_sha256") or "")
        if got != want:
            _fail_session(report, sid, "upgrade_checksum", "checksum mismatch")
            return
        text = before.decode("utf-8")
        body, passport = split_passport(text)
        if not body.startswith(SNAPSHOT_MAGIC):
            _fail_session(report, sid, "bad_snapshot", "unsupported snapshot header")
            return
        from memnet.config import Caps

        ss = load_snapshot_text(body, caps=Caps(), keep_id=True, preserve_clocks=True)
        entry = get_entry(ss.session_id)
        if entry is None:
            _fail_session(report, sid, "upgrade_restore", "session missing after load")
            return
        if source == SOURCE_CHECKPOINT:
            # No passport: the ACL came from the #@ACL line; product and clock from the row.
            if row.get("expires_at") and row.get("expires_at") != entry.meta.expires_at:
                _fail_session(report, sid, "upgrade_clock", "ttl clock mismatch")
                return
            entry.meta.product = row.get("product")
        elif passport:
            if passport.get("expires_at") and passport.get("expires_at") != entry.meta.expires_at:
                _fail_session(report, sid, "upgrade_clock", "ttl clock mismatch")
                return
            _apply_acl(entry, passport.get("acl"))
            entry.meta.product = passport.get("product")
        if ss.session_id != sid:
            _fail_session(report, sid, "upgrade_session_id", "session id changed")
            return
        rows = entry.store.row_count_non_law()
        edges = _edge_count(entry.store)
        if rows != int(row.get("rows", -1)) or edges != int(row.get("edges", -1)):
            _fail_session(report, sid, "upgrade_counts", "row or edge count mismatch")
            return
        house = _house_tags(entry.tag_map)
        if house != list(row.get("house_tags") or []):
            _fail_session(report, sid, "upgrade_house", "house tag map mismatch")
            return
        if path.read_bytes() != before:
            _fail_session(report, sid, "upgrade_snapshot_mutated", "snapshot file changed")
            return
        report.ok += 1
        report.session_ids.append(ss.session_id)
        bind = entry.acl.bind.mission_id if entry.acl and entry.acl.bind else None
        report.details.append(
            {
                "session_id": ss.session_id,
                "expires_at": entry.meta.expires_at,
                "ttl_minutes": entry.meta.ttl_minutes,
                "acl_enabled": bool(entry.acl and entry.acl.enabled),
                "bind_mission": bind,
                "rows": rows,
                "edges": edges,
                "product": entry.meta.product,
            }
        )
    except MemNetError as exc:
        _fail_session(report, sid, exc.code, exc.message)
    finally:
        if before is not None and path.is_file() and path.read_bytes() != before:
            atomic_write_bytes(path, before)


def restore_manifest(directory: Path | None = None) -> RestoreReport:
    """Reload the newest valid snapshot set. Does not delete snapshot files.

    Candidates are the admin checkpoint and the upgrade-prepare manifest.
    Newer sets that fail pre-flight are listed in ``rejected``. None on disk
    is skipped; none valid raises the newest set's own error.
    """
    root = directory or state_dir()
    ranked = _ranked(root)
    if not ranked:
        return RestoreReport(skipped=True)
    chosen: tuple[RestoreCandidate, dict[str, Any]] | None = None
    rejected: list[dict[str, str]] = []
    for cand, manifest in ranked:
        if cand.error_code is None and manifest is not None:
            chosen = (cand, manifest)
            break
        rejected.append(
            {"source": cand.source, "code": str(cand.error_code), "detail": cand.error_detail}
        )
    if chosen is None:
        newest = ranked[0][0]
        raise MemNetError(str(newest.error_code), newest.error_detail, exit_code=3)
    if count() > 0:
        raise MemNetError("upgrade_restore_registry_busy", "registry is not empty", exit_code=3)
    cand, manifest = chosen
    report = RestoreReport(
        source=cand.source,
        timestamp=cand.timestamp,
        timestamp_source=cand.timestamp_source,
        manifest=str(cand.manifest_path.relative_to(root)),
        rejected=rejected,
    )
    for row in manifest.get("sessions") or []:
        _restore_one(cand.snap_root, row, report, cand.source)
    _atomic_write(
        root / RESTORE_NAME,
        json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n",
    )
    return report


def _emit(line: str) -> None:
    import sys

    sys.stdout.write(line + "\n")
    sys.stderr.write(line + "\n")


def startup_restore_or_exit(directory: Path | None = None) -> RestoreReport:
    """Serve startup. Exit 3 on a loud restore failure. Leave files in place."""
    try:
        report = restore_manifest(directory)
    except MemNetError as exc:
        _emit(f"@ERR: {exc.code}|{exc.message}")
        raise SystemExit(exc.exit_code) from exc
    if report.skipped:
        return report
    for item in report.rejected:
        _emit(f"@WARN: restore_fallback|{item['source']}|{item['code']}|{item['detail']}")
    _emit(report.source_stat)
    _emit(report.stat)
    if report.failed:
        raise SystemExit(3)
    if report.source == SOURCE_UPGRADE:
        retire_manifest(directory)
    return report


def retire_manifest(directory: Path | None = None) -> None:
    """Mark the upgrade manifest restored at least once. It stays a candidate.

    Refuses when the restore report is missing or not clean. The manifest
    keeps its mtime, so a set with no timestamp keeps its age.
    """
    from memnet.session import iso_timestamp

    root = directory or state_dir()
    report_path = root / RESTORE_NAME
    if not report_path.is_file():
        raise MemNetError("upgrade_retire_refused", "restore not verified", exit_code=2)
    report = _load_json(report_path)
    if int(report.get("failed") or 0) != 0 or report.get("skipped"):
        raise MemNetError("upgrade_retire_refused", "restore not verified", exit_code=2)
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        raise MemNetError("upgrade_manifest_missing", "no manifest", exit_code=2)
    manifest = _load_json(manifest_path)
    if manifest.get("retired") and manifest.get("retired_at"):
        return
    manifest["retired"] = True
    manifest.setdefault("retired_at", iso_timestamp())
    stat = manifest_path.stat()
    _atomic_write(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    os.utime(manifest_path, ns=(stat.st_atime_ns, stat.st_mtime_ns))


def upgrade_prepare_envelope(
    token: str | None,
    *,
    allow_unsaved: bool = False,
) -> dict[str, Any]:
    try:
        result = prepare_upgrade(token, allow_unsaved=allow_unsaved)
    except MemNetError as exc:
        return {
            "exit_code": exc.exit_code,
            "stdout": "",
            "stderr": f"@ERR: {exc.code}|{exc.message}\n",
        }
    stderr = ""
    if result.exit_code:
        stderr = f"@ERR: upgrade_blocked|unsaved|{len(result.unsaved)}\n{result.stat}\n"
    else:
        stderr = result.stat + "\n"
    return {"exit_code": result.exit_code, "stdout": result.stdout_json(), "stderr": stderr}
