"""Agent id file paths for novel_cursor."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "applications" / "novel_cursor"))

from app_config import load_config, repo_root  # noqa: E402


def test_agent_id_paths() -> None:
    cfg = load_config(app_id="shenjia_caifa")
    assert cfg.agents_dir == repo_root() / "novel-output/shenjia_caifa/agents"
    assert cfg.script_agent_id_file == cfg.agents_dir / "script_agent_id.txt"
    assert cfg.prose_agent_id_file == cfg.agents_dir / "prose_agent_id.txt"
