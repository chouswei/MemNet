"""LawSeedHelper — auto-seed engine-law rows on MCP session_open."""

from __future__ import annotations

from memnet_mcp.seed import supplement_seed_lines

LawSeedHelper = supplement_seed_lines

__all__ = ["LawSeedHelper", "supplement_seed_lines"]
