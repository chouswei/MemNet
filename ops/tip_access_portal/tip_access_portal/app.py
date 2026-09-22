"""Portal web: admin invites, Google redeem, one-time Bearer, nginx auth_request."""

from __future__ import annotations

import html
import secrets
import time
from collections.abc import Callable
from urllib.parse import quote

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.routing import Route

from tip_access_portal.config import Settings
from tip_access_portal.gate import bearer_token
from tip_access_portal.google_oauth import GoogleOAuth
from tip_access_portal.signing import read_payload, sign_payload
from tip_access_portal.status import ProbeResult, probe_all
from tip_access_portal.store import PortalStore

SESSION_COOKIE = "tip_portal_session"
FLASH_COOKIE = "tip_portal_flash"
SESSION_TTL = 12 * 60 * 60
STATE_TTL = 10 * 60
FLASH_TTL = 120

STRANGER = (
    "This portal does not give a free MemNet. "
    "Strangers use the SysMLEdge free tier or self-host memnet-llm."
)


def create_app(
    settings: Settings,
    store: PortalStore,
    google: GoogleOAuth,
    *,
    probe_http: Callable[[str], int] | None = None,
    probe_tcp: Callable[[str, int], None] | None = None,
) -> Starlette:
    def _session(request: Request) -> dict | None:
        raw = request.cookies.get(SESSION_COOKIE)
        if not raw:
            return None
        payload = read_payload(raw, settings.portal_secret)
        if payload is None or payload.get("kind") != "session":
            return None
        return payload

    def _is_admin(session: dict | None) -> bool:
        return bool(session and session.get("email") == settings.admin_email)

    def _set_cookie(response: Response, name: str, value: str, max_age: int) -> None:
        response.set_cookie(
            name,
            value,
            max_age=max_age,
            httponly=True,
            secure=settings.secure_cookies,
            samesite="lax",
            path="/",
        )

    def _clear_cookie(response: Response, name: str) -> None:
        response.delete_cookie(
            name,
            path="/",
            secure=settings.secure_cookies,
            httponly=True,
            samesite="lax",
        )

    def _redirect(
        location: str, *, session: dict | None = None, flash: dict | None = None
    ) -> RedirectResponse:
        response = RedirectResponse(location, status_code=303)
        if session is not None:
            _set_cookie(
                response, SESSION_COOKIE, sign_payload(session, settings.portal_secret), SESSION_TTL
            )
        if flash is not None:
            _set_cookie(
                response, FLASH_COOKIE, sign_payload(flash, settings.portal_secret), FLASH_TTL
            )
        return response

    def _page(title: str, body: str, *, session: dict | None = None) -> HTMLResponse:
        who = ""
        if session:
            who = f"<p class='who'>{html.escape(str(session.get('email', '')))}</p>"
        nav = ""
        if _is_admin(session):
            nav = (
                "<p><a href='/admin'>Invites</a> · "
                "<a href='/status'>Status</a> · "
                "<a href='/logout'>Sign out</a></p>"
            )
        elif session:
            nav = "<p><a href='/status'>Status</a> · <a href='/logout'>Sign out</a></p>"
        else:
            nav = "<p><a href='/status'>Status</a></p>"
        document = f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{html.escape(title)}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 52rem; }}
code, input[type=text] {{ font-family: ui-monospace, monospace; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border-bottom: 1px solid #ccc; text-align: left; padding: 0.35rem; vertical-align: top; }}
.secret {{ word-break: break-all; background: #f4f4f4; padding: 0.6rem; }}
.who {{ color: #444; }}
button {{ margin-right: 0.4rem; }}
.up {{ color: #0a7a32; font-weight: 600; }}
.down {{ color: #b00020; font-weight: 600; }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
{who}
{nav}
{body}
</body>
</html>"""
        return HTMLResponse(document)

    async def home(request: Request) -> Response:
        session = _session(request)
        if _is_admin(session):
            return _redirect("/admin")
        body = (
            "<p>Keyed access for the tip MemNet MCP. "
            "This is not a SysMLEdge product page and it does not open a project.</p>"
            f"<p>{html.escape(STRANGER)}</p>"
            "<p><a href='/auth/google'>Sign in with Google</a> if you are the admin.</p>"
            "<p>Invitees should open the invite link they were sent.</p>"
            + _services_html(_look(), include_targets=False)
        )
        return _page("Tip MemNet access", body, session=session)

    async def admin(request: Request) -> Response:
        session = _session(request)
        if not _is_admin(session):
            return _page("Admin only", f"<p>{html.escape(STRANGER)}</p>", session=session)
        flash = _take_flash(request)
        notice = ""
        if flash and flash.get("kind") == "invite":
            url = str(flash.get("url", ""))
            notice = (
                "<h2>Invite link (shown once)</h2>"
                f"<p class='secret'>{html.escape(url)}</p>"
                "<p>Copy this link now. The portal stores only a hash of the token.</p>"
            )
        csrf = str(session.get("csrf"))
        invites = store.list_invites()
        keys = store.list_keys()
        invite_rows = "".join(
            "<tr>"
            f"<td>{html.escape(row.id)}</td>"
            f"<td>{html.escape(row.label or '—')}</td>"
            f"<td>{html.escape(row.status)}</td>"
            f"<td>{html.escape(row.redeemed_email or '')}</td>"
            f"<td>{_invite_revoke(row, csrf)}</td>"
            "</tr>"
            for row in invites
        )
        key_rows = "".join(
            "<tr>"
            f"<td>{html.escape(row.id)}</td>"
            f"<td>{html.escape(row.email)}</td>"
            f"<td>{html.escape(row.invite_id)}</td>"
            f"<td>{'revoked' if row.revoked else 'active'}</td>"
            f"<td>{html.escape(row.last_used_at or 'never')}</td>"
            f"<td>{row.use_count}</td>"
            f"<td>{_key_revoke(row, csrf)}</td>"
            "</tr>"
            for row in keys
        )
        body = (
            notice
            + _services_html(_look(), include_targets=True)
            + "<h2>Mint invite</h2>"
            + "<form method='post' action='/admin/invites'>"
            + f"<input type='hidden' name='csrf' value='{html.escape(csrf)}'>"
            + "<label>Label <input type='text' name='label' maxlength='80'></label> "
            + "<button type='submit'>Mint invite</button></form>"
            + "<h2>Invites</h2>"
            + "<table><tr><th>Id</th><th>Label</th><th>Status</th>"
            + "<th>Redeemed by</th><th></th></tr>"
            + (invite_rows or "<tr><td colspan='5'>None yet</td></tr>")
            + "</table>"
            + "<h2>Bearer clients</h2>"
            + "<p>Look only for usage. Plaintext keys are not stored. "
            "Revoke refuses the key at the tip gate. "
            "Memnetor and Devicor manage serve from CLI, not this page.</p>"
            + "<table><tr><th>Id</th><th>Email</th><th>Invite</th>"
            + "<th>Status</th><th>Last used</th><th>Calls</th><th></th></tr>"
            + (key_rows or "<tr><td colspan='7'>None yet</td></tr>")
            + "</table>"
        )
        response = _page("Tip access admin", body, session=session)
        if flash is not None:
            _clear_cookie(response, FLASH_COOKIE)
        return response

    async def mint_invite(request: Request) -> Response:
        session = _session(request)
        if not _is_admin(session):
            return HTMLResponse("Forbidden", status_code=403)
        form = await request.form()
        if not _csrf_ok(session, form.get("csrf")):
            return HTMLResponse("Forbidden", status_code=403)
        label = str(form.get("label") or "")
        _row, token = store.mint_invite(label=label, ttl_hours=settings.invite_ttl_hours)
        url = f"{settings.base_url}/invite/{token}"
        flash = {"kind": "invite", "url": url, "exp": int(time.time()) + FLASH_TTL}
        return _redirect("/admin", flash=flash)

    async def revoke_invite(request: Request) -> Response:
        return await _admin_post(
            request, lambda: store.revoke_invite(request.path_params["invite_id"])
        )

    async def revoke_key(request: Request) -> Response:
        return await _admin_post(request, lambda: store.revoke_key(request.path_params["key_id"]))

    async def _admin_post(request: Request, action) -> Response:
        session = _session(request)
        if not _is_admin(session):
            return HTMLResponse("Forbidden", status_code=403)
        form = await request.form()
        if not _csrf_ok(session, form.get("csrf")):
            return HTMLResponse("Forbidden", status_code=403)
        action()
        return _redirect("/admin")

    async def invite_page(request: Request) -> Response:
        token = request.path_params["token"]
        invite = store.invite_by_token(token)
        if invite is None or invite.status != "open":
            return _page(
                "Invite unavailable",
                "<p>This invite is missing, expired, revoked, or already redeemed.</p>",
            )
        start = f"/auth/google?invite={quote(token)}"
        body = (
            "<p>Sign in with Google to fetch a tip MemNet MCP Bearer. "
            "The key is shown once.</p>"
            f"<p><a href='{html.escape(start)}'>Continue with Google</a></p>"
        )
        return _page("Redeem invite", body)

    async def auth_google(request: Request) -> Response:
        invite_token = request.query_params.get("invite", "")
        if invite_token:
            invite = store.invite_by_token(invite_token)
            if invite is None or invite.status != "open":
                return _page("Invite unavailable", "<p>This invite cannot be redeemed.</p>")
        state = sign_payload(
            {
                "kind": "oauth",
                "invite": invite_token,
                "nonce": secrets.token_urlsafe(16),
                "exp": int(time.time()) + STATE_TTL,
            },
            settings.portal_secret,
        )
        return RedirectResponse(google.authorization_url(state), status_code=302)

    async def auth_callback(request: Request) -> Response:
        error = request.query_params.get("error")
        if error:
            return _page("Sign-in refused", "<p>Google did not complete sign-in.</p>")
        code = request.query_params.get("code", "")
        state_raw = request.query_params.get("state", "")
        state = read_payload(state_raw, settings.portal_secret)
        if not code or state is None or state.get("kind") != "oauth":
            return _page("Sign-in refused", "<p>The sign-in state is not valid.</p>")
        try:
            identity = google.exchange(code)
        except (ValueError, httpx.HTTPError, OSError):
            return _page("Sign-in refused", "<p>Google did not return a verified email.</p>")
        invite_token = str(state.get("invite") or "")
        session = {
            "kind": "session",
            "email": identity.email,
            "sub": identity.sub,
            "csrf": secrets.token_urlsafe(16),
            "exp": int(time.time()) + SESSION_TTL,
        }
        if identity.email == settings.admin_email and not invite_token:
            return _redirect("/admin", session=session)
        if not invite_token:
            response = _page("No invite", f"<p>{html.escape(STRANGER)}</p>")
            return response
        invite = store.invite_by_token(invite_token)
        if invite is None or invite.status != "open":
            return _page("Invite unavailable", "<p>This invite cannot be redeemed.</p>")
        try:
            plaintext = store.issue_key(invite, email=identity.email, google_sub=identity.sub)
        except PermissionError:
            return _page("Invite unavailable", "<p>This invite cannot be redeemed.</p>")
        flash = {"kind": "key", "key": plaintext, "exp": int(time.time()) + FLASH_TTL}
        return _redirect("/key", session=session, flash=flash)

    async def show_key(request: Request) -> Response:
        session = _session(request)
        flash = _take_flash(request)
        if flash is None or flash.get("kind") != "key":
            body = (
                "<p>There is no Bearer to show. Keys are displayed once and only a hash is stored. "
                "Ask the admin to revoke the old key and mint a new invite if you need another.</p>"
            )
            return _page("Bearer", body, session=session)
        key = str(flash.get("key", ""))
        body = (
            "<p>Copy this Bearer now. Reloading this page will not show it again.</p>"
            f"<p class='secret' id='bearer'>{html.escape(key)}</p>"
            "<p><button type='button' id='copy'>Copy</button></p>"
            "<p>Call <code>https://memnet.139-59-255-181.nip.io/mcp</code> with header "
            "<code>Authorization: Bearer</code> and this key. "
            "A missing or revoked key is refused. This key does not open a SysMLEdge project.</p>"
            "<script>"
            "document.getElementById('copy').addEventListener('click', function () {"
            "navigator.clipboard.writeText(document.getElementById('bearer').textContent);"
            "});"
            "</script>"
        )
        response = _page("Your tip Bearer", body, session=session)
        _clear_cookie(response, FLASH_COOKIE)
        return response

    async def logout(request: Request) -> Response:
        response = _redirect("/")
        _clear_cookie(response, SESSION_COOKIE)
        _clear_cookie(response, FLASH_COOKIE)
        return response

    async def status_page(request: Request) -> Response:
        session = _session(request)
        admin = _is_admin(session)
        body = (
            "<p>Look only. This page does not manage serve, mutate, or open a project.</p>"
            + _services_html(_look(), include_targets=admin)
        )
        if admin:
            body += _admin_client_look()
        else:
            body += (
                "<h2>Clients</h2><p>Bearer client emails and last-used times are admin-only.</p>"
            )
        return _page("MemNet status", body, session=session)

    async def validate(request: Request) -> Response:
        token = bearer_token(request.headers.get("authorization"))
        if token is None or not store.key_is_active(token):
            return Response(status_code=401)
        store.record_use(token)
        return Response(status_code=200)

    def _look() -> list[ProbeResult]:
        return probe_all(
            settings.status_probes,
            http_request=probe_http,
            tcp_connect=probe_tcp,
        )

    def _admin_client_look() -> str:
        keys = store.list_keys()
        active = sum(1 for row in keys if not row.revoked)
        used = sum(1 for row in keys if row.last_used_at)
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(row.email)}</td>"
            f"<td>{'revoked' if row.revoked else 'active'}</td>"
            f"<td>{html.escape(row.last_used_at or 'never')}</td>"
            f"<td>{row.use_count}</td>"
            "</tr>"
            for row in keys
        )
        return (
            "<h2>Clients</h2>"
            f"<p>Active Bearers: {active}. Ever used: {used}. "
            "Look only — revoke stays on the admin page.</p>"
            + "<table><tr><th>Email</th><th>Status</th>"
            + "<th>Last used</th><th>Calls</th></tr>"
            + (rows or "<tr><td colspan='4'>None yet</td></tr>")
            + "</table>"
        )

    def _take_flash(request: Request) -> dict | None:
        raw = request.cookies.get(FLASH_COOKIE)
        if not raw:
            return None
        payload = read_payload(raw, settings.portal_secret)
        if payload is None:
            return None
        return payload

    routes = [
        Route("/", home, methods=["GET"]),
        Route("/admin", admin, methods=["GET"]),
        Route("/admin/invites", mint_invite, methods=["POST"]),
        Route("/admin/invites/{invite_id}/revoke", revoke_invite, methods=["POST"]),
        Route("/admin/keys/{key_id}/revoke", revoke_key, methods=["POST"]),
        Route("/invite/{token}", invite_page, methods=["GET"]),
        Route("/auth/google", auth_google, methods=["GET"]),
        Route("/auth/callback", auth_callback, methods=["GET"]),
        Route("/key", show_key, methods=["GET"]),
        Route("/status", status_page, methods=["GET"]),
        Route("/logout", logout, methods=["GET"]),
        Route("/auth/validate", validate, methods=["GET"]),
        Route("/internal/bearer-check", validate, methods=["GET"]),
        Route("/healthz", lambda _request: Response("ok", status_code=200), methods=["GET"]),
    ]
    return Starlette(routes=routes)


def _csrf_ok(session: dict | None, posted: object) -> bool:
    if session is None:
        return False
    expected = session.get("csrf")
    if not isinstance(expected, str) or not isinstance(posted, str):
        return False
    return secrets.compare_digest(expected, posted)


def _invite_revoke(row, csrf: str) -> str:
    if row.status == "revoked":
        return ""
    return _revoke_form("/admin/invites/" + quote(row.id) + "/revoke", csrf)


def _key_revoke(row, csrf: str) -> str:
    if row.revoked:
        return ""
    return _revoke_form("/admin/keys/" + quote(row.id) + "/revoke", csrf)


def _services_html(results: list[ProbeResult], *, include_targets: bool) -> str:
    rows = []
    for item in results:
        mark = "up" if item.up else "down"
        target = f"<td><code>{html.escape(item.target)}</code></td>" if include_targets else ""
        rows.append(
            "<tr>"
            f"<td>{html.escape(item.name)}</td>"
            f"<td class='{mark}'>{mark}</td>"
            f"<td>{html.escape(item.detail)}</td>"
            f"{target}"
            "</tr>"
        )
    heading = "<h2>Services</h2>"
    note = (
        "<p>Look-only probe of configured MemNet listeners. "
        "A 401 on the tip MCP still counts as up. No restart from this page.</p>"
    )
    if not rows:
        empty = (
            "<p>No service probes configured. "
            "Set <code>MEMNET_STATUS_PROBES</code> or <code>MEMNET_TIP_MCP_PROBE</code>.</p>"
        )
        return heading + note + empty
    head = "<tr><th>Name</th><th>State</th><th>Detail</th>"
    if include_targets:
        head += "<th>Target</th>"
    head += "</tr>"
    return heading + note + "<table>" + head + "".join(rows) + "</table>"


def _revoke_form(action: str, csrf: str) -> str:
    return (
        f"<form method='post' action='{html.escape(action)}'>"
        f"<input type='hidden' name='csrf' value='{html.escape(csrf)}'>"
        "<button type='submit'>Revoke</button></form>"
    )
