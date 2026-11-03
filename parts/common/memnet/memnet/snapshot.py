"""Optional user-initiated session export/import — wire-format snapshot files."""

from __future__ import annotations

import json
import os
import secrets
from datetime import timedelta
from pathlib import Path

from memnet.acl import SessionAcl, acl_from_dict, acl_to_dict
from memnet.atomic_file import atomic_write_bytes
from memnet.config import (
    Caps,
    normalize_relation,
    standard_relation,
    validate_snapshot_relation,
)
from memnet.exceptions import MemNetError
from memnet.fixed_tags import FIXED_TAGS
from memnet.mem_store import MemStore, _split_suffix
from memnet.models import Record, SessionMeta, TagDef, TagMap
from memnet.output import emit_record, emit_record_line, emit_wrn
from memnet.registry import SessionEntry
from memnet.session import (
    SessionStore,
    _next_touch_seq,
    claim_slot,
    purge_expired,
    register_claimed,
    release_claim,
    utc_now,
)
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
# Per-prefix minted-id high-water, written only when it is above the live ids
# (a deleted id must not be re-minted after reload). A ``#`` line; optional.
_IDHW_PREFIX = "#@IDHW: "
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
    if rec.tag == "EDG":
        # Legacy id-less edge: emit an empty id so it reloads id-less (no sn_edg_ nick).
        return ""
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


def collect_undeclared_extras(ss: SessionStore) -> dict[str, list[str]]:
    """Undeclared RAM keys per canonical tag, first-seen order (MN-REQ-01.9).

    Fixed-tag extras fail closed (``snapshot_unsaveable``), same as save.
    """
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
    return extras


def effective_snapshot_fields(ss: SessionStore) -> dict[str, list[str]]:
    """Field lists snapshot save would emit (MN-REQ-05.4).

    Declared SCHEMA fields, plus undeclared extras on any row of that tag,
    plus ``id`` when save appends it. Mutate and save MUST share this helper.
    """
    extras = collect_undeclared_extras(ss)
    fields_by_tag: dict[str, list[str]] = {}
    for tag, td in ss.tag_map.tags.items():
        fields_by_tag[tag] = _append_id_column(tag, list(td.fields) + extras.get(tag, []))
    for tag, extra in extras.items():
        if tag in fields_by_tag or not extra:
            continue
        fields_by_tag[tag] = _append_id_column(tag, ["id"] + extra)
    return fields_by_tag


def first_over_field_cap(
    ss: SessionStore,
    *,
    skip_fixed: bool = False,
) -> tuple[str, int, int] | None:
    """First tag whose effective field count exceeds ``max_fields``, else None.

    Mutate skips fixed tags (EDG/LAW): their declared width is engine-defined
    and is not a write the caller made. Save still checks every tag.
    """
    max_fields = ss.caps.max_fields
    for tag, fields in effective_snapshot_fields(ss).items():
        if skip_fixed and tag in FIXED_TAGS:
            continue
        if len(fields) > max_fields:
            return tag, len(fields), max_fields
    return None


def _indexed_field_counts(ss: SessionStore) -> tuple[dict[str, int], bool]:
    """Effective field count per canonical tag from the store's field-key index.

    Same counts as ``effective_snapshot_fields`` (an undeclared key counts once
    per row that carries it, as ``collect_undeclared_extras`` does) without a
    row walk. The flag is True when some fixed tag carries an undeclared key.
    """
    store = ss.store
    extra_n: dict[str, int] = {}
    extra_has_id: set[str] = set()
    fixed_extra = False
    for raw_tag, keys in store.field_keys_by_tag().items():
        canon = _canonical_tag(ss, raw_tag)
        td = ss.tag_map.get(canon)
        known = set(td.fields) if td else {"id"}
        undeclared = [k for k in keys if k not in known]
        if not undeclared:
            continue
        if canon in FIXED_TAGS or raw_tag in FIXED_TAGS:
            fixed_extra = True
        counts = store.field_key_counts(raw_tag)
        extra_n[canon] = extra_n.get(canon, 0) + sum(counts[k] for k in undeclared)
        if "id" in undeclared:
            extra_has_id.add(canon)
    out: dict[str, int] = {}
    for tag, td in ss.tag_map.tags.items():
        n = len(td.fields) + extra_n.get(tag, 0)
        if tag not in FIXED_TAGS and "id" not in td.fields and tag not in extra_has_id:
            n += 1
        out[tag] = n
    for tag, n in extra_n.items():
        if tag not in out:
            out[tag] = 1 + n
    return out, fixed_extra


def refuse_mutate_field_cap(ss: SessionStore) -> None:
    """Mutate: refuse when a user tag's effective fields could not save.

    Decided from the store's field-key index; the full row walk runs only to
    build the refusal (same code and message as before).
    """
    counts, fixed_extra = _indexed_field_counts(ss)
    cap = ss.caps.max_fields
    if not fixed_extra and not any(n > cap for tag, n in counts.items() if tag not in FIXED_TAGS):
        return
    over = first_over_field_cap(ss, skip_fixed=True)
    if over is None:
        return
    _tag, n, cap = over
    raise MemNetError("limit_exceeded", f"fields|{n}/{cap}")


def _snapshot_emit_tag_map(ss: SessionStore) -> TagMap:
    """Widen SCHEMA with undeclared RAM keys so extras round-trip (MN-REQ-01.9)."""
    field_lists = effective_snapshot_fields(ss)
    max_fields = ss.caps.max_fields
    tags: dict[str, TagDef] = {}
    for tag, fields in field_lists.items():
        if len(fields) > max_fields:
            raise MemNetError(
                "snapshot_unsaveable",
                f"{tag} nick=- fields|{len(fields)}/{max_fields}",
            )
        td = ss.tag_map.get(tag)
        if td is not None:
            tags[tag] = TagDef(tag=td.tag, fields=fields, kind=td.kind)
        else:
            tags[tag] = TagDef(tag=tag, fields=fields, kind="node")
    return TagMap(tags=tags)


def _snapshot_nicks(ss: SessionStore) -> dict[str, str]:
    used: set[str] = set()
    hid_to_nick: dict[str, str] = {}
    for rid in ss.store.write_order:
        rec = ss.store._by_hid.get(rid)
        if rec:
            hid_to_nick[rec.hid] = _snapshot_emit_nick(rec, used)
    return hid_to_nick


def _emit_one_record_line(
    ss: SessionStore,
    rec: Record,
    hid_to_nick: dict[str, str],
    emit_map: TagMap,
) -> str:
    """One record line exactly as snapshot save writes it."""
    fields = dict(rec.fields)
    fields["id"] = hid_to_nick[rec.hid]
    if rec.tag == "EDG":
        if fields.get("relation"):
            # Fold a raw stored name (pre-fix store) to the standard one.
            fields["relation"] = standard_relation(fields["relation"])
        for key in ("src", "dist"):
            token = fields.get(key, "")
            if token in hid_to_nick:
                fields[key] = hid_to_nick[token]
    clone = rec.model_copy(update={"fields": fields, "tag": _canonical_tag(ss, rec.tag)})
    if rec.tag == "EDG" and not fields.get("id"):
        # Id-less edge: write the stored (empty) id, not the _elN display handle.
        td = emit_map.get(clone.tag)
        if td is None:
            raise MemNetError(
                "snapshot_unsaveable",
                f"{clone.tag} nick=- no emit row",
            )
        values = [fields.get(f, "") for f in td.fields]
        return emit_record_line(clone.tag, values)
    return emit_record(clone, emit_map)


def _emit_record_lines(
    ss: SessionStore,
) -> tuple[list[str], dict[str, str], TagMap]:
    emit_map = _snapshot_emit_tag_map(ss)
    hid_to_nick = _snapshot_nicks(ss)
    rec_lines: list[str] = []
    for rid in ss.store.write_order:
        rec = ss.store._by_hid.get(rid)
        if rec:
            rec_lines.append(_emit_one_record_line(ss, rec, hid_to_nick, emit_map))
    return rec_lines, hid_to_nick, emit_map


def refuse_mutate_line_cap(ss: SessionStore, hids: set[str], *, budget: bool = True) -> None:
    """Mutate: refuse when a written record's whole escaped line could not save.

    Measures the full record line (all fields) as snapshot save would emit it,
    so no accepted write makes a snapshot unsaveable. ``budget=False`` skips the
    session byte budget (bypass-path deletes shrink the session; MN-REQ-14.11).
    """
    if not hids:
        return
    from memnet.session_bytes import _debug, _sync_view, assert_consistent, check_budget

    # MN-REQ-14.12: sync the byte ledger first (always, so its total stays exact).
    view = _sync_view(ss, hids)
    if view is not None:
        hid_to_nick, emit_map = view
    else:
        try:
            emit_map = _snapshot_emit_tag_map(ss)
        except MemNetError as exc:
            if exc.code == "snapshot_unsaveable":
                return  # fixed-tag width; save reports it
            raise
        hid_to_nick = _snapshot_nicks(ss)
    cap = ss.caps.max_line_bytes
    total = 0
    # The SCHEMA lines: a write can widen them (undeclared keys on a record).
    for line in tag_map_to_lines(emit_map):
        n = len(line.encode("utf-8"))
        if n > cap:
            raise MemNetError("limit_exceeded", f"line_bytes|{n}/{cap}")
        total += n
    # Edges are written with endpoint nicks, so a node write or rename changes
    # every incident edge line as well.
    store = ss.store
    check = set(hids)
    for hid in hids:
        check |= store._edges_by_src.get(hid, set())
        check |= store._edges_by_dist.get(hid, set())
    for hid in check:
        rec = store._by_hid.get(hid)
        if rec is None:
            continue
        n = len(_emit_one_record_line(ss, rec, hid_to_nick, emit_map).encode("utf-8"))
        if n > cap:
            raise MemNetError("limit_exceeded", f"line_bytes|{n}/{cap}")
    if budget:
        check_budget(ss, total, hid_to_nick, emit_map)
    elif view is not None and _debug():
        assert_consistent(ss)


def _refuse_session_bytes(
    ss: SessionStore, hid_to_nick: dict[str, str], emit_map: TagMap, total: int
) -> None:
    """MN-REQ-14.10: refuse when the session's escaped snapshot line bytes
    (schema + record + edge lines, UTF-8) would exceed max_session_bytes."""
    budget = ss.caps.max_session_bytes
    for rid in ss.store.write_order:
        rec = ss.store._by_hid.get(rid)
        if rec:
            total += len(_emit_one_record_line(ss, rec, hid_to_nick, emit_map).encode("utf-8"))
            if total > budget:
                break
    if total > budget:
        raise MemNetError("limit_exceeded", f"session_bytes|{total}/{budget}")


def refuse_session_budget(ss: SessionStore) -> None:
    """MN-REQ-14.10/14.11: refuse when the whole session exceeds its byte budget.

    Used by save (the file would be over budget); the write-time check lives in
    :func:`refuse_mutate_line_cap`.
    """
    try:
        emit_map = _snapshot_emit_tag_map(ss)
    except MemNetError as exc:
        if exc.code == "snapshot_unsaveable":
            return  # save reports it
        raise
    total = sum(len(line.encode("utf-8")) for line in tag_map_to_lines(emit_map))
    _refuse_session_bytes(ss, _snapshot_nicks(ss), emit_map, total)


def refuse_snapshot_text_budget(map_lines: list[str], rec_lines: list[str], caps: Caps) -> None:
    """Load: refuse a snapshot whose stored SCHEMA + record lines exceed the budget."""
    budget = caps.max_session_bytes
    total = 0
    for line in (*map_lines, *rec_lines):
        total += len(line.encode("utf-8"))
        if total > budget:
            raise MemNetError("limit_exceeded", f"session_bytes|{total}/{budget}")


def snapshot_text(ss: SessionStore) -> str:
    rec_lines, hid_to_nick, emit_map = _emit_record_lines(ss)
    text = _format_snapshot(ss, rec_lines, emit_map)
    _verify_emitted_snapshot(ss, text, hid_to_nick, emit_map)
    return text


def _acl_line(acl: SessionAcl) -> str:
    payload = json.dumps(acl_to_dict(acl), sort_keys=True, separators=(",", ":"))
    return f"{_ACL_PREFIX}{payload}"


def _idhw_line(ss: SessionStore) -> str | None:
    """``#@IDHW:`` line when some prefix's high-water is above its max live suffix."""
    hw = ss.store.id_high_water()
    if not hw:
        return None
    live: dict[str, int] = {}
    for nick in ss.store._by_hid._nick:  # live nicknames (index keys); save walks rows anyway
        split = _split_suffix(nick)
        if split is not None and split[1] > live.get(split[0], -1):
            live[split[0]] = split[1]
    if not any(n > live.get(prefix, -1) for prefix, n in hw.items()):
        return None
    return _IDHW_PREFIX + json.dumps(hw, sort_keys=True, separators=(",", ":"))


def _parse_idhw(lines: list[str]) -> dict[str, int] | None:
    """High-water from the ``#@IDHW:`` line. Absent or malformed: None (ignored)."""
    for raw in lines:
        line = raw.strip()
        if not line.startswith(_IDHW_PREFIX.rstrip()):
            continue
        try:
            data = json.loads(line.removeprefix(_IDHW_PREFIX.rstrip()))
        except ValueError:
            return None
        if not isinstance(data, dict):
            return None
        return {
            k: v
            for k, v in data.items()
            if isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool) and v >= 0
        }
    return None


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
    idhw = _idhw_line(ss)
    if idhw is not None:
        lines.append(idhw)
    lines.append(_SECTION_MAP)
    lines.extend(tag_map_to_lines(emit_map))
    lines.append(_SECTION_REL)
    for rel in sorted({standard_relation(r) for r in ss.relations}):
        validate_snapshot_relation(rel)
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
            parsed = parse_line(
                line,
                loaded_map,
                ss.caps,
                used_nicks=used_nicks,
                keep_edge_id_less=True,
            )
        except MemNetError as exc:
            raise MemNetError(
                "snapshot_unsaveable",
                f"{rec.tag} nick={_nick_of(rec)} {exc.code} {exc.message}",
            ) from exc
        if rec.tag == "EDG" and rec.fields.get("relation"):
            validate_snapshot_relation(standard_relation(rec.fields["relation"]))
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
            elif rec.tag == "EDG" and key == "relation":
                expected = standard_relation(raw)
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
    refuse_session_budget(ss)  # MN-REQ-14.11: a file over budget would not reload
    dest = Path(path)
    try:
        backup_v1_before_v2(dest)
        atomic_write_bytes(dest, (text + trailer).encode("utf-8"))
    except OSError as exc:
        # A real I/O failure is a refused save, not an internal error. Eviction
        # and session save both see the typed refusal.
        raise MemNetError("snapshot_unsaveable", f"write failed: {exc.strerror or 'I/O'}") from exc
    ss.mark_saved()
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
                relations.add(normalize_relation(name))
        elif line and not line.startswith("#"):
            relations.add(normalize_relation(line))
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
    refuse_snapshot_text_budget(map_lines, rec_lines, caps)  # MN-REQ-14.11
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
    # A load is a touch with a fresh TTL (MN-REQ-05.5). Upgrade restore keeps its clocks.
    if preserve_clocks:
        created_at = meta.created_at
        expires_at = meta.expires_at
        modified_at = meta.modified_at
    else:
        created_at = now.isoformat().replace("+00:00", "Z")
        expires_at = (now + timedelta(minutes=ttl)).isoformat().replace("+00:00", "Z")
        modified_at = created_at
    new_meta = SessionMeta(
        session_id=session_id,
        created_at=created_at,
        expires_at=expires_at,
        ttl_minutes=ttl,
        has_writes=meta.has_writes,
        modified_at=modified_at,
        acl_enabled=bool(acl and acl.enabled),
    )
    store = MemStore(tag_map, caps)
    used_nicks: set[str] = set()
    parsed = [
        parse_line(line, tag_map, caps, used_nicks=used_nicks, keep_edge_id_less=True)
        for line in rec_lines
    ]
    for rec in parsed:
        store.upsert(rec, relations=relations)
    idhw = _parse_idhw(lines)
    if idhw:
        store.raise_id_high_water(idhw)
    entry = SessionEntry(
        meta=new_meta,
        tag_map=tag_map,
        store=store,
        relations=relations,
        acl=acl,
        touch_seq=_next_touch_seq(),
    )
    claim_slot(caps)
    try:
        register_claimed(session_id, entry)
    except BaseException:
        release_claim()  # never registered: the slot goes back, the error goes up
        raise
    loaded = SessionStore(session_id, caps)
    loaded.restored = True
    return loaded


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
    parsed = [
        parse_line(line, tag_map, caps, used_nicks=used_nicks, keep_edge_id_less=True)
        for line in rec_lines
    ]
    for rec in parsed:
        store.upsert(rec, relations=relations)
    idhw = _parse_idhw(lines)
    if idhw:
        store.raise_id_high_water(idhw)
    return SessionEntry(
        meta=meta,
        tag_map=tag_map,
        store=store,
        relations=relations,
        acl=acl,
    )
