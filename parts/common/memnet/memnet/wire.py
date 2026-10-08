"""Wire-format line parsing and emission."""

from __future__ import annotations

import re

# Python str.splitlines() separators. Snapshot records split on LF only;
# these MUST be escaped so load cannot FIELD_COUNT-split a property.
_SPLITLINES_ESC: dict[str, str] = {
    "\n": "\\n",
    "\r": "\\r",
    "\x0b": "\\v",
    "\x0c": "\\f",
    "\x1c": "\\x1c",
    "\x1d": "\\x1d",
    "\x1e": "\\x1e",
    "\x85": "\\x85",
    "\u2028": "\\u2028",
    "\u2029": "\\u2029",
}
SPLITLINES_SEPARATORS: tuple[str, ...] = tuple(_SPLITLINES_ESC)
_HEX = frozenset("0123456789abcdefABCDEF")


def split_snapshot_lines(text: str) -> list[str]:
    """Record split for leftover snapshots: LF only, optional CRLF trim.

    MUST NOT use str.splitlines() — that splits on CR / VT / FF / NEL / LS / PS
    before unescape and yields FIELD_COUNT.
    """
    if text.endswith("\n"):
        text = text[:-1]
    lines: list[str] = []
    for raw in text.split("\n"):
        if raw.endswith("\r"):
            raw = raw[:-1]
        lines.append(raw)
    return lines


def split_payload(payload: str) -> list[str]:
    if "\\" not in payload:
        return payload.split("|")
    fields: list[str] = []
    current: list[str] = []
    i = 0
    n = len(payload)
    while i < n:
        ch = payload[i]
        if ch == "\\" and i + 1 < n:
            nxt = payload[i + 1]
            if nxt in ("|", "\\"):
                current.append(nxt)
                i += 2
                continue
            if nxt == "n":
                current.append("\n")
                i += 2
                continue
            if nxt == "r":
                current.append("\r")
                i += 2
                continue
            if nxt == "v":
                current.append("\x0b")
                i += 2
                continue
            if nxt == "f":
                current.append("\x0c")
                i += 2
                continue
            if nxt == "x" and i + 3 < n:
                hx = payload[i + 2 : i + 4]
                if hx[0] in _HEX and hx[1] in _HEX:
                    current.append(chr(int(hx, 16)))
                    i += 4
                    continue
            if nxt == "u" and i + 5 < n:
                hx = payload[i + 2 : i + 6]
                if all(c in _HEX for c in hx):
                    current.append(chr(int(hx, 16)))
                    i += 6
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
        escaped: list[str] = []
        for ch in field:
            if ch == "\\":
                escaped.append("\\\\")
            elif ch == "|":
                escaped.append("\\|")
            elif ch in _SPLITLINES_ESC:
                escaped.append(_SPLITLINES_ESC[ch])
            else:
                escaped.append(ch)
        out.append("".join(escaped))
    return "|".join(out)


def parse_tag_line(line: str) -> tuple[str, str]:
    m = re.match(r"^@([A-Za-z0-9_]+):\s*(.*)$", line.strip())
    if not m:
        raise ValueError("invalid wire line")
    return m.group(1).upper(), m.group(2)


def emit_record_line(tag: str, values: list[str]) -> str:
    return f"@{tag}: {join_payload(values)}"
