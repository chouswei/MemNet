"""MN-REQ-05.5 read-touch regression guard.

Every caller read in READ_SURFACES moves modified_at, the in-process get_session()
included. The session-scoped CLI path (MCP reads and CLI-only reads) calls
_load_session, which touches.

test_open_stamps_first_touch is the open side of the same rule: open is the
first touch, so modified_at = created_at right after open.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from evict_surfaces import BASE, READ_SURFACES, caller_read, runner
from memnet.cli import app
from memnet.registry import get_entry
from memnet.session import open_session, set_now_override


def _instant(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _seeded_session(schema_file, workflow_file) -> str:
    set_now_override(BASE)
    sid = open_session(map_file=str(schema_file), ttl_minutes=600).session_id
    r = runner.invoke(app, ["add", "--file", str(workflow_file), "--session", sid])
    assert r.exit_code == 0, "seed write failed"
    return sid


SURFACE_PARAMS = [pytest.param(surface) for surface in READ_SURFACES]


@pytest.mark.parametrize("surface", SURFACE_PARAMS)
def test_cli_path_read_moves_modified_at(memnet_temp, schema_file, workflow_file, surface):
    sid = _seeded_session(schema_file, workflow_file)
    before = get_entry(sid).meta.modified_at
    set_now_override(BASE + timedelta(minutes=3))
    assert caller_read(surface, sid) == 0, f"{surface} read must succeed before its touch"
    after = get_entry(sid).meta.modified_at
    assert _instant(after) > _instant(before), f"{surface} must set modified_at"


def test_open_stamps_first_touch(memnet_temp, schema_file):
    set_now_override(BASE)
    sid = open_session(map_file=str(schema_file), ttl_minutes=600).session_id
    meta = get_entry(sid).meta
    assert meta.modified_at == meta.created_at, "open is the first touch: modified_at = created_at"
