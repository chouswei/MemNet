"""Bearer check used by nginx auth_request. Missing or revoked keys fail."""

from __future__ import annotations

from tip_access_portal.store import PortalStore


def authorization_active(store: PortalStore, authorization: str | None) -> bool:
    token = bearer_token(authorization)
    if token is None:
        return False
    return store.key_is_active(token)


def bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    scheme, _, rest = authorization.strip().partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = rest.strip()
    if not token or " " in token:
        return None
    return token
