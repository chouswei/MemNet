"""Helpers for one-session-per-document serve probes. Never emit a session id."""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from memnet.serve import send_command

SID_RE = re.compile(r"mn_[0-9a-fA-F]+")
ADMIN_TOKEN = "probe-admin-token"
TECHDOCS_MAP = (
    Path(__file__).resolve().parents[1]
    / "parts"
    / "common"
    / "memnet"
    / "memnet"
    / "examples"
    / "schema.techdocs.example.txt"
)
SNAPSHOT_PY = (
    Path(__file__).resolve().parents[1] / "parts" / "common" / "memnet" / "memnet" / "snapshot.py"
)
CAP_CONTRACT = Path(__file__).resolve().parents[1] / "docs" / "cap-contract.md"

# Needles that must remain in docs/cap-contract.md on 0.19.18.
CAP_CONTRACT_NEEDLES = (
    "CLI / serve",
    r"@ERR: {code}\|{message}",
    "exit_code`, `stdout`, `stderr`, `session_id`, `errors`",
    r"@ERR: ingest_budget\|pin budget exceeded (max_nodes={N})",
    "@ERR: limit_exceeded|rows",
    "## Truncation truncated=true M={max_rows} omitted={n} reason=max_rows",
    "snap_missing",
    "snap_available",
    r"@ERR: acl_who\|",
    r"@ERR: acl_denied\|",
    r"@ERR: acl_scope\|",
    "MEMNET_MAX_SESSIONS",
    "1024",
    "MEMNET_SESSION_TTL_MINUTES",
    "MEMNET_SAVE_ON_EXPIRE",
    "MEMNET_SERVE_INTERNAL=1",
    "DEFAULT_QUERY_MAX_ROWS",
    "MEMNET_MAX_FIELDS",
    "Never treat a clipped read as complete",
)

PROP32 = ["id"] + [f"p{i:02d}" for i in range(31)]
assert len(PROP32) == 32


def redact(text: str | None) -> str:
    return SID_RE.sub("<session>", text or "")


def assert_sid_free(*parts: str) -> None:
    blob = "\n".join(parts)
    if SID_RE.search(blob) or "mn_" in blob:
        raise AssertionError("session id leaked")


def redact_obj(obj: Any) -> Any:
    return json.loads(redact(json.dumps(obj)))


def gql_str(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f"'{escaped}'"


def err_lines(stderr: str) -> list[str]:
    return [ln for ln in redact(stderr).splitlines() if ln.startswith("@ERR:")]


def stat_lines(text: str) -> list[str]:
    return [ln for ln in redact(text).splitlines() if ln.startswith("@STAT:")]


def wrn_lines(text: str) -> list[str]:
    return [ln for ln in redact(text).splitlines() if ln.startswith("@WRN:")]


def parse_session_stat(stdout: str) -> tuple[int, int] | None:
    for line in stdout.splitlines():
        if line.startswith("@STAT: sessions|"):
            body = line.split("|", 2)
            if len(body) >= 2 and "/" in body[1]:
                n_s, max_s = body[1].split("/", 1)
                return int(n_s), int(max_s)
    return None


def extract_sid(stdout: str) -> str:
    for line in stdout.splitlines():
        if line.startswith("@SESSION:"):
            return line.split("|", 1)[0].replace("@SESSION:", "").strip()
    raise RuntimeError("no session in reply")


def rss_bytes(pid: int) -> int | None:
    try:
        with open(f"/proc/{pid}/statm", encoding="ascii") as fh:
            pages = int(fh.read().split()[1])
        return pages * int(os.sysconf("SC_PAGE_SIZE"))
    except (OSError, IndexError, ValueError):
        return None


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def schema_prop32() -> str:
    fields = " ".join(PROP32)
    return f"SCHEMA PRT ; fields={fields}\nSCHEMA TSK ; fields=id goal status recycle\n"


def canonical_snapshot(text: str) -> str:
    """Sid-free snapshot body: map + relations + records; drop @SNAP meta."""
    lines: list[str] = []
    skip_snap = False
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if line.startswith("@SNAP:"):
            skip_snap = True
            lines.append("@SNAP: <meta>")
            continue
        if skip_snap:
            skip_snap = False
        lines.append(redact(line))
    body = "\n".join(lines).strip() + "\n"
    assert_sid_free(body)
    return body


def snapshot_write_once_report() -> dict[str, Any]:
    """What exists today. Do not invent write-once in the engine."""
    src = SNAPSHOT_PY.read_text(encoding="utf-8")
    return {
        "write_snapshot_uses_path_write_text": "Path(path).write_text(" in src,
        "engine_o_excl": "O_EXCL" in src,
        "engine_chmod": "chmod" in src,
        "engine_immutable_flag": "immutable" in src.lower() or "chattr" in src,
        "caller_or_filesystem_only": True,
    }


def sec_create(i: int, *, status: str = "active") -> str:
    nid = f"SEC_{i:04d}"
    return (
        "CREATE (:SEC {"
        f"id: {gql_str(nid)}, art: 'ART_doc', heading: {gql_str(f'Part {i}')}, "
        f"numbering: {gql_str(str(i))}, parent: '', order: {gql_str(str(i))}, "
        f"status: {gql_str(status)}, recycle: ''"
        "})"
    )


def populate_batches(
    n_parts: int,
    *,
    text_nodes: int = 8,
    edges: int = 40,
    batch_lines: int = 900,
) -> list[str]:
    """Synthetic document graph: one ART, n SEC parts, USR text, contains edges."""
    lines: list[str] = [
        (
            "CREATE (:ART {id: 'ART_doc', title: 'Synthetic manual', "
            "source: 'synthetic.txt', kind: 'instrument_manual', "
            "status: 'active', recycle: ''})"
        )
    ]
    for i in range(1, n_parts + 1):
        lines.append(sec_create(i))
    sample = "Line one.\nLine two with unicode 测例 Ω.\nPipes | and quotes \"double\" and 'single'."
    for t in range(text_nodes):
        lines.append(
            "CREATE (:USR {"
            f"id: {gql_str(f'USR_txt{t:02d}')}, key: {gql_str(f'blob{t}')}, "
            f"value: {gql_str(sample if t == 0 else f'text-{t}')}, recycle: ''"
            "})"
        )
    n_edges = min(edges, n_parts)
    for i in range(1, n_edges + 1):
        lines.append(
            f"MATCH (a {{id: 'ART_doc'}}), (b {{id: 'SEC_{i:04d}'}})\n"
            f"CREATE (a)-[:contains {{id: 'E_c{i:04d}'}}]->(b)"
        )
    batches: list[str] = []
    cur: list[str] = []
    cur_n = 0
    for stmt in lines:
        n = stmt.count("\n") + 1
        if cur and cur_n + n > batch_lines:
            batches.append("\n".join(cur) + "\n")
            cur = []
            cur_n = 0
        cur.append(stmt)
        cur_n += n
    if cur:
        batches.append("\n".join(cur) + "\n")
    return batches


@dataclass
class ServeReply:
    exit_code: int
    stdout: str
    stderr: str
    keys: tuple[str, ...]
    request: dict[str, Any]

    @property
    def errors(self) -> list[str]:
        return err_lines(self.stderr)


@dataclass
class ServeProc:
    host: str
    port: int
    pid: int
    proc: subprocess.Popen[str]
    snap_dir: Path
    map_file: Path
    timeout_s: float = 120.0

    def send(
        self,
        args: list[str],
        *,
        stdin: str | None = None,
        admin_token: str | None = None,
        admin_usage: bool = False,
        timeout: float | None = None,
    ) -> ServeReply:
        payload: dict[str, Any] = {"args": args}
        if stdin is not None:
            payload["stdin"] = stdin
        if admin_token is not None:
            payload["admin_token"] = admin_token
        if admin_usage:
            payload["admin_usage"] = True
        raw = send_command(
            args,
            stdin=stdin,
            host=self.host,
            port=self.port,
            admin_token=admin_token,
            admin_usage=admin_usage,
            timeout=self.timeout_s if timeout is None else timeout,
        )
        return ServeReply(
            exit_code=int(raw.get("exit_code") or 0),
            stdout=raw.get("stdout") or "",
            stderr=raw.get("stderr") or "",
            keys=tuple(sorted(raw.keys())),
            request=payload,
        )

    def open_session(
        self,
        *,
        map_file: Path | None = None,
        ttl: int | None = None,
        product: str | None = None,
        map_lines: list[str] | None = None,
    ) -> str:
        args = ["session", "open"]
        if map_lines:
            for line in map_lines:
                args.extend(["--map", line])
        else:
            args.extend(["--map-file", str(map_file or self.map_file)])
        if ttl is not None:
            args.extend(["--ttl", str(ttl)])
        if product:
            args.extend(["--product", product])
        reply = self.send(args)
        if reply.exit_code != 0:
            raise RuntimeError(redact(reply.stderr) or "session open failed")
        return extract_sid(reply.stdout)

    def close(self, sid: str) -> ServeReply:
        return self.send(["session", "close", sid])

    def live_count(self) -> tuple[int, int]:
        reply = self.send(["session", "list"])
        parsed = parse_session_stat(reply.stdout)
        if parsed is None:
            raise RuntimeError("no @STAT: sessions on list")
        return parsed

    def mutate(self, sid: str, gql: str, *, caller: str | None = None) -> ServeReply:
        args = ["mutate", "--stdin", "--session", sid]
        if caller:
            args.extend(["--caller", caller])
        return self.send(args, stdin=gql if gql.endswith("\n") else gql + "\n")

    def populate(self, sid: str, n_parts: int, **kwargs: Any) -> list[ServeReply]:
        out: list[ServeReply] = []
        for batch in populate_batches(n_parts, **kwargs):
            reply = self.mutate(sid, batch)
            out.append(reply)
            if reply.exit_code != 0:
                break
        return out

    def pin_map(
        self,
        sid: str,
        *,
        cue: str | None = None,
        kind: str | None = None,
        depth: int | None = None,
        max_rows: int | None = None,
        caller: str | None = None,
        locator: str | None = None,
    ) -> ServeReply:
        args = ["query", "pin-map", "--session", sid]
        if cue:
            args.extend(["--cue", cue])
        if kind:
            args.extend(["--kind", kind])
        if locator:
            args.extend(["--locator", locator])
        if depth is not None:
            args.extend(["--depth", str(depth)])
        if max_rows is not None:
            args.extend(["--max-rows", str(max_rows)])
        if caller:
            args.extend(["--caller", caller])
        return self.send(args)

    def housekeep_stats(self, sid: str, *, caller: str | None = None) -> ServeReply:
        args = ["housekeep", "stats", "--session", sid]
        if caller:
            args.extend(["--caller", caller])
        return self.send(args)

    def expire_status(self) -> ServeReply:
        return self.send(["session", "expire-status"])

    def save(self, sid: str, path: Path, *, caller: str | None = None) -> ServeReply:
        args = ["session", "save", "--file", str(path), "--session", sid]
        if caller:
            args.extend(["--caller", caller])
        return self.send(args)

    def load_file(self, path: Path, *, caller: str | None = None) -> ServeReply:
        args = ["session", "load", "--file", str(path)]
        if caller:
            args.extend(["--caller", caller])
        return self.send(args)

    def load_sid(self, sid: str, *, caller: str | None = None) -> ServeReply:
        args = ["session", "load", "--session", sid]
        if caller:
            args.extend(["--caller", caller])
        return self.send(args)

    def export_pin_map(
        self,
        sid: str,
        *,
        cue: str | None = None,
        caller: str | None = None,
    ) -> ServeReply:
        args = ["export", "pin-map", "--session", sid]
        if cue:
            args.extend(["--cue", cue])
        if caller:
            args.extend(["--caller", caller])
        return self.send(args)

    def grant(self, sid: str, caller: str, *, write_scope: str | None = None) -> ServeReply:
        args = ["session", "acl-grant", "--caller", caller, "--session", sid]
        if write_scope:
            args.extend(["--write-scope", write_scope])
        return self.send(args)

    def acl_bind(self, sid: str, mission_id: str, lease: str) -> ServeReply:
        return self.send(
            [
                "session",
                "acl-bind",
                "--mission-id",
                mission_id,
                "--lease",
                lease,
                "--session",
                sid,
            ]
        )

    def snap_count(self) -> int:
        return len(list(self.snap_dir.glob("*.snap")))

    def usage_report(self) -> ServeReply:
        return self.send(
            ["admin", "usage-report"],
            admin_token=ADMIN_TOKEN,
            admin_usage=True,
        )

    def rss(self) -> int | None:
        return rss_bytes(self.pid)

    def stop(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=4)


def start_serve(
    tmp: Path,
    *,
    ttl_minutes: int = 60,
    max_sessions: int = 1024,
    extra_env: dict[str, str] | None = None,
) -> ServeProc:
    host = "127.0.0.1"
    port = free_port()
    snap_dir = tmp / "expire-snaps"
    snap_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.pop("MEMNET_TEST_INLINE", None)
    env.pop("MEMNET_SESSION", None)
    env.pop("MEMNET_CALLER", None)
    env["MEMNET_SERVE_HOST"] = host
    env["MEMNET_SERVE_PORT"] = str(port)
    env["MEMNET_MAX_SESSIONS"] = str(max_sessions)
    env["MEMNET_SESSION_TTL_MINUTES"] = str(ttl_minutes)
    env["MEMNET_SAVE_ON_EXPIRE"] = "1"
    env["MEMNET_EXPIRE_SNAPSHOT_DIR"] = str(snap_dir)
    env["MEMNET_ADMIN_TOKEN"] = ADMIN_TOKEN
    env["PYTHONUNBUFFERED"] = "1"
    if extra_env:
        env.update(extra_env)
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "memnet",
            "serve",
            "--host",
            host,
            "--port",
            str(port),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.time() + 10
    while time.time() < deadline:
        if proc.poll() is not None:
            err = proc.stderr.read() if proc.stderr else ""
            raise RuntimeError(f"serve exited: {redact(err)}")
        try:
            with socket.create_connection((host, port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.05)
    else:
        proc.kill()
        raise RuntimeError("memnet serve did not start")
    if proc.pid is None:
        raise RuntimeError("serve pid missing")
    return ServeProc(
        host=host,
        port=port,
        pid=int(proc.pid),
        proc=proc,
        snap_dir=snap_dir,
        map_file=TECHDOCS_MAP,
    )


@contextmanager
def running_serve(tmp: Path, **kwargs: Any) -> Iterator[ServeProc]:
    svc = start_serve(tmp, **kwargs)
    try:
        yield svc
    finally:
        svc.stop()


@dataclass
class ItemResult:
    item: str
    verdict: str
    notes: list[str] = field(default_factory=list)
    numbers: dict[str, Any] = field(default_factory=dict)
    wires: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = [f"## {self.item}", f"verdict: {self.verdict}"]
        if self.numbers:
            lines.append("numbers: " + json.dumps(self.numbers, sort_keys=True))
        for w in self.wires:
            lines.append("wire: " + redact(w))
        for n in self.notes:
            lines.append("note: " + redact(n))
        for g in self.gaps:
            lines.append("gap: " + redact(g))
        return "\n".join(lines) + "\n"
