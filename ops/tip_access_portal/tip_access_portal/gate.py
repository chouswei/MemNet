"""Bearer check used by nginx auth_request. Missing or revoked keys fail."""

from __future__ import annotations

from tip_access_portal.store import PortalStore


def authorization_active(store: PortalStore, authorization: str | None) -> bool:
    if authorization is None:
        return False
    scheme, _, rest = authorization.strip().partition(" ")
    if scheme.lower() != "bearer":
        return False
    token = rest.strip()
    if not token or " " in token:
        return False
    return store.key_is_active(token)
