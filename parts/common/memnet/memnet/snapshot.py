"""Optional user-initiated session export/import — wire-format snapshot files."""

from __future__ import annotations

import json
import os
import secrets
from datetime import timedelta
from pathlib import Path

from memnet.acl import SessionAcl, acl_from_dict, acl_to_dict
from memnet.atomic_file import atomic_write_bytes
from memnet.config import Caps
from memnet.exceptions import MemNetError
from memnet.fixed_tags import FIXED_TAGS
from memnet.mem_store import MemStore
from memnet.models import Record, SessionMeta, TagDef, TagMap
from memnet.output import emit_record, emit_wrn
from memnet.registry import SessionEntry, count, register
from memnet.session import SessionStore, purge_expired, utc_now
from memnet.tag_map import (
    leftover_wire_nick,
    load_persisted_map_from_lines,
    parse_line,
    tag_map_to_lines,
    validate_id,
)
from memnet.wire import split_snapshot_lines

SNAPSHOT_MAGIC = "# memnet-snapshot-v1"
# @SNAP format version (MN-REQ-06.16). 2 = carries the #@ACL: line, which is required.
# 1 = written before the ACL was persisted; it loads with ACL off (@ACL: absent|off).
SNAPSHOT_FORMAT = 2
SUPPORTED_SNAPSHOT_FORMATS = (1, 2)
# Copy of a format 1 file, kept once before the first format 2 write (MN-REQ-06.16).
V1_BACKUP_SUFFIX = ".v1.bak"
# Session ACL line. A ``#`` line, so readers that predate it skip it.
_ACL_PREFIX = "#@ACL:"
_SECTION_MAP = "# map"
_SECTION_REL = "# relations"
_SECTION_REC = "# records"


def _snapshot_emit_nick(rec: Record, used: set[str]) -> str:
    nick = rec.fields.get("id") or ""
    if nick:
        try:
            validate_id(nick)
            used.add(nick)
            return nick
        except MemNetError:
            pass
    return leftover_wire_nick(rec.hid, kind=rec.tag, used=used)


def _nick_of(rec: Record) -> str:
    return rec.fields.get("id") or rec.tag


def _canonical_tag(ss: SessionStore, tag: str) -> str:
    """SCHEMA key for a stored label. TagMap lookup is case-folding."""
    td = ss.tag_map.get(tag)
    if td is not None:
        return td.tag
    return tag.upper()


def _append_id_column(tag: str, fields: list[str]) -> list[str]:
    """Snapshot SCHEMA gains ``id`` when the live map omitted it (MN-REQ-01.9).

    Live SCHEMA is not rewritten. Fixed tags keep their declared columns.
    ``id`` is appended, not forced first.
    """
    if tag in FIXED_TAGS or "id" in fields:
        return fields
    return [*fields, "id"]


def _snapshot_emit_tag_map(ss: SessionStore) -> TagMap:
    """Widen SCHEMA with undeclared RAM keys so extras round-trip (MN-REQ-01.9)."""
    extras: dict[str, list[str]] = {}
    for rid in ss.store.write_order:
        rec = ss.store._by_hid.get(rid)
        if not rec:
            continue
        canon = _canonical_tag(ss, rec.tag)
        td = ss.tag_map.get(canon)
        base = list(td.fields) if td else ["id"]
        known = set(base)
        extra = extras.setdefault(canon, [])
        for key in rec.fields:
            if key in known:
                continue
            if canon in FIXED_TAGS or rec.tag in FIXED_TAGS:
                raise MemNetError(
                    "snapshot_unsaveable",
                    f"{rec.tag} nick={_nick_of(rec)} field={key} fixed_tag extra",
                )
            extra.append(key)
            known.add(key)
    tags: dict[str, TagDef] = {}
    max_fields = ss.caps.max_fields
    for tag, td in ss.tag_map.tags.items():
        fields = _append_id_column(tag, list(td.fields) + extras.get(tag, []))
        if len(fields) > max_fields:
            raise MemNetError(
                "snapshot_unsaveable",
                f"{tag} nick=- fields|{len(fields)}/{max_fields}",
            )
        tags[tag] = TagDef(tag=td.tag, fields=fields, kind=td.kind)
    for tag, extra in extras.items():
        if tag in tags or not extra:
            continue
        fields = _append_id_column(tag, ["id"] + extra)
        if len(fields) > max_fields:
            raise MemNetError(
                "snapshot_unsaveable",
                f"{tag} nick=- fields|{len(fields)}/{max_fields}",
            )
        tags[tag] = TagDef(tag=tag, fields=fields, kind="node")
    return TagMap(tags=tags)


def _emit_record_lines(
    ss: SessionStore,
) -> tuple[list[str], dict[str, str], TagMap]:
    emit_map = _snapshot_emit_tag_map(ss)
    used: set[str] = set()
    hid_to_nick: dict[str, str] = {}
    for rid in ss.store.write_order:
        rec = ss.store._by_hid.get(rid)
        if rec:
            hid_to_nick[rec.hid] = _snapshot_emit_nick(rec, used)
    rec_lines: list[str] = []
    for rid in ss.store.write_order:
        rec = ss.store._by_hid.get(rid)
        if not rec:
            continue
        fields = dict(rec.fields)
        fields["id"] = hid_to_nick[rec.hid]
        if rec.tag == "EDG":
            for key in ("src", "dist"):
                token = fields.get(key, "")
                if token in hid_to_nick:
                    fields[key] = hid_to_nick[token]
        clone = rec.model_copy(update={"fields": fields, "tag": _canonical_tag(ss, rec.tag)})
        rec_lines.append(emit_record(clone, emit_map))
    return rec_lines, hid_to_nick, emit_map


def snapshot_text(ss: SessionStore) -> str:
    rec_lines, hid_to_nick, emit_map = _emit_record_lines(ss)
    text = _format_snapshot(ss, rec_lines, emit_map)
    _verify_emitted_snapshot(ss, text, hid_to_nick, emit_map)
    return text


def _acl_line(acl: SessionAcl) -> str:
    payload = json.dumps(acl_to_dict(acl), sort_keys=True, separators=(",", ":"))
    return f"{_ACL_PREFIX}{payload}"


def _format_snapshot(ss: SessionStore, rec_lines: list[str], emit_map: TagMap) -> str:
    lines = [SNAPSHOT_MAGIC]
    m = ss.meta
    hw = "1" if m.has_writes else "0"
    modified = m.modified_at or "-"
    lines.append(
        f"@SNAP: {SNAPSHOT_FORMAT}|{m.session_id}|{m.created_at}|{m.expires_at}|"
        f"{m.ttl_minutes}|{hw}|{modified}"
    )
    lines.append(_acl_line(ss.acl))
    lines.append(_SECTION_MAP)
    lines.extend(tag_map_to_lines(emit_map))
    lines.append(_SECTION_REL)
    for rel in sorted(ss.relations):
        lines.append(f"@REL: {rel}")
    lines.append(_SECTION_REC)
    lines.extend(rec_lines)
    return "\n".join(lines) + "\n"


def _verify_emitted_snapshot(
    ss: SessionStore,
    text: str,
    hid_to_nick: dict[str, str],
    emit_map: TagMap,
) -> None:
    """Refuse save if the formatted blob would not load as the same values."""
    used_nicks: set[str] = set()
    lines = split_snapshot_lines(text)
    reloaded_acl = _parse_acl(lines)
    if reloaded_acl is None or acl_to_dict(reloaded_acl) != acl_to_dict(ss.acl):
        raise MemNetError("snapshot_unsaveable", "acl not reloadable")
    _, map_lines, _, rec_lines = _parse_sections(lines)
    try:
        loaded_map = load_persisted_map_from_lines(map_lines, ss.caps)
    except MemNetError as exc:
        raise MemNetError(
            "snapshot_unsaveable",
            f"map {exc.code} {exc.message}",
        ) from exc
    for tag, td in emit_map.tags.items():
        if tag in FIXED_TAGS:
            continue
        loaded = loaded_map.get(tag)
        if loaded is None or list(loaded.fields) != list(td.fields):
            raise MemNetError(
                "snapshot_unsaveable",
                f"{tag} nick=- schema not reloadable",
            )
    rec_iter = iter(rec_lines)
    for rid in ss.store.write_order:
        rec = ss.store._by_hid.get(rid)
        if not rec:
            continue
        try:
            line = next(rec_iter)
        except StopIteration as exc:
            raise MemNetError(
                "snapshot_unsaveable",
                f"{rec.tag} nick={_nick_of(rec)} missing emit row",
            ) from exc
        try:
            parsed = parse_line(line, loaded_map, ss.caps, used_nicks=used_nicks)
        except MemNetError as exc:
            raise MemNetError(
                "snapshot_unsaveable",
                f"{rec.tag} nick={_nick_of(rec)} {exc.code} {exc.message}",
            ) from exc
        want_id = hid_to_nick.get(rec.hid) or rec.fields.get("id") or ""
        keys = list(rec.fields.keys())
        if "id" not in keys:
            keys = ["id", *keys]
        for key in keys:
            raw = rec.fields.get(key, "")
            if key == "id":
                expected = want_id
            elif rec.tag == "EDG" and key in ("src", "dist"):
                expected = hid_to_nick.get(raw, raw)
            else:
                expected = raw
            got = parsed.fields.get(key, "")
            if got != expected:
                raise MemNetError(
                    "snapshot_unsaveable",
                    f"{rec.tag} nick={_nick_of(rec)} field={key}",
                )
    leftover = list(rec_iter)
    if leftover:
        raise MemNetError(
            "snapshot_unsaveable",
            f"extra emit rows {len(leftover)}",
        )


def snapshot_locator_schema_warnings(ss: SessionStore) -> list[str]:
    """Extras persist by widening snapshot SCHEMA. Warn only if save cannot.

    Fixed-tag extras (EDG / LAW) cannot widen; save refuses instead.
    """
    msgs: list[str] = []
    seen: set[tuple[str, str]] = set()
    for rid in ss.store.write_order:
        rec = ss.store._by_hid.get(rid)
        if not rec or rec.tag not in FIXED_TAGS:
            continue
        td = ss.tag_map.get(rec.tag)
        schema_fields = set(td.fields) if td else set()
        for key, val in rec.fields.items():
            if not val or key in schema_fields:
                continue
            pair = (rec.tag, key)
            if pair in seen:
                continue
            seen.add(pair)
            msgs.append(f"{rec.tag}.{key} fixed_tag extra cannot persist")
    return msgs


def _snap_format_of(raw: bytes) -> int | None:
    """@SNAP version of a snapshot blob, or None when there is no readable @SNAP line."""
    for line in raw.decode("utf-8", errors="replace").splitlines():
        if line.startswith("@SNAP:"):
            head = line.removeprefix("@SNAP:").strip().split("|", 1)[0]
            return int(head) if head.isdigit() else None
    return None


def backup_v1_before_v2(path: Path) -> None:
    """Keep the format 1 bytes once, before the first format 2 write over them (MN-REQ-06.16).

    Only a file whose @SNAP version is 1 is copied, to ``<file>.v1.bak`` at
    mode 0600. An existing backup is never overwritten. Nothing is dual-written:
    the snapshot itself is always format 2. A failed backup raises, so the v1
    file is not replaced without its copy.
    """
    if not path.is_file():
        return
    bak = path.with_name(path.name + V1_BACKUP_SUFFIX)
    if bak.exists():
        return
    raw = path.read_bytes()
    if _snap_format_of(raw) != 1:
        return
    atomic_write_bytes(bak, raw)


def write_snapshot(ss: SessionStore, path: str | Path, *, trailer: str = "") -> int:
    """Write the snapshot atomically at mode 0600 (MN-REQ-06.16).

    ``trailer`` is appended after the verified body. The caller passes only
    ``#`` lines (the upgrade passport), which readers skip. A format 1 file
    at ``path`` is backed up once to ``<file>.v1.bak`` before it is replaced.
    """
    for msg in snapshot_locator_schema_warnings(ss):
        emit_wrn("snapshot_schema_drop", msg)
    rec_lines, hid_to_nick, emit_map = _emit_record_lines(ss)
    text = _format_snapshot(ss, rec_lines, emit_map)
    _verify_emitted_snapshot(ss, text, hid_to_nick, emit_map)
    dest = Path(path)
    backup_v1_before_v2(dest)
    atomic_write_bytes(dest, (text + trailer).encode("utf-8"))
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
    meta, version = _parse_snap(snap_line)
    # Format 2 always carries the ACL line. Its absence is a corrupt file, not ACL off.
    if version >= 2 and not any(raw.strip().startswith(_ACL_PREFIX) for raw in lines):
        raise MemNetError("bad_snapshot", "format 2 snapshot is missing the #@ACL line")
    return meta, map_lines, rel_lines, rec_lines


def _parse_snap(line: str) -> tuple[SessionMeta, int]:
    payload = line.removeprefix("@SNAP:").strip()
    parts = payload.split("|")
    if len(parts) < 5:
        raise MemNetError("bad_snapshot", "malformed @SNAP line")
    version = int(parts[0])
    if version not in SUPPORTED_SNAPSHOT_FORMATS:
        raise MemNetError("bad_snapshot", f"unsupported snapshot version {version}")
    has_writes = len(parts) > 5 and parts[5] == "1"
    modified_at = parts[6] if len(parts) > 6 and parts[6] not in ("", "-") else None
    meta = SessionMeta(
        session_id=parts[1],
        created_at=parts[2],
        expires_at=parts[3],
        ttl_minutes=int(parts[4]),
        has_writes=has_writes,
        modified_at=modified_at,
    )
    return meta, version


def _parse_acl(lines: list[str]) -> SessionAcl | None:
    """Session ACL from the ``#@ACL:`` header line. None when the snapshot has none.

    A malformed line fails the load. Dropping it would silently turn ACL off.
    """
    for raw in lines:
        line = raw.strip()
        if not line.startswith(_ACL_PREFIX):
            continue
        try:
            data = json.loads(line.removeprefix(_ACL_PREFIX))
        except json.JSONDecodeError as exc:
            raise MemNetError("bad_snapshot", "malformed ACL line") from exc
        if not isinstance(data, dict):
            raise MemNetError("bad_snapshot", "ACL line must be an object")
        return acl_from_dict(data)
    return None


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
    hide_path: bool = False,
    preserve_clocks: bool = False,
) -> SessionStore:
    caps = caps or Caps()
    purge_expired(caps)
    if count() >= caps.max_sessions:
        raise MemNetError(
            "limit_exceeded",
            f"sessions|{count() + 1}/{caps.max_sessions}",
        )
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        cwd = os.getcwd()
        if hide_path:
            raise MemNetError("snapshot_not_found", "expire_snap", exit_code=2) from None
        raise MemNetError(
            "snapshot_not_found",
            f"{path}|serve_cwd={cwd}",
            example=(
                "path is resolved on the memnet serve host; "
                "use a path visible there or stream via session_load_lines"
            ),
        ) from None
    except OSError as exc:
        cwd = os.getcwd()
        if hide_path:
            raise MemNetError("snapshot_io_error", "expire_snap", exit_code=2) from exc
        raise MemNetError(
            "snapshot_io_error",
            f"{type(exc).__name__}|{path}|serve_cwd={cwd}",
        ) from exc
    return load_snapshot_text(
        text,
        caps=caps,
        ttl_minutes=ttl_minutes,
        keep_id=keep_id,
        preserve_clocks=preserve_clocks,
    )


def load_snapshot_text(
    text: str,
    *,
    caps: Caps | None = None,
    ttl_minutes: int | None = None,
    keep_id: bool = False,
    preserve_clocks: bool = False,
) -> SessionStore:
    caps = caps or Caps()
    lines = split_snapshot_lines(text)
    meta, map_lines, rel_lines, rec_lines = _parse_sections(lines)
    acl = _parse_acl(lines)
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
    if preserve_clocks:
        created_at = meta.created_at
        expires_at = meta.expires_at
    else:
        created_at = now.isoformat().replace("+00:00", "Z")
        expires_at = (now + timedelta(minutes=ttl)).isoformat().replace("+00:00", "Z")
    new_meta = SessionMeta(
        session_id=session_id,
        created_at=created_at,
        expires_at=expires_at,
        ttl_minutes=ttl,
        has_writes=meta.has_writes,
        modified_at=meta.modified_at,
        acl_enabled=bool(acl and acl.enabled),
    )
    store = MemStore(tag_map, caps)
    used_nicks: set[str] = set()
    for line in rec_lines:
        rec = parse_line(line, tag_map, caps, used_nicks=used_nicks)
        store.upsert(rec, relations=relations)
    entry = SessionEntry(
        meta=new_meta,
        tag_map=tag_map,
        store=store,
        relations=relations,
        acl=acl,
    )
    register(session_id, entry)
    return SessionStore(session_id, caps)


def materialise_snapshot_text(text: str, *, caps: Caps | None = None) -> SessionEntry:
    """Parse a snapshot into a store that is not registered.

    Checkpoint verify uses this throwaway store. It does not mint an id,
    slide clocks, or touch the live registry.
    """
    caps = caps or Caps()
    lines = split_snapshot_lines(text)
    meta, map_lines, rel_lines, rec_lines = _parse_sections(lines)
    # Parsed so checkpoint-verify fails on a corrupt ACL line; the throwaway entry keeps it.
    acl = _parse_acl(lines)
    tag_map = load_persisted_map_from_lines(map_lines, caps)
    relations = _parse_relations(rel_lines)
    if not relations:
        from memnet.session import _seed_relations

        relations = set(_seed_relations())
    store = MemStore(tag_map, caps)
    used_nicks: set[str] = set()
    for line in rec_lines:
        rec = parse_line(line, tag_map, caps, used_nicks=used_nicks)
        store.upsert(rec, relations=relations)
    return SessionEntry(
        meta=meta,
        tag_map=tag_map,
        store=store,
        relations=relations,
        acl=acl,
    )
