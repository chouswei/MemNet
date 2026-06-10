"""Wire format and sanitiser tests."""

from __future__ import annotations

import pytest

from memnet.exceptions import MemNetError
from memnet.sanitiser import sanitise_batch, sanitise_line


def test_json_rejected():
    with pytest.raises(MemNetError) as exc:
        sanitise_line('{"tag":"NPC"}')
    assert exc.value.code == "json_not_supported"


def test_strip_fences():
    lines = sanitise_batch(["```", "@PLR: PLR01|a|1|0|0|0|x", "```"])
    assert len(lines) == 1
    assert lines[0].startswith("@PLR:")
