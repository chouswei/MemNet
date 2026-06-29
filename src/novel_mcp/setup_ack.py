"""Persist god-realm setup narration acks on the session graph (generic FSM)."""

from __future__ import annotations

from typing import Any

from novel_mcp.setup_constants import SENTINEL
from novel_mcp.setup_graph import ensure_usr_row, graph_update, read_usr_by_key, usr_id_for_key

SETUP_GOD_ACK_KEY = "setup_god_ack"
SETUP_GOD_ACK_USR_ID = "USR98"
VALID_SETUP_ACK_STEPS = frozenset(
    {"narrate_open", "narrate_pre_pick", "narrate_transmigration"}
)


def _parse_acks(raw: str | None) -> set[str]:
    if not raw or raw == SENTINEL:
        return set()
    return {p.strip() for p in raw.split(";") if p.strip()}


def is_setup_acked(session: str | None, step: str) -> bool:
    if not session or step not in VALID_SETUP_ACK_STEPS:
        return False
    return step in _parse_acks(read_usr_by_key(session, SETUP_GOD_ACK_KEY))


def commit_setup_ack(session: str | None, step: str) -> dict[str, Any]:
    if not session:
        return {"exit_code": 2, "errors": ["missing session"]}
    if step not in VALID_SETUP_ACK_STEPS:
        return {"exit_code": 2, "errors": [f"invalid ack step: {step}"]}

    acks = _parse_acks(read_usr_by_key(session, SETUP_GOD_ACK_KEY))
    if step in acks:
        return {"exit_code": 0, "acked": step, "already": True}

    acks.add(step)
    value = ";".join(sorted(acks))
    usr_id = ensure_usr_row(
        session,
        SETUP_GOD_ACK_KEY,
        initial="_",
        preferred_ids=(SETUP_GOD_ACK_USR_ID, "USR99"),
    )
    if not usr_id:
        return {"exit_code": 2, "errors": ["ack usr row unavailable"]}
    line = f"@USR: {usr_id}|{SETUP_GOD_ACK_KEY}|{value}|persistent"
    code, errors = graph_update(session, [line])

    if code != 0 or errors:
        return {"exit_code": code if code != 0 else 2, "errors": errors or ["ack persist failed"]}
    return {"exit_code": 0, "acked": step, "already": False}


def seed_cli_setup_acks(session: str | None) -> None:
    """CLI/bootstrap paths skip mobile narration — ack all steps so play is not gated."""
    if not session:
        return
    for step in sorted(VALID_SETUP_ACK_STEPS):
        commit_setup_ack(session, step)
