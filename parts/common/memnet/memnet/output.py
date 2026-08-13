"""Wire-format stdout/stderr formatters."""

from __future__ import annotations

import sys

from memnet.exceptions import MemNetError
from memnet.models import Record, TagDef, TagMap
from memnet.wire import join_payload

_MAX_WRN = 12


def reset_warn_budget() -> None:
    global _WARN_EMITTED
    _WARN_EMITTED = 0


def emit_stdout(line: str) -> None:
    sys.stdout.write(line + "\n")


def emit_stderr(line: str) -> None:
    sys.stderr.write(line + "\n")


def format_err(code: str, message: str, example: str | None = None) -> str:
    msg = message.replace("|", " ")
    if example:
        return f"@ERR: {code}|{msg}|{example}"
    return f"@ERR: {code}|{msg}"


def format_wrn(code: str, message: str, example: str | None = None) -> str | None:
    global _WARN_EMITTED
    if _WARN_EMITTED >= _MAX_WRN:
        return None
    _WARN_EMITTED += 1
    msg = message.replace("|", " ")
    if example:
        return f"@WRN: {code}|{msg}|{example}"
    return f"@WRN: {code}|{msg}"


def emit_err(error: MemNetError) -> None:
    emit_stderr(format_err(error.code, error.message, error.example))


def emit_wrn(code: str, message: str, example: str | None = None) -> None:
    line = format_wrn(code, message, example)
    if line:
        emit_stderr(line)


def emit_session(
    session_id: str,
    field2: str,
    field3: str = "",
    field4: str = "",
) -> None:
    parts = [session_id, field2]
    if field3:
        parts.append(field3)
    if field4:
        parts.append(field4)
    emit_stdout(f"@SESSION: {'|'.join(parts)}")


def emit_record_line(tag: str, values: list[str]) -> str:
    payload = join_payload(values)
    return f"@{tag}: {payload}"


def emit_record(record: Record, tag_map: TagMap) -> str:
    tag_def = tag_map.get(record.tag)
    if not tag_def:
        values = [record.fields.get("id", "")]
        values.extend(v for k, v in record.fields.items() if k != "id")
        return emit_record_line(record.tag, values)
    values = [record.fields.get(f, "") for f in tag_def.fields]
    return emit_record_line(record.tag, values)


def parse_err_line(line: str) -> tuple[str, str, str | None]:
    if not line.startswith("@ERR: "):
        raise ValueError("not an ERR line")
    rest = line[6:]
    parts = rest.split("|", 2)
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], parts[1], None
    return parts[0], "", None


def values_from_record(record: Record, tag_def: TagDef) -> list[str]:
    return [record.fields.get(f, "") for f in tag_def.fields]
