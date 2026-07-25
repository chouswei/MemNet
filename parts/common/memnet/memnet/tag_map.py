"""tagMap — merge fixed + user map; parse and validate ingest lines."""

from __future__ import annotations

import re

from memnet.config import ID_PATTERN, RELATION_PATTERN, RESERVED_TAGS, Caps
from memnet.exceptions import MemNetError
from memnet.fixed_tags import FIXED_TAGS, fixed_tag_map
from memnet.models import Record, TagDef, TagMap
from memnet.wire import emit_record_line, parse_tag_line, split_payload, join_payload

_ID_RE = re.compile(ID_PATTERN)
_REL_RE = re.compile(RELATION_PATTERN)
# Shared dialect: SCHEMA MOD ; fields=id path summary status recycle
_RE_SCHEMA = re.compile(
    r"^SCHEMA\s+([A-Za-z_][A-Za-z0-9_]*)\s*(.*)$",
    re.IGNORECASE,
)
_RE_FIELD = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$",
)


def _split_schema_fields_tail(tail: str) -> dict[str, str]:
    """Parse ``;``-joined ``key=value`` atoms from a SCHEMA line tail."""
    tail = tail.strip()
    if not tail:
        return {}
    if tail.startswith(";"):
        tail = tail[1:].strip()
    out: dict[str, str] = {}
    if not tail:
        return out
    parts: list[str] = []
    buf: list[str] = []
    in_str = False
    i = 0
    while i < len(tail):
        ch = tail[i]
        if ch == '"' and (i == 0 or tail[i - 1] != "\\"):
            in_str = not in_str
            buf.append(ch)
            i += 1
            continue
        if ch == ";" and not in_str:
            parts.append("".join(buf).strip())
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    parts.append("".join(buf).strip())
    for part in parts:
        if not part:
            continue
        m = _RE_FIELD.match(part)
        if not m:
            raise MemNetError(
                "invalid_schema",
                f"SCHEMA field must be key=value got {part!r}",
            )
        key, val = m.group(1), m.group(2).strip()
        if val.startswith('"') and val.endswith('"') and len(val) >= 2:
            val = val[1:-1]
        out[key] = val
    return out


def parse_schema_shared_line(line: str) -> tuple[str, list[str]] | None:
    """Parse shared-dialect SCHEMA line → (kind, ordered field names).

    Returns None if the line is not a SCHEMA declaration.
    """
    s = line.strip()
    m = _RE_SCHEMA.match(s)
    if not m:
        return None
    tag = m.group(1).upper()
    kv = _split_schema_fields_tail(m.group(2) or "")
    raw_fields = kv.get("fields", "").strip()
    if not raw_fields:
        raise MemNetError("empty_fields", f"SCHEMA {tag} missing fields=")
    # Space-separated field names (R1 atom; matches MemNet.g4 BARE_ATOM).
    field_names = [p for p in raw_fields.split() if p]
    if not field_names:
        raise MemNetError("empty_fields", f"SCHEMA {tag} has no fields")
    return tag, field_names


def parse_map_line(line: str) -> tuple[str, list[str]]:
    """Parse one map line: shared-dialect SCHEMA preferred; legacy @TAG pipe accepted."""
    s = line.strip()
    shared = parse_schema_shared_line(s)
    if shared is not None:
        return shared
    tag, payload = parse_tag_line(s)
    return tag, split_payload(payload)


def _register_user_tag(
    user: dict[str, TagDef],
    tag: str,
    field_names: list[str],
    caps: Caps,
    *,
    allow_fixed_skip: bool = False,
) -> None:
    if tag in RESERVED_TAGS:
        raise MemNetError("reserved_tag", f"tag {tag} is reserved")
    if tag in FIXED_TAGS:
        if allow_fixed_skip:
            return
        raise MemNetError("fixed_tag", f"cannot redefine fixed tag {tag}")
    if tag in user:
        raise MemNetError("duplicate_tag", f"duplicate tag {tag} in map")
    if not field_names:
        raise MemNetError("empty_fields", f"tag {tag} has no fields")
    if field_names[0] != "id":
        raise MemNetError("id_first", f"tag {tag} must start with id field")
    if len(field_names) > caps.max_fields:
        raise MemNetError(
            "limit_exceeded",
            f"fields|{len(field_names)}/{caps.max_fields}",
        )
    kind = "edge" if tag == "EDG" else "node"
    user[tag] = TagDef(tag=tag, fields=field_names, kind=kind)


def load_user_map(lines: list[str], caps: Caps | None = None) -> dict[str, TagDef]:
    caps = caps or Caps()
    user: dict[str, TagDef] = {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        tag, field_names = parse_map_line(line)
        _register_user_tag(user, tag, field_names, caps)
    if len(user) > caps.max_tags:
        raise MemNetError("limit_exceeded", f"tags|{len(user)}/{caps.max_tags}")
    return user


def merge_fixed(user_map: dict[str, TagDef]) -> TagMap:
    merged = dict(FIXED_TAGS)
    merged.update(user_map)
    return TagMap(tags=merged)


def load_persisted_map_from_lines(lines: list[str], caps: Caps | None = None) -> TagMap:
    """Load tag_map.txt from session dir (may include fixed tags — skip those)."""
    caps = caps or Caps()
    user: dict[str, TagDef] = {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        tag, field_names = parse_map_line(line)
        _register_user_tag(
            user, tag, field_names, caps, allow_fixed_skip=True
        )
    return merge_fixed(user)


def load_map_from_lines(lines: list[str], caps: Caps | None = None) -> TagMap:
    user = load_user_map(lines, caps)
    return merge_fixed(user)


def load_map_from_file(path: str, caps: Caps | None = None) -> TagMap:
    text = open(path, encoding="utf-8").read()
    return load_map_from_lines(text.splitlines(), caps)


def emit_schema_line(tag: str, fields: list[str]) -> str:
    """Emit shared-dialect SCHEMA line (preferred map surface)."""
    return f"SCHEMA {tag} ; fields={' '.join(fields)}"


def tag_map_to_lines(tag_map: TagMap) -> list[str]:
    lines: list[str] = []
    for tag in tag_map.tag_names():
        td = tag_map.tags[tag]
        lines.append(emit_schema_line(tag, td.fields))
    return lines


def validate_id(record_id: str) -> None:
    if not record_id or len(record_id) > 64:
        raise MemNetError("invalid_id", f"id length must be 1-64 got {len(record_id)}")
    if not _ID_RE.match(record_id):
        raise MemNetError("invalid_id", f"id {record_id} invalid use A-Za-z0-9_.-")


def _coerce_edg_values(values: list[str], nfields: int) -> list[str]:
    """Legacy 6-field @EDG lines omit empty ``at`` before attrs."""
    if nfields == 7 and len(values) == 6:
        return values[:4] + [""] + values[4:]
    return values


def validate_values(tag_def: TagDef, values: list[str], caps: Caps) -> dict[str, str]:
    if tag_def.tag == "EDG":
        values = _coerce_edg_values(values, len(tag_def.fields))
    if len(values) != len(tag_def.fields):
        example = emit_record_line(
            tag_def.tag,
            values[: len(tag_def.fields)] if values else ["id01"],
        )
        raise MemNetError(
            "FIELD_COUNT",
            f"Expected {len(tag_def.fields)} fields for {tag_def.tag} got {len(values)}",
            example=example,
        )
    result: dict[str, str] = {}
    for name, val in zip(tag_def.fields, values, strict=True):
        if "\n" in val or "\r" in val:
            raise MemNetError(
                "newline_in_value",
                "newline in field split into two records",
            )
        if len(val.encode("utf-8")) > caps.max_value_bytes:
            raise MemNetError(
                "limit_exceeded",
                f"value_bytes|{len(val.encode('utf-8'))}/{caps.max_value_bytes}",
            )
        result[name] = val
    validate_id(result["id"])
    if tag_def.tag == "EDG":
        rel = result.get("relation", "")
        if rel and not _REL_RE.match(rel):
            raise MemNetError(
                "invalid_relation",
                f"relation {rel} must match {RELATION_PATTERN}",
            )
    return result


def parse_line(line: str, tag_map: TagMap, caps: Caps | None = None) -> Record:
    caps = caps or Caps()
    if len(line.encode("utf-8")) > caps.max_line_bytes:
        raise MemNetError(
            "limit_exceeded",
            f"line_bytes|{len(line.encode('utf-8'))}/{caps.max_line_bytes}",
        )
    try:
        tag, payload = parse_tag_line(line.strip())
    except ValueError as exc:
        raise MemNetError("invalid_line", str(exc)) from exc
    if tag in RESERVED_TAGS:
        raise MemNetError("reserved_tag", f"tag {tag} is reserved")
    tag_def = tag_map.get(tag)
    if not tag_def:
        known = ",".join(tag_map.tag_names())
        raise MemNetError("unknown_tag", f"{tag} not in tagMap known: {known}")
    values = split_payload(payload)
    fields = validate_values(tag_def, values, caps)
    return Record(tag=tag, fields=fields)


def example_ingest_line(tag_def: TagDef) -> str:
    samples = {
        "id": "X01",
        "src": "N01",
        "dist": "PLR01",
        "relation": "links",
        "at": "",
        "attrs": "",
        "recycle": "persistent",
        "name": "Example",
        "world": "World",
        "economy": "Economy",
        "identity": "Role",
        "core_ability": "Ability",
        "crisis": "Crisis",
        "round": "1",
        "time": "Day 1",
        "deficit": "0",
        "revenue": "0",
        "chaos": "0",
        "exchange_rate": "1:1",
        "wealth": "0",
        "cashflow": "0",
        "monopoly": "0",
        "reputation": "0",
        "inventory": "none",
        "type": "none",
        "location": "none",
        "profit": "0",
        "employees": "0",
        "traits": "trait",
        "corruption": "0",
        "craft": "skill",
        "funding_gap": "0",
        "status": "active",
        "goal": "goal",
        "deadline": "1",
        "domain": "domain",
        "effect": "effect",
        "cost": "0",
        "price": "0",
        "cycle": "on_read",
        "mechanism": "include",
        "constraint": "policy text",
    }
    values = [samples.get(f, f"val_{f}") for f in tag_def.fields]
    if tag_def.fields[0] == "id":
        values[0] = f"{tag_def.tag}01" if tag_def.tag != "EDG" else "E01"
    return emit_record_line(tag_def.tag, values)
