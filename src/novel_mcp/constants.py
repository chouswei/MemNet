"""Shared novel-mcp tuning constants."""

from __future__ import annotations

# STEP01 warm at depth 2 must include all @USR rows (70+ in shenjia seed).
# 55 truncated USR21 (prose_target) and other mid-sequence USRs.
NOVEL_WARM_MAX_ROWS = 150
