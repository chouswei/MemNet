"""Environment configuration. Secrets stay in the process environment."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from tip_access_portal.status import Probe, parse_probes


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable {name}")
    return value


@dataclass(frozen=True)
class Settings:
    google_client_id: str
    google_client_secret: str
    portal_secret: str
    admin_email: str
    base_url: str
    db_path: str
    bind: str = "127.0.0.1"
    port: int = 8766
    invite_ttl_hours: int = 168
    cookie_secure: bool | None = None
    status_probes: tuple[Probe, ...] = field(default_factory=tuple)

    @property
    def redirect_uri(self) -> str:
        return self.base_url.rstrip("/") + "/auth/callback"

    @property
    def secure_cookies(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.base_url.lower().startswith("https://")

    @classmethod
    def from_env(cls) -> Settings:
        base = _required("MEMNET_TIP_PORTAL_BASE_URL").rstrip("/")
        ttl_raw = os.environ.get("MEMNET_TIP_INVITE_TTL_HOURS", "168").strip() or "168"
        port_raw = os.environ.get("MEMNET_TIP_PORTAL_PORT", "8766").strip() or "8766"
        try:
            ttl = int(ttl_raw)
            port = int(port_raw)
        except ValueError as exc:
            raise SystemExit(
                "MEMNET_TIP_INVITE_TTL_HOURS and MEMNET_TIP_PORTAL_PORT must be integers"
            ) from exc
        if ttl < 1 or port < 1:
            raise SystemExit(
                "MEMNET_TIP_INVITE_TTL_HOURS and MEMNET_TIP_PORTAL_PORT must be positive"
            )
        return cls(
            google_client_id=_required("MEMNET_GOOGLE_CLIENT_ID"),
            google_client_secret=_required("MEMNET_GOOGLE_CLIENT_SECRET"),
            portal_secret=_required("MEMNET_TIP_PORTAL_SECRET"),
            admin_email=_required("MEMNET_TIP_ADMIN_EMAIL").lower(),
            base_url=base,
            db_path=os.environ.get("MEMNET_TIP_PORTAL_DB", "data/tip-access-portal.sqlite").strip()
            or "data/tip-access-portal.sqlite",
            bind=os.environ.get("MEMNET_TIP_PORTAL_BIND", "127.0.0.1").strip() or "127.0.0.1",
            port=port,
            invite_ttl_hours=ttl,
            status_probes=_status_probes(),
        )


def _status_probes() -> tuple[Probe, ...]:
    listed = parse_probes(os.environ.get("MEMNET_STATUS_PROBES", "").strip())
    extra = os.environ.get("MEMNET_TIP_MCP_PROBE", "").strip()
    if not extra:
        return listed
    names = {item.name for item in listed}
    if "tip-mcp" in names:
        return listed
    return listed + (Probe(name="tip-mcp", target=extra),)
