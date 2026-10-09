"""Safe serve upgrade: drain, manifest, and startup restore (MN-REQ-06.14).

Admin-only. Not an agent MCP tool. A session that cannot be snapshotted
blocks ready-to-stop unless the operator passes allow-unsaved. A clean
restore retires the manifest in that same startup. Snapshot files are
not deleted, and a failed restore does not retire.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from memnet import __version__
from memnet.acl import SessionAcl, parse_write_scope
from memnet.admin_usage import authenticate
from memnet.exceptions import MemNetError
from memnet.registry import count, get_entry, list_entries
from memnet.snapshot import SNAPSHOT_MAGIC, load_snapshot_text, write_snapshot

SUPPORTED_SNAPSHOT_FORMATS = (1,)
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
    """Format written by this patch. Older v1 snapshots still load."""
    if not SNAPSHOT_MAGIC.endswith("v1"):
        raise MemNetError("bad_snapshot", "snapshot magic is not v1")
    return 1


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


def _acl_to_dict(acl: SessionAcl | None) -> dict[str, Any]:
    if acl is None:
        return {"enabled": False, "callers": [], "bind": None}
    callers = []
    for grant in acl.callers.values():
        scope = grant.write_scope.to_wire() if grant.write_scope else None
        callers.append(
            {
                "caller": grant.caller,
                "can_pin_map": grant.can_pin_map,
                "can_mutate": grant.can_mutate,
                "write_scope": scope,
            }
        )
    bind = None
    if acl.bind is not None:
        bind = {"mission_id": acl.bind.mission_id, "lease": acl.bind.lease}
    return {"enabled": acl.enabled, "callers": callers, "bind": bind}


def _apply_acl(entry: Any, data: dict[str, Any] | None) -> None:
    if not data:
        return
    acl = SessionAcl(enabled=bool(data.get("enabled")))
    for row in data.get("callers") or []:
        acl.grant(
            str(row.get("caller") or ""),
            can_pin_map=bool(row.get("can_pin_map", True)),
            can_mutate=bool(row.get("can_mutate", True)),
            write_scope=parse_write_scope(row.get("write_scope")),
        )
    bind = data.get("bind")
    if isinstance(bind, dict) and bind.get("mission_id") and bind.get("lease"):
        acl.set_bind(str(bind["mission_id"]), str(bind["lease"]))
    if data.get("enabled"):
        acl.enabled = True
    entry.acl = acl
    entry.meta.acl_enabled = acl.enabled


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _passport(entry: Any) -> dict[str, Any]:
    meta = entry.meta
    return {
        "acl": _acl_to_dict(entry.acl),
        "product": meta.product,
        "created_at": meta.created_at,
        "expires_at": meta.expires_at,
        "ttl_minutes": meta.ttl_minutes,
        "house_tags": _house_tags(entry.tag_map),
    }


def _append_passport(path: Path, payload: dict[str, Any]) -> None:
    line = PASSPORT_PREFIX + json.dumps(payload, separators=(",", ":"), sort_keys=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


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
        write_snapshot(SessionStore(sid, entry.store.caps), path)
        _append_passport(path, passport)
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

    @property
    def stat(self) -> str:
        return f"@STAT: upgrade_restore|ok|{self.ok}|failed|{self.failed}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "failed": self.failed,
            "skipped": self.skipped,
            "stat": self.stat,
            "errors": self.errors,
            "session_ids": self.session_ids,
            "details": self.details,
        }


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MemNetError("upgrade_manifest", type(exc).__name__, exit_code=3) from exc
    if not isinstance(data, dict):
        raise MemNetError("upgrade_manifest", "manifest must be an object", exit_code=3)
    return data


def _fail_session(report: RestoreReport, sid: str, code: str, detail: str) -> None:
    report.failed += 1
    report.errors.append({"session_id": sid, "code": code, "detail": detail})


def _restore_one(root: Path, row: dict[str, Any], report: RestoreReport) -> None:
    sid = str(row.get("session_id") or "")
    rel = str(row.get("file") or "")
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
        if passport:
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
            path.write_bytes(before)


def restore_manifest(directory: Path | None = None) -> RestoreReport:
    """Reload a ready manifest. Does not delete snapshot files."""
    root = directory or state_dir()
    path = root / MANIFEST_NAME
    if not path.is_file():
        return RestoreReport(skipped=True)
    manifest = _load_json(path)
    if manifest.get("retired"):
        return RestoreReport(skipped=True)
    if not manifest.get("ready_to_stop"):
        raise MemNetError("upgrade_not_ready", "manifest is not ready_to_stop", exit_code=3)
    fmt = int(manifest.get("snapshot_format") or 0)
    if fmt not in SUPPORTED_SNAPSHOT_FORMATS:
        raise MemNetError(
            "upgrade_snapshot_format",
            f"unsupported snapshot format {fmt}",
            exit_code=3,
        )
    if count() > 0:
        raise MemNetError("upgrade_restore_registry_busy", "registry is not empty", exit_code=3)
    report = RestoreReport()
    sessions = manifest.get("sessions") or []
    if not isinstance(sessions, list):
        raise MemNetError("upgrade_manifest", "sessions must be a list", exit_code=3)
    for row in sessions:
        if not isinstance(row, dict):
            report.failed += 1
            report.errors.append(
                {"session_id": "", "code": "upgrade_manifest", "detail": "bad row"}
            )
            continue
        _restore_one(root, row, report)
    _atomic_write(
        root / RESTORE_NAME,
        json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n",
    )
    return report


def startup_restore_or_exit(directory: Path | None = None) -> RestoreReport:
    """Serve startup. Exit 3 on a loud restore failure. Leave files in place."""
    try:
        report = restore_manifest(directory)
    except MemNetError as exc:
        line = f"@ERR: {exc.code}|{exc.message}\n"
        import sys

        sys.stdout.write(line)
        sys.stderr.write(line)
        raise SystemExit(exc.exit_code) from exc
    if report.skipped:
        return report
    import sys

    line = report.stat + "\n"
    sys.stdout.write(line)
    sys.stderr.write(line)
    if report.failed:
        raise SystemExit(3)
    retire_manifest(directory)
    return report


def retire_manifest(directory: Path | None = None) -> None:
    """Keep snapshot files, and stop replaying them on the next start.

    Refuses when the restore report is missing or not clean.
    """
    root = directory or state_dir()
    report_path = root / RESTORE_NAME
    if not report_path.is_file():
        raise MemNetError("upgrade_retire_refused", "restore not verified", exit_code=2)
    report = _load_json(report_path)
    if int(report.get("failed") or 0) != 0 or int(report.get("ok") or 0) < 0:
        raise MemNetError("upgrade_retire_refused", "restore not verified", exit_code=2)
    if int(report.get("failed") or 0) != 0:
        raise MemNetError("upgrade_retire_refused", "restore not verified", exit_code=2)
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        raise MemNetError("upgrade_manifest_missing", "no manifest", exit_code=2)
    manifest = _load_json(manifest_path)
    if int(report.get("failed") or 0) != 0 or report.get("skipped"):
        raise MemNetError("upgrade_retire_refused", "restore not verified", exit_code=2)
    manifest["retired"] = True
    _atomic_write(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")


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
