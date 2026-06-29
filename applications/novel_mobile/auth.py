"""Google sign-in and per-user app session tokens for novel_mobile."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Literal

import jwt

from novel_mobile.world_slot import normalise_user_id

AuthMode = Literal["open", "token", "google", "guest"]
_DEFAULT_JWT_TTL = 7 * 24 * 3600


@dataclass(frozen=True)
class AuthConfig:
    mode: AuthMode
    shared_token: str | None = None
    google_client_id: str | None = None
    jwt_secret: str | None = None
    jwt_ttl_seconds: int = _DEFAULT_JWT_TTL
    allowed_emails: frozenset[str] | None = None


@dataclass(frozen=True)
class AuthContext:
    user_id: str | None = None
    email: str | None = None


def load_auth_config(
    *,
    shared_token: str | None = None,
    google_client_id: str | None = None,
    jwt_secret: str | None = None,
) -> AuthConfig:
    """Resolve auth mode from explicit args then environment."""
    cid = (google_client_id or os.environ.get("GOOGLE_CLIENT_ID", "")).strip() or None
    secret = (jwt_secret or os.environ.get("NOVEL_MOBILE_JWT_SECRET", "")).strip() or None
    shared = (shared_token or os.environ.get("NOVEL_MOBILE_TOKEN", "")).strip() or None
    ttl_raw = os.environ.get("NOVEL_MOBILE_JWT_TTL_SECONDS", "").strip()
    ttl = int(ttl_raw) if ttl_raw.isdigit() else _DEFAULT_JWT_TTL
    allow_raw = os.environ.get("NOVEL_MOBILE_GOOGLE_ALLOWED_EMAILS", "").strip()
    allowed = (
        frozenset(e.strip().lower() for e in allow_raw.split(",") if e.strip())
        if allow_raw
        else None
    )

    if cid:
        if not secret:
            raise ValueError("GOOGLE_CLIENT_ID requires NOVEL_MOBILE_JWT_SECRET")
        return AuthConfig(
            mode="google",
            google_client_id=cid,
            jwt_secret=secret,
            jwt_ttl_seconds=ttl,
            allowed_emails=allowed,
        )
    if secret:
        return AuthConfig(
            mode="guest",
            jwt_secret=secret,
            jwt_ttl_seconds=ttl,
        )
    if shared:
        return AuthConfig(mode="token", shared_token=shared)
    return AuthConfig(mode="open")


def user_id_from_google_sub(sub: str) -> str:
    """Stable account id for a Google user (not a world id)."""
    uid = f"google_{sub}"
    if len(uid) > 63:
        import hashlib

        uid = "google_" + hashlib.sha256(sub.encode("utf-8")).hexdigest()[:32]
    normalise_user_id(uid)
    return uid


def verify_google_credential(credential: str, client_id: str) -> dict[str, Any]:
    """Verify Google Identity Services ID token; return claims."""
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    return id_token.verify_oauth2_token(
        credential,
        google_requests.Request(),
        client_id,
    )


def issue_app_token(
    config: AuthConfig,
    *,
    user_id: str,
    email: str | None,
    google_sub: str,
) -> tuple[str, int]:
    if not config.jwt_secret:
        raise RuntimeError("jwt_secret required")
    now = int(time.time())
    expires = now + config.jwt_ttl_seconds
    payload = {
        "sub": google_sub,
        "user_id": user_id,
        "email": email,
        "iat": now,
        "exp": expires,
    }
    token = jwt.encode(payload, config.jwt_secret, algorithm="HS256")
    return token, config.jwt_ttl_seconds


def verify_app_token(config: AuthConfig, token: str) -> AuthContext:
    if not config.jwt_secret:
        raise RuntimeError("jwt_secret required")
    try:
        claims = jwt.decode(token, config.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as err:
        raise ValueError("invalid_token") from err
    user_id = str(claims.get("user_id") or "").strip()
    if not user_id:
        raise ValueError("invalid_token")
    normalise_user_id(user_id)
    email = str(claims.get("email") or "").strip() or None
    return AuthContext(user_id=user_id, email=email)


def authenticate_request(
    config: AuthConfig,
    authorization: str | None,
) -> AuthContext:
    if config.mode == "open":
        return AuthContext()
    if not authorization or not authorization.startswith("Bearer "):
        raise PermissionError("unauthorized")
    token = authorization[7:].strip()
    if not token:
        raise PermissionError("unauthorized")
    if config.mode == "token":
        if token != config.shared_token:
            raise PermissionError("unauthorized")
        return AuthContext()
    if config.mode in ("google", "guest"):
        return verify_app_token(config, token)
    return AuthContext()


def resolve_user_id(
    auth_ctx: AuthContext,
    x_novel_user_id: str | None,
    *,
    auth_mode: AuthMode,
) -> str | None:
    if auth_ctx.user_id:
        header_id = normalise_user_id(x_novel_user_id)
        if header_id and header_id != auth_ctx.user_id:
            raise ValueError("user_id_mismatch")
        return auth_ctx.user_id
    if auth_mode in ("google", "guest"):
        return None
    return normalise_user_id(x_novel_user_id)


def new_guest_user_id() -> str:
    import uuid

    uid = f"guest_{uuid.uuid4().hex[:16]}"
    normalise_user_id(uid)
    return uid


def exchange_guest_login(config: AuthConfig) -> dict[str, Any]:
    """Issue a signed per-device player id (LAN open mode without Google)."""
    if config.mode != "guest" or not config.jwt_secret:
        raise RuntimeError("guest auth not configured")
    user_id = new_guest_user_id()
    access_token, expires_in = issue_app_token(
        config,
        user_id=user_id,
        email=None,
        google_sub="guest",
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user_id": user_id,
        "email": None,
    }


def exchange_google_login(
    config: AuthConfig,
    credential: str,
) -> dict[str, Any]:
    if config.mode != "google" or not config.google_client_id:
        raise RuntimeError("google auth not configured")
    claims = verify_google_credential(credential, config.google_client_id)
    sub = str(claims.get("sub") or "").strip()
    if not sub:
        raise ValueError("invalid_google_token")
    email = str(claims.get("email") or "").strip().lower() or None
    if config.allowed_emails is not None:
        if not email or email not in config.allowed_emails:
            raise PermissionError("email_not_allowed")
    user_id = user_id_from_google_sub(sub)
    access_token, expires_in = issue_app_token(
        config,
        user_id=user_id,
        email=email,
        google_sub=sub,
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user_id": user_id,
        "email": email,
    }
