"""Optional user-initiated session export/import — wire-format snapshot files."""

from __future__ import annotations

import secrets
from datetime import timedelta
from pathlib import Path

from memnet.config import Caps
from memnet.exceptions import MemNetError
from memnet.mem_store import MemStore
from memnet.models import SessionMeta
from memnet.output import emit_record
from memnet.registry import SessionEntry, count, register
from memnet.session import SessionStore, purge_expired, utc_now
from memnet.tag_map import load_persisted_map_from_lines, parse_line, tag_map_to_lines

SNAPSHOT_MAGIC = "# memnet-snapshot-v1"
_SECTION_MAP = "# map"
_SECTION_REL = "# relations"
_SECTION_REC = "# records"


def snapshot_text(ss: SessionStore) -> str:
    lines = [SNAPSHOT_MAGIC]
    m = ss.meta
    hw = "1" if m.has_writes else "0"
    lines.append(f"@SNAP: 1|{m.session_id}|{m.created_at}|{m.expires_at}|{m.ttl_minutes}|{hw}")
    lines.append(_SECTION_MAP)
    lines.extend(tag_map_to_lines(ss.tag_map))
    lines.append(_SECTION_REL)
    for rel in sorted(ss.relations):
        lines.append(f"@REL: {rel}")
    lines.append(_SECTION_REC)
    for rid in ss.store.write_order:
        rec = ss.store.by_id.get(rid)
        if rec:
            lines.append(emit_record(rec, ss.tag_map))
    return "\n".join(lines) + "\n"


def write_snapshot(ss: SessionStore, path: str | Path) -> int:
    text = snapshot_text(ss)
    Path(path).write_text(text, encoding="utf-8")
    return ss.store.row_count_non_law()


def _parse_sections(lines: list[str]) -> tuple[SessionMeta, list[str], list[str], list[str]]:
    if not lines or lines[0].strip() != SNAPSHOT_MAGIC:
        raise MemNetError("bad_snapshot", "expected memnet-snapshot-v1 header")
    snap_line = ""
    map_lines: list[str] = []
    rel_lines: list[str] = []
    rec_lines: list[str] = []
    section = ""
    for raw in lines[1:]:
        line = raw.strip()
        if not line:
            continue
        if line in (_SECTION_MAP, _SECTION_REL, _SECTION_REC):
            section = line
            continue
        if line.startswith("#"):
            continue
        if line.startswith("@SNAP:"):
            snap_line = line
            continue
        if section == _SECTION_MAP:
            map_lines.append(line)
        elif section == _SECTION_REL:
            rel_lines.append(line)
        elif section == _SECTION_REC:
            rec_lines.append(line)
    if not snap_line:
        raise MemNetError("bad_snapshot", "missing @SNAP line")
    return _parse_snap(snap_line), map_lines, rel_lines, rec_lines


def _parse_snap(line: str) -> SessionMeta:
    payload = line.removeprefix("@SNAP:").strip()
    parts = payload.split("|")
    if len(parts) < 5:
        raise MemNetError("bad_snapshot", "malformed @SNAP line")
    version = int(parts[0])
    if version != 1:
        raise MemNetError("bad_snapshot", f"unsupported snapshot version {version}")
    has_writes = len(parts) > 5 and parts[5] == "1"
    return SessionMeta(
        session_id=parts[1],
        created_at=parts[2],
        expires_at=parts[3],
        ttl_minutes=int(parts[4]),
        has_writes=has_writes,
    )


def _parse_relations(rel_lines: list[str]) -> set[str]:
    relations: set[str] = set()
    for line in rel_lines:
        if line.startswith("@REL:"):
            name = line.removeprefix("@REL:").strip()
            if name:
                relations.add(name)
        elif line and not line.startswith("#"):
            relations.add(line)
    return relations


def load_snapshot(
    path: str | Path,
    *,
    caps: Caps | None = None,
    ttl_minutes: int | None = None,
    keep_id: bool = False,
) -> SessionStore:
    caps = caps or Caps()
    purge_expired(caps)
    if count() >= caps.max_sessions:
        raise MemNetError(
            "limit_exceeded",
            f"sessions|{count() + 1}/{caps.max_sessions}",
        )
    text = Path(path).read_text(encoding="utf-8")
    return load_snapshot_text(
        text,
        caps=caps,
        ttl_minutes=ttl_minutes,
        keep_id=keep_id,
    )


def load_snapshot_text(
    text: str,
    *,
    caps: Caps | None = None,
    ttl_minutes: int | None = None,
    keep_id: bool = False,
) -> SessionStore:
    caps = caps or Caps()
    meta, map_lines, rel_lines, rec_lines = _parse_sections(text.splitlines())
    tag_map = load_persisted_map_from_lines(map_lines, caps)
    relations = _parse_relations(rel_lines)
    if not relations:
        from memnet.session import _seed_relations

        relations = set(_seed_relations())

    session_id = meta.session_id if keep_id else f"mn_{secrets.token_hex(4)}"
    now = utc_now()
    ttl = ttl_minutes if ttl_minutes is not None else meta.ttl_minutes
    if ttl < 1 or ttl > 1440:
        raise MemNetError("bad_ttl", "ttl must be 1..1440")
    expires = now + timedelta(minutes=ttl)
    new_meta = SessionMeta(
        session_id=session_id,
        created_at=now.isoformat().replace("+00:00", "Z"),
        expires_at=expires.isoformat().replace("+00:00", "Z"),
        ttl_minutes=ttl,
        has_writes=meta.has_writes,
    )
    store = MemStore(tag_map, caps)
    for line in rec_lines:
        rec = parse_line(line, tag_map, caps)
        store.upsert(rec, relations=relations)
    entry = SessionEntry(
        meta=new_meta,
        tag_map=tag_map,
        store=store,
        relations=relations,
    )
    register(session_id, entry)
    return SessionStore(session_id, caps)
