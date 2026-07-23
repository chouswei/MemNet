"""docs/grammar/tools twin — delegates to package ``memnet.tier_a``.

Run golden tests via ``pytest tests/grammar`` (pythonpath includes the package).
"""

from __future__ import annotations

try:
    from memnet.tier_a import *  # noqa: F403
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Install/use package path parts/common/memnet so memnet.tier_a imports"
    ) from exc
