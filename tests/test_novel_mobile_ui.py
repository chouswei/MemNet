"""Static layout tests for novel_mobile SPA (2/3 narrative + 1/3 system chrome)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_root = Path(__file__).resolve().parents[1]
_static = _root / "applications" / "novel_mobile" / "static"
sys.path.insert(0, str(_root / "applications" / "novel_cursor"))
sys.path.insert(0, str(_root / "src"))
sys.path.insert(0, str(_root / "applications" / "novel_mobile"))

from app_config import NovelAppConfig
from novel_mobile.server import create_app


def _config(tmp_path: Path) -> NovelAppConfig:
    out = tmp_path / "out"
    out.mkdir()
    (out / "session_id.txt").write_text("mn_fixture\n", encoding="utf-8")
    return NovelAppConfig(
        app_id="shenjia_caifa",
        seed_md=tmp_path / "seed.md",
        title="工匠傳奇",
        output_dir=out,
        chapter_dir=out / "chapters",
        snapshot_file=out / "session_snap.json",
        session_id_file=out / "session_id.txt",
        last_beat_file=out / "last_beat.json",
        agents_dir=out / "agents",
    )


@pytest.fixture
def static_client(tmp_path, monkeypatch):
    cfg = _config(tmp_path)
    monkeypatch.setattr("novel_mobile.server.probe_serve", lambda: True)
    monkeypatch.setattr("novel_mobile.server._llm_configured", lambda: True)
    monkeypatch.setattr(
        "novel_mobile.server.read_player_setup",
        lambda session, **kw: {
            "exit_code": 0,
            "setup_complete": False,
            "setup_guidance": {"next_action": "narrate_open"},
        },
    )
    return TestClient(create_app(cfg))


def test_index_html_split_layout():
    html = (_static / "index.html").read_text(encoding="utf-8")
    assert 'id="narrative-pane"' in html
    assert 'id="system-pane"' in html
    assert 'id="narrative-options"' in html
    assert 'id="panel-choices"' in html
    for overlay in ("items-overlay", "skills-overlay", "production-overlay"):
        assert f'id="{overlay}"' in html
    assert 'id="narrative-party"' in html
    assert "party-overlay" not in html
    assert 'data-tab="party"' in html
    party_pos = html.index("narrative-party")
    system_pos = html.index("system-pane")
    assert party_pos < system_pos
    assert 'data-tab="skills"' in html
    assert "system-body" not in html
    assert 'id="panel-items"' not in html
    assert 'id="items-panel"' in html
    assert 'id="skills-panel"' in html
    assert 'id="production-panel"' in html
    narrative_pos = html.index("narrative-pane")
    options_pos = html.index("narrative-options")
    system_pos = html.index("system-pane")
    items_overlay_pos = html.index("items-overlay")
    assert narrative_pos < options_pos < system_pos < items_overlay_pos


def test_css_flex_ratio_and_choice_styles():
    css = (_static / "app.css").read_text(encoding="utf-8")
    assert re.search(r"#narrative-pane\s*\{[^}]*flex:\s*2", css, re.S)
    assert re.search(r"#system-pane\s*\{[^}]*flex:\s*1", css, re.S)
    assert "#narrative-options" in css
    assert ".sheet-overlay" in css
    assert ".sheet-window-body" in css
    assert ".choice-read-item" in css
    assert ".choice-num-btn" in css
    assert ".choice-btn" not in css


def test_separate_sheet_modules():
    html = (_static / "index.html").read_text(encoding="utf-8")
    for script in (
        "sheet_common.js",
        "sheet_items.js",
        "sheet_skills.js",
        "sheet_production.js",
        "sheet_party.js",
        "sheet.js",
    ):
        assert script in html
    assert "NovelItemsPanel" in (_static / "sheet_items.js").read_text(encoding="utf-8")
    assert "NovelSkillsPanel" in (_static / "sheet_skills.js").read_text(encoding="utf-8")
    assert "NovelProductionPanel" in (_static / "sheet_production.js").read_text(encoding="utf-8")
    party_js = (_static / "sheet_party.js").read_text(encoding="utf-8")
    assert "NovelPartyPanel" in party_js
    assert "narrative-party" in party_js


def test_sheet_facade_delegates():
    js = (_static / "sheet.js").read_text(encoding="utf-8")
    assert "NovelItemsPanel" in js
    assert "NovelSkillsPanel" in js
    assert "NovelProductionPanel" in js
    assert "NovelPartyPanel" in js
    assert "closeSheet" in js


def test_play_js_splits_option_text_and_number_buttons():
    js = (_static / "play.js").read_text(encoding="utf-8")
    assert "narrative-options" in js
    assert "choice-read-item" in js
    assert "choice-num-btn" in js
    assert 'btn.textContent = String(n)' in js
    assert "n + \". \" + text" not in js


def test_index_served(static_client):
    r = static_client.get("/")
    assert r.status_code == 200
    body = r.text
    assert "narrative-pane" in body
    assert "items-overlay" in body
    assert "skills-overlay" in body
    assert "production-overlay" in body
    assert "narrative-party" in body
    assert "party-overlay" not in body


def test_static_assets_served(static_client):
    for path in (
        "/static/app.css",
        "/static/play.js",
        "/static/sheet_items.js",
        "/static/sheet_skills.js",
        "/static/sheet_production.js",
    ):
        r = static_client.get(path)
        assert r.status_code == 200
        assert r.text
