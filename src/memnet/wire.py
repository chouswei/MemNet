"""Wire-format line parsing and emission."""

from __future__ import annotations

import re


def split_payload(payload: str) -> list[str]:
    fields: list[str] = []
    current: list[str] = []
    i = 0
    while i < len(payload):
        ch = payload[i]
        if ch == "\\" and i + 1 < len(payload):
            nxt = payload[i + 1]
            if nxt in ("|", "\\"):
                current.append(nxt)
                i += 2
                continue
        if ch == "|":
            fields.append("".join(current))
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1
    fields.append("".join(current))
    return fields


def join_payload(fields: list[str]) -> str:
    out: list[str] = []
    for field in fields:
        escaped = field.replace("\\", "\\\\").replace("|", "\\|")
        out.append(escaped)
    return "|".join(out)


def parse_tag_line(line: str) -> tuple[str, str]:
    m = re.match(r"^@([A-Za-z0-9_]+):\s*(.*)$", line.strip())
    if not m:
        raise ValueError("invalid wire line")
    return m.group(1).upper(), m.group(2)


def emit_record_line(tag: str, values: list[str]) -> str:
    return f"@{tag}: {join_payload(values)}"
