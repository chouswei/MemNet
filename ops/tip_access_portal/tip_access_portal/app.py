"""Portal web: admin invites, Google redeem, one-time Bearer, nginx auth_request."""

from __future__ import annotations

import html
import secrets
import time
from collections.abc import Callable
from datetime import UTC, datetime
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
WWW_MCP = "https://memnet.139-59-255-181.nip.io/mcp"

STRANGER = (
    "This portal does not give a free MemNet. "
    "Strangers use the SysMLEdge free tier or self-host memnet-llm."
)

PAGE_CSS = """
body { font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 52rem;
  padding: 0 1rem; line-height: 1.45; color: #111; }
code, input[type=text], pre { font-family: ui-monospace, monospace; }
nav.bar { display: flex; flex-wrap: wrap; gap: 0.85rem; margin: 0 0 1.25rem; }
nav.bar a { color: #0b57d0; }
nav.bar .here { color: #111; font-weight: 600; text-decoration: none; }
.who { color: #444; margin: 0 0 0.4rem; }
.btn { display: inline-block; padding: 0.55rem 0.95rem; border: 1px solid #111;
  background: #111; color: #fff; text-decoration: none; font: inherit;
  cursor: pointer; border-radius: 0.25rem; }
.btn-google { background: #fff; color: #111; }
.btn-copy { min-width: 7rem; }
.btn-danger { background: #fff; color: #b00020; border-color: #b00020; }
.btn:focus-visible, a:focus-visible, input:focus-visible {
  outline: 2px solid #0b57d0; outline-offset: 2px; }
.secret { word-break: break-all; background: #f4f4f4; padding: 0.75rem;
  border-radius: 0.25rem; }
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; min-width: 28rem; }
th, td { border-bottom: 1px solid #ccc; text-align: left; padding: 0.4rem;
  vertical-align: top; }
.up { color: #0a7a32; font-weight: 600; }
.down { color: #b00020; font-weight: 600; }
.dot { display: inline-block; width: 0.55rem; height: 0.55rem;
  border-radius: 50%; margin-right: 0.35rem; vertical-align: middle; }
.dot-up { background: #0a7a32; }
.dot-down { background: #b00020; }
.foot { margin-top: 2rem; color: #555; font-size: 0.9rem; }
.muted { color: #555; }
.card { border: 1px solid #ddd; padding: 1.25rem; border-radius: 0.4rem; }
#copy-status { min-height: 1.2em; color: #0a7a32; }
label { display: inline-flex; gap: 0.4rem; align-items: center; }
input[type=text] { padding: 0.35rem 0.5rem; }
""".strip()


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
                response,
                SESSION_COOKIE,
                sign_payload(session, settings.portal_secret),
                SESSION_TTL,
            )
        if flash is not None:
            _set_cookie(
                response,
                FLASH_COOKIE,
                sign_payload(flash, settings.portal_secret),
                FLASH_TTL,
            )
        return response

    def _page(
        title: str,
        body: str,
        *,
        session: dict | None = None,
        current: str = "",
    ) -> HTMLResponse:
        who = ""
        if session:
            who = f"<p class='who'>{html.escape(str(session.get('email', '')))}</p>"
        nav = _nav_html(session, current, admin=_is_admin(session))
        document = f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{html.escape(title)}</title>
<style>
{PAGE_CSS}
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
            "<p>Invite-only keys for tip MemNet MCP.</p>"
            + _google_button("/auth/google", "Sign in with Google")
            + "<p class='muted'>Admin sign-in. If you were invited, open the link "
            "in your email.</p>"
            + "<p class='foot'>This is not a SysMLEdge product page and it does "
            "not open a project. " + html.escape(STRANGER) + "</p>"
        )
        return _page("Tip MemNet access", body, session=session, current="home")

    async def admin(request: Request) -> Response:
        session = _session(request)
        if not _is_admin(session):
            return _page(
                "Admin only",
                f"<p>{html.escape(STRANGER)}</p>",
                session=session,
                current="admin",
            )
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
            f"<td>{html.escape(row.label or '—')}</td>"
            f"<td>{html.escape(row.status)}</td>"
            f"<td>{html.escape(row.redeemed_email or '')}</td>"
            f"<td>{_invite_revoke(row, csrf)}</td>"
            "</tr>"
            for row in invites
        )
        key_rows = "".join(
            "<tr>"
            f"<td>{html.escape(row.email)}</td>"
            f"<td>{'revoked' if row.revoked else 'active'}</td>"
            f"<td>{html.escape(_relative_used(row.last_used_at))}</td>"
            f"<td>{row.use_count}</td>"
            f"<td>{_key_revoke(row, csrf)}</td>"
            "</tr>"
            for row in keys
        )
        body = (
            notice
            + "<h2>Mint invite</h2>"
            + "<form method='post' action='/admin/invites'>"
            + f"<input type='hidden' name='csrf' value='{html.escape(csrf)}'>"
            + "<label>Label <input type='text' name='label' maxlength='80'></label> "
            + "<button class='btn' type='submit'>Mint invite</button></form>"
            + "<h2>Invites</h2>"
            + "<div class='table-wrap'><table><tr><th>Label</th><th>Status</th>"
            + "<th>Redeemed by</th><th></th></tr>"
            + (invite_rows or "<tr><td colspan='4'>None yet</td></tr>")
            + "</table></div>"
            + "<h2>Bearer clients</h2>"
            + "<p class='muted'>Look only for usage. Plaintext keys are not stored. "
            "Revoke refuses the key at the tip gate. Serve stays on the CLI.</p>"
            + "<div class='table-wrap'><table><tr><th>Email</th>"
            + "<th>Status</th><th>Last used</th><th>Calls</th><th></th></tr>"
            + (key_rows or "<tr><td colspan='5'>None yet</td></tr>")
            + "</table></div>"
            + _services_html(_look(), include_targets=True)
        )
        response = _page("Tip access admin", body, session=session, current="admin")
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
                "<p>This invite cannot be used. Ask the admin for a new link.</p>",
                current="invite",
            )
        start = f"/auth/google?invite={quote(token)}"
        body = (
            "<div class='card'>"
            "<p>You were invited to a tip MemNet key. "
            "The key is shown once after sign-in.</p>"
            + _google_button(start, "Continue with Google")
            + "</div>"
        )
        return _page("Redeem invite", body, current="invite")

    async def auth_google(request: Request) -> Response:
        invite_token = request.query_params.get("invite", "")
        if invite_token:
            invite = store.invite_by_token(invite_token)
            if invite is None or invite.status != "open":
                return _page(
                    "Invite unavailable",
                    "<p>This invite cannot be redeemed.</p>",
                    current="invite",
                )
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
            response = _page(
                "No invite",
                f"<p>{html.escape(STRANGER)}</p>",
                current="home",
            )
            return response
        invite = store.invite_by_token(invite_token)
        if invite is None or invite.status != "open":
            return _page(
                "Invite unavailable",
                "<p>This invite cannot be redeemed.</p>",
                current="invite",
            )
        try:
            plaintext = store.issue_key(invite, email=identity.email, google_sub=identity.sub)
        except PermissionError:
            return _page(
                "Invite unavailable",
                "<p>This invite cannot be redeemed.</p>",
                current="invite",
            )
        flash = {"kind": "key", "key": plaintext, "exp": int(time.time()) + FLASH_TTL}
        return _redirect("/key", session=session, flash=flash)

    async def show_key(request: Request) -> Response:
        session = _session(request)
        flash = _take_flash(request)
        if flash is None or flash.get("kind") != "key":
            body = (
                "<p>This key was already shown. Keys are displayed once "
                "and only a hash is stored.</p>"
                "<p>Ask Szu-Wei for a new invite if you need another key.</p>"
            )
            return _page("Key already shown", body, session=session, current="key")
        key = str(flash.get("key", ""))
        snippet = f"Authorization: Bearer {key}"
        body = (
            "<p>Copy this key now. Reloading this page will not show it again.</p>"
            f"<p class='secret' id='bearer'>{html.escape(key)}</p>"
            "<p><button class='btn btn-copy' type='button' id='copy'>Copy</button></p>"
            "<p id='copy-status' role='status' aria-live='polite'></p>"
            "<p>Next: add this header to your MCP client for "
            f"<code>{html.escape(WWW_MCP)}</code>.</p>"
            f"<pre class='secret' id='snippet'>{html.escape(snippet)}</pre>"
            "<p class='muted'>A missing or revoked key is refused. "
            "This key does not open a SysMLEdge project.</p>" + _COPY_SCRIPT
        )
        response = _page("Your tip key", body, session=session, current="key")
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
        body = "<p>Look only. These listeners are not managed from this page.</p>" + _services_html(
            _look(), include_targets=admin
        )
        if admin:
            body += _admin_client_look()
        return _page("MemNet status", body, session=session, current="status")

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
            f"<td>{html.escape(_relative_used(row.last_used_at))}</td>"
            f"<td>{row.use_count}</td>"
            "</tr>"
            for row in keys
        )
        return (
            "<h2>Clients</h2>"
            f"<p>Active keys: {active}. Ever used: {used}. "
            "Look only — revoke stays on the admin page.</p>"
            + "<div class='table-wrap'><table><tr><th>Email</th><th>Status</th>"
            + "<th>Last used</th><th>Calls</th></tr>"
            + (rows or "<tr><td colspan='4'>None yet</td></tr>")
            + "</table></div>"
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


def _nav_html(session: dict | None, current: str, *, admin: bool) -> str:
    if current == "invite" and not session:
        return ""
    items: list[tuple[str, str, str]] = []
    if admin:
        items = [
            ("admin", "/admin", "Invites"),
            ("status", "/status", "Status"),
            ("logout", "/logout", "Sign out"),
        ]
    elif session:
        items = [
            ("status", "/status", "Status"),
            ("logout", "/logout", "Sign out"),
        ]
    else:
        items = [("status", "/status", "Status")]
    parts = []
    for key, href, label in items:
        if key == current:
            parts.append(f"<span class='here'>{html.escape(label)}</span>")
        else:
            parts.append(f"<a href='{html.escape(href)}'>{html.escape(label)}</a>")
    return "<nav class='bar'>" + "".join(parts) + "</nav>"


def _google_button(href: str, label: str) -> str:
    return f"<p><a class='btn btn-google' href='{html.escape(href)}'>{html.escape(label)}</a></p>"


def _invite_revoke(row, csrf: str) -> str:
    if row.status == "revoked":
        return ""
    if row.status == "redeemed":
        message = "Revoke the key issued from this invite? It will be refused at the tip gate."
        label = "Revoke key"
    else:
        message = "Revoke this invite? It can no longer be redeemed."
        label = "Revoke"
    return _revoke_form("/admin/invites/" + quote(row.id) + "/revoke", csrf, message, label)


def _key_revoke(row, csrf: str) -> str:
    if row.revoked:
        return ""
    return _revoke_form(
        "/admin/keys/" + quote(row.id) + "/revoke",
        csrf,
        "Revoke this key? It will be refused at the tip gate.",
        "Revoke",
    )


def _probe_detail(item: ProbeResult) -> str:
    if item.up:
        detail = item.detail
        if detail.startswith("http 401") or detail.startswith("http 403"):
            return "Reachable (auth required)"
        return "Reachable"
    if item.detail == "unsupported target":
        return "Unsupported target"
    return "Unreachable"


def _services_html(results: list[ProbeResult], *, include_targets: bool) -> str:
    rows = []
    for item in results:
        mark = "Up" if item.up else "Down"
        css = "up" if item.up else "down"
        dot = "dot-up" if item.up else "dot-down"
        target = f"<td><code>{html.escape(item.target)}</code></td>" if include_targets else ""
        rows.append(
            "<tr>"
            f"<td>{html.escape(item.name)}</td>"
            f"<td class='{css}'><span class='dot {dot}'></span>{mark}</td>"
            f"<td>{html.escape(_probe_detail(item))}</td>"
            f"{target}"
            "</tr>"
        )
    heading = "<h2>Services</h2>"
    if include_targets:
        note = (
            "<p class='muted'>Look-only probe of configured MemNet listeners. "
            "A 401 on the tip MCP still counts as up. No restart from this page.</p>"
        )
    else:
        note = (
            "<p class='muted'>Look-only probe of configured MemNet listeners. "
            "No restart from this page.</p>"
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
    table = "<div class='table-wrap'><table>" + head + "".join(rows) + "</table></div>"
    return heading + note + table


def _revoke_form(action: str, csrf: str, message: str, label: str) -> str:
    return (
        f'<form method="post" action="{html.escape(action)}" '
        f'onsubmit="return confirm({_js_string(message)});">'
        f'<input type="hidden" name="csrf" value="{html.escape(csrf)}">'
        f'<button class="btn btn-danger" type="submit">{html.escape(label)}</button></form>'
    )


def _js_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
    return "'" + escaped + "'"


def _relative_used(raw: str | None, *, now: datetime | None = None) -> str:
    if not raw:
        return "never"
    try:
        moment = datetime.fromisoformat(raw)
    except ValueError:
        return raw
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    stamp = now or datetime.now(UTC)
    seconds = int((stamp - moment.astimezone(UTC)).total_seconds())
    if seconds < 0:
        seconds = 0
    if seconds < 45:
        return "just now"
    if seconds < 90:
        return "1 min ago"
    if seconds < 3600:
        return f"{seconds // 60} min ago"
    hours = seconds // 3600
    if hours == 1:
        return "1 h ago"
    if hours < 36:
        return f"{hours} h ago"
    days = seconds // 86400
    if days == 1:
        return "1 d ago"
    return f"{days} d ago"


_COPY_SCRIPT = """
<script>
(function () {
  var btn = document.getElementById('copy');
  var secret = document.getElementById('bearer');
  var status = document.getElementById('copy-status');
  if (!btn || !secret) return;
  secret.addEventListener('click', function () {
    var range = document.createRange();
    range.selectNodeContents(secret);
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  });
  btn.addEventListener('click', function () {
    var text = secret.textContent || '';
    function ok() {
      btn.textContent = 'Copied';
      if (status) status.textContent = 'Copied to clipboard.';
    }
    function fail() {
      if (status) status.textContent = 'Copy failed. Select the key and copy it yourself.';
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(ok, fail);
    } else { fail(); }
  });
})();
</script>
"""
