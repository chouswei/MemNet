"""Tests for ensure_usr_row graph helper."""

from __future__ import annotations

from unittest.mock import patch

from novel_mcp.setup_graph import ensure_usr_row


def test_ensure_usr_row_returns_existing():
    with patch("novel_mcp.setup_graph.usr_id_for_key", return_value="USR74"):
        assert ensure_usr_row("mn_x", "opening_offer_neigong") == "USR74"


def test_ensure_usr_row_ingests_when_missing():
    with patch("novel_mcp.setup_graph.usr_id_for_key", return_value=None), patch(
        "novel_mcp.setup_graph.list_tag_data_rows", return_value=[]
    ), patch(
        "novel_mcp.setup_graph.ingest_lines",
        return_value={"exit_code": 0, "errors": []},
    ) as mock_ingest:
        uid = ensure_usr_row(
            "mn_x",
            "opening_offer_neigong",
            preferred_ids=("USR74",),
        )
    assert uid == "USR74"
    mock_ingest.assert_called_once()
    assert "opening_offer_neigong" in mock_ingest.call_args[0][1][0]
