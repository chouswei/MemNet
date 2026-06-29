"""Tests for setup_ack graph persistence."""

from __future__ import annotations

from unittest.mock import patch

from novel_mcp.setup_ack import (
    SETUP_GOD_ACK_KEY,
    commit_setup_ack,
    is_setup_acked,
)


def test_is_setup_acked_parses_semicolon_list():
    with patch(
        "novel_mcp.setup_ack.read_usr_by_key",
        return_value="narrate_open;narrate_pre_pick",
    ):
        assert is_setup_acked("mn_x", "narrate_open")
        assert is_setup_acked("mn_x", "narrate_pre_pick")
        assert not is_setup_acked("mn_x", "narrate_transmigration")


def test_commit_setup_ack_writes_graph():
    with patch("novel_mcp.setup_ack.read_usr_by_key", return_value=None), patch(
        "novel_mcp.setup_ack.ensure_usr_row", return_value="USR98"
    ), patch(
        "novel_mcp.setup_ack.graph_update", return_value=(0, [])
    ) as mock_update:
        out = commit_setup_ack("mn_x", "narrate_open")
    assert out["exit_code"] == 0
    assert out["acked"] == "narrate_open"
    mock_update.assert_called_once()


def test_commit_setup_ack_updates_existing_row():
    with patch("novel_mcp.setup_ack.read_usr_by_key", return_value="narrate_open"), patch(
        "novel_mcp.setup_ack.ensure_usr_row", return_value="USR98"
    ), patch(
        "novel_mcp.setup_ack.graph_update", return_value=(0, [])
    ) as mock_update:
        out = commit_setup_ack("mn_x", "narrate_open")
    assert out["exit_code"] == 0
    assert out["already"] is True
    mock_update.assert_not_called()
