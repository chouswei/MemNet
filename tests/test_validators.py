"""Tests for finish validators."""

from __future__ import annotations

from novel_mcp.validators import validate_option_lines

WARM = """\
@LAW: LAW-PERS02|選項|1|opt_readable_baihua|full_sentence;no_action_chain;max_chars:28
@USR: U1|option_style|12-28字|persistent
"""


def test_validate_options_rejects_action_chain():
    hints = validate_option_lines(
        ["起身，端水，回坊"],
        warm_stdout=WARM,
    )
    assert hints["violations"]


def test_validate_options_auto_beat():
    hints = validate_option_lines(
        ["我先歇一會兒。"],
        warm_stdout=WARM,
        auto_beat=True,
    )
    assert any("auto_beat" in v for v in hints["violations"])


def test_validate_options_slot6_lib_template_shorter_than_min():
    warm = WARM + "@USR: U2|lib_opt_copy|閉目入殿查閱|persistent\n"
    hints = validate_option_lines(
        ["", "", "", "", "", "閉目入殿查閱"],
        warm_stdout=warm,
    )
    assert not any("option_short" in v and "slot 6" in v for v in hints["violations"])
