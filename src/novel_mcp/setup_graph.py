"""MemNet graph helpers for player setup (read-only + update)."""

from __future__ import annotations

import re
from pathlib import Path

from memnet_mcp.client import run_memnet
from novel_mcp.bootstrap import ingest_lines
from novel_mcp.paths import workspace_root
from novel_mcp.setup_constants import SENTINEL

_TAG_MAP_RE = re.compile(r"^@\w+:\s*id\|")


def _parse_wire_line(line: str) -> tuple[str, list[str]] | None:
    s = line.strip()
    if not s.startswith("@") or ":" not in s:
        return None
    tag, body = s.split(":", 1)
    tag = tag.lstrip("@")
    return tag, body.strip().split("|")


def read_get_body(session: str | None, record_id: str) -> str | None:
    if not session:
        return None
    resp = run_memnet(["read", "get", "--id", record_id], session=session)
    if resp.exit_code != 0 or not resp.stdout:
        return None
    for line in resp.stdout.splitlines():
        parsed = _parse_wire_line(line)
        if parsed:
            return "|".join(parsed[1])
    return None


def read_usr_by_key(session: str | None, key: str) -> str | None:
    if not session:
        return None
    resp = run_memnet(["read", "list", "--tag", "USR"], session=session)
    if resp.exit_code != 0:
        return None
    for line in resp.stdout.splitlines():
        parsed = _parse_wire_line(line)
        if not parsed or parsed[0] != "USR":
            continue
        parts = parsed[1]
        if _TAG_MAP_RE.match(line.strip()):
            continue
        if len(parts) >= 3 and parts[1] == key:
            return parts[2]
    return None


def read_usr_record(session: str | None, usr_id: str) -> list[str] | None:
    body = read_get_body(session, usr_id)
    if not body:
        return None
    return body.split("|")


def list_tag_data_rows(session: str | None, tag: str) -> list[list[str]]:
    if not session:
        return []
    resp = run_memnet(["read", "list", "--tag", tag], session=session)
    if resp.exit_code != 0:
        return []
    rows: list[list[str]] = []
    for line in resp.stdout.splitlines():
        parsed = _parse_wire_line(line)
        if not parsed or parsed[0] != tag:
            continue
        if _TAG_MAP_RE.match(line.strip()):
            continue
        rows.append(parsed[1])
    return rows


def first_plr_id(session: str | None) -> str | None:
    rows = list_tag_data_rows(session, "PLR")
    if not rows:
        return None
    return rows[0][0]


def graph_update(session: str | None, lines: list[str]) -> tuple[int, list[str]]:
    if not session or not lines:
        return 2, ["missing session or update lines"]
    resp = run_memnet(
        ["update", "--stdin", "--allow-new-relation"],
        stdin="\n".join(lines),
        session=session,
    )
    return resp.exit_code, list(resp.errors or [])


def graph_apply_setup_lines(session: str | None, lines: list[str]) -> tuple[int, list[str]]:
    """Update USR/PLR; add new EDG/MWU/WUX rows."""
    if not session or not lines:
        return 2, ["missing session or update lines"]
    updates = [ln for ln in lines if ln.startswith("@USR:") or ln.startswith("@PLR:")]
    adds = [ln for ln in lines if ln not in updates]
    errors: list[str] = []
    if updates:
        code, err = graph_update(session, updates)
        if code != 0:
            errors.extend(err or ["update failed"])
    if adds and not errors:
        ing = ingest_lines(session, adds)
        if ing.get("exit_code", 1) != 0:
            errors.extend(ing.get("errors") or ["add failed"])
    return (0 if not errors else 2), errors


def is_setup_locked(session: str | None) -> bool:
    """True after first play beat has started (STEP.n>1 or OLN rows exist)."""
    if not session:
        return False
    step_body = read_get_body(session, "STEP01")
    if step_body:
        parts = step_body.split("|")
        if len(parts) >= 2 and parts[0] == "STEP01":
            try:
                if int(parts[1]) > 1:
                    return True
            except ValueError:
                pass
    for _ in list_tag_data_rows(session, "OLN"):
        return True
    return False


def setup_commit_errors(session: str | None, *, setup_complete: bool) -> list[str]:
    if is_setup_locked(session):
        return ["setup_locked_after_first_beat"]
    if setup_complete:
        return ["setup_already_complete"]
    return []


def resolve_catalog_path(session: str | None, workspace_root_path: str | None = None) -> Path:
    rel = read_usr_by_key(session, "martial_catalog_md")
    if not rel or rel == SENTINEL:
        raise ValueError("missing_usr67_martial_catalog_md")
    root = workspace_root(workspace_root_path)
    return root / rel.replace("\\", "/")


def merge_plr_gender(body_state: str, gender: str) -> str:
    key = f"性別:{gender}"
    if "性別:" in body_state:
        return re.sub(r"性別:[^；;]+", key, body_state, count=1)
    sep = "；" if "；" in body_state else ";"
    return f"{body_state}{sep}{key}" if body_state else key
