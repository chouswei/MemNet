"""Tests for seed bootstrap helper."""

from __future__ import annotations

from novel_mcp.bootstrap import fence_lines, seed_lines_from_md


def test_fence_and_seed_lines():
    md = """\
# Title

## Tag map

```text
@PLR: id|name
```

## Opening seed — Engine

```text
@STEP: STEP01|1|SCN|persistent
```

## Opening seed — World

```text
@PLR: P01|hero|0|0|0|0|bag
```
"""
    assert fence_lines(md, "Tag map") == ["@PLR: id|name"]
    seeds = seed_lines_from_md(md)
    assert any("STEP01" in ln for ln in seeds)
    assert any("P01" in ln for ln in seeds)
