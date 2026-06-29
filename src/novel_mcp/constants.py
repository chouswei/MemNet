"""Shared novel-mcp tuning constants."""

from __future__ import annotations

# STEP01 → SCN → cast → aff_to needs depth 3 (depth 2 stops before edge attrs).
# warm_supplement also merges missing aff_to for PLR/NPC ids in warm.
NOVEL_WARM_DEPTH = 3

# STEP01 warm must include all @USR rows (70+ in shenjia seed).
# 55 truncated USR21 (prose_target) and other mid-sequence USRs.
NOVEL_WARM_MAX_ROWS = 150
