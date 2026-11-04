"""A real 0.20.4 build next to this one, and serve processes on either build (upgrade tests).

The old code comes from git history (``git archive``) into a temp venv. The venv reads its
third-party deps from this interpreter's site-packages through a ``.pth`` line, so no
network is needed and this checkout's editable install is not visible to it.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import sysconfig
import tarfile
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import pytest

from memnet.serve import probe, send_command

OLD_COMMIT = "0a9c7c5"
OLD_VERSION = "0.20.4"
REPO = Path(__file__).resolve().parents[1]
TOKEN = "test-admin-token"
HOST = "127.0.0.1"
_SOURCE_DIRS = ("parts/common/memnet", "parts/memnet-mcp/software")


@dataclass(frozen=True)
class Build:
    venv: Path
    python: Path

    def client_argv(self, args: list[str]) -> list[str]:
        """The ``memnet`` console script (memnet.cli:main), which forwards to a serve."""
        return [str(self.python), "-c", "from memnet.cli import main; main()", *args]


def _git(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, timeout=60)


def build_old(root: Path) -> Build:
    """Unpack OLD_COMMIT into a temp venv, or skip when the history is not in this clone."""
    if shutil.which("git") is None:
        pytest.skip("git is not installed; the 0.20.4 build comes from git history")
    if _git("cat-file", "-e", f"{OLD_COMMIT}^{{commit}}").returncode != 0:
        pytest.skip(
            f"commit {OLD_COMMIT} (0.20.4) is not in this clone (shallow?); "
            "fetch full history (fetch-depth: 0) to run the cross-version upgrade tests"
        )
    archive = _git("archive", "--format=tar", OLD_COMMIT, *_SOURCE_DIRS)
    assert archive.returncode == 0, archive.stderr.decode(errors="replace")
    src = root / "src-0.20.4"
    with tarfile.open(fileobj=BytesIO(archive.stdout)) as tar:
        tar.extractall(src, filter="data")
    venv = root / "venv-0.20.4"
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True, timeout=60
    )
    python = venv / "bin" / "python"
    site = Path(
        subprocess.run(
            [str(python), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout.strip()
    )
    deps = {sysconfig.get_path("purelib"), sysconfig.get_path("platlib")}
    lines = [str(src / part) for part in _SOURCE_DIRS] + sorted(deps)
    (site / "memnet_old_build.pth").write_text("\n".join(lines) + "\n", encoding="utf-8")
    seen = subprocess.run(
        [str(python), "-c", "import memnet; print(memnet.__version__, memnet.__file__)"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert seen.returncode == 0, seen.stderr
    version, where = seen.stdout.split()
    assert version == OLD_VERSION and Path(where).is_relative_to(src), seen.stdout
    return Build(venv=venv, python=python)


def new_build(root: Path) -> Build:
    """This checkout, behind a venv-shaped wrapper (``bin/python``) so a link can swap it."""
    venv = root / "venv-new"
    (venv / "bin").mkdir(parents=True)
    python = venv / "bin" / "python"
    python.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n', encoding="utf-8")
    python.chmod(0o755)
    return Build(venv=venv, python=python)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return int(sock.getsockname()[1])


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class Serve:
    """One state dir and one port; serve processes on either build in turn."""

    def __init__(self, tmp_path: Path, schema_file: Path) -> None:
        self.port = free_port()
        self.state = tmp_path / "state"
        self.state.mkdir()
        self.schema = schema_file
        self.log = tmp_path / "serve.log"
        self.pidfile = tmp_path / "serve.pid"
        self.proc: subprocess.Popen[bytes] | None = None
        env = os.environ.copy()
        env.update(
            {
                "MEMNET_ADMIN_TOKEN": TOKEN,
                "MEMNET_STATE_DIR": str(self.state),
                "MEMNET_SERVE_HOST": HOST,
                "MEMNET_SERVE_PORT": str(self.port),
            }
        )
        # Earlier in-process tests leave MEMNET_SERVE_INTERNAL set; a client must forward.
        for key in (
            "MEMNET_TEST_INLINE",
            "MEMNET_SERVE_INTERNAL",
            "MEMNET_SESSION",
            "MEMNET_IPC_SOCKET",
        ):
            env.pop(key, None)
        self.env = env

    def log_text(self) -> str:
        return self.log.read_text(encoding="utf-8") if self.log.is_file() else ""

    def serve_argv(self, python: Path | str) -> list[str]:
        return [str(python), "-m", "memnet", "serve", "--host", HOST, "--port", str(self.port)]

    def start(self, build: Build, timeout_s: float = 20.0) -> None:
        handle = self.log.open("a", encoding="utf-8")
        self.proc = subprocess.Popen(
            self.serve_argv(build.python), env=self.env, stdout=handle, stderr=subprocess.STDOUT
        )
        handle.close()
        self.pidfile.write_text(f"{self.proc.pid}\n", encoding="utf-8")
        self.wait_up(timeout_s)

    def wait_up(self, timeout_s: float = 20.0) -> None:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if probe(host=HOST, port=self.port):
                return
            if self.proc is not None and self.proc.poll() is not None:
                break
            time.sleep(0.05)
        raise AssertionError(f"serve did not come up: {self.log_text()[-2000:]}")

    def wait_down(self, timeout_s: float = 10.0) -> None:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline and probe(host=HOST, port=self.port):
            time.sleep(0.05)
        assert not probe(host=HOST, port=self.port), "port still open after stop"

    def stop(self, sig: int = signal.SIGTERM) -> None:
        proc, self.proc = self.proc, None
        if proc is not None and proc.poll() is None:
            proc.send_signal(sig)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
        self.wait_down()

    def kill_any(self) -> None:
        """Teardown: the tracked process, and one a start command left in the pid file."""
        if self.pidfile.is_file():
            try:
                os.kill(int(self.pidfile.read_text().strip()), signal.SIGKILL)
            except (OSError, ValueError):
                pass
        self.stop(signal.SIGKILL)

    def cmd(self, args: list[str], *, stdin: str | None = None, admin: bool = False) -> dict:
        return send_command(
            args,
            stdin=stdin,
            host=HOST,
            port=self.port,
            admin_token=TOKEN if admin else None,
            timeout=30,
        )

    def client(self, build: Build, args: list[str], *, stdin: str | None = None):
        """Run the ``memnet`` client of ``build`` as its own process against this serve."""
        return subprocess.run(
            build.client_argv(args),
            input=stdin,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def open(self) -> str:
        got = self.cmd(["session", "open", "--map-file", str(self.schema), "--ttl", "30"])
        assert got["exit_code"] == 0, got
        return got["stdout"].split("|", 1)[0].replace("@SESSION: ", "").strip()

    def mutate(self, sid: str, text: str) -> None:
        got = self.cmd(["mutate", "--stdin", "--session", sid], stdin=text)
        assert got["exit_code"] == 0, got

    def find(self, sid: str) -> list[str]:
        got = self.cmd(["query", "find", "--kind", "TSK", "--limit", "20", "--session", sid])
        assert got["exit_code"] == 0, got
        return sorted(got["stdout"].splitlines())

    def session_ids(self) -> set[str]:
        got = self.cmd(["session", "list"])
        assert got["exit_code"] == 0, got
        return {
            line.split("|", 1)[0].replace("@SESSION: ", "").strip()
            for line in got["stdout"].splitlines()
            if line.startswith("@SESSION: ")
        }

    def prepare(self) -> dict:
        got = self.cmd(["admin", "upgrade-prepare", "--state-dir", str(self.state)], admin=True)
        assert got["exit_code"] == 0, got
        assert "upgrade_prepare|ready|" in got["stderr"], got
        return read_json(self.state / "upgrade-manifest.json")


def seed(serve: Serve, sessions: int = 3) -> list[str]:
    """Open small sessions: session i gets 3+i TSK nodes and 2+i owns relations."""
    sids = [serve.open() for _ in range(sessions)]
    for idx, sid in enumerate(sids):
        nodes = 3 + idx
        lines = [
            f"CREATE (:TSK {{id: 'TSK_{idx}_{n}', goal: 's{idx}-n{n}', status: 'open'}})"
            for n in range(nodes)
        ]
        for n in range(2 + idx):
            src, dst = n % nodes, (n + 1) % nodes
            lines.append(
                f"MATCH (a {{id: 'TSK_{idx}_{src}'}}), (b {{id: 'TSK_{idx}_{dst}'}}) "
                f"CREATE (a)-[:owns {{id: 'E_{idx}_{n}'}}]->(b)"
            )
        serve.mutate(sid, "\n".join(lines) + "\n")
    return sids
