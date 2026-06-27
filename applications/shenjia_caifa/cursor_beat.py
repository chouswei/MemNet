#!/usr/bin/env python3
"""Legacy entry point — forwards to applications/novel_cursor/cursor_beat.py --app shenjia_caifa."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

_NOVEL_BEAT = Path(__file__).resolve().parents[1] / "novel_cursor" / "cursor_beat.py"
sys.argv = [str(_NOVEL_BEAT), "--app", "shenjia_caifa", *sys.argv[1:]]
runpy.run_path(str(_NOVEL_BEAT), run_name="__main__")
