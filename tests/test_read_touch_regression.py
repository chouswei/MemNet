"""MN-REQ-05.5 read-touch regression guard. Not xfail: passes on the shipped engine.

Every caller read in READ_SURFACES moves modified_at today, except get_session.
The session-scoped CLI path (MCP reads and CLI-only reads) calls _load_session,
which touches. The in-process get_session() only extends the TTL, so it is
marked xfail(strict=True): the mark must come off when the touch rule ships,
and it fails loudly if that happens without the mark being removed.

test_open_stamps_first_touch is the open side of the same rule: open is the
first touch, so modified_at = created_at right after open. It is strict xfail
until the engine stamps it.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from evict_surfaces import READ_SURFACES
from memnet.cli import app
from memnet.registry import get_entry
from memnet.session import open_session, set_now_override
from test_session_evict import BASE, caller_read, runner


def _instant(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _seeded_session(schema_file, workflow_file) -> str:
    set_now_override(BASE)
    sid = open_session(map_file=str(schema_file), ttl_minutes=600).session_id
    r = runner.invoke(app, ["add", "--file", str(workflow_file), "--session", sid])
    assert r.exit_code == 0, "seed write failed"
    return sid


_GET_SESSION_XFAIL = pytest.mark.xfail(
    strict=True,
    reason="get_session() only extends the TTL; the touch rule is not shipped",
)
# Module-level so the sync test can read the get_session mark from the parameter set.
SURFACE_PARAMS = [
    pytest.param(surface, marks=_GET_SESSION_XFAIL)
    if surface == "get_session"
    else pytest.param(surface)
    for surface in READ_SURFACES
]


@pytest.mark.parametrize("surface", SURFACE_PARAMS)
def test_cli_path_read_moves_modified_at(memnet_temp, schema_file, workflow_file, surface):
    sid = _seeded_session(schema_file, workflow_file)
    before = get_entry(sid).meta.modified_at
    set_now_override(BASE + timedelta(minutes=3))
    assert caller_read(surface, sid) == 0, f"{surface} read must succeed before its touch"
    after = get_entry(sid).meta.modified_at
    assert _instant(after) > _instant(before), f"{surface} must set modified_at"


@pytest.mark.xfail(
    strict=True,
    reason="open does not stamp modified_at yet; open is the first touch once the rule ships",
)
def test_open_stamps_first_touch(memnet_temp, schema_file):
    set_now_override(BASE)
    sid = open_session(map_file=str(schema_file), ttl_minutes=600).session_id
    meta = get_entry(sid).meta
    assert meta.modified_at == meta.created_at, "open is the first touch: modified_at = created_at"
