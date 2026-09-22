"""Google OAuth code exchange. Tests inject the HTTP calls."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

from tip_access_portal.config import Settings

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


@dataclass(frozen=True)
class GoogleIdentity:
    sub: str
    email: str
    email_verified: bool


class GoogleOAuth:
    def __init__(
        self,
        settings: Settings,
        *,
        post: Callable[..., Any] | None = None,
        get: Callable[..., Any] | None = None,
    ) -> None:
        self._settings = settings
        self._post = post
        self._get = get

    def authorization_url(self, state: str) -> str:
        query = urlencode(
            {
                "client_id": self._settings.google_client_id,
                "redirect_uri": self._settings.redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "access_type": "online",
                "prompt": "select_account",
            }
        )
        return f"{AUTH_URL}?{query}"

    def exchange(self, code: str) -> GoogleIdentity:
        form = {
            "code": code,
            "client_id": self._settings.google_client_id,
            "client_secret": self._settings.google_client_secret,
            "redirect_uri": self._settings.redirect_uri,
            "grant_type": "authorization_code",
        }
        if self._post is None:
            response = httpx.post(TOKEN_URL, data=form, timeout=15.0)
            response.raise_for_status()
            token_body = response.json()
        else:
            token_body = self._post(TOKEN_URL, form)
        access = token_body.get("access_token")
        if not isinstance(access, str) or not access:
            raise ValueError("google_token")
        if self._get is None:
            info_response = httpx.get(
                USERINFO_URL,
                headers={"Authorization": f"Bearer {access}"},
                timeout=15.0,
            )
            info_response.raise_for_status()
            info = info_response.json()
        else:
            info = self._get(USERINFO_URL, access)
        sub = info.get("sub")
        email = info.get("email")
        verified = info.get("email_verified")
        if not isinstance(sub, str) or not isinstance(email, str):
            raise ValueError("google_profile")
        if verified is not True:
            raise ValueError("email_unverified")
        return GoogleIdentity(sub=sub, email=email.strip().lower(), email_verified=True)
