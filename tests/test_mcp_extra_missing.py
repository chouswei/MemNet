"""memnet-mcp without the [mcp] extra fails fast with one line (score §1.7, D-M1..D-M3).

Red-first for symphony restart-restore (node P-type). Each case runs
``python -m memnet_mcp`` in a subprocess whose import system refuses ``mcp`` (or
``uvicorn``), as on a host that installed ``memnet-llm`` without ``[mcp]``. It must
write exactly one stderr line, exit 2, print nothing on stdout and show no
traceback, for every transport and for ``--help``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HINT = "pip install 'memnet-llm[mcp]'"

_SCRIPT = textwrap.dedent(
    """
    import sys

    BLOCKED = {blocked!r}

    class _Missing:
        def find_spec(self, name, path=None, target=None):
            if name == BLOCKED or name.startswith(BLOCKED + "."):
                raise ImportError(f"No module named {{name!r}}", name=name)
            return None

    for _m in [m for m in sys.modules if m == BLOCKED or m.startswith(BLOCKED + ".")]:
        del sys.modules[_m]
    sys.meta_path.insert(0, _Missing())
    sys.argv = ["memnet-mcp", *{argv!r}]

    import runpy

    runpy.run_module("memnet_mcp", run_name="__main__", alter_sys=True)
    """
)


def _line(module: str) -> str:
    return (
        f"@ERR: mcp_extra_missing|memnet-mcp needs the mcp extra (missing module: {module}); "
        f"install with: {HINT}"
    )


def _env(tmp: Path) -> dict[str, str]:
    # keep any run that gets past the check off the real snapshot dirs
    env = dict(os.environ)
    env["MEMNET_TEST_INLINE"] = "1"
    env["MEMNET_SNAPSHOT_DIR"] = str(tmp / "snap")
    env["MEMNET_EXPIRE_SNAPSHOT_DIR"] = str(tmp / "expire")
    env["MEMNET_REQUEST_LOG"] = str(tmp / "request.log")
    return env


def _run(tmp: Path, blocked: str, argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", _SCRIPT.format(blocked=blocked, argv=argv)],
        capture_output=True,
        text=True,
        timeout=30,
        stdin=subprocess.DEVNULL,
        cwd=str(REPO),
        env=_env(tmp),
    )


_ARGVS = [
    pytest.param(["--transport", "stdio"], id="stdio"),
    pytest.param(["--transport", "streamable-http"], id="streamable-http"),
    pytest.param(["--transport", "gateway"], id="gateway"),
    pytest.param(["--help"], id="help"),
]


@pytest.mark.parametrize("blocked", ["mcp", "uvicorn"])
@pytest.mark.parametrize("argv", _ARGVS)
def test_missing_extra_one_line_exit_2(tmp_path, blocked, argv):
    proc = _run(tmp_path, blocked, argv)
    assert "Traceback" not in proc.stderr, proc.stderr[-2000:]
    assert proc.returncode == 2, (proc.returncode, proc.stderr[-2000:])
    assert proc.stdout == "", proc.stdout[-2000:]
    assert proc.stderr.splitlines() == [_line(blocked)], proc.stderr[-2000:]
    assert proc.stderr.endswith("\n")


def test_entry_module_interface():
    from memnet_mcp import entry

    assert entry.MCP_EXTRA_HINT == HINT
    assert callable(entry.main)
    assert callable(entry.require_mcp_extra)


def test_console_script_points_at_entry():
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["scripts"]["memnet-mcp"] == "memnet_mcp.entry:main"


def test_with_extra_help_still_works(tmp_path):
    # guard: with the extra present, --help still prints usage and exits 0
    proc = subprocess.run(
        [sys.executable, "-m", "memnet_mcp", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
        stdin=subprocess.DEVNULL,
        cwd=str(REPO),
        env=_env(tmp_path),
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "usage" in proc.stdout.lower()
    assert "mcp_extra_missing" not in proc.stderr
