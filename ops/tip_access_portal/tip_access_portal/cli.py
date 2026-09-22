"""Console entry: memnet-tip-portal."""

from __future__ import annotations

import uvicorn

from tip_access_portal.app import create_app
from tip_access_portal.config import Settings
from tip_access_portal.google_oauth import GoogleOAuth
from tip_access_portal.store import PortalStore


def main() -> None:
    settings = Settings.from_env()
    store = PortalStore(settings.db_path)
    app = create_app(settings, store, GoogleOAuth(settings))
    uvicorn.run(app, host=settings.bind, port=settings.port)
