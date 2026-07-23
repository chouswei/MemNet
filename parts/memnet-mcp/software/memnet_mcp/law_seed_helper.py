"""LawSeedHelper — auto-seed engine-law rows on MCP session_open.

Wraps ``supplement_seed_lines`` (Tier A by default; pipe only to match
legacy ``seed_lines`` dialect). Not the agent write surface.
"""

from __future__ import annotations

from memnet_mcp.seed import supplement_seed_lines

LawSeedHelper = supplement_seed_lines

__all__ = ["LawSeedHelper", "supplement_seed_lines"]
