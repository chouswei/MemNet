"""SQLite invite and Bearer stores. Plaintext keys are never written."""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat()


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class InviteRow:
    id: str
    label: str
    created_at: str
    expires_at: str
    redeemed_at: str | None
    redeemed_email: str | None
    redeemed_sub: str | None
    revoked: bool

    @property
    def status(self) -> str:
        if self.revoked:
            return "revoked"
        if self.redeemed_at:
            return "redeemed"
        if datetime.fromisoformat(self.expires_at) < _now():
            return "expired"
        return "open"


@dataclass(frozen=True)
class KeyRow:
    id: str
    email: str
    google_sub: str
    invite_id: str
    created_at: str
    revoked: bool


class PortalStore:
    def __init__(self, path: str) -> None:
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self.migrate()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def migrate(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS invites (
                    id TEXT PRIMARY KEY,
                    token_hash TEXT NOT NULL UNIQUE,
                    label TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    redeemed_at TEXT,
                    redeemed_email TEXT,
                    redeemed_sub TEXT,
                    revoked INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS keys (
                    id TEXT PRIMARY KEY,
                    key_hash TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL,
                    google_sub TEXT NOT NULL,
                    invite_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            self._conn.commit()

    def mint_invite(self, *, label: str, ttl_hours: int) -> tuple[InviteRow, str]:
        token = secrets.token_urlsafe(32)
        row_id = "inv_" + secrets.token_hex(4)
        created = _now()
        expires = created + timedelta(hours=ttl_hours)
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO invites (
                    id, token_hash, label, created_at, expires_at, revoked
                ) VALUES (?, ?, ?, ?, ?, 0)
                """,
                (row_id, hash_secret(token), label.strip(), _iso(created), _iso(expires)),
            )
            self._conn.commit()
        row = self._invite_by_id(row_id)
        assert row is not None
        return row, token

    def list_invites(self) -> list[InviteRow]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM invites ORDER BY created_at DESC").fetchall()
        return [self._invite(row) for row in rows]

    def invite_by_token(self, token: str) -> InviteRow | None:
        if not token:
            return None
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM invites WHERE token_hash = ?",
                (hash_secret(token),),
            ).fetchone()
        return self._invite(row) if row else None

    def revoke_invite(self, invite_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE invites SET revoked = 1 WHERE id = ?",
                (invite_id,),
            )
            self._conn.execute(
                "UPDATE keys SET revoked = 1 WHERE invite_id = ?",
                (invite_id,),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def issue_key(self, invite: InviteRow, *, email: str, google_sub: str) -> str:
        if invite.status != "open":
            raise PermissionError(invite.status)
        plaintext = "mn_tip_" + secrets.token_urlsafe(32)
        key_id = "key_" + secrets.token_hex(4)
        created = _iso(_now())
        with self._lock:
            fresh = self._conn.execute(
                "SELECT * FROM invites WHERE id = ?",
                (invite.id,),
            ).fetchone()
            current = self._invite(fresh) if fresh else None
            if current is None or current.status != "open":
                raise PermissionError(current.status if current else "missing")
            self._conn.execute(
                """
                INSERT INTO keys (
                    id, key_hash, email, google_sub, invite_id, created_at, revoked
                ) VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (key_id, hash_secret(plaintext), email.lower(), google_sub, invite.id, created),
            )
            self._conn.execute(
                """
                UPDATE invites
                SET redeemed_at = ?, redeemed_email = ?, redeemed_sub = ?
                WHERE id = ?
                """,
                (created, email.lower(), google_sub, invite.id),
            )
            self._conn.commit()
        return plaintext

    def list_keys(self) -> list[KeyRow]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM keys ORDER BY created_at DESC").fetchall()
        return [self._key(row) for row in rows]

    def revoke_key(self, key_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE keys SET revoked = 1 WHERE id = ?",
                (key_id,),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def key_is_active(self, plaintext: str) -> bool:
        if not plaintext:
            return False
        with self._lock:
            row = self._conn.execute(
                """
                SELECT keys.revoked AS key_revoked, invites.revoked AS invite_revoked
                FROM keys
                JOIN invites ON invites.id = keys.invite_id
                WHERE keys.key_hash = ?
                """,
                (hash_secret(plaintext),),
            ).fetchone()
        if row is None:
            return False
        return row["key_revoked"] == 0 and row["invite_revoked"] == 0

    def contains_plaintext(self, plaintext: str) -> bool:
        """True when the raw secret appears in stored columns (it must not)."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT token_hash, label, redeemed_email, redeemed_sub FROM invites"
            ).fetchall()
            keys = self._conn.execute("SELECT key_hash, email, google_sub FROM keys").fetchall()
        haystack = " ".join(
            str(value) for row in list(rows) + list(keys) for value in row if value is not None
        )
        return plaintext in haystack

    def _invite_by_id(self, invite_id: str) -> InviteRow | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM invites WHERE id = ?",
                (invite_id,),
            ).fetchone()
        return self._invite(row) if row else None

    @staticmethod
    def _invite(row: sqlite3.Row) -> InviteRow:
        return InviteRow(
            id=row["id"],
            label=row["label"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            redeemed_at=row["redeemed_at"],
            redeemed_email=row["redeemed_email"],
            redeemed_sub=row["redeemed_sub"],
            revoked=bool(row["revoked"]),
        )

    @staticmethod
    def _key(row: sqlite3.Row) -> KeyRow:
        return KeyRow(
            id=row["id"],
            email=row["email"],
            google_sub=row["google_sub"],
            invite_id=row["invite_id"],
            created_at=row["created_at"],
            revoked=bool(row["revoked"]),
        )
