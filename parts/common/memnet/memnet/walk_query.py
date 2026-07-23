"""WalkQuery — anchored walk hop lines over NODE|EDGE."""

from __future__ import annotations

from memnet.config import DEFAULT_QUERY_DEPTH, DEFAULT_QUERY_MAX_ROWS
from memnet.context_view import format_walk_hop
from memnet.exceptions import MemNetError


class WalkQuery:
    def __init__(self, session_store) -> None:
        self.ss = session_store

    def hops(
        self,
        *,
        anchor: str,
        depth: int = DEFAULT_QUERY_DEPTH,
        max_rows: int = DEFAULT_QUERY_MAX_ROWS,
    ) -> list[str]:
        if not anchor:
            raise MemNetError("no_anchor", "query walk requires --anchor")
        raw = self.ss.store.context_walk_hops(
            anchor_id=anchor,
            depth=depth,
            max_rows=max_rows,
            active_only=True,
        )
        return [format_walk_hop(src, rel, dst) for src, rel, dst in raw]
