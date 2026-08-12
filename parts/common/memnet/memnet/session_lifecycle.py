"""SessionLifecycle — SysML facade over session registry + SessionStore."""

from __future__ import annotations

from memnet.session import (
    SessionStore,
    close_session,
    get_session,
    list_sessions,
    open_session,
    purge_expired,
    resolve_session_id,
)

__all__ = [
    "SessionLifecycle",
    "SessionStore",
    "close_session",
    "get_session",
    "list_sessions",
    "open_session",
    "purge_expired",
    "resolve_session_id",
]


class SessionLifecycle:
    """Named sessions with GraphStore + schema + mutate/query facades.

    Optional M2.5 hydrate/flush ports are served by ``memnet.durable``
    (DurableSyncOwner) — not by exposing the durable store to agents.
    """

    open = staticmethod(open_session)
    get = staticmethod(get_session)
    close = staticmethod(close_session)
    list = staticmethod(list_sessions)
    purge = staticmethod(purge_expired)
    resolve = staticmethod(resolve_session_id)

    @staticmethod
    def hydrate_from_durable(
        session: SessionStore,
        ego_id: str,
        *,
        max_nodes: int = 50,
        max_edges: int = 100,
        depth: int = 2,
        view: str | None = None,
    ):
        """Hydrate an ego-bounded durable slice into ``session`` (one sync owner)."""
        from memnet.durable import HydrateBudget, get_sync_owner

        return get_sync_owner().hydrate_into_session(
            session,
            ego_id,
            HydrateBudget(
                max_nodes=max_nodes,
                max_edges=max_edges,
                depth=depth,
                view=view,
            ),
        )

    @staticmethod
    def flush_to_durable(
        session: SessionStore,
        ego_id: str,
        *,
        max_nodes: int = 50,
        max_edges: int = 100,
        depth: int = 2,
        view: str | None = None,
    ):
        """Flush an ego-bounded live slice to the durable store (one sync owner)."""
        from memnet.durable import HydrateBudget, get_sync_owner

        return get_sync_owner().flush_from_session(
            session,
            ego_id,
            HydrateBudget(
                max_nodes=max_nodes,
                max_edges=max_edges,
                depth=depth,
                view=view,
            ),
        )
