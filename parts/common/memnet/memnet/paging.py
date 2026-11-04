"""Opaque paging cursor (issue #247 item 4; find and typed-walk).

A cursor is ``c_`` plus lowercase base32 of a small payload and a MAC. The
payload holds a format version, the query kind, the resume position (a row
count into this result, never an id or an id's order), the store change counter
and a fingerprint of the query parameters. The MAC is HMAC-SHA256 under the
session id, so a cursor is forged or foreign only if the MAC fails: it never
resolves in another session. ``limit`` is not in the fingerprint, so the page
size may change between pages.

Refusals: ``bad_cursor`` (malformed, forged, foreign session or other query
kind), ``cursor_mismatch`` (query parameters differ) and ``stale_cursor``
(the store changed since the page was made; reads do not change it).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json

from memnet.exceptions import MemNetError
from memnet.mem_store import MemStore

CURSOR_PREFIX = "c_"
CURSOR_VERSION = "1"
_MAC_LEN = 12  # bytes kept from the HMAC-SHA256 digest
_FP_LEN = 16  # hex characters of the parameter fingerprint


def fingerprint(query: str, /, **params: object) -> str:
    """Short digest of the query parameters a cursor is bound to."""
    text = json.dumps([query, params], sort_keys=True, default=str, ensure_ascii=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:_FP_LEN]


def _mac(session_id: str, body: bytes) -> bytes:
    key = session_id.encode("utf-8")
    return hmac.new(key, b"cursor:" + body, hashlib.sha256).digest()[:_MAC_LEN]


def encode_cursor(session_id: str, kind: str, fp: str, change_count: int, offset: int) -> str:
    body = "|".join((CURSOR_VERSION, kind, str(offset), str(change_count), fp)).encode("utf-8")
    raw = base64.b32encode(body + _mac(session_id, body)).decode("ascii")
    return CURSOR_PREFIX + raw.rstrip("=").lower()


def _bad(why: str) -> MemNetError:
    return MemNetError("bad_cursor", f"cursor is not valid: {why}")


def decode_cursor(session_id: str, token: str, kind: str, fp: str, store: MemStore) -> int:
    """Resume offset for ``token``, or raise bad_cursor / cursor_mismatch / stale_cursor."""
    if not token.startswith(CURSOR_PREFIX) or len(token) == len(CURSOR_PREFIX):
        raise _bad("not a cursor")
    text = token[len(CURSOR_PREFIX) :].upper()
    try:
        raw = base64.b32decode(text + "=" * (-len(text) % 8))
    except ValueError as exc:
        raise _bad("not a cursor") from exc
    if len(raw) <= _MAC_LEN:
        raise _bad("too short")
    body, mac = raw[:-_MAC_LEN], raw[-_MAC_LEN:]
    if not hmac.compare_digest(mac, _mac(session_id, body)):
        raise _bad("not issued by this session")
    try:
        version, c_kind, c_offset, c_count, c_fp = body.decode("utf-8").split("|")
        offset, count = int(c_offset), int(c_count)
    except ValueError as exc:
        raise _bad("unreadable") from exc
    if version != CURSOR_VERSION or c_kind != kind or offset < 0:
        raise _bad("not a cursor for this query")
    if c_fp != fp:
        raise MemNetError(
            "cursor_mismatch", "query parameters differ from the cursor's; restart without it"
        )
    if count != store.change_count:
        raise MemNetError(
            "stale_cursor", "the session changed since this cursor was issued; restart the query"
        )
    return offset
