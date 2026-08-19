"""Tier A MemNet agent-surface parser / emit / lint (R1 atoms-only).

**Retired from product accept (ADR-001 M2).** MutateGate rejects Tier A /
Layer batches with ``legacy_dialect_retired``. Kept for archive tests and
historical fixtures under ``docs/grammar/archive/``. Agent wire = GQL
(``memnet.gql_codec.GqlCodec``).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# Soft lint: atom / field value character budget (R1 prompt discipline).
SOFT_ATOM_CHARS = 80
PROSE_WORD_HINT = 8  # many whitespace-separated tokens → likely prose blob


class Op(str, Enum):  # noqa: UP042
    CREATE = "+"
    PATCH = "~"
    DROP = "-"
    LAW = "LAW"
    PRESENT = ""  # pin-map display: bare atom (no mutate op)


@dataclass
class Field:
    key: str
    op: str  # "=", "+=", "-="
    value: str


@dataclass
class NodeRec:
    op: Op
    kind: str
    id: str  # optional nickname; empty when omitted
    fields: list[Field] = field(default_factory=list)
    raw: str = ""
    match_props: dict[str, str] = field(default_factory=dict)
    # SameThingAbsorb Commit (MATCH (a),(b) SET a += b). Not a product verb.
    same_thing: bool = False
    absorb_kind: str = ""
    absorb_match_props: dict[str, str] = field(default_factory=dict)


@dataclass
class EdgeRec:
    op: Op
    edge_id: str | None  # optional nickname; empty/None when omitted
    frm: str
    rel: str
    to: str
    fields: list[Field] = field(default_factory=list)
    raw: str = ""
    frm_label: str = ""
    to_label: str = ""
    frm_props: dict[str, str] = field(default_factory=dict)
    to_props: dict[str, str] = field(default_factory=dict)


@dataclass
class Section:
    name: str
    raw: str = ""


@dataclass
class SchemaRec:
    """Session schema declaration (session_open --map-file), not a graph node."""

    kind: str
    fields: list[Field] = field(default_factory=list)
    raw: str = ""

    @property
    def field_names(self) -> list[str]:
        for f in self.fields:
            if f.key == "fields" and f.op == "=":
                return [p for p in f.value.split() if p]
        return []


@dataclass
class Document:
    items: list[Section | NodeRec | EdgeRec | SchemaRec] = field(default_factory=list)


@dataclass
class LintIssue:
    severity: str  # "error" | "warning"
    code: str
    message: str
    line: int | None = None


class ParseError(Exception):
    def __init__(self, message: str, line: int | None = None) -> None:
        super().__init__(message)
        self.line = line


_RE_SECTION = re.compile(r"^##\s+([A-Za-z][A-Za-z0-9_ ]*)\s*$")
_RE_ARROW = re.compile(
    r"^(\+|\~)\s+"
    r"(?:(NEW|[A-Za-z_][A-Za-z0-9_]*)\s+)?"
    r"\[(NEW|[A-Za-z_][A-Za-z0-9_]*)\]\s*"
    r"--\(([a-z][a-z0-9_]*)\)-->\s*"
    r"\[(NEW|[A-Za-z_][A-Za-z0-9_]*)\]\s*"
    r"(.*)$"
)
_RE_CREATE_NODE = re.compile(r"^\+\s+([A-Z][A-Z0-9_]*)\s+\[(NEW|[A-Za-z_][A-Za-z0-9_]*)\]\s*(.*)$")
_RE_PATCH_NODE = re.compile(r"^\~\s+\[([A-Za-z_][A-Za-z0-9_]*)\]\s*(.*)$")
_RE_PATCH_EDGE_BARE = re.compile(r"^\~\s+([A-Za-z_][A-Za-z0-9_]*)\s*(.*)$")
_RE_DROP = re.compile(r"^-\s+([A-Za-z_][A-Za-z0-9_]*)\s*$")
_RE_LAW = re.compile(r"^(LAW[A-Za-z0-9_.-]+)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(.*)$")
# Pin-map present (MemNet->LLM): no leading +/~/-
_RE_PRESENT_NODE = re.compile(r"^([A-Z][A-Z0-9_]*)\s+\[([A-Za-z_][A-Za-z0-9_]*)\]\s*(.*)$")
_RE_PRESENT_EDGE = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)\s+"
    r"\[([A-Za-z_][A-Za-z0-9_]*)\]\s*"
    r"--\(([a-z][a-z0-9_]*)\)-->\s*"
    r"\[([A-Za-z_][A-Za-z0-9_]*)\]\s*"
    r"(.*)$"
)
_RE_SCHEMA = re.compile(
    r"^SCHEMA\s+([A-Za-z_][A-Za-z0-9_]*)\s*(.*)$",
    re.IGNORECASE,
)


def _unescape_string(body: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(body):
        if body[i] == "\\" and i + 1 < len(body):
            nxt = body[i + 1]
            mapping = {"\\": "\\", '"': '"', "n": "\n", "r": "\r", "t": "\t"}
            if nxt not in mapping:
                raise ParseError(f"unknown string escape \\{nxt}")
            out.append(mapping[nxt])
            i += 2
            continue
        out.append(body[i])
        i += 1
    return "".join(out)


def _escape_string(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _parse_fields(tail: str, line_no: int) -> list[Field]:
    """Parse ';'-joined fields. R1: values are atoms (no nested list/map)."""
    tail = tail.strip()
    if not tail:
        return []
    if tail.startswith(";"):
        tail = tail[1:].strip()
    fields: list[Field] = []
    # Split on ' ; ' / ';' outside quotes
    parts = _split_fields(tail)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = re.match(
            r"^([A-Za-z_][A-Za-z0-9_]*)\s*(\+=|-=|=)\s*(.*)$",
            part,
            re.DOTALL,
        )
        if not m:
            raise ParseError(f"bad field: {part!r}", line_no)
        key, op, raw_val = m.group(1), m.group(2), m.group(3).strip()
        if op in ("+=", "-="):
            if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", raw_val):
                raise ParseError(f"{op} requires number, got {raw_val!r}", line_no)
            fields.append(Field(key=key, op=op, value=raw_val))
            continue
        fields.append(Field(key=key, op="=", value=_parse_atom(raw_val, line_no)))
    return fields


def _split_fields(s: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    in_str = False
    while i < len(s):
        ch = s[i]
        if in_str:
            buf.append(ch)
            if ch == "\\" and i + 1 < len(s):
                buf.append(s[i + 1])
                i += 2
                continue
            if ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            buf.append(ch)
            i += 1
            continue
        if ch == ";":
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return parts


def _parse_atom(raw: str, line_no: int) -> str:
    raw = raw.strip()
    if not raw:
        raise ParseError("empty atom", line_no)
    if raw.startswith('"'):
        if not raw.endswith('"') or len(raw) < 2:
            raise ParseError(f"unterminated string: {raw!r}", line_no)
        return _unescape_string(raw[1:-1])
    # bare atom / number / IDENT / NEW — reject ';'
    if ";" in raw:
        raise ParseError("'; ';' in bare atom (R1 atoms-only)", line_no)
    return raw


def _law_fields(first_key: str, rest: str, line_no: int) -> list[Field]:
    """LAW line: first field already started (no leading ';')."""
    rest = rest.strip()
    if rest.startswith(";"):
        combined = f"{first_key}{rest}"
    elif rest:
        # rest begins with =value ; more…
        if rest.startswith(("=", "+=", "-=")):
            combined = f"{first_key}{rest}"
        else:
            combined = f"{first_key} {rest}"
    else:
        raise ParseError("LAW line missing field value", line_no)
    return _parse_fields(combined, line_no)


def parse_line(line: str, line_no: int = 1) -> Section | NodeRec | EdgeRec | SchemaRec | None:
    s = line.strip()
    if not s:
        return None
    if s.startswith("#") and not s.startswith("##"):
        return None

    m = _RE_SECTION.match(s)
    if m:
        return Section(name=m.group(1).strip(), raw=s)

    m = _RE_SCHEMA.match(s)
    if m:
        kind, tail = m.groups()
        fields = _parse_fields(tail or "", line_no)
        if not any(f.key == "fields" and f.op == "=" for f in fields):
            raise ParseError(f"SCHEMA {kind} requires fields=", line_no)
        names = []
        for f in fields:
            if f.key == "fields" and f.op == "=":
                names = [p for p in f.value.split() if p]
                break
        if not names:
            raise ParseError(f"SCHEMA {kind} fields= is empty", line_no)
        if names[0] != "id":
            raise ParseError(f"SCHEMA {kind} must start with id field", line_no)
        return SchemaRec(kind=kind.upper(), fields=fields, raw=s)

    m = _RE_DROP.match(s)
    if m:
        return EdgeRec(
            op=Op.DROP,
            edge_id=m.group(1),
            frm="",
            rel="",
            to="",
            raw=s,
        )

    m = _RE_ARROW.match(s)
    if m:
        op_s, eid, frm, rel, to, tail = m.groups()
        op = Op.CREATE if op_s == "+" else Op.PATCH
        if op == Op.PATCH and (eid == "NEW" or frm == "NEW" or to == "NEW"):
            raise ParseError("[NEW] / NEW illegal on patch edge", line_no)
        fields = _parse_fields(tail or "", line_no)
        return EdgeRec(
            op=op,
            edge_id=eid,
            frm=frm,
            rel=rel,
            to=to,
            fields=fields,
            raw=s,
        )

    m = _RE_CREATE_NODE.match(s)
    if m:
        kind, nid, tail = m.groups()
        return NodeRec(
            op=Op.CREATE,
            kind=kind,
            id=nid,
            fields=_parse_fields(tail or "", line_no),
            raw=s,
        )

    m = _RE_PATCH_NODE.match(s)
    if m:
        nid, tail = m.groups()
        if nid == "NEW":
            raise ParseError("[NEW] illegal on patch node", line_no)
        return NodeRec(
            op=Op.PATCH,
            kind="",
            id=nid,
            fields=_parse_fields(tail or "", line_no),
            raw=s,
        )

    m = _RE_PATCH_EDGE_BARE.match(s)
    if m:
        eid, tail = m.groups()
        if eid == "NEW":
            raise ParseError("NEW illegal on bare patch edge", line_no)
        return EdgeRec(
            op=Op.PATCH,
            edge_id=eid,
            frm="",
            rel="",
            to="",
            fields=_parse_fields(tail or "", line_no),
            raw=s,
        )

    m = _RE_LAW.match(s)
    if m:
        law_id, first_key, rest = m.groups()
        # rest is remainder after first key token — usually "=engine ; …"
        fields = _law_fields(first_key, rest, line_no)
        return NodeRec(
            op=Op.LAW,
            kind="LAW",
            id=law_id,
            fields=fields,
            raw=s,
        )

    m = _RE_PRESENT_EDGE.match(s)
    if m:
        eid, frm, rel, to, tail = m.groups()
        if eid == "NEW" or frm == "NEW" or to == "NEW":
            raise ParseError("NEW illegal on pin-map present edge", line_no)
        return EdgeRec(
            op=Op.PRESENT,
            edge_id=eid,
            frm=frm,
            rel=rel,
            to=to,
            fields=_parse_fields(tail or "", line_no),
            raw=s,
        )

    m = _RE_PRESENT_NODE.match(s)
    if m:
        kind, nid, tail = m.groups()
        if nid == "NEW":
            raise ParseError("[NEW] illegal on pin-map present node", line_no)
        return NodeRec(
            op=Op.PRESENT,
            kind=kind,
            id=nid,
            fields=_parse_fields(tail or "", line_no),
            raw=s,
        )

    raise ParseError(f"unrecognised Tier A line: {s!r}", line_no)


def parse(text: str) -> Document:
    doc = Document()
    for i, line in enumerate(text.splitlines(), start=1):
        try:
            item = parse_line(line, i)
        except ParseError as e:
            if e.line is None:
                e.line = i
            raise
        if item is not None:
            doc.items.append(item)
    return doc


def _format_atom(value: str) -> str:
    needs_quote = bool(
        re.search(r'[\s;"\\]', value)
        or value == ""
        or not re.fullmatch(r"[A-Za-z0-9_./+-]+(?:[ \t]+[A-Za-z0-9_./+-]+)*", value)
    )
    # Prefer bare when safe (multi-word without specials already allowed by BARE_ATOM).
    if re.fullmatch(r"[A-Za-z0-9_./+-]+(?:[ \t]+[A-Za-z0-9_./+-]+)*", value):
        return value
    if needs_quote or "\\" in value or '"' in value:
        return f'"{_escape_string(value)}"'
    return value


def _format_fields(fields: list[Field]) -> str:
    if not fields:
        return ""
    bits: list[str] = []
    for f in fields:
        if f.op in ("+=", "-="):
            bits.append(f"{f.key}{f.op}{f.value}")
        else:
            bits.append(f"{f.key}={_format_atom(f.value)}")
    return " ; ".join(bits)


def emit_item(item: Section | NodeRec | EdgeRec | SchemaRec) -> str:
    if isinstance(item, Section):
        return f"## {item.name}"
    if isinstance(item, SchemaRec):
        fields = _format_fields(item.fields)
        return f"SCHEMA {item.kind} ; {fields}" if fields else f"SCHEMA {item.kind}"
    if isinstance(item, NodeRec):
        if item.op == Op.LAW:
            body = _format_fields(item.fields)
            return f"{item.id} {body}" if body else item.id
        if item.op == Op.PRESENT:
            head = f"{item.kind} [{item.id}]"
        elif item.op == Op.CREATE:
            head = f"+ {item.kind} [{item.id}]"
        else:
            head = f"~ [{item.id}]"
        fields = _format_fields(item.fields)
        return f"{head} ; {fields}" if fields else head
    # Edge
    assert isinstance(item, EdgeRec)
    if item.op == Op.DROP:
        return f"- {item.edge_id}"
    if item.op == Op.PATCH and not item.frm:
        head = f"~ {item.edge_id}"
        fields = _format_fields(item.fields)
        return f"{head} ; {fields}" if fields else head
    if item.op == Op.PRESENT:
        head = f"{item.edge_id} [{item.frm}] --({item.rel})--> [{item.to}]"
    else:
        op = "+" if item.op == Op.CREATE else "~"
        if item.edge_id:
            head = f"{op} {item.edge_id} [{item.frm}] --({item.rel})--> [{item.to}]"
        else:
            head = f"{op} [{item.frm}] --({item.rel})--> [{item.to}]"
    fields = _format_fields(item.fields)
    return f"{head} ; {fields}" if fields else head


def emit(doc: Document) -> str:
    lines = [emit_item(it) for it in doc.items]
    return "\n".join(lines) + ("\n" if lines else "")


def lint(doc: Document) -> list[LintIssue]:
    """Soft lint for R1: invent ids, prose blobs, NEW on wrong ops, pipe dialect."""
    issues: list[LintIssue] = []
    for it in doc.items:
        if isinstance(it, Section):
            continue
        if isinstance(it, SchemaRec):
            names = it.field_names
            if not names:
                issues.append(
                    LintIssue("error", "schema_fields", f"SCHEMA {it.kind} missing fields=")
                )
            elif names[0] != "id":
                issues.append(
                    LintIssue(
                        "error",
                        "schema_id_first",
                        f"SCHEMA {it.kind} must start with id",
                    )
                )
            if it.raw.startswith("@"):
                issues.append(LintIssue("error", "pipe_dialect", "pipe TagMap on SCHEMA surface"))
            continue
        if isinstance(it, NodeRec):
            if it.op == Op.CREATE and it.id != "NEW":
                # Warm/response may show ground ids; invent pattern flagged only for
                # suspicious client-minted shapes when kind create without NEW.
                # Golden: invent fixtures are mutate batches — flag non-NEW creates
                # that look invented (contain _rand, _maybe, or mixed guess tokens).
                if re.search(r"(?i)(_rand|_maybe|guess)", it.id):
                    issues.append(
                        LintIssue(
                            "error",
                            "invent_id",
                            f"invented create id [{it.id}]; use [NEW]",
                        )
                    )
                elif not re.fullmatch(r"[A-Z][A-Z0-9_]*\d+[A-Za-z0-9_]*|[A-Z][A-Za-z0-9_]*", it.id):
                    pass
                # Also flag any create with ground id that looks random (C_rand style)
                if (
                    "_" in it.id
                    and it.id not in ("NEW",)
                    and re.search(r"(?i)rand|maybe|tmp|guess|todo", it.id)
                ):
                    issues.append(
                        LintIssue(
                            "error",
                            "invent_id",
                            f"invented create id [{it.id}]; use [NEW]",
                        )
                    )
            if it.op == Op.PATCH and it.id == "NEW":
                issues.append(LintIssue("error", "new_on_patch", "[NEW] illegal on update/settle"))
            if it.op == Op.CREATE:
                for f in it.fields:
                    if f.op in ("+=", "-="):
                        issues.append(
                            LintIssue(
                                "error",
                                "numeric_op_on_create",
                                f"{f.key}{f.op} illegal on create; use =",
                            )
                        )
            for f in it.fields:
                issues.extend(_lint_value(f.value, it.raw, field_key=f.key))
            # Pipe dialect leaked into values
            if it.raw.startswith("@"):
                issues.append(LintIssue("error", "pipe_dialect", "Tier B pipe on agent surface"))
        elif isinstance(it, EdgeRec):
            if it.op == Op.CREATE:
                for f in it.fields:
                    if f.op in ("+=", "-="):
                        issues.append(
                            LintIssue(
                                "error",
                                "numeric_op_on_create",
                                f"{f.key}{f.op} illegal on create; use =",
                            )
                        )
                for end in (it.frm, it.to):
                    if end == "NEW":
                        issues.append(
                            LintIssue(
                                "warning",
                                "new_endpoint",
                                "NEW as edge endpoint is open; "
                                "prefer known ids after create response",
                            )
                        )
            for f in it.fields:
                issues.extend(_lint_value(f.value, it.raw, field_key=f.key))
    return _dedupe(issues)


def _lint_value(value: str, raw: str, *, field_key: str | None = None) -> list[LintIssue]:
    issues: list[LintIssue] = []
    if len(value) > SOFT_ATOM_CHARS:
        issues.append(
            LintIssue(
                "warning",
                "fat_field",
                f"atom length {len(value)} > {SOFT_ATOM_CHARS} (soft @WRN)",
            )
        )
    words = value.split()
    if len(words) >= PROSE_WORD_HINT:
        issues.append(
            LintIssue(
                "error",
                "prose_blob",
                f"value looks like prose ({len(words)} words); atomise",
            )
        )
    # Formula EDGE src_fields is a comma-separated name list (memnet-field-formulas.md).
    if (
        field_key != "src_fields"
        and "," in value
        and re.search(r"[A-Za-z0-9_]+,[A-Za-z0-9_]", value)
    ):
        issues.append(
            LintIssue(
                "error",
                "embedded_rel",
                "comma id-list in field — use EDGE lines (R1 SET→EDGE)",
            )
        )
    if "<" in value and ">" in value and len(value) > 40:
        issues.append(LintIssue("error", "corpus_dump", "value looks like corpus / markup dump"))
    if raw.lstrip().startswith("@") or "|persistent" in raw or re.match(r"^@[A-Z]+:", raw):
        issues.append(LintIssue("error", "pipe_dialect", "pipe row on agent surface"))
    return issues


def _dedupe(issues: list[LintIssue]) -> list[LintIssue]:
    seen: set[tuple[str, str]] = set()
    out: list[LintIssue] = []
    for i in issues:
        key = (i.code, i.message)
        if key in seen:
            continue
        seen.add(key)
        out.append(i)
    return out


def expect_from_text(text: str) -> str | None:
    """Read '# expect: parse-reject|lint-reject|parse-ok' from fixture header."""
    for line in text.splitlines()[:8]:
        m = re.match(r"^#\s*expect:\s*(\S+)", line.strip(), re.I)
        if m:
            return m.group(1).lower()
    return None


def iter_example_files(examples_dir: Path) -> Iterator[Path]:
    yield from sorted(examples_dir.glob("*.txt"))


def round_trip_ok(text: str) -> bool:
    doc = parse(text)
    emitted = emit(doc)
    doc2 = parse(emitted)
    return emit(doc2) == emitted
