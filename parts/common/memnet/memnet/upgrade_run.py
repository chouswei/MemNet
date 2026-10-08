"""Operator helper for a side-by-side venv upgrade (MN-REQ-06.14).

Order is fixed: the caller must confirm memnet-mcp and the gateway already
retry ``serve_draining``. This process then preflights the new interpreter,
drains, swaps ExecStart, updates the gateway pin, starts the new serve, and
rolls back to the unit backup if verification fails.

No session ids are printed. Tokens are read from the environment.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from memnet.exceptions import MemNetError
from memnet.upgrade import (
    MANIFEST_NAME,
    RESTORE_NAME,
    SUPPORTED_SNAPSHOT_FORMATS,
    retire_manifest,
)

_PROBE = (
    "import json,memnet\n"
    "from memnet.upgrade import SUPPORTED_SNAPSHOT_FORMATS\n"
    "print(json.dumps({'version': memnet.__version__, "
    "'formats': list(SUPPORTED_SNAPSHOT_FORMATS)}))\n"
)


class UpgradeRunError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def swap_execstart(text: str, new_exec: str) -> str:
    """Replace every ExecStart= line. The previous text is the rollback copy."""
    lines = text.splitlines(keepends=True)
    found = False
    out: list[str] = []
    for line in lines:
        if line.startswith("ExecStart="):
            nl = "\n" if line.endswith("\n") else ""
            out.append(f"ExecStart={new_exec}{nl}")
            found = True
        else:
            out.append(line)
    if not found:
        raise UpgradeRunError("upgrade_unit", "unit has no ExecStart")
    return "".join(out)


def set_pinned_version(config_text: str, product: str, version: str) -> str:
    data = json.loads(config_text)
    products = data.get("products")
    if not isinstance(products, dict) or product not in products:
        raise UpgradeRunError("upgrade_pin", "product is not in the gateway config")
    row = products[product]
    if not isinstance(row, dict):
        raise UpgradeRunError("upgrade_pin", "product entry must be an object")
    row["pinned_version"] = version
    return json.dumps(data, indent=2) + "\n"


def preflight_new_python(python: str, directory: Path) -> dict[str, Any]:
    """Import the new version and check snapshot format support."""
    proc = subprocess.run(
        [python, "-c", _PROBE],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise UpgradeRunError("upgrade_preflight", "new interpreter failed to import memnet")
    try:
        info = json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        raise UpgradeRunError("upgrade_preflight", "new interpreter probe was not JSON") from exc
    formats = set(info.get("formats") or [])
    manifest_path = directory / MANIFEST_NAME
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        fmt = int(manifest.get("snapshot_format") or 0)
        if fmt not in formats:
            raise UpgradeRunError(
                "upgrade_snapshot_format",
                f"new version cannot load snapshot format {fmt}",
            )
    elif snapshot_local_format() not in formats:
        raise UpgradeRunError(
            "upgrade_snapshot_format",
            "new version cannot load the current snapshot format",
        )
    return info


def snapshot_local_format() -> int:
    return int(SUPPORTED_SNAPSHOT_FORMATS[0])


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def run_upgrade(
    *,
    new_python: str,
    new_exec: str,
    state: Path,
    clients_ready: bool,
    unit_path: Path | None = None,
    gateway_config: Path | None = None,
    product: str | None = None,
    admin_token: str | None = None,
    allow_unsaved: bool = False,
    restarter: Callable[[], None] | None = None,
    drainer: Callable[[], Any] | None = None,
    verify_wait_s: float = 30.0,
) -> dict[str, Any]:
    """Drain, swap, verify. Roll back the unit and pin if verify fails."""
    if not clients_ready:
        raise UpgradeRunError(
            "upgrade_clients",
            "deploy memnet-mcp and gateway retry before the serve swap",
        )
    info = preflight_new_python(new_python, state)
    token = admin_token if admin_token is not None else os.environ.get("MEMNET_ADMIN_TOKEN")
    if drainer is None:
        _drain_via_serve(state, token, allow_unsaved=allow_unsaved)
    else:
        drainer()
    unit_backup: str | None = None
    pin_backup: str | None = None
    if unit_path is not None:
        unit_backup = _read(unit_path)
        backup_path = unit_path.with_suffix(unit_path.suffix + ".bak")
        _write(backup_path, unit_backup)
        _write(unit_path, swap_execstart(unit_backup, new_exec))
    if gateway_config is not None:
        if not product:
            raise UpgradeRunError("upgrade_pin", "product is required to update the pin")
        pin_backup = _read(gateway_config)
        pin_path = gateway_config.with_suffix(gateway_config.suffix + ".bak")
        _write(pin_path, pin_backup)
        _write(
            gateway_config,
            set_pinned_version(pin_backup, product, str(info["version"])),
        )
    if restarter is not None:
        restarter()
    report = _wait_restore(state, verify_wait_s)
    if report is None or int(report.get("failed") or 0) != 0 or report.get("skipped"):
        _rollback(unit_path, unit_backup, gateway_config, pin_backup, restarter)
        raise UpgradeRunError("upgrade_verify", "restore did not verify; rolled back")
    retire_manifest(state)
    return {"ok": True, "version": info["version"], "restored": int(report.get("ok") or 0)}


def _drain_via_serve(state: Path, token: str | None, *, allow_unsaved: bool) -> None:
    from memnet.serve import send_command

    args = ["admin", "upgrade-prepare", "--state-dir", str(state)]
    if allow_unsaved:
        args.append("--allow-unsaved")
    raw = send_command(args, admin_token=token, timeout=120.0)
    if int(raw.get("exit_code") or 1) != 0:
        raise UpgradeRunError("upgrade_drain", "drain did not reach ready_to_stop")


def _wait_restore(state: Path, timeout_s: float) -> dict[str, Any] | None:
    deadline = time.monotonic() + timeout_s
    path = state / RESTORE_NAME
    while time.monotonic() < deadline:
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                time.sleep(0.05)
                continue
            if isinstance(data, dict):
                return data
        time.sleep(0.05)
    return None


def _rollback(
    unit_path: Path | None,
    unit_backup: str | None,
    gateway_config: Path | None,
    pin_backup: str | None,
    restarter: Callable[[], None] | None,
) -> None:
    if unit_path is not None and unit_backup is not None:
        _write(unit_path, unit_backup)
    if gateway_config is not None and pin_backup is not None:
        _write(gateway_config, pin_backup)
    if restarter is not None:
        restarter()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="memnet-upgrade")
    parser.add_argument("--new-python", required=True)
    parser.add_argument("--new-exec", required=True, help="New unit ExecStart value")
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--unit", default="")
    parser.add_argument("--gateway-config", default="")
    parser.add_argument("--product", default="")
    parser.add_argument("--allow-unsaved", action="store_true")
    parser.add_argument(
        "--clients-ready",
        action="store_true",
        help="Confirm memnet-mcp and the gateway already retry serve_draining",
    )
    parser.add_argument("--restart-unit", default="", help="systemctl unit name to restart")
    args = parser.parse_args(argv)
    restarter = None
    if args.restart_unit:
        unit_name = args.restart_unit

        def restarter() -> None:
            subprocess.run(["systemctl", "restart", unit_name], check=True)

    try:
        result = run_upgrade(
            new_python=args.new_python,
            new_exec=args.new_exec,
            state=Path(args.state_dir),
            clients_ready=args.clients_ready,
            unit_path=Path(args.unit) if args.unit else None,
            gateway_config=Path(args.gateway_config) if args.gateway_config else None,
            product=args.product or None,
            allow_unsaved=args.allow_unsaved,
            restarter=restarter,
        )
    except (UpgradeRunError, MemNetError) as exc:
        code = getattr(exc, "code", "upgrade")
        sys.stderr.write(f"@ERR: {code}|{exc}\n")
        return 2
    sys.stdout.write(json.dumps({"ok": True, "restored": result["restored"]}) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
