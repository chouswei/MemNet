"""Tests for chapter_io append/replace."""

from __future__ import annotations

from pathlib import Path

from memnet_mcp.chapter_io import chapter_prose_append, chapter_heading


def _zh(n: int) -> str:
    return "字" * n


def test_append_rejects_short_prose(tmp_path: Path):
    result = chapter_prose_append(
        _zh(150),
        chapter_dir="chapters",
        chp_num=1,
        workspace_root=tmp_path,
    )
    assert result["exit_code"] == 1
    assert result["status"] == "short"
    assert not (tmp_path / "chapters" / "第001回.md").exists()


def test_append_first_paragraph(tmp_path: Path):
    result = chapter_prose_append(
        _zh(450),
        chapter_dir="chapters",
        chp_num=1,
        workspace_root=tmp_path,
    )
    assert result["exit_code"] == 0
    assert result["appended_chars"] == 450
    assert result["file_char_total"] == 450
    assert result["paragraph_count"] == 1
    path = tmp_path / "chapters" / "第001回.md"
    text = path.read_text(encoding="utf-8")
    assert text.startswith(chapter_heading(1))
    assert _zh(450) in text


def test_append_second_paragraph(tmp_path: Path):
    chapter_prose_append(_zh(400), chapter_dir="ch", chp_num=1, workspace_root=tmp_path)
    result = chapter_prose_append(_zh(500), chapter_dir="ch", chp_num=1, workspace_root=tmp_path)
    assert result["exit_code"] == 0
    assert result["file_char_total"] == 900
    assert result["paragraph_count"] == 2


def test_replace_last_paragraph(tmp_path: Path):
    chapter_prose_append(_zh(400), chapter_dir="ch", chp_num=1, workspace_root=tmp_path)
    chapter_prose_append(_zh(420), chapter_dir="ch", chp_num=1, workspace_root=tmp_path)
    result = chapter_prose_append(
        _zh(550),
        chapter_dir="ch",
        chp_num=1,
        workspace_root=tmp_path,
        replace_last_paragraph=True,
    )
    assert result["exit_code"] == 0
    assert result["file_char_total"] == 950
    assert result["paragraph_count"] == 2
    assert result["replaced_last"] is True


def test_replace_last_without_paragraph_fails(tmp_path: Path):
    result = chapter_prose_append(
        _zh(450),
        chapter_dir="ch",
        chp_num=2,
        workspace_root=tmp_path,
        replace_last_paragraph=True,
    )
    assert result["exit_code"] == 1
    assert "no_paragraph" in result["errors"][0]
