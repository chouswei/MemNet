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
    """Named sessions with GraphStore + schema + mutate/query facades."""

    open = staticmethod(open_session)
    get = staticmethod(get_session)
    close = staticmethod(close_session)
    list = staticmethod(list_sessions)
    purge = staticmethod(purge_expired)
    resolve = staticmethod(resolve_session_id)
